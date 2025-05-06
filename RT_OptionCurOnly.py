import win32com.client
import pythoncom
import mysql.connector
from Comms_Class import InitPlusCheck
import csv
from datetime import datetime
import time

# 종료 시각 지정 (예: 15:46:00)
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
cursor.execute("DROP TABLE IF EXISTS OptionCurOnly")
create_table_query = """
CREATE TABLE OptionCurOnly (
    code VARCHAR(20),
    time VARCHAR(10),
    price DOUBLE,
    diff DOUBLE,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    volume DOUBLE,
    value DOUBLE,
    theoretical DOUBLE,
    iv DOUBLE,
    delta DOUBLE,
    gamma DOUBLE,
    theta DOUBLE,
    vega DOUBLE,
    rho DOUBLE,
    open_interest DOUBLE,
    ask DOUBLE,
    bid DOUBLE,
    ask_vol DOUBLE,
    bid_vol DOUBLE,
    match_type INT,
    prev_price_22 DOUBLE,
    trade_type_code INT,
    block_sum DOUBLE,
    receive_type INT,
    prev_price_26 DOUBLE,
    INDEX idx_code_time (code, time)
) ENGINE=MEMORY;
"""
cursor.execute(create_table_query)
db.commit()

# 필드 정의
HEADERS = [
    "code", "time", "price", "diff", "open", "high", "low",
    "volume", "value", "theoretical", "iv", "delta", "gamma", "theta",
    "vega", "rho", "open_interest", "ask", "bid", "ask_vol", "bid_vol",
    "match_type", "prev_price_22", "trade_type_code", "block_sum", "receive_type", "prev_price_26"
]

# INSERT 쿼리
INSERT_QUERY = f"""
INSERT INTO OptionCurOnly ({', '.join(HEADERS)})
VALUES ({', '.join(['%s'] * len(HEADERS))})
"""

# 이벤트 핸들러 클래스
class OptionEventHandler:
    def __init__(self):
        self.obj = None

    def OnReceived(self):
        try:
            values = [self.obj.GetHeaderValue(i) for i in range(27)]
            cursor.execute(INSERT_QUERY, values)
            db.commit()
        except Exception as e:
            print("OnReceived 에러:", e)

# 구독 함수
def subscribe_option(code):
    try:
        base_obj = win32com.client.Dispatch("CpSysDib.OptionCurOnly")
        handler = win32com.client.WithEvents(base_obj, OptionEventHandler)
        handler.obj = base_obj
        base_obj.SetInputValue(0, code)
        base_obj.Subscribe()
        print(f"[구독 시작] 옵션 코드: {code}")
        return base_obj
    except Exception as e:
        print("구독 오류:", e)
        return None

# 메모리 테이블을 CSV + prim_db로 백업
def dump_memory_table_to_csv_and_mysql():
    try:
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        time_str = now.strftime("%Y%m%d_%H%M%S")

        # CSV 저장
        cursor.execute("SELECT * FROM OptionCurOnly")
        rows = cursor.fetchall()
        csv_filename = f"OptionCurOnly_dump_{time_str}.csv"
        with open(csv_filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(HEADERS)
            writer.writerows(rows)
        print(f"[CSV 저장 완료] {csv_filename}")

        # prim_db로 데이터베이스 변경
        cursor.execute("USE prim_db")

        new_table_name = f"OptionCurOnly_{date_str}"
        cursor.execute(f"DROP TABLE IF EXISTS {new_table_name}")
        cursor.execute(f"CREATE TABLE {new_table_name} LIKE memdb.OptionCurOnly")
        cursor.execute(f"ALTER TABLE {new_table_name} ENGINE=InnoDB")
        cursor.execute(f"INSERT INTO {new_table_name} SELECT * FROM memdb.OptionCurOnly")
        db.commit()
        print(f"[MySQL 백업 완료] {new_table_name} → prim_db")

        # 다시 memdb로 전환 (선택 사항)
        cursor.execute("USE memdb")

    except Exception as e:
        print("덤프/백업 오류:", e)

# 메인 실행
if __name__ == "__main__":
    if not InitPlusCheck():
        print("CREON 연결 실패")
        exit()

    option_code = "*"  # 실제 옵션 코드로 교체
    sub = subscribe_option(option_code)

    if sub:
        print("[시작] 데이터 수신 대기 중...")
        while True:
            pythoncom.PumpWaitingMessages()
#            now = datetime.now().time()
#            if now >= end_time:
#                print(f"[종료 시각 도달] {now} >= {end_time}")
 #               dump_memory_table_to_csv_and_mysql()
#                break
            time.sleep(0.05)

        print("[종료 완료]")