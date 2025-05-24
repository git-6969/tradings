import win32com.client
import pythoncom
import redis
from Comms_Class import InitPlusCheck
import csv
from datetime import datetime
import time
import json

# 종료 시각 지정
end_time_str = "15:46:00"
end_time = datetime.strptime(end_time_str, "%H:%M:%S").time()

# Redis 연결
r = redis.Redis(host='192.168.55.13', port=6379, db=0, decode_responses=True)

# 필드 정의
HEADERS = [
    "code", "time",
    "ask1", "ask2", "ask3", "ask4", "ask5",
    "ask_vol1", "ask_vol2", "ask_vol3", "ask_vol4", "ask_vol5", "ask_total_vol",
    "ask_cnt1", "ask_cnt2", "ask_cnt3", "ask_cnt4", "ask_cnt5", "ask_total_cnt",
    "bid1", "bid2", "bid3", "bid4", "bid5",
    "bid_vol1", "bid_vol2", "bid_vol3", "bid_vol4", "bid_vol5", "bid_total_vol",
    "bid_cnt1", "bid_cnt2", "bid_cnt3", "bid_cnt4", "bid_cnt5", "bid_total_cnt",
    "market_status"
]

# Redis 키 형식: future:<code>:bids → List 구조로 저장
class FutureJpBidEventHandler:
    def __init__(self):
        self.obj = None

    def SetObject(self, obj):
        self.obj = obj

    def OnReceived(self):
        try:
            values = [self.obj.GetHeaderValue(i) for i in range(37)]
            record = dict(zip(HEADERS, values))
            code = record["code"]
            redis_key = f"future:{code}:bids"
            r.rpush(redis_key, json.dumps(record))
        except Exception as e:
            print("Redis 저장 오류:", e)


# 구독 함수 (멀티 코드)
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


# Redis → CSV 덤프
def dump_redis_to_csv():
    try:
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        time_str = now.strftime("%Y%m%d_%H%M%S")

        for code in ["101W6", "101W9", "101WC", "A0163"]:  # 수신 코드 목록
            redis_key = f"future:{code}:bids"
            records = r.lrange(redis_key, 0, -1)
            parsed = [json.loads(r) for r in records]

            if not parsed:
                continue

            csv_filename = f"FutureJpBid_{code}_{time_str}.csv"
            with open(csv_filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=HEADERS)
                writer.writeheader()
                writer.writerows(parsed)

            print(f"[CSV 저장 완료] {csv_filename}")

    except Exception as e:
        print("CSV 저장 오류:", e)


# 메인
if __name__ == "__main__":
    if not InitPlusCheck():
        print("CREON 연결 실패")
        exit()

    future_codes = ["101W6", "101W9", "101WC", "A0163"]
    subscriptions = subscribe_future_codes(future_codes)

    if subscriptions:
        print("[시작] 데이터 수신 대기 중...")
        while True:
            pythoncom.PumpWaitingMessages()
#            now = datetime.now().time()
#            if now >= end_time:
#                print(f"[종료 시각 도달] {now} >= {end_time}")
#                dump_redis_to_csv()
#                break
            time.sleep(0.1)

        print("[종료 완료]")