import sys
import json
from datetime import datetime, time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem
)
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QColor

# Comms_Class 실제 파일이 없을 경우를 대비한 더미 (Dummy) 클래스 및 함수
# 실제 환경에서는 이 부분을 제거하고 Comms_Class.py를 사용해야 합니다.
try:
    from Comms_Class import InitPlusCheck, CpFutureMst, CpOptionMst, get_current_price
except ImportError:
    print("경고: Comms_Class.py를 찾을 수 없습니다. 테스트용 더미 구현을 사용합니다.")
    import random  # 더미 구현에 필요


    def InitPlusCheck():
        print("더미 InitPlusCheck 호출됨")
        return True


    class CpFutureMst:
        def request(self, code, item_dict):
            print(f"더미 CpFutureMst.request 호출됨 (코드: {code})")
            item_dict['현재가'] = 350.0 + random.uniform(-0.5, 0.5)  # 임의의 값 반환


    class CpOptionMst:
        def __init__(self):
            # 옵션 코드 접두사 예시 (실제 Creon API 구조에 맞게 조정 필요)
            self.CallPrefix = "2"
            self.PutPrefix = "3"


    def get_current_price(code):
        # print(f"더미 get_current_price 호출됨 (코드: {code})")
        return round(random.uniform(0.01, 5.00), 2)  # 임의의 가격 반환


class OptionViewer(QWidget):
    # 시장 시작 시간 변수 (디폴트: 8시 45분 00초)
    MARKET_START_HOUR = 8  # 시간을 테스트하려면 현재 시간보다 약간 뒤로 설정 (예: 현재 14:30이면 14:31로)
    MARKET_START_MINUTE = 45
    MARKET_START_SECOND = 0

    # 타이머 관련 변수 선언
    UPDATE_INTERVAL = 170  # 가격 업데이트 타이머 간격 (밀리초)
    FLASH_DURATION = 180  # 깜빡임 효과 지속 시간 (밀리초)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("옵션 코드 및 가격 보기")
        self.setGeometry(140, 70, 900, 900)

        self.market_start_time_obj = time(self.MARKET_START_HOUR, self.MARKET_START_MINUTE, self.MARKET_START_SECOND)
        self.option_updates_started_this_session = False  # 자동 실행 여부 플래그

        # CpOptionMst 인스턴스 생성 (옵션 접두사 등에 사용 가능)
        self.option_mst_instance = CpOptionMst()

        main_layout = QVBoxLayout(self)
        header_layout = QHBoxLayout()
        tables_layout = QHBoxLayout()

        self.label = QLabel("초기화 중...")  # 초기 레이블 메시지
        self.start_button = QPushButton("옵션 가격 보기")
        self.start_button.clicked.connect(self.handle_start_request)

        header_layout.addWidget(self.label)
        header_layout.addStretch()
        header_layout.addWidget(self.start_button)

        self.call_table = QTableWidget()
        self.call_table.setColumnCount(2)
        self.call_table.setHorizontalHeaderLabels(["콜 옵션", "현재가"])
        self.call_prices = {}

        self.put_table = QTableWidget()
        self.put_table.setColumnCount(2)
        self.put_table.setHorizontalHeaderLabels(["풋 옵션", "현재가"])
        self.put_prices = {}

        tables_layout.addWidget(self.call_table)
        tables_layout.addWidget(self.put_table)

        main_layout.addLayout(header_layout)
        main_layout.addLayout(tables_layout)

        self.call_codes = []
        self.put_codes = []
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_prices)

        self.current_index = 0
        self.total_codes = []

        self._setup_automatic_start()  # 자동 시작 설정 호출

    def _setup_automatic_start(self):
        now_dt = datetime.now()
        # 오늘 날짜와 설정된 시장 시작 시간으로 datetime 객체 생성
        market_open_datetime = datetime.combine(now_dt.date(), self.market_start_time_obj)

        if now_dt < market_open_datetime:
            # 현재 시간이 시장 시작 전이면 자동 시작 타이머 설정
            delay_seconds = (market_open_datetime - now_dt).total_seconds()
            self.label.setText(f"⏳ 자동 시작 대기 중... ({self.market_start_time_obj.strftime('%H:%M:%S')})")
            self.start_button.setEnabled(False)  # 자동 시작 대기 중 버튼 비활성화
            # 시장 시작 시간에 _attempt_automatic_fetch 호출 (1초 버퍼 추가)
            QTimer.singleShot(int(delay_seconds * 1000) + 1000, self._attempt_automatic_fetch)
        else:
            # 이미 시장이 시작된 경우
            self.label.setText(f"📈 시장 시작됨 ({self.market_start_time_obj.strftime('%H:%M:%S')}). 수동으로 시작하세요.")
            self.start_button.setEnabled(True)  # 수동 시작 가능하도록 버튼 활성화

    def _attempt_automatic_fetch(self):
        # QTimer에 의해 시장 시작 시간에 호출됨
        self.start_button.setEnabled(True)  # 시장이 열렸으므로 버튼 활성화

        if not self.option_updates_started_this_session:
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: 시장 시작 시간 도달 - 자동 실행 개시")
            self.label.setText("🔔 자동 실행 중...")
            self.start_button.setEnabled(False)  # 자동 실행 중 버튼 일시 비활성화
            self._load_and_start_updates()  # 핵심 로직 실행
            self.start_button.setEnabled(True)  # 핵심 로직 실행 후 버튼 다시 활성화
        else:
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: 시장 시작 시간 도달 - 자동 실행 건너뜀 (이미 수동 등으로 실행됨)")

    def handle_start_request(self):
        """사용자가 '옵션 가격 보기' 버튼을 수동으로 클릭했을 때 호출됨"""
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: 수동 시작 버튼 클릭됨.")
        now_dt = datetime.now()
        market_open_datetime = datetime.combine(now_dt.date(), self.market_start_time_obj)

        if now_dt < market_open_datetime:
            # 버튼이 (어떤 이유로) 시장 개장 전에 활성화되어 클릭된 경우
            self.label.setText(f"시장 개장 전입니다. ({self.market_start_time_obj.strftime('%H:%M:%S')} 이후 자동 시작 또는 그때 수동 실행)")
            return  # 자동 시작이 예약되어 있으므로 별도 처리 안 함

        # 시장이 열렸거나 지난 경우
        self.label.setText("🔄 데이터 준비 중 (수동 실행)...")
        self.start_button.setEnabled(False)  # 데이터 처리 중 버튼 비활성화
        self._load_and_start_updates()  # 핵심 로직 실행
        self.start_button.setEnabled(True)  # 핵심 로직 실행 후 버튼 다시 활성화

    def _load_and_start_updates(self):
        """실제 옵션 코드를 가져오고 가격 업데이트를 시작하는 로직. 성공 시 플래그 설정."""
        # 이전 데이터 정리 및 타이머 중지
        if self.update_timer.isActive():
            self.update_timer.stop()
        self.call_table.setRowCount(0)
        self.put_table.setRowCount(0)
        self.call_prices.clear()
        self.put_prices.clear()
        self.call_codes.clear()
        self.put_codes.clear()
        self.total_codes.clear()
        self.current_index = 0
        # self.option_updates_started_this_session = False # 여기서 리셋하면 자동실행 로직과 충돌 가능성

        future_code = "101W6000"  # 필요시 설정 파일 등에서 동적으로 가져오도록 수정
        future_item = {}
        try:
            CpFutureMst().request(future_code, future_item)  # 선물 현재가 요청
            current_price_full = future_item.get("현재가", 0)
            current_price_rounded = round(current_price_full, 2)

            if current_price_full == 0:
                self.label.setText(f"⚠️ 선물 현재가({future_code}) 조회 실패. 기준가: {current_price_rounded}")
                # self.start_button.setEnabled(True) # 호출한 쪽에서 finally로 처리하거나 여기서 직접 제어
                return
            else:
                self.label.setText(f"📈 옵션 코드 및 가격 - 기준가({future_code}): {current_price_rounded}")

            with open("atm_optioncode.json", "r", encoding="utf-8") as f:  # encoding 명시
                option_data = json.load(f)
                call_base = option_data.get("call_code", "")
                put_base = option_data.get("put_code", "")

                if call_base and put_base:
                    num_strikes_around_atm = 5
                    atm_strike_approx = round(current_price_rounded / 2.5) * 2.5

                    temp_call_codes = []
                    temp_put_codes = []
                    for i in range(-num_strikes_around_atm, num_strikes_around_atm + 1):
                        strike = atm_strike_approx + (i * 2.5)
                        if strike <= 0: continue
                        strike_code_part = str(int(strike)).zfill(3)
                        temp_call_codes.append(f"{call_base}{strike_code_part}")
                        temp_put_codes.append(f"{put_base}{strike_code_part}")

                    self.call_codes = sorted(list(set(temp_call_codes)))
                    self.put_codes = sorted(list(set(temp_put_codes)), reverse=True)

                    for code in self.call_codes: self.call_prices[code] = None  # 초기화
                    for code in self.put_codes: self.put_prices[code] = None  # 초기화

                    self.total_codes = self.call_codes + self.put_codes

                    self.call_table.setRowCount(len(self.call_codes))
                    for r_idx, code in enumerate(self.call_codes):
                        self.call_table.setItem(r_idx, 0, QTableWidgetItem(code))
                        self.call_table.setItem(r_idx, 1, QTableWidgetItem("N/A"))

                    self.put_table.setRowCount(len(self.put_codes))
                    for r_idx, code in enumerate(self.put_codes):
                        self.put_table.setItem(r_idx, 0, QTableWidgetItem(code))
                        self.put_table.setItem(r_idx, 1, QTableWidgetItem("N/A"))

                    if self.total_codes:
                        self.update_timer.start(self.UPDATE_INTERVAL)
                        self.option_updates_started_this_session = True  # 성공적으로 시작됨을 표시
                        print(
                            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: 옵션 업데이트 타이머 시작됨. 총 코드 수: {len(self.total_codes)}")
                    else:
                        self.label.setText(f"⚠️ 옵션 코드 생성 실패 (데이터 확인). 기준가: {current_price_rounded}")
                else:
                    self.label.setText("❌ atm_optioncode.json 파일에 call_code 또는 put_code가 없습니다.")

        except FileNotFoundError:
            self.label.setText("❌ atm_optioncode.json 파일을 찾을 수 없습니다.")
        except json.JSONDecodeError:
            self.label.setText("❌ atm_optioncode.json 파일 형식이 잘못되었습니다.")
        except Exception as e:
            self.label.setText(f"🚫 데이터 처리 중 오류: {str(e)}")
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: _load_and_start_updates 내부 오류: {e}")

        # finally 블록 대신, 이 메서드를 호출한 곳에서 버튼 상태를 관리하도록 변경했으므로
        # 여기서 버튼을 직접 활성화할 필요는 없음 (호출부에서 처리).
        # 단, 이 메서드 내에서 조기 리턴하는 경우, 호출부의 버튼 활성화 로직이 실행되도록 보장해야 함.
        # 현재 구조에서는 _attempt_automatic_fetch와 handle_start_request가 _load_and_start_updates 호출 후 버튼을 활성화함.

    def update_prices(self):
        if not self.total_codes:
            return

        if self.current_index >= len(self.total_codes):
            self.current_index = 0

        code = self.total_codes[self.current_index]
        try:
            price = get_current_price(code)
            if price is None:
                self.current_index += 1
                return

            call_prefix = getattr(self.option_mst_instance, 'CallPrefix', "2")
            put_prefix = getattr(self.option_mst_instance, 'PutPrefix', "3")

            is_call = code.startswith(call_prefix)
            is_put = code.startswith(put_prefix)

            price_map = None
            table_widget = None
            code_list = None

            if is_call:
                price_map = self.call_prices
                table_widget = self.call_table
                code_list = self.call_codes
            elif is_put:
                price_map = self.put_prices
                table_widget = self.put_table
                code_list = self.put_codes

            if price_map is not None and price_map.get(code) != price:
                try:
                    idx = code_list.index(code)
                    self.update_cell_with_flash(table_widget, idx, 1, price)
                except ValueError:
                    # print(f"Code {code} not found in respective list.")
                    pass
                price_map[code] = price
        except Exception as e:
            # print(f"Error updating price for {code}: {e}")
            pass
        self.current_index += 1

    def update_cell_with_flash(self, table, row, col, price):
        item = QTableWidgetItem(f"{price:.2f}")
        item.setBackground(QColor("yellow"))
        table.setItem(row, col, item)
        QTimer.singleShot(self.FLASH_DURATION, lambda: item.setBackground(QColor("white")))


if __name__ == "__main__":
    if not InitPlusCheck():  # PLUS API 초기화
        print("❌ PLUS 초기화 실패")
        sys.exit()

    app = QApplication(sys.argv)
    viewer = OptionViewer()
    viewer.show()
    sys.exit(app.exec_())