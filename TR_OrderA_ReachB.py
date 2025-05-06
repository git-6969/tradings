import sys
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QLineEdit, QPushButton, QComboBox, QTimeEdit
)
from PyQt5.QtCore import Qt, QTimer, QCoreApplication, QTime
from Comms_Class import InitPlusCheck
from Comms_Class import CpOptionMst
from Comms_Class import CpFutureOptionOrder

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
        for i in range(31):
            self.interval_combo.addItem(f"{i:02d}")

        self.end_hour_combo.setCurrentText(f"{QTime.currentTime().hour():02d}")
        self.end_minute_combo.setCurrentText(f"{QTime.currentTime().minute():02d}")
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

    def start_trading(self):
        try:
            self.watch_code = self.watch_code_input.text().strip()
            self.order_code = self.order_code_input.text().strip()
            self.option_trigger_price = float(self.trigger_price_input.text())
            self.order_amount = int(self.order_amount_input.text().replace(",", ""))
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
            self.timer.start(int(self.interval_combo.currentText()) * 1000)
        except ValueError:
            self.text_edit.append("❌ 입력 오류: 숫자 형식을 확인하세요.")

    def stop_trading(self):
        self.timer.stop()
        self.text_edit.append("🛑 감시 중지됨.\n")

    def fetch_prices(self):
        current_time = time.time()
        interval = int(self.interval_combo.currentText())

        watch_price = self.get_option_price(self.watch_code)
        order_price = self.get_option_price(self.order_code)
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

        if isinstance(watch_price, float) and isinstance(order_price, float):
            formatted_watch_price = f"{watch_price:.2f}"
            formatted_order_price = f"{order_price:.2f}"

            # 처음 호출되거나 설정된 인터벌 시간이 지났으면 로그 기록
            if current_time - self.last_log_time >= interval or self.last_log_time == 0:
                self.log_count += 1
                background = "#f0f0f0" if self.log_count % 2 == 0 else "transparent"

                snapshot_line = (
                    f"<div style='background-color:{background}; padding:2px;'>"
                    f"[{timestamp}] 감시 옵션({self.watch_code}) 현재가: {formatted_watch_price} | "
                    f"주문 옵션({self.order_code}) 현재가: {formatted_order_price}"
                    f"</div>"
                )
                self.text_edit.append(snapshot_line)
                self.last_log_time = current_time  # 마지막 로그 기록 시간 업데이트

            # 트리거 가격 감지 및 주문 로직
            if abs(watch_price - self.option_trigger_price) < 0.01:
                quantity = int(self.order_amount // (order_price * self.contract_unit))

                self.text_edit.append("\n🚨 [트리거 감지]")
                self.text_edit.append(f"⏰ 감지 시간: {timestamp}")
                self.text_edit.append(f"🎯 감시 옵션 ({self.watch_code}) 가격: {formatted_watch_price}")
                self.text_edit.append(f"🛒 주문 옵션 ({self.order_code}) 가격: {formatted_order_price}")
                self.text_edit.append(f"💰 주문 수량: {quantity} | 주문 가격: {formatted_order_price}")
                self.text_edit.append(f"📤 주문 유형: {'매수' if self.order_type == 'buy' else '매도'}")

                if quantity > 0:
                    self.place_option_order(order_price, quantity) # 현재 주문 옵션 가격을 초기 가격으로 전달
                else:
                    self.text_edit.append("⚠️ 주문 수량이 0입니다. 금액을 늘리세요.")
                    self.timer.stop()
        else:
            self.text_edit.append(f"⚠️ 가격 조회 실패 (감시: {watch_price}, 주문: {order_price})")

        # 감시 종료 시간 확인
        if self.end_time is not None and QTime.currentTime() >= self.end_time:
            self.text_edit.append("\n⏱️ 감시 종료 시간에 도달하여 모니터링을 중지합니다.")
            self.stop_trading()

    def get_option_price(self, code):
        objOptionMst = CpOptionMst()
        retItem = {}
        if objOptionMst.request(code, retItem):
            current_price = retItem.get('현재가', '정보 없음')
            if isinstance(current_price, (int, float)):
                return round(current_price, 2)
            return "옵션 현재가 조회 실패"
        else:
            return "옵션 현재가 조회 실패"

    def place_option_order(self, initial_price, total_quantity):
        objOrder = CpFutureOptionOrder()
        split_quantity = total_quantity // 3
        remaining_quantity = total_quantity % 3

        self.text_edit.append("\n📦 [분할 주문 처리 시작]")
        self.text_edit.append(f"📝 총 주문 수량: {total_quantity}")
        self.text_edit.append(f"쪼개진 주문 수량: {split_quantity} (나머지: {remaining_quantity})")

        for i in range(3):
            current_order_quantity = split_quantity
            if i < remaining_quantity:
                current_order_quantity += 1

            if current_order_quantity > 0:
                order_price = initial_price
                if self.order_type == 'buy':
                    order_price += 0.01 * i
                    order_type_str = "매수"
                else:
                    order_price -= 0.01 * i
                    order_type_str = "매도"

                formatted_price = f"{order_price:.2f}"
                retOrder = {}

                if self.order_type == 'buy':
                    success = objOrder.buyOrder(self.order_code, order_price, current_order_quantity, retOrder)
                else:
                    success = objOrder.sellOrder(self.order_code, order_price, current_order_quantity, retOrder)

                self.text_edit.append(f"\n📤 [{i+1}/3] {order_type_str} 분할 주문 시도 (수량: {current_order_quantity}, 가격: {formatted_price})")

                if success:
                    self.text_edit.append(f"✅ {order_type_str} 주문 성공!")
                    self.text_edit.append(f"🟢 주문 옵션: {self.order_code}")
                    self.text_edit.append(f"📊 수량: {current_order_quantity} | 가격: {formatted_price}")
                    self.text_edit.append(f"📨 주문 응답: {retOrder}")
                else:
                    self.text_edit.append(f"❌ {order_type_str} 주문 실패")
                    self.text_edit.append(f"📨 주문 응답: {retOrder}")
            else:
                self.text_edit.append(f"\n⚠️ [{i+1}/3] 주문할 수량이 없습니다.")

        self.timer.stop()


if __name__ == "__main__":
    if not InitPlusCheck():
        exit()

    app = QApplication(sys.argv)
    window = FutureOptionApp()
    window.show()
    sys.exit(app.exec_())