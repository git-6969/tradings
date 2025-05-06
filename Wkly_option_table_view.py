import sys
import math
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem
)
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QColor
from Comms_Class import InitPlusCheck, CpFutureMst, CpOptionMst


class OptionViewer(QWidget):
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

        self.put_table = QTableWidget()
        self.put_table.setColumnCount(2)
        self.put_table.setHorizontalHeaderLabels(["풋 옵션", "현재가"])

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

        # 기준 날짜 및 시작 시리얼 변수 선언
        self.monday_base_date = datetime(2025, 4, 15).date()  # 화요일 기준일
        self.monday_start_serial = 90
        self.thursday_base_date = datetime(2025, 4, 17).date()  # 금요일 기준일
        self.thursday_start_serial = "DR"

    def start_fetching(self):
        self.call_table.setRowCount(0)
        self.put_table.setRowCount(0)

        # 선물 현재가 가져오기
        future_code = "101W6000"
        future_item = {}
        CpFutureMst().request(future_code, future_item)
        current_price_full = future_item.get("현재가", 0)
        current_price_rounded = round(current_price_full, 2)
        self.label.setText(f"📈 옵션 코드 및 가격 - 기준가: {current_price_rounded}")

        today = datetime.now().date()
        weekday = today.weekday()  # 월=0, 화=1, 수=2, 목=3, 금=4, 토=5, 일=6

        if weekday == 0 or weekday == 4:  # 월요일 또는 금요일
            call_codes, put_codes = self.generate_weekly_monday_code(current_price_rounded)
        elif 1 <= weekday <= 3:  # 화요일, 수요일, 목요일
            call_codes, put_codes = self.generate_weekly_thursday_code(current_price_rounded)
        else:  # 토요일, 일요일
            call_codes, put_codes = self.generate_weekly_monday_code(current_price_rounded)

        # 콜/풋 옵션 코드 생성 시 기준 가격 중심으로 위/아래 5개씩 생성
        num_to_generate = 5
        self.call_codes = self.select_near_strikes(call_codes, current_price_rounded, num_to_generate)
        self.put_codes = self.select_near_strikes(put_codes, current_price_rounded, num_to_generate, reverse=True)

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

        # 타이머 시작 (0.75초마다 가격 갱신)
        self.update_timer.start(750)

    def select_near_strikes(self, all_codes, base_price, num_to_select, reverse=False):
        """기준 가격 중심으로 가까운 행사가 코드 num_to_select 개수만큼 선택"""
        if not all_codes:
            return []

        # 행사가 추출 및 정렬
        strikes = sorted([(code, abs(int(code[5:]) - base_price)) for code in all_codes], key=lambda x: x[1])
        selected_codes = [code for code, diff in strikes[:(num_to_select * 2 + 1)]] # 기준 포함 위아래

        # 필요하다면 최종적으로 정렬 (콜은 오름차순, 풋은 내림차순)
        if not reverse:
            selected_codes.sort(key=lambda code: code)
        else:
            selected_codes.sort(key=lambda code: code, reverse=True)

        # 최종 num_to_select 개수 선택 (중앙 부근)
        center_index = len(selected_codes) // 2
        start_index = max(0, center_index - num_to_select)
        end_index = min(len(selected_codes), center_index + num_to_select + 1)
        return selected_codes[start_index:end_index]


    def get_serial_number_monday(self):
        """화요일부터 다음 주 월요일까지 동일한 일련번호를 반환."""
        today = datetime.now().date()
        monday_of_current_week = today - timedelta(days=today.weekday()) # 현재 주 월요일

        # 기준일이 속한 주의 화요일
        first_tuesday = self.monday_base_date

        if today < first_tuesday:
            # 2025년 4월 15일 이전은 이전 규칙 적용 (필요하다면)
            base_date_old = datetime(2025, 4, 14).date()
            delta_weeks = (today - base_date_old).days // 7
            serial = 89
            for _ in range(delta_weeks):
                serial_str = str(serial)
                if serial_str == '99':
                    serial = 'A0'
                elif serial_str.isalpha():
                    if serial_str[-1] == 'Z':
                        serial = chr(ord(serial_str[0]) + 1) + '0'
                    else:
                        serial = serial_str[0] + chr(ord(serial_str[-1]) + 1)
                else:
                    serial += 1
            return str(serial).zfill(2)
        else:
            # 현재 날짜가 속한 주의 화요일 계산
            current_tuesday = monday_of_current_week + timedelta(days=1)

            # 첫 번째 화요일 이후 몇 주가 지났는지 계산
            delta_weeks = 0
            if current_tuesday >= first_tuesday:
                delta_weeks = (current_tuesday - first_tuesday).days // 7

            current_serial = self.monday_start_serial + delta_weeks

            def format_serial(n):
                return str(n).zfill(2)

            return format_serial(current_serial)


    def get_serial_number_thursday(self):
        """금요일부터 다음 주 목요일까지 유효."""
        today = datetime.now().date()
        friday_of_current_week = today - timedelta(days=(today.weekday() - 4) % 7) # 현재 주 금요일

        if today < self.thursday_base_date:
            base_date = datetime(2025, 4, 11).date() # 이전 목요일
            delta_weeks = (today - base_date).days // 7
            current_serial = self.thursday_start_serial
            for _ in range(delta_weeks):
                next_serial = self.increment_serial_alphanumeric(current_serial)
                if next_serial:
                    current_serial = next_serial
                else:
                    break
            return current_serial
        else:
            first_friday = self.thursday_base_date # 기준일은 금요일로 봐야 함
            delta_weeks = 0
            if friday_of_current_week >= first_friday:
                delta_weeks = (friday_of_current_week - first_friday).days // 7

            current_serial = self.thursday_start_serial
            for _ in range(delta_weeks):
                next_serial = self.increment_serial_alphanumeric(current_serial)
                if next_serial:
                    current_serial = next_serial
                else:
                    break
            return current_serial

    def increment_serial_alphanumeric(self, serial):
        part1 = list(serial)
        part2_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

        for i in range(len(part1) - 1, -1, -1):
            current_char_index = part2_chars.find(part1[i])
            if current_char_index < len(part2_chars) - 1:
                part1[i] = part2_chars[current_char_index + 1]
                return "".join(part1)
            else:
                part1[i] = '0' if part1[i].isdigit() else 'A' # Reset to beginning of alphanumeric

        # All characters rolled over, need to increase length (not expected with current serials)
        return None


    def generate_weekly_monday_code(self, base_price):
        call_codes = []
        put_codes = []
        serial_number = self.get_serial_number_monday() # 월요일 시리얼 번호 함수 호출
        increment_units = [0, 2, 5, 7]
        num_strikes_around = 10 # 충분한 행사가 코드 생성
        closest_strike = round(base_price / 2.5) * 2.5
        generated_strikes = set()

        for i in range(-num_strikes_around, num_strikes_around + 1):
            for unit in increment_units:
                strike = closest_strike + i * 2.5
                strike_int = int(strike)
                if strike >= 0 and strike not in generated_strikes:
                    strike_str = str(strike_int).zfill(3)
                    call_codes.append(f"2AF{serial_number}{strike_str}")
                    put_codes.append(f"3AF{serial_number}{strike_str}")
                    generated_strikes.add(strike)

        return call_codes, put_codes

    def generate_weekly_thursday_code(self, base_price):
        call_codes = []
        put_codes = []
        serial_number = self.get_serial_number_thursday() # 목요일 시리얼 번호 함수 호출
        increment_units = [0, 2, 5, 7]
        num_strikes_around = 10 # 충분한 행사가 코드 생성
        closest_strike = round(base_price / 2.5) * 2.5
        generated_strikes = set()

        for i in range(-num_strikes_around, num_strikes_around + 1):
            for unit in increment_units:
                strike = closest_strike + i * 2.5
                strike_int = int(strike)
                if strike >= 0 and strike not in generated_strikes:
                    strike_str = str(strike_int).zfill(3)
                    call_codes.append(f"209{serial_number}{strike_str}")
                    put_codes.append(f"309{serial_number}{strike_str}")
                    generated_strikes.add(strike)

        return call_codes, put_codes

    def update_prices(self):
        if not self.total_codes:
            return

        if self.current_index >= len(self.total_codes):
            self.current_index = 0

        code = self.total_codes[self.current_index]
        item = {}
        try:
            self.option_mst.request(code, item)
            price = round(item.get("현재가", 0), 2)
        except Exception:
            price = 0.00

        if code.startswith("2AF") or code.startswith("209"): # 콜 옵션 코드 prefix 확인
            try:
                # 콜 옵션 코드 리스트에서 찾기 (두 가지 prefix 모두 고려)
                if code.startswith("2AF"):
                    idx = self.call_codes.index(code)
                else:
                    idx = self.call_codes.index(code)
                self.update_cell_with_flash(self.call_table, idx, 1, price)
            except ValueError:
                pass # 코드가 리스트에 없는 경우 무시
        elif code.startswith("3AF") or code.startswith("309"): # 풋 옵션 코드 prefix 확인
            try:
                # 풋 옵션 코드 리스트에서 찾기 (두 가지 prefix 모두 고려)
                if code.startswith("3AF"):
                    idx = self.put_codes.index(code)
                else:
                    idx = self.put_codes.index(code)
                self.update_cell_with_flash(self.put_table, idx, 1, price)
            except ValueError:
                pass # 코드가 리스트에 없는 경우 무시

        self.current_index += 1

    def update_cell_with_flash(self, table, row, col, price):
        item = QTableWidgetItem(f"{price:.2f}")
        item.setBackground(QColor("yellow"))
        table.setItem(row, col, item)

        def reset_background():
            item.setBackground(QColor("white"))
            table.setItem(row, col, item)

        QTimer.singleShot(300, reset_background)


if __name__ == "__main__":
    if not InitPlusCheck():
        print("❌ PLUS 초기화 실패")
        sys.exit()

    app = QApplication(sys.argv)
    viewer = OptionViewer()
    viewer.show()
    sys.exit(app.exec_())