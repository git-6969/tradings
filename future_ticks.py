import sys
import pythoncom
import win32com.client


# 실시간 데이터 이벤트 핸들러
class FutureCurOnlyEventHandler:
    def __init__(self, client):
        self.client = client

    def OnReceived(self):
        """ 실시간 체결 데이터 수신 이벤트 """
        code = self.client.GetHeaderValue(0)  # 선물 코드
        cur_price = self.client.GetHeaderValue(13)  # 현재가
        volume = self.client.GetHeaderValue(9)  # 거래량
        time = self.client.GetHeaderValue(1)  # 체결 시간 (HHMMSS)

        print(f"[선물 코드: {code}] 체결 시간: {time}, 현재가: {cur_price}, 거래량: {volume}")


# 실시간 선물 체결 요청 클래스
class FutureCurOnly:
    def __init__(self, code):
        self.client = win32com.client.Dispatch("Dscbo1.FutureCurOnly")  # 선물 체결 객체 생성
        self.handler = FutureCurOnlyEventHandler(self.client)  # 이벤트 핸들러 등록
        win32com.client.WithEvents(self.client, FutureCurOnlyEventHandler)  # 이벤트 등록
        self.code = code

    def subscribe(self):
        self.client.SetInputValue(0, self.code)  # 선물 코드 설정
        self.client.Subscribe()  # 실시간 데이터 요청
        print(f"[구독 시작] 선물 코드: {self.code}")

    def unsubscribe(self):
        self.client.Unsubscribe()
        print(f"[구독 종료] 선물 코드: {self.code}")


# Creon Plus 연결 상태 확인
def check_creon_status():
    cybos = win32com.client.Dispatch("CpUtil.CpCybos")
    if cybos.IsConnect == 0:
        print("Creon Plus 연결 실패. 프로그램을 종료합니다.")
        sys.exit()


if __name__ == "__main__":
    check_creon_status()

    future_code = "101P3000"  # 원하는 선물 코드 입력
    future_cur = FutureCurOnly(future_code)

    future_cur.subscribe()

    try:
        while True:
            pythoncom.PumpWaitingMessages()  # 이벤트 메시지 루프
    except KeyboardInterrupt:
        future_cur.unsubscribe()
        print("프로그램 종료.")