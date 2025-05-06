import sys
import pythoncom
import win32com.client


# 실시간 데이터 이벤트 핸들러
class StockCurEventHandler:
    def __init__(self, client):
        self.client = client

    def OnReceived(self):
        """ 실시간 체결 데이터 수신 이벤트 """
        code = self.client.GetHeaderValue(0)  # 종목 코드
        cur_price = self.client.GetHeaderValue(13)  # 현재가
        volume = self.client.GetHeaderValue(9)  # 거래량

        print(f"[종목 코드: {code}] 현재가: {cur_price}, 거래량: {volume}")


# 실시간 주식 현재가 요청 클래스
class StockCur:
    def __init__(self, code):
        self.client = win32com.client.Dispatch("Dscbo1.StockCur")  # 주식 체결 객체 생성
        self.handler = win32com.client.WithEvents(self.client, StockCurEventHandler)  # 이벤트 핸들러 등록
        self.event_handler = StockCurEventHandler(self.client)  # 이벤트 핸들러 객체 생성
        self.code = code

    def subscribe(self):
        self.client.SetInputValue(0, self.code)  # 종목 코드 설정
        self.client.Subscribe()  # 실시간 데이터 요청
        print(f"[구독 시작] 종목 코드: {self.code}")

    def unsubscribe(self):
        self.client.Unsubscribe()
        print(f"[구독 종료] 종목 코드: {self.code}")


# Creon Plus 연결 상태 확인
def check_creon_status():
    cybos = win32com.client.Dispatch("CpUtil.CpCybos")
    if cybos.IsConnect == 0:
        print("Creon Plus 연결 실패. 프로그램을 종료합니다.")
        sys.exit()


if __name__ == "__main__":
    check_creon_status()

    stock_code = "005930"  # 삼성전자 (원하는 종목 코드 입력)
    stock_cur = StockCur(stock_code)

    stock_cur.subscribe()

    try:
        while True:
            pythoncom.PumpWaitingMessages()  # 이벤트 메시지 루프
    except KeyboardInterrupt:
        stock_cur.unsubscribe()
        print("프로그램 종료.")