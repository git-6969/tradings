import win32com.client
import pythoncom
import mysql.connector
from Comms_Class import InitPlusCheck
import csv
from datetime import datetime
import time

# 종료 시각 지정
end_time_str = "15:46:00"
end_time = datetime.strptime(end_time_str, "%H:%M:%S").time()

# MySQL 연결 (초기 연결은 memdb)
db = mysql.connector.connect(
    host="192.168.55.13",
    user="root",
    password="3838",
    database="memdb",
    port=3838
)
cursor = db.cursor()

# 기존 테이블 삭제 후 생성 (MEMORY 엔진 + 인덱스 추가)
cursor.execute("DROP TABLE IF EXISTS FutureJpBid")
create_table_query = """
CREATE TABLE FutureJpBid (
    code VARCHAR(20),
    time INT,
    ask1 DOUBLE, ask2 DOUBLE, ask3 DOUBLE, ask4 DOUBLE, ask5 DOUBLE,
    ask_vol1 INT, ask_vol2 INT, ask_vol3 INT, ask_vol4 INT, ask_vol5 INT, ask_total_vol INT,
    ask_cnt1 INT, ask_cnt2 INT, ask_cnt3 INT, ask_cnt4 INT, ask_cnt5 INT, ask_total_cnt INT,
    bid1 DOUBLE, bid2 DOUBLE, bid3 DOUBLE, bid4 DOUBLE, bid5 DOUBLE,
    bid_vol1 INT, bid_vol2 INT, bid_vol3 INT, bid_vol4 INT, bid_vol5 INT, bid_total_vol INT,
    bid_cnt1 INT, bid_cnt2 INT, bid_cnt3 INT, bid_cnt4 INT, bid_cnt5 INT, bid_total_cnt INT,
    market_status INT,
    INDEX idx_code_time (code, time)
) ENGINE=MEMORY;
"""
cursor.execute(create_table_query)
db.commit()

# 헤더 정의
HEADERS = [
    "code", "time", "ask1", "ask2", "ask3", "ask4", "ask5",
    "ask_vol1", "ask_vol2", "ask_vol3", "ask_vol4", "ask_vol5", "ask_total_vol",
    "ask_cnt1", "ask_cnt2", "ask_cnt3", "ask_cnt4", "ask_cnt5", "ask_total_cnt",
    "bid1", "bid2", "bid3", "bid4", "bid5",
    "bid_vol1", "bid_vol2", "bid_vol3", "bid_vol4", "bid_vol5", "bid_total_vol",
    "bid_cnt1", "bid_cnt2", "bid_cnt3", "bid_cnt4", "bid_cnt5", "bid_total_cnt",
    "market_status"
]

INSERT_QUERY = f"""
INSERT INTO FutureJpBid ({', '.join(HEADERS)})
VALUES ({', '.join(['%s'] * len(HEADERS))})
"""

# 이벤트 핸들러 클래스
class FutureJpBidEventHandler:
    def __init__(self):
        self.obj = None

    def SetObject(self, obj):
        self.obj = obj

    def OnReceived(self):
        try:
            values = [self.obj.GetHeaderValue(i) for i in range(37)]
            cursor.execute(INSERT_QUERY, values)
            db.commit()
        except Exception as e:
            print("OnReceived 에러:", e)

# 구독 함수 (멀티 코드 지원)
def subscribe_future_codes(code_list):
    subscriptions = []
    for code in code_list:
        try:
            base_obj = win32com.client.Dispatch("CpSysDib.FutureJpBid")
            handler = win32com.client.WithEvents(base_obj, FutureJpBidEventHandler)
            handler.SetObject(base_obj)
            base_obj.SetInputValue(0, code)
            base_obj.Subscribe()
            print(f"[구독 시작] 선물 코드: {code}")
            subscriptions.append(base_obj)
        except Exception as e:
            print(f"[구독 실패] 코드: {code}, 오류: {e}")
    return subscriptions

# 덤프 및 백업 함수
def dump_memory_table_to_csv_and_mysql():
    try:
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        time_str = now.strftime("%Y%m%d_%H%M%S")

        # CSV 저장
        cursor.execute("SELECT * FROM FutureJpBid")
        rows = cursor.fetchall()
        csv_filename = f"FutureJpBid_{time_str}.csv"
        with open(csv_filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(HEADERS)
            writer.writerows(rows)
        print(f"[CSV 저장 완료] {csv_filename}")

        # prim_db로 데이터베이스 변경
        cursor.execute("USE prim_db")

        new_table_name = f"FutureJpBid_{date_str}"
        cursor.execute(f"DROP TABLE IF EXISTS {new_table_name}")
        cursor.execute(f"CREATE TABLE {new_table_name} LIKE memdb.FutureJpBid")
        cursor.execute(f"ALTER TABLE {new_table_name} ENGINE=InnoDB")
        cursor.execute(f"INSERT INTO {new_table_name} SELECT * FROM memdb.FutureJpBid")
        db.commit()
        print(f"[MySQL 백업 완료] {new_table_name} → prim_db")

        # 다시 memdb로 전환
        cursor.execute("USE memdb")

    except Exception as e:
        print("덤프/백업 오류:", e)

# 메인
if __name__ == "__main__":
    if not InitPlusCheck():
        print("CREON 연결 실패")
        exit()

    # 수신할 선물 코드 리스트
    future_codes = ["101W6", "101W9", "101WC", "A0163"]  # 원하는 코드 추가 가능

    # 구독 시작
    subscriptions = subscribe_future_codes(future_codes)

    if subscriptions:
        print("[시작] 데이터 수신 대기 중...")
        while True:
            pythoncom.PumpWaitingMessages()
#            now = datetime.now().time()
#            if now >= end_time:
#                print(f"[종료 시각 도달] {now} >= {end_time}")
#                dump_memory_table_to_csv_and_mysql()
#                break
            time.sleep(0.1)

        print("[종료 완료]")