import sys
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QLineEdit, QPushButton, QComboBox
)
from PyQt5.QtCore import Qt, QTimer, QCoreApplication, QTime
from functools import partial

# 실제 Comms_Class.py 파일에서 필요한 함수 및 클래스를 임포트합니다.
# 사용자님의 환경에 맞게 Comms_Class.py 파일이 올바르게 존재하고,
# 아래 함수들이 해당 파일 내에 구현되어 있어야 합니다.
from Comms_Class import InitPlusCheck, get_current_price, CpFutureOptionOrder, send_telegram_message


class TR_OpBothSellApp(QWidget):
    contract_unit = 250000
    API_CALL_DELAY = 0.33  # 각 API 호출 후 대기 시간 (초)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("TR_OpBothSell")
        self.setGeometry(100, 100, 900, 600)
        self.move(
            QApplication.desktop().screen().rect().center() - self.rect().center()
        )
        self.layout = QVBoxLayout()
        self.log_count = 0
        self.orders_placed_for_target_time = False

        # UI 구성
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

        default_order_time = QTime.currentTime().addSecs(60 * 5)
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
        self.objOrder = CpFutureOptionOrder()  # 실제 주문 객체 사용

        self.option_code1 = ""
        self.option_code2 = ""
        self.order_amount1 = 0
        self.order_amount2 = 0

    def format_amount_input(self, qlineedit_widget):
        text = qlineedit_widget.text().replace(",", "")
        if text.isdigit():
            formatted = f"{int(text):,}"
            qlineedit_widget.blockSignals(True)
            qlineedit_widget.setText(formatted)
            qlineedit_widget.setCursorPosition(len(formatted))
            qlineedit_widget.blockSignals(False)
        elif not text:
            qlineedit_widget.blockSignals(True)
            qlineedit_widget.setText("")
            qlineedit_widget.blockSignals(False)

    def add_log(self, message):
        self.log_count += 1
        self.log_output.append(message)
        self.log_output.ensureCursorVisible()

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
            self.log_output.clear()
            self.log_count = 0

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
        if not (isinstance(initial_price, float) and initial_price > 0.009):  # API가 0 또는 None등을 반환할 경우 대비
            self.add_log(f"  ❌ {option_code}: 유효한 기준가({initial_price}) 조회 실패. 주문 파트 준비 불가.")
            return [], 0

        total_quantity = int(specific_order_amount // (initial_price * self.contract_unit))

        if total_quantity <= 0:
            self.add_log(
                f"  ⚠️ {option_code}: 주문금액 {specific_order_amount:,}원, 기준가 {initial_price:.2f} 기준 총 주문 수량 0. 주문 파트 준비 불가.")
            return [], 0

        self.add_log(
            f"  ℹ️ {option_code}: 주문금액 {specific_order_amount:,}원, 기준가 {initial_price:.2f}, 총 계산 수량 {total_quantity}")

        split_qty_base = total_quantity // 3
        rem_qty = total_quantity % 3
        for i in range(3):
            part_qty = split_qty_base + (1 if i < rem_qty else 0)
            part_price = max(0.01, initial_price - (0.01 * i))
            if part_qty > 0:
                order_parts.append({'quantity': part_qty, 'price': part_price})
        return order_parts, total_quantity

    def _place_single_order_part(self, option_code, price_to_order, quantity_to_order, part_num_display):
        order_timestamp = time.strftime('%H:%M:%S')
        formatted_price = f"{price_to_order:.2f}"

        attempt_log = f"  📤 [{part_num_display}] {option_code} 매도 (수량: {quantity_to_order}, 가격: {formatted_price}) @{order_timestamp}"
        self.add_log(attempt_log)

        retOrder = {}
        # 실제 주문 객체의 sellOrder 메소드 사용
        success = self.objOrder.sellOrder(option_code, price_to_order, quantity_to_order, retOrder)

        if success:
            result_log = f"    ✅ 성공! 응답: {retOrder}"
            tg_result = f"  [{part_num_display}] {option_code} S {quantity_to_order}@{formatted_price} ✅ 성공 {retOrder} (@{order_timestamp})"
        else:
            result_log = f"    ❌ 실패. 응답: {retOrder}"
            tg_result = f"  [{part_num_display}] {option_code} S {quantity_to_order}@{formatted_price} ❌ 실패 {retOrder} (@{order_timestamp})"

        self.add_log(result_log)
        return tg_result

    def check_time_and_execute_orders(self):
        current_qtime = QTime.currentTime()

        price1_log_str = "N/A"
        price2_log_str = "N/A"

        if self.option_code1:
            price1 = get_current_price(self.option_code1)  # 실제 Comms_Class의 함수 호출
            price1_log_str = f"{price1:.2f}" if isinstance(price1, float) else str(price1)

        if self.option_code2:
            price2 = get_current_price(self.option_code2)  # 실제 Comms_Class의 함수 호출
            price2_log_str = f"{price2:.2f}" if isinstance(price2, float) else str(price2)

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
            send_telegram_message(
                f"[TR_OpBothSell 알림]\n🔔 목표 주문 시간 도달 ({self.target_order_time.toString('hh:mm')})\n🚀 옵션 {self.option_code1}, {self.option_code2} 교차 분할 매도 시작.")

            price1_exec = get_current_price(self.option_code1)  # 실제 Comms_Class의 함수 호출
            order_parts1, total_quantity1 = self._prepare_order_parts(self.option_code1, price1_exec,
                                                                      self.order_amount1)

            price2_exec = get_current_price(self.option_code2)  # 실제 Comms_Class의 함수 호출
            order_parts2, total_quantity2 = self._prepare_order_parts(self.option_code2, price2_exec,
                                                                      self.order_amount2)

            if not order_parts1 and not order_parts2:  # 둘 다 주문할 파트가 없는 경우
                self.add_log("\n⚠️ 두 옵션 모두 주문 가능한 수량이 없어 주문을 실행하지 않습니다.")
                send_telegram_message(
                    f"[TR_OpBothSell 알림]\n⚠️ {self.option_code1}, {self.option_code2} 모두 주문 가능 수량 0. 주문 미실행.")
                self.start_button.setEnabled(True)
                self.stop_button.setEnabled(False)
                return

            telegram_details_summary = [
                f"[TR_OpBothSell 교차 분할 주문 결과]",
                f"⏰ 실행 시작 시간: {current_timestamp_full}"
            ]
            # total_quantity가 0이어도 price_exec가 유효하면 로그에 남김
            price1_exec_str = f"{price1_exec:.2f}" if isinstance(price1_exec, float) else str(price1_exec)
            price2_exec_str = f"{price2_exec:.2f}" if isinstance(price2_exec, float) else str(price2_exec)

            if self.option_code1: telegram_details_summary.append(
                f"--- {self.option_code1} (주문금액: {self.order_amount1:,}원, 기준가: {price1_exec_str}, 총계산: {total_quantity1}개) ---")
            if self.option_code2: telegram_details_summary.append(
                f"--- {self.option_code2} (주문금액: {self.order_amount2:,}원, 기준가: {price2_exec_str}, 총계산: {total_quantity2}개) ---")

            num_order_api_calls = 0
            # 실제 주문이 생성된 파트 수 기반으로 총 API 호출 수 계산
            actual_parts_opt1 = len(order_parts1)
            actual_parts_opt2 = len(order_parts2)
            total_api_calls_planned = actual_parts_opt1 + actual_parts_opt2

            for i in range(3):  # 최대 3단계 분할
                # 옵션 1의 i번째 분할 주문
                if i < actual_parts_opt1:  # 준비된 파트가 있을 경우에만 진행
                    part_data = order_parts1[i]
                    # quantity > 0 조건은 _prepare_order_parts에서 이미 처리됨
                    tg_detail = self._place_single_order_part(self.option_code1, part_data['price'],
                                                              part_data['quantity'], f"옵션1-{i + 1}")
                    telegram_details_summary.append(tg_detail)
                    num_order_api_calls += 1
                    if num_order_api_calls < total_api_calls_planned:
                        time.sleep(self.API_CALL_DELAY)

                # 옵션 2의 i번째 분할 주문
                if i < actual_parts_opt2:  # 준비된 파트가 있을 경우에만 진행
                    part_data = order_parts2[i]
                    # quantity > 0 조건은 _prepare_order_parts에서 이미 처리됨
                    tg_detail = self._place_single_order_part(self.option_code2, part_data['price'],
                                                              part_data['quantity'], f"옵션2-{i + 1}")
                    telegram_details_summary.append(tg_detail)
                    num_order_api_calls += 1
                    if num_order_api_calls < total_api_calls_planned:  # 마지막 API 호출 후에는 sleep 안 함
                        time.sleep(self.API_CALL_DELAY)

            try:
                send_telegram_message("\n".join(telegram_details_summary))
                self.add_log("\n✉️ 텔레그램으로 교차 분할 주문 전체 결과 전송 완료.")
            except Exception as e:
                self.add_log(f"\n텔레그램 (교차 분할 주문 결과) 알림 전송 실패: {e}")

            self.add_log("\n✅ 모든 교차 분할 주문 처리 시도 완료.")
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)


if __name__ == "__main__":
    if not InitPlusCheck():  # 실제 Comms_Class의 함수 호출
        sys.exit(1)

    app = QApplication(sys.argv)
    window = TR_OpBothSellApp()
    window.show()
    sys.exit(app.exec_())