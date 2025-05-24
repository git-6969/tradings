import requests
import time
import json
from datetime import datetime, timedelta
from Comms_Class import CpOptionMst

BASE_URL = "http://192.168.55.13:8000"
DELAY = 0.5  # 요청 간 딜레이 (초)
MAX_COUNT = 60  # 최대 조회할 코드 개수 (0 또는 음수면 전체 조회)
ALLOWED_PREFIXES = ("201", "209", "2AF")  # 필터링할 앞자리 코드
TARGET_HOUR = 15
TARGET_MINUTE = 47

def fetch_codes():
    try:
        resp = requests.get(f"{BASE_URL}/codes")
        resp.raise_for_status()
        return resp.json().get("option_codes", [])
    except Exception as e:
        print(f"[Error] 옵션 코드 조회 실패: {e}")
        return []

if __name__ == "__main__":
    while True:
        now = datetime.now()
        if now.hour == TARGET_HOUR and now.minute == TARGET_MINUTE:
            option_codes = fetch_codes()

            # 앞자리가 허용된 것들만 필터링
            option_codes = [code for code in option_codes if code.startswith(ALLOWED_PREFIXES)]

            # 조회 개수 제한 적용
            if MAX_COUNT > 0:
                option_codes = option_codes[:MAX_COUNT]

            total_codes = len(option_codes)

            if total_codes == 0:
                print("조회할 옵션 코드가 없습니다.")
                exit()

            mst = CpOptionMst()

            print(f"===== 옵션 마스터 정보 조회 시작 ({total_codes}개 코드) =====")

            start_time = time.time()
            all_data = []
            fail_count = 0

            for idx, code in enumerate(option_codes, start=1):
                data = mst.request(code)
                if data:
                    data["option_code"] = code  # 원본 코드 포함
                    all_data.append(data)
                    print(f"[{idx}/{total_codes}] [{code}] 조회 성공")
                else:
                    print(f"[{idx}/{total_codes}] [{code}] 조회 실패")
                    fail_count += 1

                elapsed = time.time() - start_time
                remaining = (total_codes - idx) * DELAY
                est_end = datetime.now() + timedelta(seconds=remaining)
                print(
                    f"    진행률: {idx}/{total_codes} ({idx / total_codes * 100:.1f}%), 예상 종료 시간: {est_end.strftime('%H:%M:%S')}")
                time.sleep(DELAY)

            print("\n===== 조회 완료 =====")
            print(f"성공: {len(all_data)}건, 실패: {fail_count}건")

            # days_to_expiry 기준 정렬
            sorted_data = sorted(all_data, key=lambda x: x.get('days_to_expiry', 999999))

            # 같은 만기일은 하나만 남김
            unique_days = {}
            for data in sorted_data:
                days = data.get("days_to_expiry")
                if days not in unique_days:
                    unique_days[days] = data

            print("\n===== 만기 남은 날 수 기준 대표 옵션 코드 =====")
            for d, v in unique_days.items():
                print(f"[{v['option_code']}] | 만기남은날수: {d}")

            # ATM 옵션 코드 추출
            atm_source_data = None
            sorted_days = sorted(unique_days.keys())

            if sorted_days:
                first = sorted_days[0]
                if first == 1 and len(sorted_days) >= 2:
                    atm_source_data = unique_days[sorted_days[1]]
                    print(f"\n[!] 첫 번째 옵션은 만기일(1일 남음)이므로 두 번째로 넘어감: {atm_source_data['option_code']}")
                else:
                    atm_source_data = unique_days[first]

            if atm_source_data:
                atm_full_call_code = atm_source_data['option_code']
                call_code = atm_full_call_code[:-3]  # 뒤 3자리 제거
                base_code = call_code[1:]          # 첫 글자 제거
                put_code = "3" + base_code          # 콜(2) → 풋(3)

                print("\n===== ATM 옵션 코드 정보 =====")
                print(f"BASE CODE     : {base_code}")
                print(f"CALL CODE     : {call_code}")
                print(f"PUT CODE      : {put_code}")

                atm_info = {
                    "base": base_code,
                    "call_code": call_code,
                    "put_code": put_code
                }

                with open("atm_optioncode.json", "w", encoding="utf-8") as f:
                    json.dump(atm_info, f, ensure_ascii=False, indent=2)

                print("\n[✔] atm_optioncode.json 파일(JSON) 저장 완료.")
            else:
                print("\n[!] 유효한 옵션 코드가 없어 ATM 추출 불가.")
            break  # 목표 시간에 도달하여 실행했으므로 루프 종료
        else:
            now_str = now.strftime("%H:%M:%S")
            print(f"현재 시간: {now_str}, 목표 시간까지 대기 중...")
            time.sleep(27)  # 1초마다 현재 시간 확인