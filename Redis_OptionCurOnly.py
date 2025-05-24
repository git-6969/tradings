import win32com.client
import pythoncom
import redis
from Comms_Class import InitPlusCheck
import csv
from datetime import datetime
import time
import json

# 종료 시각 지정 (예: 15:46:00)
end_time_str = "15:46:00"
end_time = datetime.strptime(end_time_str, "%H:%M:%S").time()

# Redis 연결 설정
r = redis.Redis(host='192.168.55.13', port=6379, db=0, decode_responses=True)

# 필드 정의
HEADERS = [
    "code", "time", "price", "diff", "open", "high", "low",
    "volume", "value", "theoretical", "iv", "delta", "gamma", "theta",
    "vega", "rho", "open_interest", "ask", "bid", "ask_vol", "bid_vol",
    "match_type", "prev_price_22", "trade_type_code", "block_sum", "receive_type", "prev_price_26"
]


# Redis 키 템플릿: option:<code>:ticks → List 형식으로 append
class OptionEventHandler:
    def __init__(self):
        self.obj = None

    def OnReceived(self):
        try:
            # 옵션 데이터 수신
            values = [self.obj.GetHeaderValue(i) for i in range(27)]
            record = dict(zip(HEADERS, values))
            code = record["code"]
            tick_time = record["time"]

            # Redis 키: option:<code>:ticks
            redis_key = f"option:{code}:ticks"

            # Redis에 JSON 형식으로 저장
            r.rpush(redis_key, json.dumps(record))

        except Exception as e:
            print("Redis 저장 오류:", e)


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


# Redis에서 CSV 덤프
def dump_memory_table_to_csv():
    try:
        now = datetime.now()
        time_str = now.strftime("%Y%m%d_%H%M%S")

        # Redis에서 모든 옵션 데이터를 추출하고 CSV로 저장
        for code in ["*"]:  # 옵션 코드에 맞게 교체
            redis_key = f"option:{code}:ticks"
            records = r.lrange(redis_key, 0, -1)
            parsed = [json.loads(r) for r in records]

            if not parsed:
                continue

            csv_filename = f"OptionCurOnly_{code}_{time_str}.csv"
            with open(csv_filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=HEADERS)
                writer.writeheader()
                writer.writerows(parsed)

            print(f"[CSV 저장 완료] {csv_filename}")

    except Exception as e:
        print("CSV 저장 오류:", e)


# 메인 실행부
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
            #                dump_memory_table_to_csv()
            #                break
            time.sleep(0.05)

        print("[종료 완료]")