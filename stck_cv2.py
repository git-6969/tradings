import pythoncom
import comtypes.client


class StockCurEvent:
    """실시간 현재가 데이터를 처리하는 이벤트 핸들러"""
    def __init__(self, obj):
        self.obj = obj

    def OnReceived(self):
        code = self.obj.GetHeaderValue(0)  # 종목코드
        name = self.obj.GetHeaderValue(1)  # 종목명
        time = self.obj.GetHeaderValue(2)  # 체결 시간 (HHMMSS)
        current_price = self.obj.GetHeaderValue(3)  # 현재가
        diff = self.obj.GetHeaderValue(4)  # 전일 대비 변화량
        volume = self.obj.GetHeaderValue(9)  # 거래량

        print(f"[{time}] {name}({code}) 현재가: {current_price:,}원, 변동: {diff:+,}원, 거래량: {volume:,}주")


class StockCur:
    """현재가 및 체결 데이터를 실시간으로 수신하는 클래스"""
    def __init__(self, code):
        self.code = code
        self.obj = comtypes.client.CreateObject("DsCbo1.StockCur")  # 대신증권 현재가 API
        self.handler = comtypes.client.GetEvents(self.obj, StockCurEvent(self.obj))

    def subscribe(self):
        """실시간 현재가 데이터 요청"""
        self.obj.SetInputValue(0, self.code)  # 종목 코드 설정
        self.obj.Subscribe()
        print(f"📡 [{self.code}] 실시간 현재가 데이터 구독 시작...")

    def unsubscribe(self):
        """실시간 데이터 요청 해제"""
        self.obj.Unsubscribe()
        print(f"🛑 [{self.code}] 실시간 현재가 데이터 구독 해제")


if __name__ == "__main__":
    stock = StockCur("005930")  # 삼성전자 (005930)
    stock.subscribe()

    try:
        while True:
            pythoncom.PumpWaitingMessages()  # 이벤트 루프 실행
    except KeyboardInterrupt:
        stock.unsubscribe()
        print("프로그램 종료")