import win32com.client

# 대신증권 API 연결 확인
def check_connection():
    objCpCybos = win32com.client.Dispatch("CpUtil.CpCybos")
    if objCpCybos.IsConnect == 0:
        print("대신증권 CYBOS Plus가 연결되지 않았습니다.")
        return False
    return True

# 선물옵션 잔고 조회
def get_futures_balance():
    if not check_connection():
        return

    # 계좌번호 가져오기
    trade_util = win32com.client.Dispatch("CpTrade.CpTdUtil")
    trade_util.TradeInit()

    acc_list = []
    for i in range(trade_util.AccountCount):
        acc_list.append(trade_util.AccountNumber(i))

    account = acc_list[0]  # 첫 번째 계좌 사용

    # 선물옵션 잔고 조회
    balance = win32com.client.Dispatch("CpTrade.CpTd6033")
    balance.SetInputValue(0, account)  # 계좌번호 입력
    balance.BlockRequest()  # 요청 실행

    # 응답 개수 확인
    cnt = balance.GetHeaderValue(7)  # 데이터 개수
    print(f"총 {cnt}건의 잔고 내역이 있습니다.")

    # 데이터 출력
    result = []
    for i in range(cnt):
        item = {
            "종목코드": balance.GetDataValue(12, i),
            "종목명": balance.GetDataValue(0, i),
            "현재가": balance.GetDataValue(9, i),
            "평가손익": balance.GetDataValue(10, i),
            "잔고수량": balance.GetDataValue(2, i),
        }
        result.append(item)

    for r in result:
        print(r)

if __name__ == "__main__":
    get_futures_balance()