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
cursor.execute("DROP TABLE IF EXISTS FutureCurOnly")
create_table_query = """
CREATE TABLE FutureCurOnly (
    code VARCHAR(20),
    price DOUBLE,
    diff DOUBLE,
    theoretical DOUBLE,
    k200 DOUBLE,
    basis DOUBLE,
    base_price DOUBLE,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    high_limit DOUBLE,
    low_limit DOUBLE,
    expire_date BIGINT,
    volume BIGINT,
    open_interest BIGINT,
    time BIGINT,
    recent_month_price DOUBLE,
    distant_month_price DOUBLE,
    ask DOUBLE,
    bid DOUBLE,
    ask_vol BIGINT,
    bid_vol BIGINT,
    cum_ask_vol BIGINT,
    cum_bid_vol BIGINT,
    match_type INT,
    base_asset_price BIGINT,
    trade_value BIGINT,
    prev_price DOUBLE,
    trade_type SMALLINT,
    block_vol BIGINT,
    receive_type INT,
    last_price DOUBLE,
    INDEX idx_code_time (code, time)
) ENGINE=MEMORY;
"""
cursor.execute(create_table_query)
db.commit()

# 헤더 정의
HEADERS = [
    "code", "price", "diff", "theoretical", "k200", "basis", "base_price",
    "open", "high", "low", "high_limit", "low_limit", "expire_date", "volume",
    "open_interest", "time", "recent_month_price", "distant_month_price", "ask",
    "bid", "ask_vol", "bid_vol", "cum_ask_vol", "cum_bid_vol", "match_type",
    "base_asset_price", "trade_value", "prev_price", "trade_type", "block_vol",
    "receive_type", "last_price"
]

INSERT_QUERY = f"""
INSERT INTO FutureCurOnly ({', '.join(HEADERS)})
VALUES ({', '.join(['%s'] * len(HEADERS))})
"""

# 이벤트 핸들러 클래스
class FutureEventHandler:
    def __init__(self):
        self.obj = None

    def OnReceived(self):
        try:
            values = [self.obj.GetHeaderValue(i) for i in range(32)]
            cursor.execute(INSERT_QUERY, values)
            db.commit()
        except Exception as e:
            print("OnReceived 에러:", e)

# 구독 함수
def subscribe_future(code):
    try:
        base_obj = win32com.client.Dispatch("Dscbo1.FutureCurOnly")
        handler = win32com.client.WithEvents(base_obj, FutureEventHandler)
        handler.obj = base_obj
        base_obj.SetInputValue(0, code)
        base_obj.Subscribe()
        print(f"[구독 시작] 선물 코드: {code}")
        return base_obj
    except Exception as e:
        print("구독 오류:", e)
        return None

# 덤프 함수
def dump_memory_table_to_csv_and_mysql():
    try:
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        time_str = now.strftime("%Y%m%d_%H%M%S")

        # CSV 저장
        cursor.execute("SELECT * FROM FutureCurOnly")
        rows = cursor.fetchall()
        csv_filename = f"FutureCurOnly_dump_{time_str}.csv"
        with open(csv_filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(HEADERS)
            writer.writerows(rows)
        print(f"[CSV 저장 완료] {csv_filename}")

        # prim_db로 데이터베이스 변경
        cursor.execute("USE prim_db")

        new_table_name = f"FutureCurOnly_{date_str}"
        cursor.execute(f"DROP TABLE IF EXISTS {new_table_name}")
        cursor.execute(f"CREATE TABLE {new_table_name} LIKE memdb.FutureCurOnly")
        cursor.execute(f"ALTER TABLE {new_table_name} ENGINE=InnoDB")
        cursor.execute(f"INSERT INTO {new_table_name} SELECT * FROM memdb.FutureCurOnly")
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

    future_codes = ["101W6", "101W9", "101WC", "A0163"]  # 여러 선물 코드 예시
    subscribed_futures = []

    for code in future_codes:
        sub = subscribe_future(code)
        if sub:
            subscribed_futures.append(sub)

    print("[시작] 데이터 수신 대기 중...")
    while True:
        pythoncom.PumpWaitingMessages()
#        now = datetime.now().time()
#        if now >= end_time:
#            print(f"[종료 시각 도달] {now} >= {end_time}")
#            dump_memory_table_to_csv_and_mysql()
#            break
        time.sleep(0.1)

    print("[종료 완료]")
