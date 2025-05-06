import win32com.client
import time
import pythoncom
import mysql.connector
from Comms_Class import InitPlusCheck
from datetime import datetime

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
    code VARCHAR(10),
    name VARCHAR(40),
    diff BIGINT,
    time BIGINT,
    open BIGINT,
    high BIGINT,
    low BIGINT,
    ask BIGINT,
    bid BIGINT,
    vol BIGINT,
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
        time.sleep(0.1)