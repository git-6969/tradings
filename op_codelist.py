import win32com.client
import re  # 정규 표현식 사용

# CYBOS Plus 연결 확인
cybos = win32com.client.Dispatch("CpUtil.CpCybos")
if cybos.IsConnect == 0:
    print("❌ CYBOS Plus가 실행되지 않았습니다.")
    exit()

# CpOptionCode 객체 생성
option_code_mgr = win32com.client.Dispatch("CpUtil.CpOptionCode")

# 전체 옵션 개수 가져오기
option_count = option_code_mgr.GetCount()
print(f"📌 전체 옵션 개수: {option_count}\n")

# 전체 옵션 코드 리스트
all_options = []
filtered_options = []

for i in range(option_count):
    code = option_code_mgr.GetData(0, i)  # 옵션 코드
    name = option_code_mgr.GetData(1, i)  # 옵션 이름
    option_type = "콜" if option_code_mgr.GetData(2, i) == 0 else "풋"  # 옵션 유형 (콜/풋)
    expiry_month = option_code_mgr.GetData(3, i)  # 행사월 (YYYYMM)
    strike_price = option_code_mgr.GetData(4, i)  # 행사가

    option_info = {
        "코드": code,
        "종목명": name,
        "옵션유형": option_type,
        "행사월": expiry_month,
        "행사가": strike_price
    }

    # 전체 옵션 리스트에 추가
    all_options.append(option_info)

    # 옵션 코드에서 209 또는 309 포함 여부 체크
    if re.search(r'209|309', code):
        filtered_options.append(option_info)

# 1️⃣ 전체 옵션 출력
print("=== 📌 전체 옵션 코드 리스트 ===")
for option in all_options:
    print(f"{option['코드']} | {option['종목명']} | {option['옵션유형']} | {option['행사월']} | {option['행사가']}")

# 2️⃣ 209 또는 309 포함된 옵션 코드 출력
print("\n=== 🎯 [209 또는 309 포함 옵션 코드 리스트] ===")
if filtered_options:
    for option in filtered_options:
        print(f"{option['코드']} | {option['종목명']} | {option['옵션유형']} | {option['행사월']} | {option['행사가']}")
else:
    print("❌ 해당 코드가 포함된 옵션이 없습니다.")