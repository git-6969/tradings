import sys
import time
import multiprocessing
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit,
    QTextEdit, QGridLayout, QDesktopWidget
)
from PyQt5.QtCore import Qt
from Comms_Class import InitPlusCheck, CpOptionMst, CpFutureOptionOrder, g_objCpTrade, g_objCpTdUtil

# 매도 비율 설정 (예: 3분할)
SPLIT_COUNT = 3

def initialize_creon():
    g_objCpTdUtil.TradeInit()

def get_option_price(option_code):
    objOptionMst = CpOptionMst()
    retItem = {}
    if objOptionMst.request(option_code, retItem):
        return retItem.get('현재가', 0)
    else:
        return 0

def calculate_sell_quantity(option_price, target_sell_amount):
    cost_per_option = option_price * 250000
    return target_sell_amount // cost_per_option if cost_per_option > 0 else 0

def place_option_order(option_code, price, sell_quantity, queue):
    if sell_quantity > 0:
        log = f"[주문 시도] {option_code} {sell_quantity}개 매도 (가격: {price})"
        retData = {}
        try:
            objOrder = CpFutureOptionOrder()
            success = objOrder.sellOrder(option_code, price, sell_quantity, retData)
            if success:
                log += f"\n[주문 성공] {option_code} {sell_quantity}개 매도 완료 (가격: {price})"
            else:
                log += f"\n[주문 실패] {option_code} 매도 실패\n사유: {retData}"
        except Exception as e:
            log += f"\n[예외 발생] {str(e)}"
    else:
        log = f"[주문 오류] {option_code} 매도 수량이 0개 이하입니다."
    queue.put(log)

def run_sell_process(option_code, target_sell_amount, queue):
    initialize_creon()
    option_price = get_option_price(option_code)
    if option_price == 0:
        queue.put(f"[오류] {option_code} 현재가 조회 실패")
        return

    total_sell_qty = calculate_sell_quantity(option_price, target_sell_amount)
    slice_qty = total_sell_qty // SPLIT_COUNT
    remainder = total_sell_qty % SPLIT_COUNT

    queue.put(f"[주문 준비] 옵션: {option_code}, 현재가: {option_price}, 총 수량: {total_sell_qty}, 분할 수: {SPLIT_COUNT}")

    for i in range(SPLIT_COUNT):
        qty = slice_qty + (1 if i == SPLIT_COUNT - 1 else 0) + (remainder if i == 0 else 0)
        updated_price = get_option_price(option_code)
        if updated_price != option_price:
            queue.put(f"[이슬피지] 가격 차이 발생 - 기존: {option_price}, 변경: {updated_price}")
        place_option_order(option_code, updated_price, qty, queue)

class FutureOptionApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("옵션 매도 도구")
        self.resize(1200, 300 * 3)  # 가로 크기 2/3, 세로 3배로 조정
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

        layout = QVBoxLayout()

        grid = QGridLayout()
        grid.addWidget(QLabel("옵션 코드 1"), 0, 0)
        self.option_code_input_1 = QLineEdit("209DP332")
        grid.addWidget(self.option_code_input_1, 0, 1)

        grid.addWidget(QLabel("금액 1"), 0, 2)
        self.amount_input_1 = QLineEdit("3000000")
        grid.addWidget(self.amount_input_1, 0, 3)

        grid.addWidget(QLabel("옵션 코드 2"), 1, 0)
        self.option_code_input_2 = QLineEdit("309DP330")
        grid.addWidget(self.option_code_input_2, 1, 1)

        grid.addWidget(QLabel("금액 2"), 1, 2)
        self.amount_input_2 = QLineEdit("3000000")
        grid.addWidget(self.amount_input_2, 1, 3)

        layout.addLayout(grid)

        self.start_button = QPushButton("옵션 매도 실행")
        self.start_button.clicked.connect(self.execute_sell_orders)
        layout.addWidget(self.start_button)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        self.setLayout(layout)

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_output.append(f"[{timestamp}] {message}")

    def execute_sell_orders(self):
        option_code_1 = self.option_code_input_1.text()
        amount_1 = int(self.amount_input_1.text())
        option_code_2 = self.option_code_input_2.text()
        amount_2 = int(self.amount_input_2.text())

        queue = multiprocessing.Queue()
        p1 = multiprocessing.Process(target=run_sell_process, args=(option_code_1, amount_1, queue))
        p2 = multiprocessing.Process(target=run_sell_process, args=(option_code_2, amount_2, queue))

        p1.start()
        p2.start()

        while p1.is_alive() or p2.is_alive() or not queue.empty():
            while not queue.empty():
                self.log(queue.get())
            time.sleep(0.1)

        p1.join()
        p2.join()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    if not InitPlusCheck():
        sys.exit(0)

    app = QApplication(sys.argv)
    window = FutureOptionApp()
    window.show()
    sys.exit(app.exec_())
