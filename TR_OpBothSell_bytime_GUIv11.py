import sys
import schedule
import time
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QFormLayout
)
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QIntValidator
from Comms_Class import InitPlusCheck, CpOptionMst, CpFutureOptionOrder

# 매도 비율 설정
SELL_FIRST_PERCENT = 0.62
SELL_SECOND_PERCENT = 1.0 - SELL_FIRST_PERCENT

# 주문 가격 조정 (현재가보다 낮게)
ORDER_PRICE_ADJUSTMENT = 0.01

# 2차 매도 딜레이 (밀리초) - 디폴트 3초
SECOND_SELL_DELAY = 3000

# 시간 체크 간격 (밀리초) - 디폴트 1초
TIME_CHECK_INTERVAL = 3000

class FutureOptionApp:
    def __init__(self, option_code, target_sell_amount, log_widget):
        self.option_code = option_code
        self.target_sell_amount = target_sell_amount
        self.log_widget = log_widget
        self.objOrder = CpFutureOptionOrder()
        self.objOptionMst = CpOptionMst()
        self.first_sell_qty = 0
        self.second_sell_qty = 0

    def log_message(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_widget.append(log_entry)
        self.log_widget.ensureCursorVisible()

    def calculate_split_quantity(self):
        option_price = self.get_option_price(self.option_code)
        if option_price > 0:
            target_sell_amount = int(self.target_sell_amount.replace(',', ''))
            total_sell_qty = self.calculate_sell_quantity(option_price, target_sell_amount)
            self.first_sell_qty = round(total_sell_qty * SELL_FIRST_PERCENT)
            self.second_sell_qty = total_sell_qty - self.first_sell_qty
            self.log_message(f"[수량 분할] {self.option_code}: 총 {total_sell_qty} 계약, 1차 {self.first_sell_qty} 계약, 2차 {self.second_sell_qty} 계약")
            return True
        else:
            return False

    def execute_first_sell(self):
        if self.first_sell_qty > 0:
            option_price = self.get_option_price(self.option_code)
            if option_price > 0:
                order_price = round(option_price - ORDER_PRICE_ADJUSTMENT, 2)
                self.log_message(f"[1차 주문 스냅샷] {self.option_code}: 현재가 {option_price}, 주문가 {order_price}, 수량 {self.first_sell_qty}")
                self.place_option_order(self.option_code, order_price, self.first_sell_qty, "1차")

    def execute_second_sell(self):
        if self.second_sell_qty > 0:
            option_price = self.get_option_price(self.option_code)
            if option_price > 0:
                order_price = round(option_price - ORDER_PRICE_ADJUSTMENT, 2)
                self.log_message(f"[2차 주문 스냅샷] {self.option_code}: 현재가 {option_price}, 주문가 {order_price}, 수량 {self.second_sell_qty}")
                self.place_option_order(self.option_code, order_price, self.second_sell_qty, "2차")

    def place_option_order(self, option_code, price, sell_quantity, order_type):
        if sell_quantity > 0:
            self.log_message(f"[{order_type} 주문 실행] {option_code} 옵션 {sell_quantity}개 매도 (매도 가격: {price})")
            retData = {}
            success = self.objOrder.sellOrder(option_code, price, sell_quantity, retData)
            if success:
                self.log_message(f"[{order_type} 주문 성공] {option_code} {sell_quantity}개 매도 완료 (매도 가격: {price})")
            else:
                self.log_message(f"[{order_type} 주문 실패] {option_code} 매도 실패")
        else:
            self.log_message(f"[{order_type} 주문 오류] {option_code} 매도 수량이 0개 이하입니다.")

    def get_option_price(self, option_code):
        retItem = {}
        if self.objOptionMst.request(option_code, retItem):
            return retItem.get('현재가', 0)
        else:
            self.log_message(f"[오류] {option_code} 옵션 가격 조회 실패")
            return 0

    def calculate_sell_quantity(self, option_price, target_sell_amount):
        cost_per_option = option_price * 250000
        return target_sell_amount // cost_per_option if cost_per_option > 0 else 0

class AmountLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.textChanged.connect(self.format_amount)
        self.setValidator(QIntValidator()) # 숫자만 입력 가능하도록 설정

    def format_amount(self, text):
        text = text.replace(',', '')
        if text:
            try:
                amount = int(text)
                formatted_amount = "{:,}".format(amount)
                if self.text() != formatted_amount:
                    self.setText(formatted_amount)
                    self.setCursorPosition(len(formatted_amount)) # 커서 위치 유지
            except ValueError:
                pass # 숫자로 변환 불가능한 경우 무시

class OptionSellWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BothSell")
        self.setGeometry(100, 1200, 900, 1100)

        self.option_code_edit_1 = QLineEdit()
        self.sell_amount_edit_1 = AmountLineEdit() # AmountLineEdit 사용
        self.option_code_edit_2 = QLineEdit()
        self.sell_amount_edit_2 = AmountLineEdit() # AmountLineEdit 사용
        self.execute_time_edit = QLineEdit("11:00")
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        self.start_button = QPushButton("자동 양 매도 시작")

        layout = QVBoxLayout()
        form_layout = QFormLayout()
        form_layout.addRow("옵션 코드 1:", self.option_code_edit_1)
        form_layout.addRow("양 매도 금액 1:", self.sell_amount_edit_1)
        form_layout.addRow("옵션 코드 2:", self.option_code_edit_2)
        form_layout.addRow("양 매도 금액 2:", self.sell_amount_edit_2)
        form_layout.addRow("실행 시간 (HH:MM):", self.execute_time_edit)

        layout.addLayout(form_layout)
        layout.addWidget(self.log_text_edit)
        layout.addWidget(self.start_button)

        self.setLayout(layout)

        self.call_app = None
        self.put_app = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._check_schedule) # 메서드 이름 변경
        self.is_running = False
        self.scheduled_time = None
        self.first_sell_phase = False
        self.time_check_interval = TIME_CHECK_INTERVAL # 변수 할당

        self.start_button.clicked.connect(self.start_auto_selling)

    def start_auto_selling(self):
        if self.is_running:
            self.log("자동 매도 이미 시작되었습니다.")
            return

        call_option_code = self.option_code_edit_1.text()
        call_sell_amount = self.sell_amount_edit_1.text()
        put_option_code = self.option_code_edit_2.text()
        put_sell_amount = self.sell_amount_edit_2.text()
        execute_time_str = self.execute_time_edit.text()

        if not all([call_option_code, call_sell_amount, put_option_code, put_sell_amount, execute_time_str]):
            self.log("모든 입력 필드를 채워주세요.")
            return

        try:
            target_call_sell_amount = call_sell_amount.replace(',', '')
            target_put_sell_amount = put_sell_amount.replace(',', '')
            int(target_call_sell_amount)
            int(target_put_sell_amount)
            hour, minute = map(int, execute_time_str.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                self.log("실행 시간 형식이 잘못되었습니다 (HH:MM).")
                return
            self.scheduled_time = (hour, minute)
        except ValueError:
            self.log("양 매도 금액 및 실행 시간 형식이 잘못되었습니다.")
            return

        self.call_app = FutureOptionApp(call_option_code, call_sell_amount, self.log_text_edit)
        self.put_app = FutureOptionApp(put_option_code, put_sell_amount, self.log_text_edit)
        self.first_sell_phase = False

        self.log(f"자동 양 매도 시작 (실행 시간: {execute_time_str}, 시간 체크 간격: {self.time_check_interval/1000:.1f}초)")
        self.is_running = True
        self.start_button.setText("자동 양 매도 중지")
        self.start_button.clicked.disconnect(self.start_auto_selling)
        self.start_button.clicked.connect(self.stop_auto_selling)
        self.timer.start(self.time_check_interval) # 설정된 간격으로 타이머 시작

    def stop_auto_selling(self):
        if self.is_running:
            self.log("자동 양 매도 중지.")
            self.is_running = False
            self.timer.stop()
            self.start_button.setText("자동 양 매도 시작")
            self.start_button.clicked.disconnect(self.stop_auto_selling)
            self.start_button.clicked.connect(self.start_auto_selling)
            self.call_app = None
            self.put_app = None
            self.scheduled_time = None
            self.first_sell_phase = False
        else:
            self.log("자동 매도가 실행 중이 아닙니다.")

    def _check_schedule(self):
        if self.is_running and self.scheduled_time:
            now = datetime.now()
            self.log(f"[시간 체크] 현재 시간: {now.strftime('%H:%M:%S')}, 설정 시간: {self.scheduled_time[0]:02d}:{self.scheduled_time[1]:02d}")
            if now.hour == self.scheduled_time[0] and now.minute == self.scheduled_time[1]:
                if not self.first_sell_phase:
                    self.log("[자동 주문 실행] 1차 양 매도 준비")
                    call_qty_calculated = self.call_app.calculate_split_quantity()
                    put_qty_calculated = self.put_app.calculate_split_quantity()
                    if call_qty_calculated and put_qty_calculated:
                        self.log("[자동 주문 실행] 1차 양 매도 시작")
                        self.call_app.execute_first_sell()
                        self.put_app.execute_first_sell()
                        self.log("[자동 주문 완료] 1차 양 매도 완료, 2차 매도 대기")
                        self.first_sell_phase = True
                        QTimer.singleShot(SECOND_SELL_DELAY, self.execute_second_sell_phase)
                    else:
                        self.log("[자동 주문 오류] 매도 가능 수량 계산 실패")
                        self.stop_auto_selling()
                # 2차 매도는 execute_second_sell_phase에서 처리

    def execute_second_sell_phase(self):
        if self.is_running and self.first_sell_phase:
            self.log("[자동 주문 실행] 2차 양 매도 시작")
            self.call_app.execute_second_sell()
            self.put_app.execute_second_sell()
            self.log("[자동 주문 완료] 2차 양 매도 완료")
            self.stop_auto_selling()

    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text_edit.append(log_entry)
        self.log_text_edit.ensureCursorVisible()

if __name__ == "__main__":
    if not InitPlusCheck():
        print("❌ PLUS 초기화 실패")
        sys.exit(0)

    app = QApplication(sys.argv)
    window = OptionSellWidget()
    window.show()
    sys.exit(app.exec_())