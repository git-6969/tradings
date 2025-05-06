import win32com.client
import time
import pythoncom

# Cybos5 API 연결
CpStockCur = win32com.client.Dispatch("CpSysDib.StockCur")

# 요청 종목 코드 설정 (삼성전자: 005930)
stock_code = "005930"
CpStockCur.SetInputValue(0, stock_code)

# 실시간 시세 요청 시작
CpStockCur.Subscribe()

# 실시간 시세 업데이트 이벤트 처리 함수
def OnReceiveStockCur():
    if CpStockCur.GetDibStatus() != 0:
        print(f"통신 상태 에러: {CpStockCur.GetDibStatus()}, {CpStockCur.GetLastRequestResult()}")
        CpStockCur.Unsubscribe()
        return

    current_price = CpStockCur.GetDataValue(1)  # 현재가
    change_price = CpStockCur.GetDataValue(2)   # 전일 대비
    change_rate = CpStockCur.GetDataValue(3)    # 전일 대비 등락률

    print(f"삼성전자 ({stock_code}) 실시간 현재가: {current_price}원")
    print(f"전일 대비: {change_price}원 ({change_rate}%)")

# 이벤트 핸들러 등록
pythoncom.PumpMessages()

# 프로그램 종료 시 실시간 시세 구독 해제 (선택 사항)
CpStockCur.Unsubscribe()