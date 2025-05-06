import win32com.client

# 대신증권 API 객체 생성
g_objCodeMgr = win32com.client.Dispatch('CpUtil.CpCodeMgr')
g_objOptionMgr = win32com.client.Dispatch("CpUtil.CpOptionCode")
g_objMarketEye = win32com.client.Dispatch('CpSysDib.MarketEye')


# 현재 KOSPI200 지수 조회 함수
def get_kospi200_index():
    objK200 = win32com.client.Dispatch("CpSysDib.MarketEye")
    objK200.SetInputValue(0, [4])  # 현재가 필드
    objK200.SetInputValue(1, "001")  # KOSPI200 지수 코드
    objK200.BlockRequest()

    return objK200.GetDataValue(0, 0)  # 현재 KOSPI200 지수 반환


# 최근 월물의 풋 옵션 ATM 코드 찾기
def get_weekly_put_atm_option():
    kospi200_index = get_kospi200_index()
    print(f"[INFO] 현재 KOSPI200 지수: {kospi200_index}")

    count = g_objOptionMgr.GetCount()
    option_list = []

    for i in range(count):
        code = g_objOptionMgr.GetData(0, i)  # 옵션 코드
        name = g_objOptionMgr.GetData(1, i)  # 옵션 이름
        opt_type = g_objOptionMgr.GetData(2, i)  # 콜/풋 구분 (C: 콜, P: 풋)
        expiry_month = g_objOptionMgr.GetData(3, i)  # 만기 월
        strike_price = g_objOptionMgr.GetData(4, i)  # 행사가

        # 주간 옵션(위클리 옵션) 필터링 및 풋 옵션 선택
        if opt_type == 'P' and 'W' in name:
            option_list.append((code, name, strike_price))

    # ATM 풋 옵션 찾기 (행사가가 현재 KOSPI200과 가장 가까운 것)
    atm_put_option = min(option_list, key=lambda x: abs(x[2] - kospi200_index))
    print(f"[INFO] 선택된 위클리 풋 ATM 옵션: {atm_put_option[1]} (코드: {atm_put_option[0]}, 행사가: {atm_put_option[2]})")

    return atm_put_option[0]


# 선택된 옵션의 현재가 조회
def get_option_price(option_code):
    g_objMarketEye.SetInputValue(0, [4])  # 현재가 필드
    g_objMarketEye.SetInputValue(1, option_code)  # 옵션 코드 입력
    g_objMarketEye.BlockRequest()

    price = g_objMarketEye.GetDataValue(0, 0)  # 현재가 반환
    print(f"[INFO] {option_code} 현재가: {price}")

    return price


if __name__ == "__main__":
    atm_put_code = get_weekly_put_atm_option()  # ATM 위클리 풋 옵션 코드 찾기
    get_option_price(atm_put_code)  # 해당 옵션의 현재가 출력