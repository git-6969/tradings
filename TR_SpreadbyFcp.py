import sys
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QLineEdit, QPushButton, QComboBox, QGridLayout
)
from PyQt5.QtCore import Qt, QTimer, QCoreApplication, QTime
# 아래 Comms_Class는 실제 환경에 맞게 준비되어 있어야 합니다.
from Comms_Class import InitPlusCheck, get_current_price
from Comms_Class import CpFutureOptionOrder
from Comms_Class import send_telegram_message

# 애플리케이션 이름 정의
APP_NAME = "TR_SpreadbyFcp"


class TR_SpreadbyFcpApp(QWidget):
    contract_unit = 250000  # 옵션 1계약 단위 금액

    def __init__(self):
        super().__init__()

        self.setWindowTitle(APP_NAME)
        self.setGeometry(100, 100, 1050, 800)
        self.layout = QVBoxLayout()
        self.log_count = 0
        self.last_log_time = 0
        self.previous_watch_price = None

        grid_layout = QGridLayout()

        grid_layout.addWidget(QLabel("<b>[감시 대상]</b>"), 0, 0, 1, 6)
        grid_layout.addWidget(QLabel("감시 선물 코드:"), 1, 0)
        self.futures_watch_code_input = QLineEdit()
        self.futures_watch_code_input.setPlaceholderText("예: 101V3000")
        grid_layout.addWidget(self.futures_watch_code_input, 1, 1, 1, 2)
        grid_layout.addWidget(QLabel("선물 트리거 가격:"), 1, 3)
        self.futures_trigger_price_input = QLineEdit()
        self.futures_trigger_price_input.setPlaceholderText("예: 350.50")
        grid_layout.addWidget(self.futures_trigger_price_input, 1, 4, 1, 2)

        grid_layout.addWidget(QLabel("<b>[옵션 1 / 2]</b>"), 2, 0, 1, 6)

        grid_layout.addWidget(QLabel("옵션 1 코드:"), 3, 0)
        self.option1_code_input = QLineEdit()
        self.option1_code_input.setPlaceholderText("옵션 1 코드")
        grid_layout.addWidget(self.option1_code_input, 3, 1)
        grid_layout.addWidget(QLabel("금액(원):"), 3, 2)
        self.option1_amount_input = QLineEdit()
        self.option1_amount_input.setPlaceholderText("예: 1,000,000")
        self.option1_amount_input.textChanged.connect(
            lambda text, el=self.option1_amount_input: self.format_amount_input(el))
        grid_layout.addWidget(self.option1_amount_input, 3, 3)
        grid_layout.addWidget(QLabel("유형:"), 3, 4)
        self.option1_order_type_combo = QComboBox()
        self.option1_order_type_combo.addItems(["매도", "매수"])
        self.option1_order_type_combo.setCurrentText("매도")
        grid_layout.addWidget(self.option1_order_type_combo, 3, 5)

        grid_layout.addWidget(QLabel("옵션 2 코드:"), 4, 0)
        self.option2_code_input = QLineEdit()
        self.option2_code_input.setPlaceholderText("옵션 2 코드")
        grid_layout.addWidget(self.option2_code_input, 4, 1)
        grid_layout.addWidget(QLabel("금액(원):"), 4, 2)
        self.option2_amount_input = QLineEdit()
        self.option2_amount_input.setPlaceholderText("예: 1,000,000")
        self.option2_amount_input.textChanged.connect(
            lambda text, el=self.option2_amount_input: self.format_amount_input(el))
        grid_layout.addWidget(self.option2_amount_input, 4, 3)
        grid_layout.addWidget(QLabel("유형:"), 4, 4)
        self.option2_order_type_combo = QComboBox()
        self.option2_order_type_combo.addItems(["매도", "매수"])
        self.option2_order_type_combo.setCurrentText("매수")
        grid_layout.addWidget(self.option2_order_type_combo, 4, 5)

        grid_layout.addWidget(QLabel("<b>[실행 설정]</b>"), 5, 0, 1, 6)
        time_row_layout = QHBoxLayout()
        self.end_hour_combo = QComboBox()
        self.end_minute_combo = QComboBox()
        self.interval_combo = QComboBox()

        for i in range(24): self.end_hour_combo.addItem(f"{i:02d}")
        for i in range(60): self.end_minute_combo.addItem(f"{i:02d}")
        for i in range(31): self.interval_combo.addItem(f"{i:02d}")

        default_end_time = QTime(15, 40, 0)
        self.end_hour_combo.setCurrentText(default_end_time.toString("hh"))
        self.end_minute_combo.setCurrentText(default_end_time.toString("mm"))
        self.interval_combo.setCurrentText("03")

        time_row_layout.addWidget(QLabel("감시 종료 시간:"))
        time_row_layout.addWidget(self.end_hour_combo)
        time_row_layout.addWidget(QLabel("시"))
        time_row_layout.addWidget(self.end_minute_combo)
        time_row_layout.addWidget(QLabel("분"))
        time_row_layout.addStretch(1)
        time_row_layout.addWidget(QLabel("감시 인터벌:"))
        time_row_layout.addWidget(self.interval_combo)
        time_row_layout.addWidget(QLabel("초"))
        grid_layout.addLayout(time_row_layout, 6, 0, 1, 6)

        button_row = QHBoxLayout()
        self.start_button = QPushButton("모니터링 시작")
        self.stop_button = QPushButton("모니터링 중지")
        self.exit_button = QPushButton("프로그램 종료")

        self.start_button.clicked.connect(self.start_monitoring)
        self.stop_button.clicked.connect(self.stop_monitoring)
        self.exit_button.clicked.connect(QCoreApplication.quit)

        button_row.addWidget(self.start_button)
        button_row.addWidget(self.stop_button)
        button_row.addWidget(self.exit_button)
        grid_layout.addLayout(button_row, 7, 0, 1, 6)

        self.layout.addLayout(grid_layout)

        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setFixedHeight(300)
        self.layout.addWidget(self.text_edit)
        self.setLayout(self.layout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.fetch_market_data)
        self.end_time = None
        self.orders_placed_this_trigger = False

    def format_amount_input(self, line_edit_widget):
        text = line_edit_widget.text().replace(",", "")
        if text.isdigit():
            formatted = f"{int(text):,}"
            line_edit_widget.blockSignals(True)
            line_edit_widget.setText(formatted)
            line_edit_widget.blockSignals(False)
            line_edit_widget.setCursorPosition(len(line_edit_widget.text()))
        elif not text:
            line_edit_widget.blockSignals(True)
            line_edit_widget.setText("")
            line_edit_widget.blockSignals(False)

    def start_monitoring(self):
        try:
            self.futures_watch_code = self.futures_watch_code_input.text().strip()
            self.futures_trigger_price = float(self.futures_trigger_price_input.text())

            self.option1_code = self.option1_code_input.text().strip()
            option1_amount_text = self.option1_amount_input.text().replace(",", "")
            if not option1_amount_text or not option1_amount_text.isdigit() or int(option1_amount_text) == 0:
                self.text_edit.append("❌ 옵션 1 주문 금액을 올바르게 입력하세요 (0보다 큰 숫자).")
                return
            self.option1_amount = int(option1_amount_text)
            self.option1_order_type_display = self.option1_order_type_combo.currentText()
            self.option1_actual_order_type = 'sell' if self.option1_order_type_display == "매도" else 'buy'

            self.option2_code = self.option2_code_input.text().strip()
            option2_amount_text = self.option2_amount_input.text().replace(",", "")
            if not option2_amount_text or not option2_amount_text.isdigit() or int(option2_amount_text) == 0:
                self.text_edit.append("❌ 옵션 2 주문 금액을 올바르게 입력하세요 (0보다 큰 숫자).")
                return
            self.option2_amount = int(option2_amount_text)
            self.option2_order_type_display = self.option2_order_type_combo.currentText()
            self.option2_actual_order_type = 'sell' if self.option2_order_type_display == "매도" else 'buy'

            if not self.futures_watch_code or not self.option1_code or not self.option2_code:
                self.text_edit.append("❌ 선물 및 옵션 코드를 모두 입력하세요.")
                return

            end_hour = int(self.end_hour_combo.currentText())
            end_minute = int(self.end_minute_combo.currentText())
            self.end_time = QTime(end_hour, end_minute, 0)
            self.orders_placed_this_trigger = False

            self.text_edit.append(f"\n📌 [{APP_NAME}] 감시 설정 완료 및 시작")
            self.text_edit.append(f"📍 감시 선물 코드: {self.futures_watch_code}")
            self.text_edit.append(f"🎯 선물 트리거 가격: {self.futures_trigger_price:.2f}")
            self.text_edit.append(f"--- 옵션 1 ({self.option1_order_type_display}) ---")
            self.text_edit.append(f"🏷️ 코드: {self.option1_code}, 💵 주문금액: {self.option1_amount:,} 원")
            self.text_edit.append(f"--- 옵션 2 ({self.option2_order_type_display}) ---")
            self.text_edit.append(f"🏷️ 코드: {self.option2_code}, 💵 주문금액: {self.option2_amount:,} 원")
            self.text_edit.append(
                f"⏱ 감시 시작 (인터벌: {self.interval_combo.currentText()}초, 종료 예정: {self.end_time.toString('HH:mm')})...\n")

            self.last_log_time = 0
            self.previous_watch_price = None
            self.timer.start(int(self.interval_combo.currentText()) * 1000)
        except ValueError:
            self.text_edit.append("❌ 입력 오류: 숫자 형식을 확인하세요 (트리거 가격 등).")
        except Exception as e:
            self.text_edit.append(f"❌ 시작 중 오류 발생: {e}")

    def stop_monitoring(self):
        self.timer.stop()
        self.text_edit.append(f"🛑 [{APP_NAME}] 감시 중지됨.\n")

    def fetch_market_data(self):
        if self.orders_placed_this_trigger:
            return

        current_time_val = time.time()
        interval_seconds = int(self.interval_combo.currentText())
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_time_val))

        futures_current_price = get_current_price(self.futures_watch_code)
        option1_current_price_for_log = get_current_price(self.option1_code)
        option2_current_price_for_log = get_current_price(self.option2_code)

        if isinstance(futures_current_price, float):
            formatted_futures_price = f"{futures_current_price:.2f}"
            log_opt1_price = f"{option1_current_price_for_log:.2f}" if isinstance(option1_current_price_for_log,
                                                                                  float) else str(
                option1_current_price_for_log)
            log_opt2_price = f"{option2_current_price_for_log:.2f}" if isinstance(option2_current_price_for_log,
                                                                                  float) else str(
                option2_current_price_for_log)

            if self.last_log_time == 0 or (current_time_val - self.last_log_time >= interval_seconds):
                self.log_count += 1
                background = "#f0f0f0" if self.log_count % 2 == 0 else "transparent"

                # "주문대기" 문구 제거하고, "매도" 또는 "매수"만 표시
                option1_status_display = self.option1_order_type_display
                option2_status_display = self.option2_order_type_display

                snapshot_line = (
                    f"<div style='background-color:{background}; padding:2px;'>"
                    f"[{timestamp}] 감시선물({self.futures_watch_code}): {formatted_futures_price} | "
                    f"옵션1({self.option1_code}, {option1_status_display}): {log_opt1_price} | "
                    f"옵션2({self.option2_code}, {option2_status_display}): {log_opt2_price}"
                    f"</div>"
                )
                self.text_edit.append(snapshot_line)
                self.last_log_time = current_time_val

            triggered = False
            trigger_reason = ""

            if self.previous_watch_price is not None and self.futures_trigger_price is not None:
                if self.previous_watch_price < self.futures_trigger_price and futures_current_price > self.futures_trigger_price:
                    triggered = True
                    trigger_reason = "아래 → 위 통과"
                elif self.previous_watch_price > self.futures_trigger_price and futures_current_price < self.futures_trigger_price:
                    triggered = True
                    trigger_reason = "위 → 아래 통과"
                elif abs(futures_current_price - self.futures_trigger_price) < 0.001:
                    if self.previous_watch_price is None or abs(
                            self.previous_watch_price - self.futures_trigger_price) >= 0.001:
                        triggered = True
                        trigger_reason = "정확히 도달"

            if self.previous_watch_price is None and self.futures_trigger_price is not None:
                if abs(futures_current_price - self.futures_trigger_price) < 0.001:
                    triggered = True
                    trigger_reason = "시작 시 정확히 도달"

            if triggered and not self.orders_placed_this_trigger:
                self.orders_placed_this_trigger = True
                self.text_edit.append(f"\n🔔 [{APP_NAME}] 트리거 감지! ({trigger_reason})")
                self.text_edit.append(f"⏰ 감지 시간: {timestamp}")
                self.text_edit.append(f"🎯 감시 선물 ({self.futures_watch_code}) 트리거 시 가격: {formatted_futures_price}")

                opt1_price_for_order = get_current_price(self.option1_code)
                opt2_price_for_order = get_current_price(self.option2_code)

                telegram_base_msg = (
                    f"[{APP_NAME} 알림]\n"
                    f"🔔 트리거 발생! ({trigger_reason})\n"
                    f"⏰ 시간: {timestamp}\n"
                    f"👀 감시 선물: {self.futures_watch_code}\n"
                    f"  - 트리거 설정가: {self.futures_trigger_price:.2f}\n"
                    f"  - 현재가: {formatted_futures_price}\n"
                )

                if isinstance(opt1_price_for_order, float) and opt1_price_for_order > 0:
                    quantity1 = int(self.option1_amount // (opt1_price_for_order * self.contract_unit))
                    self.text_edit.append(f"\n--- 옵션 1 ({self.option1_order_type_display}) 주문 준비 ---")
                    self.text_edit.append(f"🛒 코드: {self.option1_code}, 현재가: {opt1_price_for_order:.2f}")
                    self.text_edit.append(f"💰 주문금액: {self.option1_amount:,} 원, 계산된 수량: {quantity1}")
                    telegram_base_msg += (
                        f"\n--- 옵션 1 ({self.option1_order_type_display}) ---\n"
                        f"  - 코드: {self.option1_code}, 현재가: {opt1_price_for_order:.2f}\n"
                        f"  - 주문금액: {self.option1_amount:,} 원, 예상수량: {quantity1}\n"
                    )
                    if quantity1 > 0:
                        self.execute_single_option_order(self.option1_code, self.option1_actual_order_type,
                                                         opt1_price_for_order, quantity1,
                                                         f"옵션 1 ({self.option1_order_type_display})")
                    else:
                        no_qty_msg = f"⚠️ 옵션 1 ({self.option1_order_type_display}): 계산된 주문 수량이 0입니다. 주문을 실행하지 않습니다."
                        self.text_edit.append(no_qty_msg)
                        telegram_base_msg += f"  {no_qty_msg}\n"
                else:
                    price_err_msg = f"⚠️ 옵션 1 ({self.option1_code}, {self.option1_order_type_display}): 현재가 조회 실패 또는 유효하지 않은 가격 ({opt1_price_for_order}). 주문 미실행."
                    self.text_edit.append(price_err_msg)
                    telegram_base_msg += f"\n--- 옵션 1 ({self.option1_order_type_display}) ---\n  {price_err_msg}\n"

                if isinstance(opt2_price_for_order, float) and opt2_price_for_order > 0:
                    quantity2 = int(self.option2_amount // (opt2_price_for_order * self.contract_unit))
                    self.text_edit.append(f"\n--- 옵션 2 ({self.option2_order_type_display}) 주문 준비 ---")
                    self.text_edit.append(f"🛒 코드: {self.option2_code}, 현재가: {opt2_price_for_order:.2f}")
                    self.text_edit.append(f"💰 주문금액: {self.option2_amount:,} 원, 계산된 수량: {quantity2}")
                    telegram_base_msg += (
                        f"\n--- 옵션 2 ({self.option2_order_type_display}) ---\n"
                        f"  - 코드: {self.option2_code}, 현재가: {opt2_price_for_order:.2f}\n"
                        f"  - 주문금액: {self.option2_amount:,} 원, 예상수량: {quantity2}\n"
                    )
                    if quantity2 > 0:
                        self.execute_single_option_order(self.option2_code, self.option2_actual_order_type,
                                                         opt2_price_for_order, quantity2,
                                                         f"옵션 2 ({self.option2_order_type_display})")
                    else:
                        no_qty_msg = f"⚠️ 옵션 2 ({self.option2_order_type_display}): 계산된 주문 수량이 0입니다. 주문을 실행하지 않습니다."
                        self.text_edit.append(no_qty_msg)
                        telegram_base_msg += f"  {no_qty_msg}\n"
                else:
                    price_err_msg = f"⚠️ 옵션 2 ({self.option2_code}, {self.option2_order_type_display}): 현재가 조회 실패 또는 유효하지 않은 가격 ({opt2_price_for_order}). 주문 미실행."
                    self.text_edit.append(price_err_msg)
                    telegram_base_msg += f"\n--- 옵션 2 ({self.option2_order_type_display}) ---\n  {price_err_msg}\n"

                try:
                    send_telegram_message(telegram_base_msg + f"\n\n[{APP_NAME}] 상세 주문 결과는 개별적으로 전송됩니다.")
                except Exception as e:
                    self.text_edit.append(f"텔레그램 (트리거 요약) 알림 전송 실패: {e}")

                self.stop_monitoring()

            self.previous_watch_price = futures_current_price
        else:
            error_msg = f"⚠️ 선물 가격 조회 실패 - ({self.futures_watch_code}): {futures_current_price}"
            self.text_edit.append(error_msg)
            self.previous_watch_price = None

        if self.end_time is not None and QTime.currentTime() >= self.end_time:
            if self.timer.isActive():
                self.text_edit.append(f"\n⏱️ [{APP_NAME}] 감시 종료 시간에 도달하여 모니터링을 중지합니다.")
                self.stop_monitoring()
                try:
                    send_telegram_message(f"[{APP_NAME} 알림]\n⏱️ 감시 종료 시간에 도달하여 모니터링을 중지합니다.")
                except Exception as e:
                    self.text_edit.append(f"텔레그램 (종료) 알림 전송 실패: {e}")

    def execute_single_option_order(self, option_code, order_type, initial_price, total_quantity, option_label=""):
        objOrder = CpFutureOptionOrder()
        split_quantity_base = total_quantity // 3
        remaining_quantity_after_split = total_quantity % 3

        log_prefix = f"\n📦 [{APP_NAME} - {option_label} 분할 주문 처리]"
        self.text_edit.append(log_prefix)
        self.text_edit.append(f"📝 총 주문 수량: {total_quantity} (코드: {option_code})")
        self.text_edit.append(f"쪼개진 주문 수량 (기본): {split_quantity_base} (나머지: {remaining_quantity_after_split})")

        telegram_order_details = [f"\n{log_prefix} (총 {total_quantity}개, 코드: {option_code})"]

        for i in range(3):
            current_order_quantity = split_quantity_base
            if i < remaining_quantity_after_split:
                current_order_quantity += 1

            if current_order_quantity > 0:
                order_price_adj = initial_price
                order_type_str_display = "매수" if order_type == 'buy' else "매도"

                if order_type == 'buy':
                    order_price_adj += 0.01 * i
                else:
                    order_price_adj -= 0.01 * i

                order_price_adj = max(0.01, round(order_price_adj, 2))
                formatted_price_adj = f"{order_price_adj:.2f}"

                retOrder = {}
                success = False

                order_attempt_log = f"\n📤 [{i + 1}/3] {order_type_str_display} 분할 주문 (수량: {current_order_quantity}, 가격: {formatted_price_adj})"
                self.text_edit.append(order_attempt_log)
                telegram_order_details.append(order_attempt_log.replace("\n", ""))

                if order_type == 'buy':
                    success = objOrder.buyOrder(option_code, order_price_adj, current_order_quantity, retOrder)
                else:
                    success = objOrder.sellOrder(option_code, order_price_adj, current_order_quantity, retOrder)

                if success:
                    success_log = (
                        f"✅ {order_type_str_display} 주문 성공!\n"
                        f"🟢 옵션: {option_code}\n"
                        f"📊 수량: {current_order_quantity} | 가격: {formatted_price_adj}\n"
                        f"📨 주문 응답: {retOrder}"
                    )
                    self.text_edit.append(success_log)
                    telegram_order_details.append(f"  ✅ 성공! 응답: {retOrder}")
                else:
                    fail_log = (
                        f"❌ {order_type_str_display} 주문 실패\n"
                        f"📨 주문 응답: {retOrder}"
                    )
                    self.text_edit.append(fail_log)
                    telegram_order_details.append(f"  ❌ 실패. 응답: {retOrder}")
            else:
                no_qty_log = f"\n⚠️ [{i + 1}/3] 주문할 수량이 없습니다 (해당 차수 건너뜀)."
                self.text_edit.append(no_qty_log)
                telegram_order_details.append(no_qty_log.replace("\n", "") + " (해당 차수 건너뜀)")

        try:
            final_telegram_msg = "\n".join(telegram_order_details)
            send_telegram_message(f"[{APP_NAME} 주문 결과]\n{final_telegram_msg}")
            self.text_edit.append(f"✉️ {option_label} 분할 주문 결과 텔레그램 전송 완료.")
        except Exception as e:
            self.text_edit.append(f"텔레그램 ({option_label} 분할 주문 결과) 알림 전송 실패: {e}")


if __name__ == "__main__":
    if not InitPlusCheck():  # 실제 환경에서는 이 함수가 True를 반환해야 합니다.
        # print("PLUS 연결 실패. 프로그램을 종료합니다.") # InitPlusCheck 내부에서 메시지 처리 가정
        exit()

    app = QApplication(sys.argv)
    window = TR_SpreadbyFcpApp()
    window.show()
    sys.exit(app.exec_())