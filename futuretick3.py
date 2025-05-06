import win32com.client
import time

# 대신증권 CybosPlus API 연결
instCpCybos = win32com.client.Dispatch("CpUtil.CpCybos")
if instCpCybos.IsConnect == 0:
    print("CybosPlus 연결 실패")
    exit()

# 선물 현재가 요청 객체 생성
instFutureCur = win32com.client.Dispatch("CpSysDib.FutureCur")
instFutureCur.SetInputValue(0, "101W6000")  # 코스피200 선물 코드
instFutureCur.Subscribe()

# 실시간 데이터 처리 함수
def OnReceived():
    print("=" * 30)
    print("시간:", instFutureCur.GetHeaderValue(0))
    print("현재가:", instFutureCur.GetHeaderValue(11))
    print("전일대비:", instFutureCur.GetHeaderValue(12))
    print("전일대비부호:", instFutureCur.GetHeaderValue(13))
    print("전일대비율:", instFutureCur.GetHeaderValue(14))
    print("거래량:", instFutureCur.GetHeaderValue(18))
    print("거래대금:", instFutureCur.GetHeaderValue(19))
    print("시가:", instFutureCur.GetHeaderValue(26))
    print("고가:", instFutureCur.GetHeaderValue(27))
    print("저가:", instFutureCur.GetHeaderValue(28))
    print("-" * 30)

# 실시간 데이터 이벤트 핸들러 등록
instFutureCur.OnReceived = OnReceived

# 프로그램 종료 방지
while True:
    time.sleep(1)