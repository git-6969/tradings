import win32com.client


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


# 예시: 출력
if __name__ == "__main__":
    kospi200_codes = get_kospi200_stocks()
    for code in kospi200_codes:
        print(code)