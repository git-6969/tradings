import sys
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QLineEdit, QPushButton, QComboBox, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, QCoreApplication, QTime
from PyQt5.QtGui import QPalette, QColor  # QPalette, QColor 임포트
from functools import partial
import random

# --- Comms_Class 임포트 ---
try:
    from Comms_Class import (
        InitPlusCheck,
        get_current_price,
        CpFutureOptionOrder,
        send_telegram_message,
        CpFutureNContract,
        CpFutureOptionCancel
    )
except ImportError as e:
    error_message = (
        f"오류: Comms_Class.py 또는 필요한 구성요소를 임포트할 수 없습니다. ({e})\n\n"
        "프로그램을 사용하려면 Comms_Class.py 파일이 올바른 위치에 있고,\n"
        "내부에 InitPlusCheck, get_current_price, CpFutureOptionOrder, send_telegram_message,\n"
        "CpFutureNContract, CpFutureOptionCancel 클래스/함수가 정의되어 있어야 합니다."
    )
    print(error_message)
    # QApplication 인스턴스가 생성되기 전에는 QMessageBox를 안전하게 사용하기 어려움
    # 필요하다면 애플리케이션 시작 부분에서 인스턴스를 만들고 메시지 박스를 띄울 수 있음
    sys.exit(1)


# --- Comms_Class 임포트 끝 ---

class TR_OpBothSellApp(QWidget):
    # =========================================================================
    # 주요 설정 변수 (Key Configuration Variables)
    # =========================================================================
    CONTRACT_UNIT = 250000
    API_CALL_DELAY = 0.33

    NUM_INITIAL_ORDER_SPLITS = 3
    INITIAL_ORDER_PRICE_TICK_ADJUSTMENT = 0.01
    MIN_OPTION_PRICE = 0.01

    POST_INITIAL_ORDER_DELAY_SECONDS = 1.0
    REORDER_ATTEMPTS = 3
    REORDER_PRICE_ADJUSTMENT_TICK = -0.01
    REORDER_MAIN_LOOP_INTERVAL_SECONDS = 7

    # =========================================================================

    def __init__(self):
        super().__init__()

        self.setWindowTitle("TR_OpBothSell (미체결 재주문 V1.1)")
        self.setGeometry(100, 100, 900, 700)

        try:
            screen = QApplication.primaryScreen()
            if screen:
                center_point = screen.geometry().center()
            else:
                desktop = QApplication.desktop()
                if desktop:  # Fallback for older Qt or specific environments
                    center_point = desktop.screen().rect().center()
                else:  # Last resort
                    center_point = self.rect().center()
            self.move(center_point - self.rect().center())
        except Exception:
            pass  # 이동 실패 시에도 프로그램은 계속 실행

        # --- 시스템 색상 기반으로 약간 어둡게 테마 적용 ---
        self.apply_slightly_darker_system_theme()
        # --- 테마 적용 끝 ---

        # QWidget의 배경색이 QPalette.Window를 사용하도록 설정
        self.setAutoFillBackground(True)

        self.layout = QVBoxLayout()
        self.log_count = 0
        self.orders_placed_for_target_time = False
        self.tracked_orders = []

        self.objOrder = CpFutureOptionOrder()
        self.objNContract = CpFutureNContract()
        self.objCancel = CpFutureOptionCancel()

        # UI 구성 (이전과 동일, QLabel 등은 팔레트 색상을 따름)
        option1_row = QHBoxLayout()
        self.option_code1_input = QLineEdit()
        self.option_code1_input.setPlaceholderText("매도 옵션코드 1")
        self.amount1_input = QLineEdit()
        self.amount1_input.setPlaceholderText("옵션 1 주문 금액 (원)")
        self.amount1_input.textChanged.connect(partial(self.format_amount_input, self.amount1_input))
        option1_row.addWidget(QLabel("옵션 1 코드:"))
        option1_row.addWidget(self.option_code1_input, 1)
        option1_row.addWidget(QLabel("옵션 1 금액:"))
        option1_row.addWidget(self.amount1_input, 1)

        option2_row = QHBoxLayout()
        self.option_code2_input = QLineEdit()
        self.option_code2_input.setPlaceholderText("매도 옵션코드 2")
        self.amount2_input = QLineEdit()
        self.amount2_input.setPlaceholderText("옵션 2 주문 금액 (원)")
        self.amount2_input.textChanged.connect(partial(self.format_amount_input, self.amount2_input))
        option2_row.addWidget(QLabel("옵션 2 코드:"))
        option2_row.addWidget(self.option_code2_input, 1)
        option2_row.addWidget(QLabel("옵션 2 금액:"))
        option2_row.addWidget(self.amount2_input, 1)

        time_config_row = QHBoxLayout()
        self.order_hour_combo = QComboBox()
        self.order_minute_combo = QComboBox()
        self.interval_combo = QComboBox()

        for i in range(24): self.order_hour_combo.addItem(f"{i:02d}")
        for i in range(60): self.order_minute_combo.addItem(f"{i:02d}")
        for i in range(1, 31): self.interval_combo.addItem(f"{i:02d}")

        default_order_time = QTime.currentTime().addSecs(60 * 1)
        self.order_hour_combo.setCurrentText(default_order_time.toString("hh"))
        self.order_minute_combo.setCurrentText(default_order_time.toString("mm"))
        self.interval_combo.setCurrentText("03")

        time_config_row.addWidget(QLabel("주문 시간:"))
        time_config_row.addWidget(self.order_hour_combo)
        time_config_row.addWidget(QLabel("시"))
        time_config_row.addWidget(self.order_minute_combo)
        time_config_row.addWidget(QLabel("분"))
        time_config_row.addStretch(1)
        time_config_row.addWidget(QLabel("점검 간격:"))
        time_config_row.addWidget(self.interval_combo)
        time_config_row.addWidget(QLabel("초"))

        button_row = QHBoxLayout()
        self.start_button = QPushButton("모니터링 시작")
        self.stop_button = QPushButton("모니터링 중지")
        self.exit_button = QPushButton("프로그램 종료")

        self.start_button.clicked.connect(self.start_monitoring)
        self.stop_button.clicked.connect(self.stop_monitoring)
        self.exit_button.clicked.connect(QCoreApplication.quit)
        self.stop_button.setEnabled(False)

        button_row.addStretch(1)
        button_row.addWidget(self.start_button)
        button_row.addWidget(self.stop_button)
        button_row.addWidget(self.exit_button)
        button_row.addStretch(1)

        self.log_output = QTextEdit(self)
        self.log_output.setReadOnly(True)

        self.layout.addLayout(option1_row)
        self.layout.addLayout(option2_row)
        self.layout.addLayout(time_config_row)
        self.layout.addLayout(button_row)
        self.layout.addWidget(self.log_output)
        self.setLayout(self.layout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_time_and_execute_orders)
        self.target_order_time = None

        self.option_code1 = ""
        self.option_code2 = ""
        self.order_amount1 = 0
        self.order_amount2 = 0

        self.target_total_qty1 = 0
        self.target_total_qty2 = 0

    def apply_slightly_darker_system_theme(self):
        original_palette = QApplication.palette()
        new_palette = QPalette(original_palette)

        # 배경 및 유사 역할 색상 어둡게 하기
        # Factor: 100 = 원본, 110 = 10% 어둡게, 120 = 20% 어둡게 등
        bg_darken_factor = 115  # 15% 어둡게

        roles_to_darken_bg = [
            QPalette.Window, QPalette.Base, QPalette.AlternateBase,
            QPalette.Button, QPalette.Highlight, QPalette.ToolTipBase,
            # QPalette.Light, QPalette.Midlight, QPalette.Dark, QPalette.Mid, QPalette.Shadow
            # 위 주석처리된 역할들은 3D 효과에 사용되므로, 단순 darker 적용 시 어색할 수 있어 제외하거나 신중히 조정
        ]
        for role in roles_to_darken_bg:
            original_color = original_palette.color(role)
            if original_color.isValid():
                new_palette.setColor(role, original_color.darker(bg_darken_factor))

        # 텍스트 및 유사 역할 색상 어둡게 하기 (배경보다 덜 어둡게)
        text_darken_factor = 105  # 5% 어둡게 (가독성 유지 위해)

        roles_to_darken_text = [
            QPalette.WindowText, QPalette.Text, QPalette.ButtonText,
            QPalette.HighlightedText, QPalette.ToolTipText, QPalette.BrightText
        ]

        # PlaceholderText는 Qt 5.12 이상에서 사용 가능
        if hasattr(QPalette, 'PlaceholderText'):
            # PlaceholderText는 배경(Base)과 대비가 있어야 하므로,
            # Base 색상이 어두워졌다면 PlaceholderText는 상대적으로 밝거나,
            # 다른 텍스트처럼 약간만 어둡게 할 수 있음.
            # 여기서는 다른 텍스트와 동일하게 처리.
            roles_to_darken_text.append(QPalette.PlaceholderText)

        for role in roles_to_darken_text:
            original_color = original_palette.color(role)
            if original_color.isValid():
                # 텍스트 색상이 배경색과 너무 유사해지지 않도록 주의
                # 예: 어두운 배경에 더 어두운 텍스트가 되지 않도록
                # 여기서는 일괄적으로 약간 어둡게 하지만, 정교한 조정이 필요할 수 있음
                darker_color = original_color.darker(text_darken_factor)

                # 만약 원래 텍스트가 매우 밝았다면(예: 흰색), 약간 어둡게 해도 괜찮음.
                # 원래 어두운 텍스트였다면, 더 어둡게 하면 가독성 문제 발생 가능.
                # QColor.lightness() 등으로 원래 밝기를 확인하여 조건부로 조정할 수도 있음.
                # 여기서는 단순하게 적용.
                new_palette.setColor(role, darker_color)

        QApplication.setPalette(new_palette)

    def format_amount_input(self, qlineedit_widget):
        text = qlineedit_widget.text().replace(",", "")
        if text.isdigit():
            formatted_text = f"{int(text):,}"
            qlineedit_widget.blockSignals(True)
            qlineedit_widget.setText(formatted_text)
            qlineedit_widget.setCursorPosition(len(formatted_text))
            qlineedit_widget.blockSignals(False)
        elif not text:
            qlineedit_widget.blockSignals(True)
            qlineedit_widget.setText("")
            qlineedit_widget.blockSignals(False)

    def add_log(self, message):
        self.log_count += 1
        current_time_str = QTime.currentTime().toString('hh:mm:ss.zzz')
        self.log_output.append(f"[{current_time_str}] {message}")
        self.log_output.ensureCursorVisible()
        QApplication.processEvents()

    def start_monitoring(self):
        try:
            self.option_code1 = self.option_code1_input.text().strip().upper()
            self.option_code2 = self.option_code2_input.text().strip().upper()

            order_amount1_text = self.amount1_input.text().replace(",", "")
            order_amount2_text = self.amount2_input.text().replace(",", "")

            if not order_amount1_text or not order_amount1_text.isdigit() or int(order_amount1_text) == 0:
                self.add_log("❌ 옵션 1 주문 금액을 올바르게 입력하세요 (0보다 큰 숫자).")
                return
            self.order_amount1 = int(order_amount1_text)

            if not order_amount2_text or not order_amount2_text.isdigit() or int(order_amount2_text) == 0:
                self.add_log("❌ 옵션 2 주문 금액을 올바르게 입력하세요 (0보다 큰 숫자).")
                return
            self.order_amount2 = int(order_amount2_text)

            if not self.option_code1 or not self.option_code2:
                self.add_log("❌ 매도할 옵션 코드 두 개를 모두 입력하세요.")
                return
            if self.option_code1 == self.option_code2:
                self.add_log("❌ 두 옵션 코드가 동일합니다. 다르게 입력해주세요.")
                return

            order_hour = int(self.order_hour_combo.currentText())
            order_minute = int(self.order_minute_combo.currentText())
            self.target_order_time = QTime(order_hour, order_minute, 0)

            self.orders_placed_for_target_time = False
            self.tracked_orders = []
            self.log_output.clear()
            self.log_count = 0

            self.target_total_qty1 = 0
            self.target_total_qty2 = 0

            self.add_log("📌 [모니터링 설정]")
            self.add_log(f"🔹 옵션 1: {self.option_code1} (주문금액: {self.order_amount1:,} 원)")
            self.add_log(f"🔹 옵션 2: {self.option_code2} (주문금액: {self.order_amount2:,} 원)")
            self.add_log(f"⏰ 목표 주문 시간: {self.target_order_time.toString('hh:mm')}")

            interval_sec = int(self.interval_combo.currentText())
            self.add_log(f"⏱ 모니터링 시작 (점검 간격: {interval_sec}초)...\n")

            self.timer.start(interval_sec * 1000)
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)

        except ValueError:
            self.add_log("❌ 입력 오류: 숫자 형식을 확인하세요.")
        except Exception as e:
            self.add_log(f"❌ 시작 중 오류 발생: {e}")

    def stop_monitoring(self):
        self.timer.stop()
        self.add_log("🛑 모니터링 중지됨.\n")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def _prepare_order_parts(self, option_code, initial_price, specific_order_amount):
        order_parts = []
        if not isinstance(initial_price, (float, int)) or initial_price < self.MIN_OPTION_PRICE:
            self.add_log(
                f"  ❌ {option_code}: 유효한 기준가({initial_price}) 조회 실패 (최소가격 {self.MIN_OPTION_PRICE} 미만 또는 타입 오류). 주문 파트 준비 불가.")
            return [], 0

        total_quantity = int(specific_order_amount // (initial_price * self.CONTRACT_UNIT))

        if total_quantity <= 0:
            self.add_log(
                f"  ⚠️ {option_code}: 주문금액 {specific_order_amount:,}원, 기준가 {initial_price:.2f} 기준 총 주문 수량 0. 주문 파트 준비 불가.")
            return [], 0

        self.add_log(
            f"  ℹ️ {option_code}: 주문금액 {specific_order_amount:,}원, 기준가 {initial_price:.2f}, 총 계산 수량 {total_quantity}")

        if option_code == self.option_code1:
            self.target_total_qty1 = total_quantity
        elif option_code == self.option_code2:
            self.target_total_qty2 = total_quantity

        split_qty_base = total_quantity // self.NUM_INITIAL_ORDER_SPLITS
        rem_qty = total_quantity % self.NUM_INITIAL_ORDER_SPLITS
        for i in range(self.NUM_INITIAL_ORDER_SPLITS):
            part_qty = split_qty_base + (1 if i < rem_qty else 0)
            part_price = round(
                max(self.MIN_OPTION_PRICE, initial_price - (self.INITIAL_ORDER_PRICE_TICK_ADJUSTMENT * i)), 2)
            if part_qty > 0:
                order_parts.append({'quantity': part_qty, 'price': part_price})
        return order_parts, total_quantity

    def _place_single_order_part(self, option_code, price_to_order, quantity_to_order, part_num_display,
                                 is_reorder=False):
        order_timestamp = time.strftime('%H:%M:%S')
        formatted_price = f"{float(price_to_order):.2f}"
        log_prefix = "♻️ 재주문" if is_reorder else "📤 초기주문"

        attempt_log = f"  {log_prefix} [{part_num_display}] {option_code} 매도 (수량: {quantity_to_order}, 가격: {formatted_price}) @{order_timestamp}"
        self.add_log(attempt_log)

        retOrder = {}
        success = self.objOrder.sellOrder(option_code, price_to_order, quantity_to_order, retOrder)
        order_no = retOrder.get('주문번호', '')

        current_status = 'reorder_pending' if is_reorder else 'pending'

        if success and order_no:
            result_log = f"    ✅ 접수 성공! 주문번호: {order_no}, 응답: {retOrder}"
            tg_result = f"  {log_prefix} [{part_num_display}] {option_code} S {quantity_to_order}@{formatted_price} ✅ 접수 {order_no} (@{order_timestamp})"
            self.tracked_orders.append({
                'order_no': order_no, 'code': option_code,
                'original_qty': quantity_to_order, 'price': price_to_order,
                'status': current_status
            })
        elif success and not order_no:
            result_log = f"    ✅ 즉시 체결 또는 확인 필요. 응답: {retOrder} (주문번호 없음)"
            tg_result = f"  {log_prefix} [{part_num_display}] {option_code} S {quantity_to_order}@{formatted_price} ✅ 즉시체결? {retOrder} (@{order_timestamp})"
            self.tracked_orders.append({
                'order_no': f"NO_ID_{random.randint(1000, 9999)}_{int(time.time())}",
                'code': option_code,
                'original_qty': quantity_to_order, 'price': price_to_order,
                'status': 'filled'
            })
        else:
            result_log = f"    ❌ 접수 실패. 응답: {retOrder}"
            tg_result = f"  {log_prefix} [{part_num_display}] {option_code} S {quantity_to_order}@{formatted_price} ❌ 실패 {retOrder} (@{order_timestamp})"

        self.add_log(result_log)
        return tg_result, order_no

    def check_time_and_execute_orders(self):
        current_qtime = QTime.currentTime()
        price1_log_str = "N/A";
        price2_log_str = "N/A"

        if self.option_code1:
            price1_val = get_current_price(self.option_code1)
            price1_log_str = f"{price1_val:.2f}" if isinstance(price1_val, (float, int)) else str(price1_val)

        if self.option_code2:
            price2_val = get_current_price(self.option_code2)
            price2_log_str = f"{price2_val:.2f}" if isinstance(price2_val, (float, int)) else str(price2_val)

        log_line = (
            f"[{current_qtime.toString('hh:mm:ss')}] 현재 (목표: {self.target_order_time.toString('hh:mm') if self.target_order_time else 'N/A'}) | "
            f"{self.option_code1 if self.option_code1 else '옵션1'}: {price1_log_str}, "
            f"{self.option_code2 if self.option_code2 else '옵션2'}: {price2_log_str}"
        )
        self.add_log(log_line)

        if not self.orders_placed_for_target_time and self.target_order_time and current_qtime >= self.target_order_time:
            current_timestamp_full = time.strftime('%Y-%m-%d %H:%M:%S')
            self.add_log(
                f"\n🔔 [{current_qtime.toString('hh:mm:ss')}] 목표 주문 시간 도달! ({self.target_order_time.toString('hh:mm')})")
            self.orders_placed_for_target_time = True
            self.timer.stop()

            self.add_log("🚀 두 옵션에 대한 교차 분할 매도 주문을 시작합니다...")
            try:
                send_telegram_message(
                    f"[TR_OpBothSell 알림]\n🔔 목표 주문 시간 도달 ({self.target_order_time.toString('hh:mm')})\n🚀 옵션 {self.option_code1}, {self.option_code2} 교차 분할 매도 시작.")
            except Exception as e:
                self.add_log(f"텔레그램 (목표시간 도달) 알림 전송 실패: {e}")

            price1_exec = get_current_price(self.option_code1)
            order_parts1, _ = self._prepare_order_parts(self.option_code1, price1_exec, self.order_amount1)

            price2_exec = get_current_price(self.option_code2)
            order_parts2, _ = self._prepare_order_parts(self.option_code2, price2_exec, self.order_amount2)

            if not order_parts1 and not order_parts2:
                self.add_log("\n⚠️ 두 옵션 모두 주문 가능한 수량이 없어 주문을 실행하지 않습니다.")
                try:
                    send_telegram_message(
                        f"[TR_OpBothSell 알림]\n⚠️ {self.option_code1}, {self.option_code2} 모두 주문 가능 수량 0. 주문 미실행.")
                except Exception as e:
                    self.add_log(f"텔레그램 (주문 미실행) 알림 전송 실패: {e}")
                self.start_button.setEnabled(True)
                self.stop_button.setEnabled(False)
                return

            telegram_details_summary = [
                f"[TR_OpBothSell 초기 교차 분할 주문 결과]",
                f"⏰ 실행 시작 시간: {current_timestamp_full}"
            ]

            price1_exec_str = f"{price1_exec:.2f}" if isinstance(price1_exec, (float, int)) else str(price1_exec)
            price2_exec_str = f"{price2_exec:.2f}" if isinstance(price2_exec, (float, int)) else str(price2_exec)

            if self.option_code1 and self.target_total_qty1 > 0:
                telegram_details_summary.append(
                    f"--- {self.option_code1} (주문금액: {self.order_amount1:,}원, 기준가: {price1_exec_str}, 총계산: {self.target_total_qty1}개) ---")
            if self.option_code2 and self.target_total_qty2 > 0:
                telegram_details_summary.append(
                    f"--- {self.option_code2} (주문금액: {self.order_amount2:,}원, 기준가: {price2_exec_str}, 총계산: {self.target_total_qty2}개) ---")

            num_order_api_calls = 0
            actual_parts_opt1 = len(order_parts1)
            actual_parts_opt2 = len(order_parts2)
            total_api_calls_planned = actual_parts_opt1 + actual_parts_opt2

            for i in range(max(actual_parts_opt1, actual_parts_opt2)):
                if i < actual_parts_opt1:
                    part_data = order_parts1[i]
                    tg_detail, _ = self._place_single_order_part(self.option_code1, part_data['price'],
                                                                 part_data['quantity'], f"옵션1-{i + 1}")
                    telegram_details_summary.append(tg_detail)
                    num_order_api_calls += 1
                    if num_order_api_calls < total_api_calls_planned: time.sleep(self.API_CALL_DELAY)

                if i < actual_parts_opt2:
                    part_data = order_parts2[i]
                    tg_detail, _ = self._place_single_order_part(self.option_code2, part_data['price'],
                                                                 part_data['quantity'], f"옵션2-{i + 1}")
                    telegram_details_summary.append(tg_detail)
                    num_order_api_calls += 1
                    if num_order_api_calls < total_api_calls_planned: time.sleep(self.API_CALL_DELAY)

            try:
                if telegram_details_summary:
                    send_telegram_message("\n".join(telegram_details_summary))
                self.add_log("\n✉️ 텔레그램으로 초기 주문 시도 결과 전송 완료.")
            except Exception as e:
                self.add_log(f"\n텔레그램 (초기 주문 결과) 알림 전송 실패: {e}")

            self.add_log(f"\n🔄 초기 주문 처리 완료. {self.POST_INITIAL_ORDER_DELAY_SECONDS}초 후 미체결 잔량에 대한 재주문 로직을 시작합니다...")
            QApplication.processEvents()
            time.sleep(self.POST_INITIAL_ORDER_DELAY_SECONDS)

            reorder_tg_summary = self._execute_reorder_strategy()

            final_telegram_message = ["[TR_OpBothSell 최종 결과 요약]"]
            filled_qty1 = sum(o['original_qty'] for o in self.tracked_orders if
                              o['code'] == self.option_code1 and o['status'] == 'filled')
            filled_qty2 = sum(o['original_qty'] for o in self.tracked_orders if
                              o['code'] == self.option_code2 and o['status'] == 'filled')

            if self.target_total_qty1 > 0:
                final_telegram_message.append(f"--- {self.option_code1} (목표: {self.target_total_qty1}) ---")
                final_telegram_message.append(f"  최종 체결 수량: {filled_qty1}")
                unfilled_qty1 = self.target_total_qty1 - filled_qty1
                if unfilled_qty1 > 0:
                    final_telegram_message.append(f"  최종 미체결 추정: {unfilled_qty1}")

            if self.target_total_qty2 > 0:
                final_telegram_message.append(f"--- {self.option_code2} (목표: {self.target_total_qty2}) ---")
                final_telegram_message.append(f"  최종 체결 수량: {filled_qty2}")
                unfilled_qty2 = self.target_total_qty2 - filled_qty2
                if unfilled_qty2 > 0:
                    final_telegram_message.append(f"  최종 미체결 추정: {unfilled_qty2}")

            if reorder_tg_summary:
                final_telegram_message.extend(reorder_tg_summary)

            try:
                if len(final_telegram_message) > 1:
                    send_telegram_message("\n".join(final_telegram_message))
                self.add_log("\n✉️ 텔레그램으로 최종 주문 결과 및 재주문 과정 요약 전송 완료.")
            except Exception as e:
                self.add_log(f"\n텔레그램 (최종 결과 요약) 알림 전송 실패: {e}")

            self.add_log("\n✅ 모든 주문 처리 및 재주문 시도 완료.")
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)

    def _execute_reorder_strategy(self):
        self.add_log(f"🔄 재주문 전략 시작 (최대 {self.REORDER_ATTEMPTS}회 시도, 주기: {self.REORDER_MAIN_LOOP_INTERVAL_SECONDS}초)")
        strategy_telegram_log = [f"\n[TR_OpBothSell 재주문 과정 상세]"]

        for attempt_cycle in range(self.REORDER_ATTEMPTS):
            self.add_log(f"\n--- 재주문 사이클 {attempt_cycle + 1}/{self.REORDER_ATTEMPTS} ---")
            strategy_telegram_log.append(f"\n--- 재주문 사이클 {attempt_cycle + 1}/{self.REORDER_ATTEMPTS} ---")
            QApplication.processEvents()

            filled_qty_opt1 = sum(o['original_qty'] for o in self.tracked_orders if
                                  o['code'] == self.option_code1 and o['status'] == 'filled')
            filled_qty_opt2 = sum(o['original_qty'] for o in self.tracked_orders if
                                  o['code'] == self.option_code2 and o['status'] == 'filled')

            all_filled_opt1 = (self.target_total_qty1 == 0) or (filled_qty_opt1 >= self.target_total_qty1)
            all_filled_opt2 = (self.target_total_qty2 == 0) or (filled_qty_opt2 >= self.target_total_qty2)

            if all_filled_opt1 and all_filled_opt2:
                log_msg = "✅ 모든 목표 수량이 체결 완료된 것으로 확인됨. 재주문 전략 종료."
                self.add_log(log_msg);
                strategy_telegram_log.append(log_msg)
                break

            ncontract_list = []
            if not self.objNContract.request(ncontract_list):
                log_msg = "  ❌ 미체결 목록 조회 실패. 이번 재주문 사이클을 건너뜁니다."
                self.add_log(log_msg);
                strategy_telegram_log.append(log_msg)
                if attempt_cycle < self.REORDER_ATTEMPTS - 1:
                    time.sleep(self.REORDER_MAIN_LOOP_INTERVAL_SECONDS)
                continue

            qty_to_reorder_from_cancelled_opt1 = 0
            qty_to_reorder_from_cancelled_opt2 = 0
            updated_tracked_orders_this_cycle = []

            for order in list(self.tracked_orders):
                if order['status'] in ['filled', 'cancelled_noretry', 'cancelled_for_reorder']:
                    updated_tracked_orders_this_cycle.append(order)
                    continue

                found_in_ncontract = False
                for n_item in ncontract_list:
                    if n_item['주문번호'] == order['order_no']:
                        found_in_ncontract = True
                        unfilled_qty_from_ncontract = int(n_item['잔량'])

                        if unfilled_qty_from_ncontract == 0:
                            order['status'] = 'filled'
                            log_msg = f"  ✅ 주문 {order['order_no']} ({order['code']}) 체결 확인 (미체결 잔량 0)."
                            self.add_log(log_msg);
                            strategy_telegram_log.append(log_msg)
                        else:
                            log_msg = f"  ⏳ 주문 {order['order_no']} ({order['code']}) 미체결 잔량 {unfilled_qty_from_ncontract}. 취소 시도."
                            self.add_log(log_msg);
                            strategy_telegram_log.append(log_msg)

                            if self.objCancel.cancel_order(order['order_no'], order['code'],
                                                           unfilled_qty_from_ncontract):
                                log_msg_cancel = f"    ✅ 주문 {order['order_no']} 취소 성공. 재주문 대상에 추가."
                                self.add_log(log_msg_cancel);
                                strategy_telegram_log.append(log_msg_cancel)
                                order['status'] = 'cancelled_for_reorder'
                                if order['code'] == self.option_code1:
                                    qty_to_reorder_from_cancelled_opt1 += unfilled_qty_from_ncontract
                                elif order['code'] == self.option_code2:
                                    qty_to_reorder_from_cancelled_opt2 += unfilled_qty_from_ncontract
                            else:
                                log_msg_cancel_fail = f"    ❌ 주문 {order['order_no']} 취소 실패 (API 응답). 다음 사이클에서 재확인."
                                self.add_log(log_msg_cancel_fail);
                                strategy_telegram_log.append(log_msg_cancel_fail)
                        break

                if not found_in_ncontract and order['status'] not in ['filled', 'cancelled_for_reorder',
                                                                      'cancelled_noretry']:
                    order['status'] = 'filled'
                    log_msg = f"  ✅ 주문 {order['order_no']} ({order['code']}) 미체결 목록에 없어 체결 간주."
                    self.add_log(log_msg);
                    strategy_telegram_log.append(log_msg)

                updated_tracked_orders_this_cycle.append(order)

            self.tracked_orders = updated_tracked_orders_this_cycle

            final_filled_qty_opt1_this_cycle = sum(o['original_qty'] for o in self.tracked_orders if
                                                   o['code'] == self.option_code1 and o['status'] == 'filled')
            final_filled_qty_opt2_this_cycle = sum(o['original_qty'] for o in self.tracked_orders if
                                                   o['code'] == self.option_code2 and o['status'] == 'filled')

            needed_to_hit_target_opt1 = self.target_total_qty1 - final_filled_qty_opt1_this_cycle
            qty_to_place_for_opt1 = 0
            if needed_to_hit_target_opt1 > 0:
                if qty_to_reorder_from_cancelled_opt1 > 0:
                    qty_to_place_for_opt1 = min(qty_to_reorder_from_cancelled_opt1, needed_to_hit_target_opt1)
                    log_msg_reorder_type = f"(취소분 {qty_to_reorder_from_cancelled_opt1} 중 필요한 만큼)"
                else:
                    qty_to_place_for_opt1 = needed_to_hit_target_opt1
                    log_msg_reorder_type = "(목표 미달분)"

                if qty_to_place_for_opt1 > 0:
                    log_msg = f"  ➡️ {self.option_code1}: {qty_to_place_for_opt1}개 재주문 시도 {log_msg_reorder_type}..."
                    self.add_log(log_msg);
                    strategy_telegram_log.append(log_msg)
                    price1 = get_current_price(self.option_code1)
                    if isinstance(price1, (float, int)) and price1 > 0:
                        reorder_price = round(max(self.MIN_OPTION_PRICE, price1 + self.REORDER_PRICE_ADJUSTMENT_TICK),
                                              2)
                        tg_detail, _ = self._place_single_order_part(self.option_code1, reorder_price,
                                                                     qty_to_place_for_opt1, f"옵션1-재{attempt_cycle + 1}",
                                                                     is_reorder=True)
                        strategy_telegram_log.append(tg_detail)
                        time.sleep(self.API_CALL_DELAY)
                    else:
                        log_msg_price_fail = f"    ❌ {self.option_code1} 현재가({price1}) 오류로 재주문 불가."
                        self.add_log(log_msg_price_fail);
                        strategy_telegram_log.append(log_msg_price_fail)

            needed_to_hit_target_opt2 = self.target_total_qty2 - final_filled_qty_opt2_this_cycle
            qty_to_place_for_opt2 = 0
            if needed_to_hit_target_opt2 > 0:
                if qty_to_reorder_from_cancelled_opt2 > 0:
                    qty_to_place_for_opt2 = min(qty_to_reorder_from_cancelled_opt2, needed_to_hit_target_opt2)
                    log_msg_reorder_type = f"(취소분 {qty_to_reorder_from_cancelled_opt2} 중 필요한 만큼)"
                else:
                    qty_to_place_for_opt2 = needed_to_hit_target_opt2
                    log_msg_reorder_type = "(목표 미달분)"

                if qty_to_place_for_opt2 > 0:
                    log_msg = f"  ➡️ {self.option_code2}: {qty_to_place_for_opt2}개 재주문 시도 {log_msg_reorder_type}..."
                    self.add_log(log_msg);
                    strategy_telegram_log.append(log_msg)
                    price2 = get_current_price(self.option_code2)
                    if isinstance(price2, (float, int)) and price2 > 0:
                        reorder_price = round(max(self.MIN_OPTION_PRICE, price2 + self.REORDER_PRICE_ADJUSTMENT_TICK),
                                              2)
                        tg_detail, _ = self._place_single_order_part(self.option_code2, reorder_price,
                                                                     qty_to_place_for_opt2, f"옵션2-재{attempt_cycle + 1}",
                                                                     is_reorder=True)
                        strategy_telegram_log.append(tg_detail)
                        time.sleep(self.API_CALL_DELAY)
                    else:
                        log_msg_price_fail = f"    ❌ {self.option_code2} 현재가({price2}) 오류로 재주문 불가."
                        self.add_log(log_msg_price_fail);
                        strategy_telegram_log.append(log_msg_price_fail)

            if attempt_cycle < self.REORDER_ATTEMPTS - 1:
                final_filled_check_opt1_after_reorder = sum(o['original_qty'] for o in self.tracked_orders if
                                                            o['code'] == self.option_code1 and o['status'] == 'filled')
                final_filled_check_opt2_after_reorder = sum(o['original_qty'] for o in self.tracked_orders if
                                                            o['code'] == self.option_code2 and o['status'] == 'filled')

                if ((self.target_total_qty1 == 0 or final_filled_check_opt1_after_reorder >= self.target_total_qty1) and
                        (
                                self.target_total_qty2 == 0 or final_filled_check_opt2_after_reorder >= self.target_total_qty2)):
                    log_msg = "✅ 이번 사이클 후 모든 목표 수량 체결 완료. 재주문 전략 종료."
                    self.add_log(log_msg);
                    strategy_telegram_log.append(log_msg)
                    break

                active_orders_exist = any(
                    o['status'] in ['pending', 'reorder_pending'] for o in self.tracked_orders
                )
                is_target_met = (
                                            final_filled_check_opt1_after_reorder >= self.target_total_qty1 or self.target_total_qty1 == 0) and \
                                (
                                            final_filled_check_opt2_after_reorder >= self.target_total_qty2 or self.target_total_qty2 == 0)

                if not active_orders_exist and not is_target_met:
                    self.add_log(f"  ℹ️ 현재 활성 주문은 없으나 목표량 미달. 다음 사이클에서 추가 주문 시도 예정.")

                self.add_log(f"  --- 다음 재주문 사이클까지 {self.REORDER_MAIN_LOOP_INTERVAL_SECONDS}초 대기 ---")
                QApplication.processEvents()
                time.sleep(self.REORDER_MAIN_LOOP_INTERVAL_SECONDS)
            else:
                self.add_log("--- 모든 재주문 시도 사이클 완료 ---")
                strategy_telegram_log.append("--- 모든 재주문 시도 사이클 완료 ---")

        self.add_log("🔄 재주문 전략 종료.")
        if len(strategy_telegram_log) <= 1:
            return []
        return strategy_telegram_log


if __name__ == "__main__":
    if not InitPlusCheck():
        print("❌ PLUS 시스템 초기화 실패. 프로그램을 종료합니다.")
        # 이 시점에서 QMessageBox를 사용하려면 QApplication 인스턴스가 필요함.
        # 간단한 콘솔 알림 후 종료.
        sys.exit(1)

    app = QApplication(sys.argv)
    # TR_OpBothSellApp 클래스 내에서 QApplication.setPalette()를 호출하므로,
    # app 인스턴스 생성 후 window 생성 전에 별도로 팔레트를 설정할 필요는 없음.

    window = TR_OpBothSellApp()
    window.show()
    sys.exit(app.exec_())