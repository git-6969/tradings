import win32com.client
import pythoncom

# 실시간 데이터 수신을 위한 이벤트 핸들러 클래스 정의
class FutureCurOnlyEventHandler:
    def __init__(self):
        self.data = []

    def OnReceived(self):
        # 실시간 데이터 수신 시 호출되는 메서드
        code = self.obj.GetHeaderValue(0)  # 종목코드
        current_price = self.obj.GetHeaderValue(1)  # 현재가
        bid_price = self.obj.GetHeaderValue(2)  # 매도호가
        ask_price = self.obj.GetHeaderValue(3)  # 매수호가
        volume = self.obj.GetHeaderValue(4)  # 거래량
        self.data.append((code, current_price, bid_price, ask_price, volume))
        print(f"종목코드: {code}, 현재가: {current_price}, 매도호가: {bid_price}, 매수호가: {ask_price}, 거래량: {volume}")

# COM 객체 초기화 및 이벤트 핸들러 설정
def main():
    pythoncom.CoInitialize()
    obj = win32com.client.DispatchWithEvents("Dscbo1.FutureCurOnly", FutureCurOnlyEventHandler)
    obj.SetInputValue(0, '101W6000')  # 선물 종목코드 설정 (예: '101P3000')
    obj.Subscribe()  # 실시간 데이터 수신 시작

    print("실시간 데이터 수신을 시작합니다. 종료하려면 Ctrl+C를 누르세요.")
    try:
        while True:
            pythoncom.PumpWaitingMessages()
    except KeyboardInterrupt:
        print("실시간 데이터 수신을 종료합니다.")
        obj.Unsubscribe()  # 실시간 데이터 수신 종료

if __name__ == "__main__":
    main()