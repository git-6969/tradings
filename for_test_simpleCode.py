import win32com.client
import pythoncom
import datetime
import csv
from Comms_Class import InitPlusCheck

option_data = {}
tick_count = 0
dump_done = False

HEADERS = [
    "code", "time", "price", "diff", "open", "high", "low",
    "volume", "value", "theoretical", "iv", "delta", "gamma", "theta",
    "vega", "rho", "open_interest", "ask", "bid", "ask_vol", "bid_vol",
    "match_type", "prev_price_22", "trade_type_code", "block_sum", "receive_type", "prev_price_26"
]

class OptionEventHandler:
    def __init__(self):
        self.obj = None

    def OnReceived(self):
        global tick_count, dump_done

        try:
            values = [self.obj.GetHeaderValue(i) for i in range(27)]
            code = values[0]

            data = dict(zip(HEADERS, values))
            option_data[code] = data
            tick_count += 1

            # 100틱마다 출력
            if tick_count % 100 == 0:
                print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [옵션 체결] 코드: {data['code']}")
                for key in HEADERS[1:]:
                    print(f"  {key}: {data[key]}")

            # 15:46 덤프
            now = datetime.datetime.now()
            if now.hour == 15 and now.minute == 46 and not dump_done:
                dump_to_csv()
                dump_done = True

        except Exception as e:
            print("OnReceived 에러:", e)

def dump_to_csv():
    try:
        now = datetime.datetime.now()
        filename = f"option_dump_{now.strftime('%Y%m%d')}.csv"
        with open(filename, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(HEADERS)
            for data in option_data.values():
                writer.writerow([data[key] for key in HEADERS])
        print(f"[CSV 저장 완료] {filename}")
    except Exception as e:
        print("CSV 저장 오류:", e)

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

if __name__ == "__main__":
    if not InitPlusCheck():
        print("CREON 연결 실패")
        exit()

    option_code = "*"  # 실제 옵션 코드로 대체
    sub = subscribe_option(option_code)

    if sub:
        while True:
            pythoncom.PumpWaitingMessages()