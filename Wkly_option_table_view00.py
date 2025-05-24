import sys
import json
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem
)
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QColor
from Comms_Class import InitPlusCheck, CpFutureMst, CpOptionMst, get_current_price


class OptionViewer(QWidget):
    # 타이머 관련 변수 선언
    UPDATE_INTERVAL = 170  # 가격 업데이트 타이머 간격 (밀리초)
    FLASH_DURATION = 180   # 깜빡임 효과 지속 시간 (밀리초)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("옵션 코드 및 가격 보기")
        self.setGeometry(140, 70, 900, 900)

        main_layout = QVBoxLayout(self)
        header_layout = QHBoxLayout()
        tables_layout = QHBoxLayout()

        self.label = QLabel("📈 옵션 코드 및 가격")
        self.start_button = QPushButton("옵션 가격 보기")
        self.start_button.clicked.connect(self.start_fetching)

        header_layout.addWidget(self.label)
        header_layout.addStretch()
        header_layout.addWidget(self.start_button)

        self.call_table = QTableWidget()
        self.call_table.setColumnCount(2)
        self.call_table.setHorizontalHeaderLabels(["콜 옵션", "현재가"])
        self.call_prices = {}  # 콜 옵션 코드별 이전 가격 저장

        self.put_table = QTableWidget()
        self.put_table.setColumnCount(2)
        self.put_table.setHorizontalHeaderLabels(["풋 옵션", "현재가"])
        self.put_prices = {}  # 풋 옵션 코드별 이전 가격 저장

        tables_layout.addWidget(self.call_table)
        tables_layout.addWidget(self.put_table)

        main_layout.addLayout(header_layout)
        main_layout.addLayout(tables_layout)

        self.option_mst = CpOptionMst()
        self.call_codes = []
        self.put_codes = []
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_prices)

        # 초기 인덱스 설정
        self.current_index = 0
        self.total_codes = []

    def start_fetching(self):
        self.call_table.setRowCount(0)
        self.put_table.setRowCount(0)
        self.call_prices = {}
        self.put_prices = {}

        # 선물 현재가 가져오기
        future_code = "101W6000"
        future_item = {}
        CpFutureMst().request(future_code, future_item)
        current_price_full = future_item.get("현재가", 0)
        current_price_rounded = round(current_price_full, 2)
        self.label.setText(f"📈 옵션 코드 및 가격 - 기준가: {current_price_rounded}")

        try:
            with open("atm_optioncode.json", "r") as f:
                option_data = json.load(f)
                base_code = option_data.get("base", "")
                call_base = option_data.get("call_code", "")
                put_base = option_data.get("put_code", "")

                if base_code:
                    # 현재가 기준으로 가까운 5개 행사가 콜/풋 옵션 코드 생성 (예시)
                    num_to_generate = 5
                    closest_strike = round(current_price_rounded / 2.5) * 2.5
                    for i in range(-num_to_generate, num_to_generate + 1):
                        strike = closest_strike + i * 2.5
                        strike_int = int(strike)
                        strike_str = str(strike_int).zfill(3)
                        call_code = f"{call_base}{strike_str}"
                        put_code = f"{put_base}{strike_str}"
                        self.call_codes.append(call_code)
                        self.put_codes.append(put_code)
                        self.call_prices[call_code] = None  # 초기 가격 None으로 설정
                        self.put_prices[put_code] = None  # 초기 가격 None으로 설정

                    # 중복 제거 및 정렬
                    self.call_codes = sorted(list(set(self.call_codes)))
                    self.put_codes = sorted(list(set(self.put_codes)), reverse=True)

                    self.total_codes = self.call_codes + self.put_codes

                    # 테이블 초기 세팅 (코드만)
                    self.call_table.setRowCount(len(self.call_codes))
                    for i, code in enumerate(self.call_codes):
                        self.call_table.setItem(i, 0, QTableWidgetItem(code))
                        self.call_table.setItem(i, 1, QTableWidgetItem("0.00"))

                    self.put_table.setRowCount(len(self.put_codes))
                    for i, code in enumerate(self.put_codes):
                        self.put_table.setItem(i, 0, QTableWidgetItem(code))
                        self.put_table.setItem(i, 1, QTableWidgetItem("0.00"))

                    # 타이머 시작
                    self.update_timer.start(self.UPDATE_INTERVAL)
                else:
                    self.label.setText("❌ atm_optioncode.json 파일에 base 코드가 없습니다.")

        except FileNotFoundError:
            self.label.setText("❌ atm_optioncode.json 파일을 찾을 수 없습니다.")
        except json.JSONDecodeError:
            self.label.setText("❌ atm_optioncode.json 파일 형식이 잘못되었습니다.")

    def update_prices(self):
        if not self.total_codes:
            return

        if self.current_index >= len(self.total_codes):
            self.current_index = 0

        code = self.total_codes[self.current_index]
        try:
            price = get_current_price(code)
            if code.startswith("2"):  # 콜 옵션
                if code in self.call_prices and self.call_prices[code] != price:
                    try:
                        idx = self.call_codes.index(code)
                        self.update_cell_with_flash(self.call_table, idx, 1, price)
                    except ValueError:
                        pass
                self.call_prices[code] = price
            elif code.startswith("3"):  # 풋 옵션
                if code in self.put_prices and self.put_prices[code] != price:
                    try:
                        idx = self.put_codes.index(code)
                        self.update_cell_with_flash(self.put_table, idx, 1, price)
                    except ValueError:
                        pass
                self.put_prices[code] = price
        except Exception:
            pass  # 가격 조회 실패 시 처리 (현재는 무시)

        self.current_index += 1

    def update_cell_with_flash(self, table, row, col, price):
        item = QTableWidgetItem(f"{price:.2f}")
        item.setBackground(QColor("yellow"))
        table.setItem(row, col, item)

        def reset_background():
            item.setBackground(QColor("white"))
            table.setItem(row, col, item)

        QTimer.singleShot(self.FLASH_DURATION, reset_background)


if __name__ == "__main__":
    if not InitPlusCheck():
        print("❌ PLUS 초기화 실패")
        sys.exit()

    app = QApplication(sys.argv)
    viewer = OptionViewer()
    viewer.show()
    sys.exit(app.exec_())