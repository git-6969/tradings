import sys
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QLineEdit, QPushButton, QComboBox
)
from PyQt5.QtCore import Qt, QTimer, QCoreApplication, QThread, pyqtSignal
from Comms_Class import InitPlusCheck
from Comms_Class import CpOptionMst
from Comms_Class import CpFutureMst
from Comms_Class import CpFutureOptionOrder


WATCH_INTERVAL = 3  # 감시 주기 (초)


class PriceWatcherThread(QThread):
    price_signal = pyqtSignal(float, float, float)

    def __init__(self, future_code, option1_code, option2_code, parent=None):
        super().__init__(parent)
        self.future_code = future_code
        self.option1_code = option1_code
        self.option2_code = option2_code
        self.running = True

    def run(self):
        future_mst = CpFutureMst()
        option_mst = CpOptionMst()
        while self.running:
            future_item, opt1_item, opt2_item = {}, {}, {}
            future_mst.request(self.future_code, future_item)
            option_mst.request(self.option1_code, opt1_item)
            option_mst.request(self.option2_code, opt2_item)

            future_price = future_item.get('현재가', 0)
            opt1_price = opt1_item.get('현재가', 0)
            opt2_price = opt2_item.get('현재가', 0)

            self.price_signal.emit(future_price, opt1_price, opt2_price)
            time.sleep(WATCH_INTERVAL)

    def stop(self):
        self.running = False


class FutureOptionApp(QWidget):
    contract_unit = 250000

    def __init__(self):
        super().__init__()

        self.setWindowTitle("OpSpreadbyFcp")
        self.setGeometry(0, 0, 1600, 600)
        self.move(QApplication.desktop().screen().rect().center() - self.rect().center())

        self.layout = QVBoxLayout()
        self.log_count = 0

        top_row = QHBoxLayout()
        self.future_code_input = QLineEdit()
        self.future_code_input.setPlaceholderText("감시 선물 코드")
        self.trigger_price_input = QLineEdit()
        self.trigger_price_input.setPlaceholderText("트리거 가격")
        self.trigger_type_combo = QComboBox()
        self.trigger_type_combo.addItems(["이상", "이하"])

        top_row.addWidget(QLabel("감시 선물:"))
        top_row.addWidget(self.future_code_input)
        top_row.addWidget(QLabel("트리거 가격:"))
        top_row.addWidget(self.trigger_price_input)
        top_row.addWidget(self.trigger_type_combo)

        option_row = QHBoxLayout()
        self.opt1_code_input = QLineEdit()
        self.opt1_code_input.setPlaceholderText("옵션1 코드")
        self.opt1_amount_input = QLineEdit()
        self.opt1_amount_input.setPlaceholderText("금액")
        self.opt1_amount_input.textChanged.connect(self.format_amount_input)
        self.opt1_type_combo = QComboBox()
        self.opt1_type_combo.addItems(["buy", "sell"])

        self.opt2_code_input = QLineEdit()
        self.opt2_code_input.setPlaceholderText("옵션2 코드")
        self.opt2_amount_input = QLineEdit()
        self.opt2_amount_input.setPlaceholderText("금액")
        self.opt2_amount_input.textChanged.connect(self.format_amount_input)
        self.opt2_type_combo = QComboBox()
        self.opt2_type_combo.addItems(["buy", "sell"])

        option_row.addWidget(QLabel("옵션1:"))
        option_row.addWidget(self.opt1_code_input)
        option_row.addWidget(self.opt1_amount_input)
        option_row.addWidget(self.opt1_type_combo)
        option_row.addWidget(QLabel("옵션2:"))
        option_row.addWidget(self.opt2_code_input)
        option_row.addWidget(self.opt2_amount_input)
        option_row.addWidget(self.opt2_type_combo)

        button_row = QHBoxLayout()
        self.start_button = QPushButton("모니터링 시작")
        self.stop_button = QPushButton("중지")
        self.exit_button = QPushButton("종료")
        button_row.addWidget(self.start_button)
        button_row.addWidget(self.stop_button)
        button_row.addWidget(self.exit_button)

        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)

        self.layout.addLayout(top_row)
        self.layout.addLayout(option_row)
        self.layout.addLayout(button_row)
        self.layout.addWidget(self.text_edit)
        self.setLayout(self.layout)

        self.start_button.clicked.connect(self.start_monitoring)
        self.stop_button.clicked.connect(self.stop_monitoring)
        self.exit_button.clicked.connect(QCoreApplication.quit)

        self.thread = None

    def format_amount_input(self):
        sender = self.sender()
        text = sender.text().replace(",", "").strip()

        if text.isdigit():
            formatted = f"{int(text):,}"
            sender.blockSignals(True)
            sender.setText(formatted)
            sender.blockSignals(False)

    def start_monitoring(self):
        self.future_code = self.future_code_input.text().strip()
        self.trigger_price = float(self.trigger_price_input.text().replace(",", ""))
        self.trigger_type = self.trigger_type_combo.currentText()

        self.opt1_code = self.opt1_code_input.text().strip()
        self.opt2_code = self.opt2_code_input.text().strip()

        self.opt1_amount = int(self.opt1_amount_input.text().replace(",", ""))
        self.opt2_amount = int(self.opt2_amount_input.text().replace(",", ""))
        self.opt1_type = self.opt1_type_combo.currentText()
        self.opt2_type = self.opt2_type_combo.currentText()

        self.text_edit.append(f"\n📌 감시 시작: 선물({self.future_code}) 트리거 {self.trigger_type} {self.trigger_price:.2f}")

        self.thread = PriceWatcherThread(self.future_code, self.opt1_code, self.opt2_code)
        self.thread.price_signal.connect(self.handle_price_update)
        self.thread.start()

    def stop_monitoring(self):
        if self.thread:
            self.thread.stop()
            self.thread.wait()
            self.thread = None
        self.text_edit.append("🛑 감시 중지됨.")

    def handle_price_update(self, future_price, opt1_price, opt2_price):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        self.log_count += 1
        background = "#f0f0f0" if self.log_count % 2 == 0 else "transparent"
        snapshot_line = (
            f"<div style='background-color:{background}; padding:2px;'>"
            f"[{timestamp}] 감시 선물({self.future_code}) 현재가: {future_price:.2f} | "
            f"옵션1({self.opt1_code}): {opt1_price:.2f} | 옵션2({self.opt2_code}): {opt2_price:.2f}"
            f"</div>"
        )
        self.text_edit.append(snapshot_line)

        trigger_hit = (
            (self.trigger_type == "이상" and future_price >= self.trigger_price) or
            (self.trigger_type == "이하" and future_price <= self.trigger_price)
        )

        if trigger_hit:
            self.text_edit.append(f"🚨 트리거 조건 만족 ({self.trigger_type}) - 주문 실행 중...")
            self.thread.stop()
            self.execute_order(self.opt1_code, opt1_price, self.opt1_amount, self.opt1_type)
            self.execute_order(self.opt2_code, opt2_price, self.opt2_amount, self.opt2_type)

    def execute_order(self, code, price, amount, order_type):
        quantity = int(amount // (price * self.contract_unit))
        objOrder = CpFutureOptionOrder()
        retOrder = {}

        if quantity <= 0:
            self.text_edit.append(f"⚠️ {code} 주문 수량 0 - 금액 부족")
            return

        success = objOrder.buyOrder(code, price, quantity, retOrder) if order_type == 'buy' \
                  else objOrder.sellOrder(code, price, quantity, retOrder)

        if success:
            self.text_edit.append(f"✅ {code} {order_type.upper()} 주문 성공: {quantity} @ {price:.2f}")
        else:
            self.text_edit.append(f"❌ {code} {order_type.upper()} 주문 실패")
        self.text_edit.append(f"📨 응답: {retOrder}")


if __name__ == "__main__":
    if not InitPlusCheck():
        exit()

    app = QApplication(sys.argv)
    window = FutureOptionApp()
    window.show()
    sys.exit(app.exec_())