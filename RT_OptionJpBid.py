import win32com.client
import pythoncom
import mysql.connector
import csv
from datetime import datetime
import time
from Comms_Class import InitPlusCheck

# 종료 시각 지정
end_time_str = "15:46:00"
end_time = datetime.strptime(end_time_str, "%H:%M:%S").time()

# MySQL 연결
db = mysql.connector.connect(
    host="192.168.55.13",
    user="root",
    password="3838",
    database="memdb",
    port=3838
)
cursor = db.cursor()

# 기존 테이블 삭제 및 생성
cursor.execute("DROP TABLE IF EXISTS OptionJpBid")
create_table = """
CREATE TABLE OptionJpBid (
    code VARCHAR(20),
    time INT,
    ask1 DOUBLE, ask2 DOUBLE, ask3 DOUBLE, ask4 DOUBLE, ask5 DOUBLE,
    ask_vol1 INT, ask_vol2 INT, ask_vol3 INT, ask_vol4 INT, ask_vol5 INT,
    total_ask_vol INT,
    ask_cnt1 INT, ask_cnt2 INT, ask_cnt3 INT, ask_cnt4 INT, ask_cnt5 INT,
    total_ask_cnt INT,
    bid1 DOUBLE, bid2 DOUBLE, bid3 DOUBLE, bid4 DOUBLE, bid5 DOUBLE,
    bid_vol1 INT, bid_vol2 INT, bid_vol3 INT, bid_vol4 INT, bid_vol5 INT,
    total_bid_vol INT,
    bid_cnt1 INT, bid_cnt2 INT, bid_cnt3 INT, bid_cnt4 INT, bid_cnt5 INT,
    total_bid_cnt INT,
    market_status INT,
    INDEX idx_code_time (code, time)
) ENGINE=MEMORY;
"""
cursor.execute(create_table)
db.commit()

# 필드명 및 insert 쿼리
HEADERS = [
    "code", "time",
    "ask1", "ask2", "ask3", "ask4", "ask5",
    "ask_vol1", "ask_vol2", "ask_vol3", "ask_vol4", "ask_vol5",
    "total_ask_vol",
    "ask_cnt1", "ask_cnt2", "ask_cnt3", "ask_cnt4", "ask_cnt5",
    "total_ask_cnt",
    "bid1", "bid2", "bid3", "bid4", "bid5",
    "bid_vol1", "bid_vol2", "bid_vol3", "bid_vol4", "bid_vol5",
    "total_bid_vol",
    "bid_cnt1", "bid_cnt2", "bid_cnt3", "bid_cnt4", "bid_cnt5",
    "total_bid_cnt",
    "market_status"
]
INSERT_QUERY = f"INSERT INTO OptionJpBid ({', '.join(HEADERS)}) VALUES ({', '.join(['%s'] * len(HEADERS))})"

# 이벤트 핸들러
class OptionJpBidHandler:
    def __init__(self):
        self.obj = None

    def OnReceived(self):
        try:
            data = [
                self.obj.GetHeaderValue(0),  # code
                self.obj.GetHeaderValue(1),  # time
                self.obj.GetHeaderValue(2), self.obj.GetHeaderValue(3), self.obj.GetHeaderValue(4),
                self.obj.GetHeaderValue(5), self.obj.GetHeaderValue(6),  # ask prices
                self.obj.GetHeaderValue(7), self.obj.GetHeaderValue(8), self.obj.GetHeaderValue(9),
                self.obj.GetHeaderValue(10), self.obj.GetHeaderValue(11),  # ask vols
                self.obj.GetHeaderValue(12),  # total ask vol
                self.obj.GetHeaderValue(13), self.obj.GetHeaderValue(14), self.obj.GetHeaderValue(15),
                self.obj.GetHeaderValue(16), self.obj.GetHeaderValue(17),  # ask cnts
                self.obj.GetHeaderValue(18),  # total ask cnt
                self.obj.GetHeaderValue(19), self.obj.GetHeaderValue(20), self.obj.GetHeaderValue(21),
                self.obj.GetHeaderValue(22), self.obj.GetHeaderValue(23),  # bid prices
                self.obj.GetHeaderValue(24), self.obj.GetHeaderValue(25), self.obj.GetHeaderValue(26),
                self.obj.GetHeaderValue(27), self.obj.GetHeaderValue(28),  # bid vols
                self.obj.GetHeaderValue(29),  # total bid vol
                self.obj.GetHeaderValue(30), self.obj.GetHeaderValue(31), self.obj.GetHeaderValue(32),
                self.obj.GetHeaderValue(33), self.obj.GetHeaderValue(34),  # bid cnts
                self.obj.GetHeaderValue(35),  # total bid cnt
                self.obj.GetHeaderValue(36),  # market status
            ]
            cursor.execute(INSERT_QUERY, data)
            db.commit()
        except Exception as e:
            print("OnReceived 에러:", e)

# 구독 함수
def subscribe_option_jpbid(code):
    try:
        base_obj = win32com.client.Dispatch("CpSysDib.OptionJpBid")
        handler = win32com.client.WithEvents(base_obj, OptionJpBidHandler)
        handler.obj = base_obj
        base_obj.SetInputValue(0, code)
        base_obj.Subscribe()
        print(f"[옵션 호가 구독 시작] 코드: {code}")
        return base_obj
    except Exception as e:
        print("구독 오류:", e)
        return None

# 덤프 및 백업
def dump_memory_table_to_csv_and_mysql():
    try:
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        time_str = now.strftime("%Y%m%d_%H%M%S")

        cursor.execute("SELECT * FROM OptionJpBid")
        rows = cursor.fetchall()
        csv_filename = f"OptionJpBid_dump_{time_str}.csv"
        with open(csv_filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(HEADERS)
            writer.writerows(rows)
        print(f"[CSV 저장 완료] {csv_filename}")

        cursor.execute("USE prim_db")
        new_table_name = f"OptionJpBid_{date_str}"
        cursor.execute(f"DROP TABLE IF EXISTS {new_table_name}")
        cursor.execute(f"CREATE TABLE {new_table_name} LIKE memdb.OptionJpBid")
        cursor.execute(f"ALTER TABLE {new_table_name} ENGINE=InnoDB")
        cursor.execute(f"INSERT INTO {new_table_name} SELECT * FROM memdb.OptionJpBid")
        db.commit()
        print(f"[MySQL 백업 완료] {new_table_name} → prim_db")
        cursor.execute("USE memdb")
    except Exception as e:
        print("덤프/백업 오류:", e)

# 메인 실행
if __name__ == "__main__":
    if not InitPlusCheck():
        print("CREON 연결 실패")
        exit()

    option_code = "*"  # ← 실제 구독할 옵션 코드로 교체
    sub = subscribe_option_jpbid(option_code)

    if sub:
        print("[시작] 실시간 호가 수신 대기 중...")
        while True:
            pythoncom.PumpWaitingMessages()
#            now = datetime.now().time()
#            if now >= end_time:
#                print(f"[종료 시각 도달] {now} >= {end_time}")
 #               dump_memory_table_to_csv_and_mysql()
#                break
            time.sleep(0.1)

        print("[종료 완료]")