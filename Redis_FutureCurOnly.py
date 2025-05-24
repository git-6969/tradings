import win32com.client
import pythoncom
import redis
import csv
from Comms_Class import InitPlusCheck
from datetime import datetime
import time
import json

# 종료 시각 지정
end_time_str = "15:46:00"
end_time = datetime.strptime(end_time_str, "%H:%M:%S").time()

# Redis 연결
r = redis.Redis(host='192.168.55.13', port=6379, db=0, decode_responses=True)
try:
    r.ping()
    print("[Redis 연결 성공]")
    # Redis 초기화 (FLUSHALL - 모든 데이터베이스 삭제)
    r.flushall()
    print("[Redis 초기화 완료 (FLUSHALL 실행)]")
except redis.exceptions.ConnectionError as e:
    print("[Redis 연결 실패]", e)
    exit()

# 필드명
HEADERS = [
    "code", "price", "diff", "theoretical", "k200", "basis", "base_price",
    "open", "high", "low", "high_limit", "low_limit", "expire_date", "volume",
    "open_interest", "time", "recent_month_price", "distant_month_price", "ask",
    "bid", "ask_vol", "bid_vol", "cum_ask_vol", "cum_bid_vol", "match_type",
    "base_asset_price", "trade_value", "prev_price", "trade_type", "block_vol",
    "receive_type", "last_price"
]

# Redis 키 템플릿: future:<code>:ticks → List 형식으로 append
class FutureEventHandler:
    def __init__(self):
        self.obj = None

    def OnReceived(self):
        try:
            values = [self.obj.GetHeaderValue(i) for i in range(32)]
            record = dict(zip(HEADERS, values))
            code = record["code"]
            tick_time = record["time"]

            # Redis 키: future:<code>:ticks
            redis_key = f"future:{code}:ticks"

            # Redis에 JSON 형식으로 push
            r.rpush(redis_key, json.dumps(record))
            # 디버깅용 출력
#             print(f"[수신됨] {code} @ {tick_time} → {record['price']}")

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

# Redis에서 CSV 덤프
def dump_memory_table_to_csv():
    try:
        now = datetime.now()
        time_str = now.strftime("%Y%m%d_%H%M%S")

        for code in future_codes:
            redis_key = f"future:{code}:ticks"
            records = r.lrange(redis_key, 0, -1)
            parsed = [json.loads(r) for r in records]

            if not parsed:
                continue

            csv_filename = f"FutureCurOnly_{code}_{time_str}.csv"
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
    subscribed_futures = []

    for code in future_codes:
        sub = subscribe_future(code)
        if sub:
            subscribed_futures.append(sub)

    print("[시작] Redis로 실시간 저장 중...")
    while True:
        pythoncom.PumpWaitingMessages()
#         now = datetime.now().time()
#         if now >= end_time:
#             print(f"[종료 시각 도달] {now} >= {end_time}")
#             dump_memory_table_to_csv()
#             break
        time.sleep(0.1)

    print("[종료 완료]")