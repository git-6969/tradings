import sys
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QLineEdit, QPushButton, QComboBox, QTimeEdit
)
from PyQt5.QtCore import Qt, QTimer, QCoreApplication, QTime
from Comms_Class import InitPlusCheck, get_current_price
from Comms_Class import CpOptionMst  # 이 줄은 실제 사용되지 않으면 제거 가능
from Comms_Class import CpFutureOptionOrder
from Comms_Class import send_telegram_message  # 텔레그램 메시지 함수 임포트


# 분할 매수/매도 기능 설명:
# 트리거 가격에 도달하면 설정된 총 주문 수량을 3등분하여 주문을 실행합니다.
# 매수 주문 시에는 첫 번째 주문은 트리거 시점의 가격으로,
# 두 번째 주문은 첫 번째 가격보다 0.01 증가된 가격으로,
# 세 번째 주문은 첫 번째 가격보다 0.02 증가된 가격으로 시도합니다.
# 매도 주문 시에는 첫 번째 주문은 트리거 시점의 가격으로,
# 두 번째 주문은 첫 번째 가격보다 0.01 감소된 가격으로,
# 세 번째 주문은 첫 번째 가격보다 0.02 감소된 가격으로 시도합니다.

class FutureOptionApp(QWidget):
    contract_unit = 250000  # 옵션 1계약 단위 금액

    def __init__(self):
        super().__init__()

        self.setWindowTitle("OrderA_ReachB")
        self.setGeometry(140, 60, 1600, 600)
        self.move(
            QApplication.desktop().screen().rect().center() - self.rect().center()
        )
        self.layout = QVBoxLayout()
        self.log_count = 0  # 로그 줄 수 카운터
        self.last_log_time = 0  # 마지막 로그 기록 시간 초기화
        self.previous_watch_price = None  # 이전 감시 가격 초기화

        # ✅ 감시 옵션 + 트리거 가격 (1줄)
        top_row = QHBoxLayout()
        self.watch_code_input = QLineEdit()
        self.watch_code_input.setPlaceholderText("감시 옵션 코드")
        self.trigger_price_input = QLineEdit()
        self.trigger_price_input.setPlaceholderText("트리거 가격")
        top_row.addWidget(QLabel("감시 옵션:"))
        top_row.addWidget(self.watch_code_input)
        top_row.addWidget(QLabel("트리거 가격:"))
        top_row.addWidget(self.trigger_price_input)

        # ✅ 주문 옵션 + 주문 금액 + 주문유형 + 버튼 (2줄)
        bottom_row = QHBoxLayout()
        self.order_code_input = QLineEdit()
        self.order_code_input.setPlaceholderText("주문 옵션 코드")
        self.order_amount_input = QLineEdit()
        self.order_amount_input.setPlaceholderText("주문 금액 (원)")
        self.order_amount_input.textChanged.connect(self.format_amount_input)
        self.order_type_combo = QComboBox()
        self.order_type_combo.addItems(["buy", "sell"])

        self.start_button = QPushButton("모니터링")
        self.stop_button = QPushButton("중지")
        self.exit_button = QPushButton("종료")

        self.start_button.clicked.connect(self.start_trading)
        self.stop_button.clicked.connect(self.stop_trading)
        self.exit_button.clicked.connect(QCoreApplication.quit)

        bottom_row.addWidget(QLabel("주문 옵션:"))
        bottom_row.addWidget(self.order_code_input)
        bottom_row.addWidget(QLabel("금액:"))
        bottom_row.addWidget(self.order_amount_input)
        bottom_row.addWidget(QLabel("유형:"))
        bottom_row.addWidget(self.order_type_combo)

        # ✅ 종료 시간 선택 UI
        time_row = QHBoxLayout()
        self.end_hour_combo = QComboBox()
        self.end_minute_combo = QComboBox()
        self.interval_combo = QComboBox()  # 감시 인터벌 드롭다운

        # 시간 드롭다운 (00~23)
        for i in range(24):
            self.end_hour_combo.addItem(f"{i:02d}")

        # 분 드롭다운 (00~59)
        for i in range(60):
            self.end_minute_combo.addItem(f"{i:02d}")

        # 감시 인터벌 드롭다운 (0~30초)
        for i in range(31):  # 0초 포함
            self.interval_combo.addItem(f"{i:02d}")

        default_end_time = QTime(10, 57, 0)  # 기본 종료 시간: 10시 57분 0초
        self.end_hour_combo.setCurrentText(default_end_time.toString("hh"))
        self.end_minute_combo.setCurrentText(default_end_time.toString("mm"))
        self.interval_combo.setCurrentText("03")  # 기본값 3초

        time_row.addWidget(QLabel("감시 종료 시간:"))
        time_row.addWidget(self.end_hour_combo)
        time_row.addWidget(QLabel("시"))
        time_row.addWidget(self.end_minute_combo)
        time_row.addWidget(QLabel("분"))
        time_row.addWidget(QLabel("감시 인터벌:"))
        time_row.addWidget(self.interval_combo)
        time_row.addWidget(QLabel("초"))

        # ✅ 버튼 행 따로
        button_row = QHBoxLayout()
        button_row.addWidget(self.start_button)
        button_row.addWidget(self.stop_button)
        button_row.addWidget(self.exit_button)

        # ✅ 로그 출력창
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)

        # 전체 레이아웃 설정
        self.layout.addLayout(top_row)
        self.layout.addLayout(bottom_row)
        self.layout.addLayout(time_row)  # 종료 시간 UI 추가
        self.layout.addLayout(button_row)
        self.layout.addWidget(self.text_edit)
        self.setLayout(self.layout)

        # 감시 타이머 설정
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.fetch_prices)

        self.end_time = None  # 종료 시간을 초기화

    def format_amount_input(self):
        text = self.order_amount_input.text().replace(",", "")
        if text.isdigit():
            formatted = f"{int(text):,}"
            self.order_amount_input.blockSignals(True)
            self.order_amount_input.setText(formatted)
            self.order_amount_input.blockSignals(False)
        elif not text:  # 입력이 없는 경우
            self.order_amount_input.blockSignals(True)
            self.order_amount_input.setText("")
            self.order_amount_input.blockSignals(False)

    def start_trading(self):
        try:
            self.watch_code = self.watch_code_input.text().strip()
            self.order_code = self.order_code_input.text().strip()
            self.option_trigger_price = float(self.trigger_price_input.text())
            # 주문 금액 입력값이 비어있거나, 숫자가 아니거나, 0일 경우 처리
            order_amount_text = self.order_amount_input.text().replace(",", "")
            if not order_amount_text or not order_amount_text.isdigit() or int(order_amount_text) == 0:
                self.text_edit.append("❌ 주문 금액을 올바르게 입력하세요 (0보다 큰 숫자).")
                return
            self.order_amount = int(order_amount_text)

            self.order_type = self.order_type_combo.currentText()

            if not self.watch_code or not self.order_code:
                self.text_edit.append("❌ 옵션 코드를 모두 입력하세요.")
                return

            # 감시 종료 시간을 설정
            end_hour = int(self.end_hour_combo.currentText())
            end_minute = int(self.end_minute_combo.currentText())
            end_second = 0  # 초는 0으로 설정 (매 분 단위 종료)
            self.end_time = QTime(end_hour, end_minute, end_second)

            self.text_edit.append("\n📌 [감시 설정 시작]")
            self.text_edit.append(f"📍 감시 옵션 코드: {self.watch_code}")
            self.text_edit.append(f"📍 트리거 가격: {self.option_trigger_price:.2f}")
            self.text_edit.append(f"📍 주문 옵션 코드: {self.order_code}")
            self.text_edit.append(f"📍 주문 금액: {self.order_amount:,} 원")
            self.text_edit.append(f"📍 주문 유형: {'매수' if self.order_type == 'buy' else '매도'}")
            self.text_edit.append(f"⏱ 감시 시작 (인터벌: {self.interval_combo.currentText()}초)...\n")

            self.last_log_time = 0  # 시작 시 마지막 로그 시간 초기화
            self.previous_watch_price = None  # 모니터링 시작 시 이전 가격 초기화
            self.timer.start(int(self.interval_combo.currentText()) * 1000)
        except ValueError:
            self.text_edit.append("❌ 입력 오류: 숫자 형식을 확인하세요.")

    def stop_trading(self):
        self.timer.stop()
        self.text_edit.append("🛑 감시 중지됨.\n")

    def fetch_prices(self):
        current_time_val = time.time()  # time.time()은 float 반환
        interval_seconds = int(self.interval_combo.currentText())  # 사용자가 선택한 인터벌 (초)

        # QTimer의 인터벌은 밀리초 단위, fetch_prices는 QTimer에 의해 호출됨
        # 로그 기록은 사용자가 설정한 초(interval_seconds) 단위로 제어

        watch_price = get_current_price(self.watch_code)
        order_price = get_current_price(self.order_code)
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_time_val))

        if isinstance(watch_price, float) and isinstance(order_price, float):
            formatted_watch_price = f"{watch_price:.2f}"
            formatted_order_price = f"{order_price:.2f}"

            # 로그 기록 (사용자가 설정한 interval_seconds마다)
            if self.last_log_time == 0 or (current_time_val - self.last_log_time >= interval_seconds):
                self.log_count += 1
                background = "#f0f0f0" if self.log_count % 2 == 0 else "transparent"
                snapshot_line = (
                    f"<div style='background-color:{background}; padding:2px;'>"
                    f"[{timestamp}] 감시({self.watch_code}): {formatted_watch_price} | "
                    f"주문({self.order_code}): {formatted_order_price}"
                    f"</div>"
                )
                self.text_edit.append(snapshot_line)
                self.last_log_time = current_time_val  # 마지막 로그 시간 업데이트

            # 트리거 가격 감지 및 주문 로직
            triggered = False
            trigger_reason = ""  # 트리거 사유 저장 변수

            if self.previous_watch_price is not None and self.option_trigger_price is not None:
                # 아래에서 위로 통과 (이전 가격 < 트리거 가격 < 현재 가격)
                if self.previous_watch_price < self.option_trigger_price and watch_price > self.option_trigger_price:
                    trigger_log_msg = "\n🔔 [트리거 감지] (아래 → 위 통과)"
                    self.text_edit.append(trigger_log_msg)
                    triggered = True
                    trigger_reason = "아래 → 위 통과"
                # 위에서 아래로 통과 (이전 가격 > 트리거 가격 > 현재 가격)
                elif self.previous_watch_price > self.option_trigger_price and watch_price < self.option_trigger_price:
                    trigger_log_msg = "\n🔔 [트리거 감지] (위 → 아래 통과)"
                    self.text_edit.append(trigger_log_msg)
                    triggered = True
                    trigger_reason = "위 → 아래 통과"
                # 정확히 트리거 가격에 도달 (현재 가격이 트리거 가격과 거의 같음)
                elif abs(watch_price - self.option_trigger_price) < 0.001:  # 더 작은 허용 오차
                    # 단, 이전 가격이 트리거 가격과 같지 않아야 처음 도달한 것으로 간주 (선택적)
                    if self.previous_watch_price is None or abs(
                            self.previous_watch_price - self.option_trigger_price) >= 0.001:
                        trigger_log_msg = "\n🔔 [트리거 감지] (정확히 도달)"
                        self.text_edit.append(trigger_log_msg)
                        triggered = True
                        trigger_reason = "정확히 도달"

            if triggered:
                quantity = int(self.order_amount // (order_price * self.contract_unit))

                # UI 로그 추가
                self.text_edit.append(f"⏰ 감지 시간: {timestamp}")
                self.text_edit.append(
                    f"🎯 감시 옵션 ({self.watch_code}) 트리거 시 가격: {formatted_watch_price}")  # 트리거 시점의 감시 옵션 가격
                self.text_edit.append(f"🛒 주문 옵션 ({self.order_code}) 현재 가격: {formatted_order_price}")  # 주문 옵션의 현재 가격
                self.text_edit.append(f"💰 계산된 주문 수량: {quantity} (주문 금액 기준)")
                self.text_edit.append(f"📤 주문 유형: {'매수' if self.order_type == 'buy' else '매도'}")

                # --- 텔레그램 메시지 전송 ---
                telegram_msg = (
                    f"[OrderA_ReachB 알림]\n"
                    f"🔔 트리거 발생! ({trigger_reason})\n"
                    f"⏰ 시간: {timestamp}\n"
                    f"👀 감시 옵션: {self.watch_code}\n"
                    f"   - 트리거 가격: {self.option_trigger_price:.2f}\n"
                    f"   - 현재가: {formatted_watch_price}\n"
                    f"🛍️ 주문 옵션: {self.order_code}\n"
                    f"   - 현재가: {formatted_order_price}\n"
                    f"   - 주문 유형: {'매수' if self.order_type == 'buy' else '매도'}\n"
                    f"   - 주문 금액: {self.order_amount:,} 원\n"
                    f"   - 예상 수량: {quantity}"
                )

                if quantity > 0:
                    self.text_edit.append("🚀 주문 실행 시도...")
                    telegram_msg += "\n\n🚀 주문 실행 시도..."
                    try:
                        send_telegram_message(telegram_msg)
                        self.text_edit.append("✉️ 텔레그램 알림 전송 완료 (주문 시도)")
                    except Exception as e:
                        self.text_edit.append(f"텔레그램 알림 전송 실패: {e}")
                    self.place_option_order(order_price, quantity)
                else:
                    self.text_edit.append("⚠️ 주문 수량이 0입니다. 주문을 실행하지 않습니다.")
                    telegram_msg += "\n\n⚠️ 주문 수량 0. 주문 미실행."
                    try:
                        send_telegram_message(telegram_msg)
                        self.text_edit.append("✉️ 텔레그램 알림 전송 완료 (주문 미실행)")
                    except Exception as e:
                        self.text_edit.append(f"텔레그램 알림 전송 실패: {e}")
                    self.timer.stop()  # 주문 수량이 0이면 타이머 중지

            self.previous_watch_price = watch_price  # 현재 감시 가격을 이전 가격으로 저장

        else:
            error_msg = f"⚠️ 가격 조회 실패 - 감시({self.watch_code}): {watch_price}, 주문({self.order_code}): {order_price}"
            self.text_edit.append(error_msg)
            # Optionally send a Telegram message for price fetch failure if persistent
            # try:
            #     send_telegram_message(f"[OrderA_ReachB 오류]\n{error_msg}")
            # except Exception as e:
            #     self.text_edit.append(f"텔레그램 (오류) 알림 전송 실패: {e}")
            self.previous_watch_price = None  # 가격 조회 실패 시 이전 가격 정보 초기화

        # 감시 종료 시간 확인
        if self.end_time is not None and QTime.currentTime() >= self.end_time:
            self.text_edit.append("\n⏱️ 감시 종료 시간에 도달하여 모니터링을 중지합니다.")
            self.stop_trading()
            try:
                send_telegram_message("[OrderA_ReachB 알림]\n⏱️ 감시 종료 시간에 도달하여 모니터링을 중지합니다.")
            except Exception as e:
                self.text_edit.append(f"텔레그램 (종료) 알림 전송 실패: {e}")

    def place_option_order(self, initial_price, total_quantity):
        objOrder = CpFutureOptionOrder()
        split_quantity_base = total_quantity // 3
        remaining_quantity_after_split = total_quantity % 3

        self.text_edit.append("\n📦 [분할 주문 처리 시작]")
        self.text_edit.append(f"📝 총 주문 수량: {total_quantity}")
        self.text_edit.append(f"쪼개진 주문 수량 (기본): {split_quantity_base} (나머지: {remaining_quantity_after_split})")

        # 텔레그램 메시지 초기화 (분할 주문 시작 알림)
        telegram_order_details = [f"\n\n📦 [분할 주문 처리 시작] (총 {total_quantity}개)"]

        for i in range(3):
            current_order_quantity = split_quantity_base
            if i < remaining_quantity_after_split:
                current_order_quantity += 1

            if current_order_quantity > 0:
                order_price_adj = initial_price  # 기준 가격은 주문 옵션의 현재가
                order_type_str_display = ""

                if self.order_type == 'buy':
                    order_price_adj += 0.01 * i
                    order_type_str_display = "매수"
                else:  # sell
                    order_price_adj -= 0.01 * i
                    order_type_str_display = "매도"

                # 가격이 음수가 되지 않도록 보정 (최소 0.01)
                order_price_adj = max(0.01, order_price_adj)
                formatted_price_adj = f"{order_price_adj:.2f}"

                retOrder = {}
                success = False

                order_attempt_log = f"\n📤 [{i + 1}/3] {order_type_str_display} 분할 주문 시도 (수량: {current_order_quantity}, 가격: {formatted_price_adj})"
                self.text_edit.append(order_attempt_log)
                telegram_order_details.append(order_attempt_log.replace("\n", ""))

                if self.order_type == 'buy':
                    success = objOrder.buyOrder(self.order_code, order_price_adj, current_order_quantity, retOrder)
                else:  # sell
                    success = objOrder.sellOrder(self.order_code, order_price_adj, current_order_quantity, retOrder)

                if success:
                    success_log = (
                        f"✅ {order_type_str_display} 주문 성공!\n"
                        f"🟢 주문 옵션: {self.order_code}\n"
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
                no_qty_log = f"\n⚠️ [{i + 1}/3] 주문할 수량이 없습니다."
                self.text_edit.append(no_qty_log)
                telegram_order_details.append(no_qty_log.replace("\n", "") + " (해당 차수 건너뜀)")

        # 분할 주문 결과 텔레그램 전송
        try:
            final_telegram_msg = "\n".join(telegram_order_details)
            send_telegram_message(f"[OrderA_ReachB 주문 결과]\n{final_telegram_msg}")
            self.text_edit.append("✉️ 텔레그램으로 분할 주문 결과 전송 완료.")
        except Exception as e:
            self.text_edit.append(f"텔레그램 (분할 주문 결과) 알림 전송 실패: {e}")

        self.timer.stop()  # 모든 분할 주문 시도 후 타이머 중지


if __name__ == "__main__":
    # Comms_Class.py에 있는 BOT_TOKEN과 CHAT_ID가 설정되어 있는지 확인하세요.
    # 예:
    # if not Comms_Class.BOT_TOKEN or not Comms_Class.CHAT_ID:
    #     print("텔레그램 BOT_TOKEN 또는 CHAT_ID가 설정되지 않았습니다. Comms_Class.py 파일을 확인하세요.")
    #     # exit() # 필요시 종료

    if not InitPlusCheck():
        # InitPlusCheck 내부에서 이미 print로 오류를 알리므로, 추가 메시지 없이 종료
        exit()

    app = QApplication(sys.argv)
    window = FutureOptionApp()
    window.show()
    sys.exit(app.exec_())