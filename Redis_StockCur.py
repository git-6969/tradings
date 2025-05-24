import win32com.client
import time
import pythoncom
import redis
import json
from Comms_Class import InitPlusCheck

# Redis 연결
r = redis.Redis(host='192.168.55.13', port=6379, db=0, decode_responses=True)
try:
    r.ping()
    print("[Redis 연결 성공]")
except redis.exceptions.ConnectionError as e:
    print("[Redis 연결 실패]", e)
    exit()

# 필드 목록 (29개)
FIELDS = [
    "code", "name", "diff", "time", "open", "high", "low", "ask", "bid",
    "vol", "value", "dummy1", "dummy2", "cur", "trade_flag", "ask_acc_vol",
    "bid_acc_vol", "instant_vol", "second", "predict_flag", "market_flag",
    "after_hour_vol", "sign", "lp_qty", "lp_diff", "lp_rate", "quote_flag",
    "ask_acc_vol_q", "bid_acc_vol_q"
]

# 이벤트 핸들러 클래스
class StockEventHandler:
    def __init__(self):
        self.obj = None

    def OnReceived(self):
        try:
            values = [self.obj.GetHeaderValue(i) for i in range(29)]
            record = dict(zip(FIELDS, values))
            code = record["code"]
            redis_key = f"stock:{code}:ticks"

            r.rpush(redis_key, json.dumps(record))
 #           print(f"[수신] {code} @ {record['time']} → 현재가 {record['cur']}")

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

# 코스피200 종목 코드 가져오기
def get_kospi200_stocks():
    code_mgr = win32com.client.Dispatch("CpUtil.CpCodeMgr")
    stock_codes = code_mgr.GetStockListByMarket(1)
    return [code for code in stock_codes if code_mgr.GetStockKospi200Kind(code) != 0]

# 메인 실행
if __name__ == "__main__":
    if not InitPlusCheck():
        print("CREON 연결 실패")
        exit()

    stock_codes = get_kospi200_stocks()
    subscribers = [subscribe_stock(code) for code in stock_codes]

    print("[시작] 실시간 시세 Redis 저장 중...")
    while True:
        pythoncom.PumpWaitingMessages()
        time.sleep(0.1)