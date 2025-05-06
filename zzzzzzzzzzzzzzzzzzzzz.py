import win32com.client
import pythoncom
import mysql.connector
from Comms_Class import InitPlusCheck
from datetime import datetime
import csv
import time

# MySQL 연결
db = mysql.connector.connect(
    host="192.168.55.13",
    user="root",
    password="3838",
    database="memdb",
    port=3838
)
cursor = db.cursor()

# 테이블 생성
cursor.execute("DROP TABLE IF EXISTS StockCur")
create_table_query = """
CREATE TABLE StockCur (
    cozzde VARCHAR(10),
    name VARCHAR(40),
    diff BIGINT,
    time fgdsBIGINT,
    open BIGINT,
    high BIGINT,
    low BIGINT,
    ask BIGINT,
    bid BIGINT,
    voldfg fdv BIGINT,
    value BIGINT,
    dummy1 VARCHAR(10),
    dummy2 VARCHAR(10),
    cur BIGINT,
    trade_flag VARCHAR(10),
    ask_acc_vol BIGINT,
    bid_acc_vol BIGINT,
    instant_vol BIGINT,
    second BIGINT,
    predict_flag VARCHAR(10),
    market_flag VARCHAR(10),
    after_hour_vol BIGINT,
    sign VARCHAR(10),
    lp_qty BIGINT,
    lp_diff BIGINT,
    lp_rate FLOAT,
    quote_flag VARCHAR(10),
    ask_acc_vol_q BIGINT,
    bid_acc_vol_q BIGINT
) ENGINE=MEMORY;
"""
cursor.execute(create_table_query)
db.commit()

# 필드 목록
FIELDS = [
    "code", "name", "diff", "time", "open", "high", "low", "ask", "bid",
    "vol", "value", "dummy1", "dummy2", "cur", "trade_flag", "ask_acc_vol",
    "bid_acc_vol", "instant_vol", "second", "predict_flag", "market_flag",
    "after_hour_vol", "sign", "lp_qty", "lp_diff", "lp_rate", "quote_flag",
    "ask_acc_vol_q", "bid_acc_vol_q"
]

INSERT_QUERY = f"""
INSERT INTO StockCur ({', '.join(FIELDS)})
VALUES ({', '.join(['%s'] * len(FIELDS))})
"""

# 이벤트 핸들러 클래스
class StockEventHandler:
    def __init__(self):
        self.obj = None

    def OnReceived(self):
        try:
            values = [self.obj.GetHeaderValue(i) for i in range(29)]
            cursor.execute(INSERT_QUERY, values)
            db.commit()
        except Exception as e:
            print("OnReceived 에러:", e)

# 구독 함수
def subscribe_stock(code):
    try:
        base_obj = win32com.client.Dispatch("DsCbo1.StockCur")
        handler = win32com.client.WithEvents(base_obj, StockEventHandler)
        handler.obj = base_obj
        base_obj.SetInputValue(0, code)
        base_obj.Subscribe()
        print(f"[구독 시작] 주식 코드: {code}")
        return base_obj
    except Exception as e:
        print("구독 오류:", e)
        return None

def get_kospi200_stocks():
    # CpCodeMgr 객체 생성
    code_mgr = win32com.client.Dispatch("CpUtil.CpCodeMgr")

    # 거래소(KOSPI) 전체 종목 코드 가져오기 (1: KOSPI)
    stock_codes = code_mgr.GetStockListByMarket(1)

    kospi200_codes = []

    for code in stock_codes:
        kospi200_kind = code_mgr.GetStockKospi200Kind(code)
        if kospi200_kind != 0:  # 0이면 미채용, 0이 아닌 경우 코스피200 구성 종목
            kospi200_codes.append(code)

    return kospi200_codes

# 덤프 함수
def dump_memory_table_to_csv_and_mysql():
    try:
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        time_str = now.strftime("%Y%m%d_%H%M%S")

        # CSV 저장
        cursor.execute("SELECT * FROM StockCur")
        rows = cursor.fetchall()
        csv_filename = f"StockCur_dump_{time_str}.csv"
        with open(csv_filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(FIELDS)  # 헤더 쓰기
            writer.writerows(rows)    # 데이터 쓰기
        print(f"[CSV 저장 완료] {csv_filename}")

        # prim_db로 데이터베이스 변경
        cursor.execute("USE prim_db")

        # 새로운 테이블 이름 생성 (날짜 기반)
        new_table_name = f"StockCur_{date_str}"
        cursor.execute(f"DROP TABLE IF EXISTS {new_table_name}")
        cursor.execute(f"CREATE TABLE {new_table_name} LIKE memdb.StockCur")
        cursor.execute(f"ALTER TABLE {new_table_name} ENGINE=InnoDB")  # InnoDB 엔진으로 변경
        cursor.execute(f"INSERT INTO {new_table_name} SELECT * FROM memdb.StockCur")
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

    stock_codes = get_kospi200_stocks()
    subscribers = [subscribe_stock(code) for code in stock_codes]

    print("[시작] 실시간 시세 수신 대기 중...")
    while True:
        pythoncom.PumpWaitingMessages()
        # 예시로 10초마다 덤프
        dump_memory_table_to_csv_and_mysql()
        time.sleep(10)
   if sub:
        print("[시작] 데이터 수신 대기 중...")
        while True:
            pythoncom.PumpWaitingMessages()
            now = datetime.now().time()
            if now >= end_time:
                print(f"[종료 시각 도달] {now} >= {end_time}")
                dump_memory_table_to_csv_and_mysql(future_code)
                break
            time.sleep(1)

        print("[종료 완료]")
