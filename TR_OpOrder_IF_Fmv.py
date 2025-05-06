import sys
import time
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QTextEdit
from PyQt5.QtCore import Qt, QTimer
from Comms_Class import InitPlusCheck
from Comms_Class import CpFutureMst
from Comms_Class import CpOptionMst
from Comms_Class import CpFutureBalance
from Comms_Class import CpFutureNContract
from Comms_Class import cancel_all_unfilled_orders
from Comms_Class import CpFutureOptionOrder
from Comms_Class import send_message

class FutureOptionApp(QWidget):
    # 주요 변수 설정 (클래스 맨 앞부분에 선언)
    future_code = "101W6000"  # 선물 코드 (예시)
    option_code = "209DP337"  # 옵션 코드 (예시)
    diff_threshold = 6.3 # 1.0포인트 이상 상승 시 옵션 매수
    previous_future_price = None  # 이전 선물 현재가
    previous_option_price = None  # 이전 옵션 현재가

    # 옵션 매수 관련 변수
    buy_quantity = 1  # 매수 수량
    buy_price = 0  # 매수 가격
    option_order_multiplier = 1  # 주문 배수 (배수는 지우기 요청에 맞춰 기본 1로 설정)

    def __init__(self):
        super().__init__()

        # UI 초기화
        self.setWindowTitle("옵션매수 선물조건부(하락장)")
        self.setGeometry(100, 100, 800, 1400)

        self.layout = QVBoxLayout()
        self.label_future = QLabel("선물 현재가: ", self)
        self.label_option = QLabel("옵션 현재가: ", self)
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)  # 항상 스크롤바 표시

        self.layout.addWidget(self.label_future)
        self.layout.addWidget(self.label_option)
        self.layout.addWidget(self.text_edit)

        self.setLayout(self.layout)

        # 타이머 설정 (3초마다 호출)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.fetch_prices)
        self.timer.start(3000)  # 3000ms = 3초

    def fetch_prices(self):
        # 선물 현재가 조회
        future_price = self.get_future_price(self.future_code)
        lowest_price = self.get_lowest_future_price(self.future_code)

        # 옵션 현재가 조회
        option_price = self.get_option_price(self.option_code)

        # 선물 현재가와 저가 차이가 1.0 이상이면 옵션 매수
        if future_price is not None and lowest_price is not None:
            price_diff = round(future_price - lowest_price, 2)
            if price_diff >= self.diff_threshold:
                self.place_option_order(option_price)

        # 윈도우에 출력 (이전 내용은 지우지 않고 추가)
        self.text_edit.append(f"시간: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.text_edit.append(f"선물 현재가: {future_price} (저가: {lowest_price})")
        self.text_edit.append(f"가격 차이: {price_diff}포인트")
        self.text_edit.append(f"옵션 현재가: {option_price}")
        self.text_edit.append(f"옵션 매수 수량: {self.buy_quantity} | 옵션 매수 가격: {option_price}")
        self.text_edit.append('--------------------------')

        send_message(f"시간: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        send_message(f"선물 현재가: {future_price} (저가: {lowest_price})")
        send_message(f"가격 차이: {price_diff}포인트")


    def get_future_price(self, code):
        objFutureMst = CpFutureMst()
        retItem = {}
        if objFutureMst.request(code, retItem):
            current_price = retItem.get('현재가', '정보 없음')
            if isinstance(current_price, (int, float)):
                return round(current_price, 2)  # 두 자리로 반올림
            return "선물 현재가 조회 실패"
        else:
            return "선물 현재가 조회 실패"

    def get_lowest_future_price(self, code):
        objFutureMst = CpFutureMst()
        retItem = {}
        if objFutureMst.request(code, retItem):
            lowest_price = retItem.get('저가', '정보 없음')
            if isinstance(lowest_price, (int, float)):
                return round(lowest_price, 2)  # 두 자리로 반올림
            return "저가 조회 실패"
        else:
            return "저가 조회 실패"

    def get_option_price(self, code):
        objOptionMst = CpOptionMst()
        retItem = {}
        if objOptionMst.request(code, retItem):
            current_price = retItem.get('현재가', '정보 없음')
            if isinstance(current_price, (int, float)):
                return round(current_price, 2)  # 두 자리로 반올림
            return "옵션 현재가 조회 실패"
        else:
            return "옵션 현재가 조회 실패"

    def place_option_order(self, option_price):
        # CpFutureOptionOrder를 사용하여 옵션 매수 주문을 처리
        objOrder = CpFutureOptionOrder()
        retOrder = {}

        # 옵션 주문 예시 (옵션 코드, 매수 가격, 매수 수량, retOrder 딕셔너리)
        success = objOrder.buyOrder(self.option_code, option_price, self.buy_quantity, retOrder)

        if success:
            self.text_edit.append(f"옵션 매수 주문 성공! 수량: {self.buy_quantity}, 가격: {option_price}")
            self.text_edit.append(f"주문 결과: {retOrder}")
            self.timer.stop()  # 주문이 성공하면 타이머를 중지하여 루프를 종료
        else:
            self.text_edit.append(f"옵션 매수 주문 실패")

if __name__ == "__main__":
    if False == InitPlusCheck():
        exit()

    # PyQt5 애플리케이션 실행
    app = QApplication(sys.argv)
    window = FutureOptionApp()
    window.show()
    sys.exit(app.exec_())