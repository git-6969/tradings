import sys
import time
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit,
    QHBoxLayout, QDesktopWidget, QLabel, QLineEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QTextCursor, QDoubleValidator

# --- 주요 설정 변수 ---
USE_MARKET_PRICE = False  # True: 시장가 청산 시도, False: 지정가 청산 시도 (현재가 기반 조정)

# ClearThread 청산 주문 시 사용
DEFAULT_PRICE_AGGRESSION_OFFSET_FUTURES = 0.05  # 선물 청산 시 적용할 기본 가격 오프셋 (1칸 기준)
DEFAULT_PRICE_AGGRESSION_OFFSET_OPTIONS = 0.01  # 옵션 청산 시 적용할 기본 가격 오프셋 (1칸 기준)
MINIMUM_LIQUIDATION_ORDER_PRICE = 0.01  # 옵션 청산 주문 시 최소 가격 (음수/0 방지)

# ⭐ 청산 주문 시 공격성 조절을 위한 "틱 배수" (몇 칸) ⭐
# 예: 1 이면 기본 오프셋(위에서 정의한 값)만큼, 2 이면 기본 오프셋의 2배만큼 가격 조정
LIQUIDATION_AGGRESSION_TICK_MULTIPLIER = 3

# ClearThread 내부 루프 및 API 호출 간격
CLEAR_THREAD_API_CALL_INTERVAL_SECONDS = 0.3  # 청산 스레드 내 개별 주문/취소 후 대기 시간 (초)
CLEAR_THREAD_MAIN_LOOP_INTERVAL_SECONDS = 7  # 청산 스레드 메인 루프 반복 대기 시간 (초)

# TradingApp의 목표 추적 타이머 간격
TARGET_TRACKING_TIMER_INTERVAL_MS = 5000  # 계좌 수익률 추적 및 자동 청산 확인 간격 (밀리초)
# --- 주요 설정 변수 끝 ---

# Comms_Class (사용자 제공 버전 유지)
try:
    from Comms_Class import InitPlusCheck, CpFutureBalance, CpFutureNContract, CpFutureOptionOrder, CpFutureOptionCancel
except ImportError:
    print("경고: Comms_Class.py를 찾을 수 없습니다. 테스트용 더미 구현을 사용합니다.")
    import random


    def InitPlusCheck():
        return True


    class CpFutureBalance:
        def request(self, balanceList_ref):
            balanceList_ref.clear()
            if random.choice([True, False, True, True]):
                num_positions = random.randint(0, 2)
                for i in range(num_positions):
                    avg_price = round(100.00 + random.uniform(-10.0, 10.0), 4)
                    qty = random.randint(1, 5)
                    multiplier = 250000 / 100
                    purchase_amount = avg_price * qty * multiplier
                    current_price_for_calc = round(avg_price + random.uniform(-5.0, 5.0), 2)
                    pl = (current_price_for_calc - avg_price) * qty * multiplier
                    balanceList_ref.append({
                        '종목명': f'DummyStock{i + 1}', '코드': f'A000{i + 1}', '잔고수량': qty,
                        '잔고구분': random.choice(['매수', '매도']),
                        '평균단가': str(avg_price), '현재가': str(current_price_for_calc),
                        '평가손익': str(int(pl)),
                        '매입금액': str(int(purchase_amount if purchase_amount > 0 else 1000000)),
                    })
            return True


    class CpFutureNContract:
        _dummy_orders_store = []

        def request(self, nContractList_ref): nContractList_ref.clear();[nContractList_ref.append(o.copy()) for o in
                                                                         CpFutureNContract._dummy_orders_store]; return True


    class CpFutureOptionOrder:
        def _add_to_pending(self, c, p, q, ot, on):
            if p != 0 and random.random() < 0.5: CpFutureNContract._dummy_orders_store.append(
                {'주문번호': on, '코드': c, '주문구분': ot, '주문가격': str(p), '주문수량': q, '잔량': q, '종목명': f'Sim{c[-4:]}'})

        def sellOrder(self, c, p, q, rd):
            on = '';
            if p == 0 or random.random() < 0.8: on = str(random.randint(10000, 99999));self._add_to_pending(c, p, q,
                                                                                                            '매도', on);
            rd['주문번호'] = on;return True
            rd['오류'] = '주문실패(더미)';
            return False

        def buyOrder(self, c, p, q, rd):
            on = '';
            if p == 0 or random.random() < 0.8: on = str(random.randint(10000, 99999));self._add_to_pending(c, p, q,
                                                                                                            '매수', on);
            rd['주문번호'] = on;return True
            rd['오류'] = '주문실패(더미)';
            return False


    class CpFutureOptionCancel:
        def cancel_order(self, on, c, q):
            olen = len(CpFutureNContract._dummy_orders_store);
            CpFutureNContract._dummy_orders_store = [o for o in CpFutureNContract._dummy_orders_store if
                                                     o['주문번호'] != on];
            return len(CpFutureNContract._dummy_orders_store) < olen


class LogThread(QThread):
    log_signal = pyqtSignal(str, bool)

    def emit_log(self, message, bold=False): current_time = datetime.now().strftime("%H:%M:%S"); self.log_signal.emit(
        f"[{current_time}] {message}", bold)


class BalanceThread(LogThread):
    def run(self):
        self.emit_log("\n=== 계좌 내역 조회 ===", False)
        objBalance = CpFutureBalance();
        balanceList = []
        if objBalance.request(balanceList):
            if not balanceList: self.emit_log("\ud83d\udcdd 현재 보유한 포지션이 없습니다.", False); return
            for item in balanceList:
                formatted_items = [];
                v_int_pl = 0
                for k, v in item.items():
                    if k == '평가손익':
                        try:
                            v_int_pl = int(float(v)); v_formatted = f"{v_int_pl:,}"
                        except:
                            v_formatted = str(v)
                        color = 'red' if v_int_pl > 0 else 'blue' if v_int_pl < 0 else 'black';
                        formatted_items.append(f"<span style='color:{color}'>[{k}] {v_formatted}</span>")
                    elif k == '평균단가':
                        try:
                            v_float = float(v); v_str = f"{v_float:.4f}"
                        except ValueError:
                            v_str = str(v)
                        formatted_items.append(f"[{k}] {v_str}")
                    elif k in ['수익률', '평가수익률']:
                        try:
                            v_float = float(v); v_str = f"{v_float:.2f}%"
                        except:
                            v_str = str(v)
                        formatted_items.append(f"[{k}] {v_str}")
                    elif k in ['매입금액', '평가금액']:
                        try:
                            v_int_amount = int(float(v)); v_str = f"{v_int_amount:,}"
                        except:
                            v_str = str(v)
                        formatted_items.append(f"[{k}] {v_str}")
                    else:
                        formatted_items.append(f"[{k}] {str(v)}")
                self.emit_log(" | ".join(formatted_items), False)
        else:
            self.emit_log("잔고 조회 실패", False)


class NContractThread(LogThread):
    def run(self):
        self.emit_log("\n=== 미체결 조회 ===", False)
        objNContract = CpFutureNContract();
        nContractList = []
        if objNContract.request(nContractList):
            if not nContractList: self.emit_log("\ud83d\udcdd 현재 미체결 주문이 없습니다.", False); return
            for item in nContractList: self.emit_log(" | ".join([f"[{k}] {v}" for k, v in item.items()]), False)
        else:
            self.emit_log("미체결 조회 실패", False)


class ClearThread(LogThread):
    def run(self):
        self.emit_log("\n=== 계좌 내 모든 종목 청산 시작 ===", False)
        objOrder = CpFutureOptionOrder()
        objBalance = CpFutureBalance()
        objNContract = CpFutureNContract()
        objCancel = CpFutureOptionCancel()

        while True:
            self.emit_log("\n\ud83d\udccc 미체결 주문 정리 및 청산 시도 중...", False)
            try:
                while True:
                    nContractList = []
                    if objNContract.request(nContractList) and nContractList:
                        self.emit_log(f"\ud83d\udea9 미체결 {len(nContractList)}건 발견 → 취소 시도", False)
                        for order in nContractList:
                            order_no = order['주문번호'];
                            code = order['코드'];
                            qty = order['잔량']
                            if objCancel.cancel_order(order_no, code, qty):
                                self.emit_log(f"\ud83d\udd01 취소 완료: {code} / 주문번호 {order_no}", False)
                            else:
                                self.emit_log(f"⚠️ 취소 실패: {code} / 주문번호 {order_no}", False)
                            time.sleep(CLEAR_THREAD_API_CALL_INTERVAL_SECONDS)
                    else:
                        self.emit_log("✅ 모든 미체결 주문 정리 완료 (또는 없음)", False);
                        break

                balanceList = []
                if objBalance.request(balanceList):
                    if not balanceList:
                        self.emit_log("✅ 모든 포지션 청산 완료 (또는 보유 포지션 없음)!", False);
                        return

                    self.emit_log(f"🔍 현재 잔고 스냅샷 ({len(balanceList)}개 종목):", False)
                    for item in balanceList:
                        self.emit_log(f"    - {item.get('종목명', item.get('코드'))}: 수량 {item['잔고수량']}, 포지션 {item['잔고구분']}",
                                      False)

                    for item in balanceList:
                        code = item['코드']
                        qty_str = item.get('잔고수량', "0")
                        price_str = item.get('현재가', "0")
                        position_type = item['잔고구분']

                        try:
                            qty = int(qty_str)
                            current_price_float = float(price_str)
                        except ValueError:
                            self.emit_log(f"⚠️ {code}의 수량({qty_str}) 또는 현재가({price_str}) 값 오류. 청산 건너뜁니다.", True)
                            continue

                        if qty <= 0:
                            continue

                        # ⭐ 상품 코드에 따른 기본 오프셋 결정 및 "틱 배수" 적용 ⭐
                        base_offset_for_item = DEFAULT_PRICE_AGGRESSION_OFFSET_FUTURES
                        is_option = isinstance(code, str) and (code.startswith('2') or code.startswith('3'))
                        if is_option:
                            base_offset_for_item = DEFAULT_PRICE_AGGRESSION_OFFSET_OPTIONS

                        # 최종 공격성 오프셋 = 기본 오프셋 * 틱 배수
                        actual_price_aggression_offset = base_offset_for_item * LIQUIDATION_AGGRESSION_TICK_MULTIPLIER
                        # ⭐ 동적 오프셋 계산 끝 ⭐

                        order_price_calculated = 0.0
                        action = ""

                        if position_type == '매수':
                            order_price_calculated = current_price_float - actual_price_aggression_offset  # 수정된 오프셋 사용
                            action = "매도"
                        elif position_type == '매도':
                            order_price_calculated = current_price_float + actual_price_aggression_offset  # 수정된 오프셋 사용
                            action = "매수"
                        else:
                            self.emit_log(f"⚠️ {code}의 알 수 없는 포지션 타입: {position_type}", True)
                            continue

                        final_order_price = round(order_price_calculated, 2)

                        if is_option:
                            final_order_price = max(MINIMUM_LIQUIDATION_ORDER_PRICE, final_order_price)
                        elif action == "매도" and final_order_price < MINIMUM_LIQUIDATION_ORDER_PRICE:
                            final_order_price = MINIMUM_LIQUIDATION_ORDER_PRICE

                        price_log_info = f"{final_order_price:.2f}"

                        retData = {}
                        success = False
                        if action == "매도":
                            success = objOrder.sellOrder(code, final_order_price, qty, retData)
                        elif action == "매수":
                            success = objOrder.buyOrder(code, final_order_price, qty, retData)

                        if success:
                            self.emit_log(
                                f"✅ {code} {qty}개 {action} 주문 성공 (주문가격: {price_log_info}, 주문번호: {retData.get('주문번호', 'N/A')})",
                                False)
                        else:
                            error_msg = retData.get('오류', '주문 실패 (상세 정보 없음)')
                            self.emit_log(f"❌ {code} {qty}개 {action} 주문 실패 (주문가격: {price_log_info}): {error_msg}", True)
                        time.sleep(CLEAR_THREAD_API_CALL_INTERVAL_SECONDS)
            except Exception as e:
                self.emit_log(f"🚨 청산 중 예외 발생: {e}", True)

            self.emit_log(f"--- {CLEAR_THREAD_MAIN_LOOP_INTERVAL_SECONDS}초 후 잔고 재확인 및 청산 시도 ---", False)
            time.sleep(CLEAR_THREAD_MAIN_LOOP_INTERVAL_SECONDS)


class TradingApp(QWidget):  # 이하 TradingApp 클래스 및 main 부분은 이전과 동일하게 유지
    def __init__(self):
        super().__init__()
        self.is_target_tracking_active = False
        self.target_tracking_timer = None
        self.profit_target_value = 0.0
        self.loss_target_value = 0.0
        self.balance_thread = None
        self.clear_thread = None
        self.ncontract_thread = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle("계좌 모니터링 및 자동 청산")
        self.resize(1200, 800)
        qr = self.frameGeometry();
        cp = QDesktopWidget().availableGeometry().center();
        qr.moveCenter(cp);
        self.move(qr.topLeft())
        main_layout = QVBoxLayout()

        button_layout = QHBoxLayout()
        self.balance_btn = QPushButton("계좌 조회");
        self.clear_btn = QPushButton("계좌 전종목 청산");
        self.ncontract_btn = QPushButton("미체결 조회")
        button_layout.addWidget(self.balance_btn);
        button_layout.addWidget(self.clear_btn);
        button_layout.addWidget(self.ncontract_btn)
        main_layout.addLayout(button_layout)

        target_tracking_controls_layout = QHBoxLayout()
        target_tracking_controls_layout.addWidget(QLabel("수익 목표(%):"));
        self.profit_target_input = QLineEdit("5.0");
        self.profit_target_input.setValidator(QDoubleValidator(0.01, 1000.0, 2, self));
        self.profit_target_input.setFixedWidth(60);
        target_tracking_controls_layout.addWidget(self.profit_target_input)
        target_tracking_controls_layout.addWidget(QLabel("손실 한도(%):"));
        self.loss_target_input = QLineEdit("3.0");
        self.loss_target_input.setValidator(QDoubleValidator(0.01, 100.0, 2, self));
        self.loss_target_input.setFixedWidth(60);
        target_tracking_controls_layout.addWidget(self.loss_target_input)
        self.target_tracking_button = QPushButton("목표 추적 시작");
        self.target_tracking_button.clicked.connect(self.toggle_target_tracking);
        target_tracking_controls_layout.addWidget(self.target_tracking_button);
        target_tracking_controls_layout.addStretch(1)
        main_layout.addLayout(target_tracking_controls_layout)

        self.output = QTextEdit();
        self.output.setReadOnly(True);
        main_layout.addWidget(self.output, 3)

        self.target_tracking_log_title_label = QLabel("<b>[자동 청산 트래킹 로그]</b>")
        main_layout.addWidget(self.target_tracking_log_title_label)
        self.target_tracking_log_output = QTextEdit();
        self.target_tracking_log_output.setReadOnly(True);
        main_layout.addWidget(self.target_tracking_log_output, 2)

        self.setLayout(main_layout)
        self.balance_btn.clicked.connect(self.run_balance_thread);
        self.clear_btn.clicked.connect(self.run_clear_thread);
        self.ncontract_btn.clicked.connect(self.run_ncontract_thread)
        self.log_to_main_panel(f"<b>애플리케이션 시작됨. 청산 목표 설정 후 추적 시작 가능.</b>", True)

    def log_to_main_panel(self, message, bold=False):
        current_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        if bold:
            formatted_message = f"<b>[{current_time}] {message}</b><br>"
        else:
            formatted_message = f"[{current_time}] {message}<br>"
        self.output.moveCursor(QTextCursor.End);
        self.output.insertHtml(formatted_message)
        scrollbar = self.output.verticalScrollBar();
        if scrollbar: scrollbar.setValue(scrollbar.maximum())

    def toggle_target_tracking(self):
        if not self.is_target_tracking_active:
            try:
                profit_target = float(self.profit_target_input.text());
                loss_target = float(self.loss_target_input.text())
                if profit_target <= 0 or loss_target <= 0: self.log_to_main_panel(
                    "<b>오류: 수익 목표와 손실 한도는 0보다 커야 합니다.</b>", True); return
                self.profit_target_value = profit_target;
                self.loss_target_value = loss_target
            except ValueError:
                self.log_to_main_panel("<b>오류: 유효한 숫자로 목표 수익률/손실 한도를 입력하세요.</b>", True); return
            self.is_target_tracking_active = True;
            self.target_tracking_button.setText("목표 추적 중지");
            self.profit_target_input.setEnabled(False);
            self.loss_target_input.setEnabled(False)
            self.append_to_tracking_panel(
                f"목표 추적 시작됨 (수익: {self.profit_target_value:.2f}%, 손실: -{self.loss_target_value:.2f}%)")
            if self.target_tracking_timer is None: self.target_tracking_timer = QTimer(
                self); self.target_tracking_timer.timeout.connect(self.check_pl_and_trigger_clear)
            self.target_tracking_timer.start(TARGET_TRACKING_TIMER_INTERVAL_MS)
            self.check_pl_and_trigger_clear()
        else:
            self.is_target_tracking_active = False;
            self.target_tracking_button.setText("목표 추적 시작");
            self.profit_target_input.setEnabled(True);
            self.loss_target_input.setEnabled(True)
            if self.target_tracking_timer is not None: self.target_tracking_timer.stop()
            self.append_to_tracking_panel("목표 추적 중지됨.")

    def check_pl_and_trigger_clear(self):
        if not self.is_target_tracking_active: return
        objBalance = CpFutureBalance();
        balanceList = []
        api_call_successful = objBalance.request(balanceList)
        current_pl_ratio_numeric = 0.0;
        message_to_log = "";
        target_hit_and_action_taken = False
        if api_call_successful:
            if not balanceList:
                message_to_log = "보유 포지션 없음 (수익률: <span style='color:black;'>0.00%</span>)"
            else:
                total_pl_amount_num = 0.0;
                total_purchase_amount_num = 0.0;
                position_count = len(balanceList)
                for item in balanceList:
                    try:
                        total_pl_amount_num += float(item.get('평가손익', "0"))
                    except ValueError:
                        pass
                    try:
                        cost = float(item.get('매입금액', "0"))
                        if cost > 0: total_purchase_amount_num += cost
                    except ValueError:
                        pass
                pl_amount_color = 'red' if total_pl_amount_num > 0 else ('blue' if total_pl_amount_num < 0 else 'black')
                pl_amount_html = f"<span style='color:{pl_amount_color};'>{int(total_pl_amount_num):,}</span>"
                purchase_display = f"{int(total_purchase_amount_num):,}"
                if total_purchase_amount_num > 0:
                    current_pl_ratio_numeric = (total_pl_amount_num / total_purchase_amount_num) * 100
                    pl_ratio_color = 'red' if current_pl_ratio_numeric > 0 else (
                        'blue' if current_pl_ratio_numeric < 0 else 'black')
                    pl_ratio_html = f"<span style='color:{pl_ratio_color};'>{current_pl_ratio_numeric:+.2f}%</span>"
                    message_to_log = f"현재 전체 수익률({position_count}개): {pl_ratio_html} (손익: {pl_amount_html} / 매입: {purchase_display})"
                elif total_pl_amount_num != 0 and total_purchase_amount_num == 0:
                    message_to_log = f"현재 전체 수익률({position_count}개): N/A (매입액 0, 손익: {pl_amount_html})"
                else:
                    pl_ratio_html = "<span style='color:black;'>0.00%</span>"; message_to_log = f"현재 전체 수익률({position_count}개): {pl_ratio_html} (손익: {pl_amount_html} / 매입: {purchase_display})"
                if self.is_target_tracking_active:
                    if self.profit_target_value > 0 and current_pl_ratio_numeric >= self.profit_target_value:
                        hit_message = f"수익 목표 [{self.profit_target_value:.2f}%] 달성! (현재: {pl_ratio_html})"
                        self.append_to_tracking_panel(f"<b>{hit_message}</b>");
                        self.log_to_main_panel(f"<b>{hit_message} >> 계좌 전종목 청산을 시도합니다.</b>", True)
                        self.clear_btn.click();
                        target_hit_and_action_taken = True
                    elif self.loss_target_value > 0 and current_pl_ratio_numeric <= -abs(self.loss_target_value):
                        hit_message = f"손실 한도 [{-abs(self.loss_target_value):.2f}%] 도달! (현재: {pl_ratio_html})"
                        self.append_to_tracking_panel(f"<b>{hit_message}</b>");
                        self.log_to_main_panel(f"<b>{hit_message} >> 계좌 전종목 청산을 시도합니다.</b>", True)
                        self.clear_btn.click();
                        target_hit_and_action_taken = True
        else:
            message_to_log = "계좌 정보 조회 실패"
        if not target_hit_and_action_taken and self.is_target_tracking_active:
            self.append_to_tracking_panel(message_to_log)
        elif target_hit_and_action_taken:
            if self.is_target_tracking_active:
                self.is_target_tracking_active = False;
                self.target_tracking_button.setText("목표 추적 시작")
                self.profit_target_input.setEnabled(True);
                self.loss_target_input.setEnabled(True)
                if self.target_tracking_timer is not None: self.target_tracking_timer.stop()
                self.append_to_tracking_panel("목표 도달로 자동 추적 및 청산 시도 후 중지됨.")

    def append_to_tracking_panel(self, message):
        current_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        formatted_message = f"[{current_time}] {message}<br>"
        self.target_tracking_log_output.moveCursor(QTextCursor.End);
        self.target_tracking_log_output.insertHtml(formatted_message)
        scrollbar = self.target_tracking_log_output.verticalScrollBar();
        if scrollbar: scrollbar.setValue(scrollbar.maximum())

    def run_balance_thread(self):
        if hasattr(self,
                   'balance_thread') and self.balance_thread and self.balance_thread.isRunning(): self.log_to_main_panel(
            "이미 계좌 조회 작업이 진행 중입니다.", True); return
        self.balance_thread = BalanceThread();
        self.balance_thread.log_signal.connect(self.log_to_main_panel);
        self.balance_thread.start()

    def run_clear_thread(self):
        if hasattr(self,
                   'clear_thread') and self.clear_thread and self.clear_thread.isRunning(): self.log_to_main_panel(
            "이미 청산 작업이 진행 중입니다.", True); return
        self.clear_thread = ClearThread();
        self.clear_thread.log_signal.connect(self.log_to_main_panel);
        self.clear_thread.start()

    def run_ncontract_thread(self):
        if hasattr(self,
                   'ncontract_thread') and self.ncontract_thread and self.ncontract_thread.isRunning(): self.log_to_main_panel(
            "이미 미체결 조회 작업이 진행 중입니다.", True); return
        self.ncontract_thread = NContractThread();
        self.ncontract_thread.log_signal.connect(self.log_to_main_panel);
        self.ncontract_thread.start()

    def closeEvent(self, event):
        print("애플리케이션 종료 요청...");
        if self.target_tracking_timer and self.target_tracking_timer.isActive(): print(
            "목표 추적 타이머 중지..."); self.target_tracking_timer.stop()
        threads_to_wait = []
        for attr_name in ['balance_thread', 'clear_thread', 'ncontract_thread']:
            thread = getattr(self, attr_name, None)
            if thread and thread.isRunning(): threads_to_wait.append(thread)
        for thread in threads_to_wait:
            print(f"{thread.__class__.__name__} 종료 대기...");
            thread.wait(1000)
            if thread.isRunning(): print(f"경고: {thread.__class__.__name__}이(가) 정상적으로 종료되지 않았습니다.")
        print("애플리케이션 종료.");
        super().closeEvent(event)


if __name__ == "__main__":
    if not InitPlusCheck(): print("❌ PLUS 초기화 실패"); sys.exit()
    app = QApplication(sys.argv);
    ex = TradingApp();
    ex.show();
    sys.exit(app.exec_())