import sys
import time
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit,
    QHBoxLayout, QDesktopWidget, QLabel
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QTextCursor

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
            on = ''
            if p == 0 or random.random() < 0.8:
                on = str(random.randint(10000, 99999));
                self._add_to_pending(c, p, q, '매도', on);
                rd['주문번호'] = on;
                return True
            rd['오류'] = '주문실패';
            return False

        def buyOrder(self, c, p, q, rd):
            on = ''
            if p == 0 or random.random() < 0.8:
                on = str(random.randint(10000, 99999));
                self._add_to_pending(c, p, q, '매수', on);
                rd['주문번호'] = on;
                return True
            rd['오류'] = '주문실패';
            return False


    class CpFutureOptionCancel:
        def cancel_order(self, on, c, q):
            olen = len(CpFutureNContract._dummy_orders_store);
            CpFutureNContract._dummy_orders_store = [o for o in CpFutureNContract._dummy_orders_store if
                                                     o['주문번호'] != on];
            return len(CpFutureNContract._dummy_orders_store) < olen

USE_MARKET_PRICE = True


class LogThread(QThread):
    log_signal = pyqtSignal(str, bool)

    def emit_log(self, message, bold=False):
        current_time = datetime.now().strftime("%H:%M:%S")
        self.log_signal.emit(f"[{current_time}] {message}", bold)


class BalanceThread(LogThread):
    def run(self):
        self.emit_log("\n=== 계좌 내역 조회 ===", False)
        objBalance = CpFutureBalance()
        balanceList = []
        if objBalance.request(balanceList):
            if not balanceList:
                self.emit_log("\ud83d\udcdd 현재 보유한 포지션이 없습니다.", False)
                return
            for item in balanceList:
                formatted_items = []
                v_int_pl = 0
                for k, v in item.items():
                    if k == '평가손익':
                        try:
                            v_int_pl = int(float(v))
                            v_formatted = f"{v_int_pl:,}"
                        except:
                            v_formatted = str(v)  # 오류 시 원본 문자열
                        color = 'red' if v_int_pl > 0 else 'blue' if v_int_pl < 0 else 'black'
                        formatted_items.append(f"<span style='color:{color}'>[{k}] {v_formatted}</span>")
                    elif k == '평균단가':  # ⭐ 평균단가 포맷팅 수정 ⭐
                        try:
                            v_float = float(v)
                            v_str = f"{v_float:.4f}"  # 소수점 4자리까지 표시
                        except ValueError:
                            v_str = str(v)  # float 변환 실패 시 원본 문자열
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
                    else:  # 그 외 다른 항목들
                        formatted_items.append(f"[{k}] {str(v)}")  # 모든 값을 문자열로 안전하게 변환
                self.emit_log(" | ".join(formatted_items), False)
        else:
            self.emit_log("잔고 조회 실패", False)


class NContractThread(LogThread):
    def run(self):
        self.emit_log("\n=== 미체결 조회 ===", False)
        objNContract = CpFutureNContract()
        nContractList = []
        if objNContract.request(nContractList):
            if not nContractList: self.emit_log("\ud83d\udcdd 현재 미체결 주문이 없습니다.", False); return
            for item in nContractList: self.emit_log(" | ".join([f"[{k}] {v}" for k, v in item.items()]), False)
        else:
            self.emit_log("미체결 조회 실패", False)


class ClearThread(LogThread):
    def run(self):
        self.emit_log("\n=== 계좌 내 모든 종목 청산 시작 ===", False)
        objOrder = CpFutureOptionOrder();
        objBalance = CpFutureBalance();
        objNContract = CpFutureNContract();
        objCancel = CpFutureOptionCancel()
        while True:
            self.emit_log("\n\ud83d\udccc 미체결 주문 정리 및 청산 시작...", False)
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
                            time.sleep(1)
                    else:
                        self.emit_log("✅ 모든 미체결 주문 취소 완료", False); break
                balanceList = []
                if objBalance.request(balanceList):
                    if not balanceList: self.emit_log("✅ 모든 포지션 청산 완료!", False); return
                    self.emit_log(f"🔍 현재 잔고 스냅샷 ({len(balanceList)}개 종목):", False)
                    for item in balanceList: self.emit_log(
                        f"    - {item.get('종목명', item.get('코드'))}: 수량 {item['잔고수량']}, 포지션 {item['잔고구분']}", False)
                    for item in balanceList:
                        code = item['코드'];
                        qty = item['잔고수량'];
                        price_str = item['현재가']
                        price = 0.0 if USE_MARKET_PRICE else float(price_str)
                        position_type = item['잔고구분']
                        if qty <= 0: continue
                        retData = {}
                        if position_type == '매수':
                            success = objOrder.sellOrder(code, price, qty, retData); action = "매도"
                        elif position_type == '매도':
                            success = objOrder.buyOrder(code, price, qty, retData); action = "매수"
                        else:
                            self.emit_log(f"⚠️ 알 수 없는 포지션 타입: {position_type}", False); continue
                        if success:
                            self.emit_log(f"✅ {code} {qty}개 {action} 주문 성공 (가격: {'시장가' if price == 0.0 else price})",
                                          False)
                        else:
                            self.emit_log(f"❌ {code} {qty}개 {action} 주문 실패", False)
                        time.sleep(1)
            except Exception as e:
                self.emit_log(f"🚨 예외 발생: {e}", True)
            time.sleep(5)


class TradingApp(QWidget):
    def __init__(self):
        super().__init__()
        self.is_hello_tracking_active = False
        self.hello_timer = None
        self.balance_thread = None
        self.clear_thread = None
        self.ncontract_thread = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle("계좌 모니터링")
        self.resize(1200, 800)  # ⭐ 창 크기 조금 크게 수정 (1000,750 -> 1200,800) ⭐
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
        main_layout = QVBoxLayout()

        button_layout = QHBoxLayout()
        self.balance_btn = QPushButton("계좌 조회")
        self.clear_btn = QPushButton("계좌 전종목 청산")
        self.ncontract_btn = QPushButton("미체결 조회")
        button_layout.addWidget(self.balance_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addWidget(self.ncontract_btn)
        main_layout.addLayout(button_layout)

        hello_tracking_controls_layout = QHBoxLayout()
        self.hello_tracking_button = QPushButton("트랙 킹")
        self.hello_tracking_button.clicked.connect(self.toggle_account_pl_tracking)
        hello_tracking_controls_layout.addWidget(self.hello_tracking_button)
        hello_tracking_controls_layout.addStretch(1)
        main_layout.addLayout(hello_tracking_controls_layout)

        self.output = QTextEdit()
        self.output.setReadOnly(True);
        main_layout.addWidget(self.output, 3)

        self.hello_log_title_label = QLabel("<b>[계좌 전체 수익률 트래킹 로그]</b>")
        main_layout.addWidget(self.hello_log_title_label)
        self.hello_log_output = QTextEdit()
        self.hello_log_output.setReadOnly(True);
        main_layout.addWidget(self.hello_log_output, 2)

        self.setLayout(main_layout)
        self.balance_btn.clicked.connect(self.run_balance_thread)
        self.clear_btn.clicked.connect(self.run_clear_thread)
        self.ncontract_btn.clicked.connect(self.run_ncontract_thread)
        self.log_to_main_panel(f"<b>애플리케이션 시작됨.</b>", True)

    def log_to_main_panel(self, message, bold=False):
        current_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        if bold:
            formatted_message = f"<b>[{current_time}] {message}</b><br>"
        else:
            formatted_message = f"[{current_time}] {message}<br>"
        self.output.moveCursor(QTextCursor.End)
        self.output.insertHtml(formatted_message)
        scrollbar = self.output.verticalScrollBar()
        if scrollbar: scrollbar.setValue(scrollbar.maximum())

    def toggle_account_pl_tracking(self):
        if not self.is_hello_tracking_active:
            self.is_hello_tracking_active = True
            self.hello_tracking_button.setText("수익률 트래킹 중지")
            self.append_to_tracking_panel("계좌 전체 수익률 트래킹 시작됨.")
            if self.hello_timer is None:
                self.hello_timer = QTimer(self)
                self.hello_timer.timeout.connect(self.track_and_print_account_pl)
            self.hello_timer.start(5000)
            self.track_and_print_account_pl()
        else:
            self.is_hello_tracking_active = False
            self.hello_tracking_button.setText("트랙 킹")
            if self.hello_timer is not None:
                self.hello_timer.stop()
            self.append_to_tracking_panel("계좌 전체 수익률 트래킹 중지됨.")

    def track_and_print_account_pl(self):
        if not self.is_hello_tracking_active:
            return
        message_to_log = "계좌 정보 조회 중..."
        objBalance = CpFutureBalance()
        balanceList = []
        api_call_successful = objBalance.request(balanceList)
        if api_call_successful:
            if not balanceList:
                message_to_log = "보유 포지션 없음 (수익률: 0.00%)"
            else:
                total_pl_amount_num = 0.0
                total_purchase_amount_num = 0.0
                position_count = len(balanceList)
                for item in balanceList:
                    try:
                        pl = float(item.get('평가손익', "0"))
                        total_pl_amount_num += pl
                    except ValueError:
                        print(f"경고: '{item.get('종목명')}'의 평가손익 값을 float으로 변환할 수 없습니다: {item.get('평가손익')}")
                    try:
                        purchase_str = item.get('매입금액', "0")
                        cost = float(purchase_str)
                        if cost > 0: total_purchase_amount_num += cost
                    except ValueError:
                        print(f"경고: '{item.get('종목명')}'의 매입금액 값을 float으로 변환할 수 없습니다: {purchase_str}")
                pl_display = f"{int(total_pl_amount_num):,}"
                purchase_display = f"{int(total_purchase_amount_num):,}"
                if total_purchase_amount_num > 0:
                    current_pl_ratio_numeric = (total_pl_amount_num / total_purchase_amount_num) * 100
                    message_to_log = f"전체 수익률({position_count}개): {current_pl_ratio_numeric:+.2f}% (손익: {pl_display} / 매입: {purchase_display})"
                elif total_pl_amount_num != 0 and total_purchase_amount_num == 0:
                    message_to_log = f"전체 수익률({position_count}개): N/A (매입액 0, 손익: {pl_display})"
                else:
                    message_to_log = f"전체 수익률({position_count}개): 0.00% (손익: {pl_display} / 매입: {purchase_display})"
        else:
            message_to_log = "계좌 정보 조회 실패"
        self.append_to_tracking_panel(message_to_log)

    def append_to_tracking_panel(self, message):
        current_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        formatted_message = f"[{current_time}] {message}<br>"
        self.hello_log_output.moveCursor(QTextCursor.End)
        self.hello_log_output.insertHtml(formatted_message)
        scrollbar = self.hello_log_output.verticalScrollBar()
        if scrollbar: scrollbar.setValue(scrollbar.maximum())

    def run_balance_thread(self):
        if hasattr(self, 'balance_thread') and self.balance_thread and self.balance_thread.isRunning():
            self.log_to_main_panel("이미 계좌 조회 작업이 진행 중입니다.", True);
            return
        self.balance_thread = BalanceThread()
        self.balance_thread.log_signal.connect(self.log_to_main_panel)
        self.balance_thread.start()

    def run_clear_thread(self):
        if hasattr(self, 'clear_thread') and self.clear_thread and self.clear_thread.isRunning():
            self.log_to_main_panel("이미 청산 작업이 진행 중입니다.", True);
            return
        self.clear_thread = ClearThread()
        self.clear_thread.log_signal.connect(self.log_to_main_panel)
        self.clear_thread.start()

    def run_ncontract_thread(self):
        if hasattr(self, 'ncontract_thread') and self.ncontract_thread and self.ncontract_thread.isRunning():
            self.log_to_main_panel("이미 미체결 조회 작업이 진행 중입니다.", True);
            return
        self.ncontract_thread = NContractThread()
        self.ncontract_thread.log_signal.connect(self.log_to_main_panel)
        self.ncontract_thread.start()

    def closeEvent(self, event):
        print("애플리케이션 종료 요청...");
        if self.hello_timer and self.hello_timer.isActive():
            print("계좌 수익률 트래킹 타이머 중지...");
            self.hello_timer.stop()
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
    if not InitPlusCheck():
        print("❌ PLUS 초기화 실패")
        sys.exit()
    app = QApplication(sys.argv)
    ex = TradingApp()
    ex.show()
    sys.exit(app.exec_())