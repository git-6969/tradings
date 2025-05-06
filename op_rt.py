import sys
import win32com.client
import time



# CpEvent: 실시간 이벤트 수신 클래스
class CpEvent:
    def set_params(self, client, name, caller):
        self.client = client  # CP 실시간 통신 object
        self.name = name  # 서비스가 다른 이벤트를 구분하기 위한 이름
        self.caller = caller  # callback 을 위해 보관

    def OnReceived(self):
        if self.name == 'optioncur':
            code = self.client.GetHeaderValue(0)  # 종목 코드
            current_price = self.client.GetHeaderValue(2)  # 현재가
            price_change = self.client.GetHeaderValue(3)  # 대비
            volume = self.client.GetHeaderValue(7)  # 거래량
            high_price = self.client.GetHeaderValue(5)  # 고가
            low_price = self.client.GetHeaderValue(6)  # 저가

            print(f"종목 코드: {code}")
            print(f"현재가: {current_price}")
            print(f"대비: {price_change}")
            print(f"거래량: {volume}")
            print(f"고가: {high_price}")
            print(f"저가: {low_price}")
            print("=" * 50)  # 구분선


# 실시간 옵션 현재가 수신 클래스
class CpPBStockCur:
    def __init__(self):
        self.obj = win32com.client.Dispatch('CpSysDib.OptionCurOnly')  # OptionCurOnly 객체
        self.bIsSB = False  # 실시간 구독 상태

    def Subscribe(self, code, caller):
        if self.bIsSB:
            self.Unsubscribe()  # 이미 구독 중이면 해지

        self.obj.SetInputValue(0, code)  # 종목 코드 설정
        handler = win32com.client.WithEvents(self.obj, CpEvent)
        handler.set_params(self.obj, 'optioncur', caller)
        self.obj.Subscribe()  # 실시간 데이터 구독
        self.bIsSB = True

    def Unsubscribe(self):
        if self.bIsSB:
            self.obj.Unsubscribe()  # 실시간 데이터 구독 해지
        self.bIsSB = False


# 실시간 옵션 한 종목 데이터를 인쇄하는 클래스
class OptionDataReceiver:
    def __init__(self):
        self.objCur = CpPBStockCur()  # 실시간 옵션 현재가 객체

    def start_receiving(self, stock_code):
        # 실시간 데이터 수신 시작
        self.objCur.Subscribe(stock_code, self)

    def stop_receiving(self):
        # 실시간 데이터 수신 종료
        self.objCur.Unsubscribe()


if __name__ == '__main__':
    stock_code = '201W4355'  # 원하는 옵션 종목 코드 입력 (예: 삼성전자 옵션)

    # 데이터 수신 객체 생성
    option_data_receiver = OptionDataReceiver()

    # 실시간 데이터 수신 시작
    option_data_receiver.start_receiving(stock_code)

    try:
        # 실시간 데이터를 계속 수신하며, Ctrl+C로 종료할 수 있음
        while True:
            time.sleep(1)  # 1초 간격으로 데이터를 계속 수신
    except KeyboardInterrupt:
        # Ctrl+C로 종료하면 실시간 수신 종료
        option_data_receiver.stop_receiving()
        print("실시간 데이터 수신 종료.")