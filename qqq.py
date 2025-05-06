import sys
import win32com.client
import ctypes
import time
import socket

g_objCodeMgr = win32com.client.Dispatch('CpUtil.CpCodeMgr')
g_objCpStatus = win32com.client.Dispatch('CpUtil.CpCybos')
g_objCpTrade = win32com.client.Dispatch('CpTrade.CpTdUtil')
g_objFutureMgr = win32com.client.Dispatch("CpUtil.CpFutureCode")







def send_message(message):
    """지정된 IP와 포트로 메시지를 전송하는 함수"""
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("192.168.55.13",12345))  # 서버에 연결
        client.sendall(message.encode())  # 메시지 전송

        response = client.recv(1024).decode()  # 서버 응답 수신
        print(f"서버 응답: {response}")

    except Exception as e:
        print(f"메시지 전송 중 오류 발생: {e}")

    finally:
        client.close()  # 소켓 닫기




def InitPlusCheck():
    # 프로세스가 관리자 권한으로 실행 여부
    if ctypes.windll.shell32.IsUserAnAdmin():
        print('정상: 관리자권한으로 실행된 프로세스입니다.')
    else:
        print('오류: 일반권한으로 실행됨. 관리자 권한으로 실행해 주세요')
        return False

    # 연결 여부 체크
    if (g_objCpStatus.IsConnect == 0):
        print("PLUS가 정상적으로 연결되지 않음. ")
        return False

    # 주문 관련 초기화
    ret = g_objCpTrade.TradeInit(0)
    if (ret != 0):
        print("주문 초기화 실패, 오류번호 ", ret)
        return False

    return True


def print_item_data(item):
    data = ''
    for key, value in item.items():
        if (type(value) == float):
            data += '%s:%.2f' % (key, value)
        elif (type(value) == str):
            data += '%s:%s' % (key, value)
        elif (type(value) == int):
            data += '%s:%d' % (key, value)
        data += ' '
    print(data)


# CpFutureMst: 선물 현재가
class CpFutureMst:
    def __init__(self):
        self.objRq = win32com.client.Dispatch("Dscbo1.FutureMst")

    def request(self, code, retItem):
        self.objRq.SetInputValue(0, code)
        self.objRq.BlockRequest()

        rqStatus = self.objRq.GetDibStatus()
        rqRet = self.objRq.GetDibMsg1()
    #    print("통신상태", rqStatus, rqRet)
        if rqStatus != 0:
            return False

        retItem['한글종목명'] = self.objRq.GetHeaderValue(2)
        retItem['잔존일'] = self.objRq.GetHeaderValue(8)
        retItem['최종거래일'] = self.objRq.GetHeaderValue(9)
        retItem['현재가'] = self.objRq.GetHeaderValue(71)
        retItem['시가'] = self.objRq.GetHeaderValue(72)
        retItem['고가'] = self.objRq.GetHeaderValue(73)
        retItem['저가'] = self.objRq.GetHeaderValue(74)

        retItem['매수1호가'] = self.objRq.GetHeaderValue(54)
        retItem['매수1호가수량'] = self.objRq.GetHeaderValue(59)
        retItem['매도1호가'] = self.objRq.GetHeaderValue(37)
        retItem['매도1호가수량'] = self.objRq.GetHeaderValue(42)

        retItem['K200지수'] = self.objRq.GetHeaderValue(89)
        retItem['BASIS'] = self.objRq.GetHeaderValue(90)

        return True

# CpOptionMst: 옵션 현재가
class CpOptionMst:
    def __init__(self):
        self.objRq = win32com.client.Dispatch("Dscbo1.OptionMst")

    def request(self, code, retItem):
        self.objRq.SetInputValue(0, code)
        self.objRq.BlockRequest()

        rqStatus = self.objRq.GetDibStatus()
        rqRet = self.objRq.GetDibMsg1()
        # print("통신상태", rqStatus, rqRet) #통신상태는 반복 출력으로 인해 주석처리함.
        if rqStatus != 0:
            return False

        retItem['한글종목명'] = self.objRq.GetHeaderValue(8)
        retItem['잔존일'] = self.objRq.GetHeaderValue(13)
        retItem['최종거래일'] = self.objRq.GetHeaderValue(18)
        retItem['현재가'] = self.objRq.GetHeaderValue(93)
        retItem['시가'] = self.objRq.GetHeaderValue(94)
        retItem['고가'] = self.objRq.GetHeaderValue(95)
        retItem['저가'] = self.objRq.GetHeaderValue(96)
        retItem['미결재약정수량'] = self.objRq.GetHeaderValue(99)
        retItem['전일미결재약정수량'] = self.objRq.GetHeaderValue(37)

        retItem['ATM구분'] = self.objRq.GetHeaderValue(15)

        retItem['매수1호가'] = self.objRq.GetHeaderValue(54)
        retItem['매수1호가수량'] = self.objRq.GetHeaderValue(59)
        retItem['매도1호가'] = self.objRq.GetHeaderValue(37)
        retItem['매도1호가수량'] = self.objRq.GetHeaderValue(42)

        retItem['K200지수'] = self.objRq.GetHeaderValue(89)
        retItem['BASIS'] = self.objRq.GetHeaderValue(90)

        return True



# CpFutureBid : 선물 시간대별 리스트 조회
class CpFutureBid:
    def __init__(self):
        self.objRq = win32com.client.Dispatch("Dscbo1.FutureBid1")

    def request(self, code, retList):
        self.objRq.SetInputValue(0, code)
        self.objRq.SetInputValue(1, 75)  # 요청개수

        datacnt = 0
        while True:
            self.objRq.BlockRequest()

            rqStatus = self.objRq.GetDibStatus()
            rqRet = self.objRq.GetDibMsg1()
            if rqStatus != 0:
                print("통신상태", rqStatus, rqRet)
                return False

            cnt = self.objRq.GetHeaderValue(2)

            for i in range(cnt):
                item = {}
                item['시각'] = self.objRq.GetDataValue(11, i)
                item['매도호가'] = self.objRq.GetDataValue(1, i)
                item['매수호가'] = self.objRq.GetDataValue(2, i)
                item['현재가'] = self.objRq.GetDataValue(3, i)
                item['전일대비'] = self.objRq.GetDataValue(4, i)
                item['누적거래량'] = self.objRq.GetDataValue(6, i)
                item['미체결약정'] = self.objRq.GetDataValue(8, i)
                item['체결거래량'] = self.objRq.GetDataValue(9, i)

                retList.append(item)
            # end of for

            datacnt += cnt
            if self.objRq.Continue == False:
                break
            if datacnt > 500:
                break

        # end of while

        for item in retList:
            data = ''
            for key, value in item.items():
                if (type(value) == float):
                    data += '%s:%.2f' % (key, value)
                elif (type(value) == str):
                    data += '%s:%s' % (key, value)
                elif (type(value) == int):
                    data += '%s:%d' % (key, value)

                data += ' '
            print(data)
        return True


# CpFutureWeek: 선물 일자별
class CpFutureWeek:
    def __init__(self):
        self.objRq = win32com.client.Dispatch("Dscbo1.FutureWeek1")

    def request(self, code, retList):
        self.objRq.SetInputValue(0, code)

        datacnt = 0
        while True:
            self.objRq.BlockRequest()

            rqStatus = self.objRq.GetDibStatus()
            rqRet = self.objRq.GetDibMsg1()
            if rqStatus != 0:
                print("통신상태", rqStatus, rqRet)
                return False

            cnt = self.objRq.GetHeaderValue(0)

            for i in range(cnt):
                item = {}
                item['일자'] = self.objRq.GetDataValue(0, i)
                item['시가'] = self.objRq.GetDataValue(1, i)
                item['고가'] = self.objRq.GetDataValue(2, i)
                item['저가'] = self.objRq.GetDataValue(3, i)
                item['종가'] = self.objRq.GetDataValue(4, i)
                item['전일대비'] = self.objRq.GetDataValue(5, i)
                item['누적거래량'] = self.objRq.GetDataValue(6, i)
                item['거래대금'] = self.objRq.GetDataValue(7, i)
                item['미결제약정'] = self.objRq.GetDataValue(8, i)

                retList.append(item)
            # end of for

            datacnt += cnt
            if self.objRq.Continue == False:
                break
        # end of while

        for item in retList:
            data = ''
            for key, value in item.items():
                if (type(value) == float):
                    data += '%s:%.2f' % (key, value)
                elif (type(value) == str):
                    data += '%s:%s' % (key, value)
                elif (type(value) == int):
                    data += '%s:%d' % (key, value)

                data += ' '
            print(data)
        return True


# CpFutureOptionOrder : 선물/옵션 주문
class CpFutureOptionOrder:
    def __init__(self):
        self.acc = g_objCpTrade.AccountNumber[0]  # 계좌번호
        self.accFlag = g_objCpTrade.GoodsList(self.acc, 2)  # 선물/옵션 계좌구분
        print(self.acc, self.accFlag[0])
        self.objOrder = win32com.client.Dispatch("CpTrade.CpTd6831")

    def Order(self, buysell, code, price, amount, retData):
        self.objOrder.SetInputValue(1, self.acc)
        self.objOrder.SetInputValue(2, code)
        self.objOrder.SetInputValue(3, amount)
        self.objOrder.SetInputValue(4, price)
        self.objOrder.SetInputValue(5, buysell)  # '1' 매도 '2' 매수
        self.objOrder.SetInputValue(6, '1')  # 주문유형 : '1' 지정가
        self.objOrder.SetInputValue(7, '0')  # '주문 조건 구분 '0' : 없음

        ret = self.objOrder.BlockRequest()
        if ret == 4:
            remainTime = g_objCpStatus.LimitRequestRemainTime
            print('연속조회 제한 오류, 남은 시간', remainTime)
            return False

        rqStatus = self.objOrder.GetDibStatus()
        rqRet = self.objOrder.GetDibMsg1()
        print("통신상태", rqStatus, rqRet)
        if rqStatus != 0:
            return False

        retData['종목'] = code
        retData['주문수량'] = self.objOrder.GetHeaderValue(3)
        retData['주문가격'] = self.objOrder.GetHeaderValue(4)
        retData['주문번호'] = self.objOrder.GetHeaderValue(8)
        return True

    def buyOrder(self, code, price, amount, retData):
        return self.Order('2', code, price, amount, retData)

    def sellOrder(self, code, price, amount, retData):
        return self.Order('1', code, price, amount, retData)


# CpFutureBalance: 선물 잔고
class CpFutureBalance:
    def __init__(self):
        self.objRq = win32com.client.Dispatch("CpTrade.CpTd0723")
        self.acc = g_objCpTrade.AccountNumber[0]  # 계좌번호
        self.accFlag = g_objCpTrade.GoodsList(self.acc, 2)  # 선물/옵션 계좌구분
        print(self.acc, self.accFlag[0])

    def request(self, retList):
        self.objRq.SetInputValue(0, self.acc)
        self.objRq.SetInputValue(1, self.accFlag[0])
        self.objRq.SetInputValue(4, 50)

        while True:
            self.objRq.BlockRequest()

            rqStatus = self.objRq.GetDibStatus()
            rqRet = self.objRq.GetDibMsg1()

            if rqStatus != 0:
                print("통신상태", rqStatus, rqRet)
                return False

            cnt = self.objRq.GetHeaderValue(2)

            for i in range(cnt):
                item = {}
                item['코드'] = self.objRq.GetDataValue(0, i)
                item['종목명'] = self.objRq.GetDataValue(1, i)
                flag = self.objRq.GetDataValue(2, i)
                if flag == '1':
                    item['잔고구분'] = '매도'
                elif flag == '2':
                    item['잔고구분'] = '매수'

                item['잔고수량'] = self.objRq.GetDataValue(3, i)
                item['청산가능수량'] = self.objRq.GetDataValue(9, i)
                item['평균단가'] = self.objRq.GetDataValue(5, i)

                if "101" in item['코드']:
                    item['현재가'] = get_future_price(item['코드'])

                    item['매입금액'] = item['평균단가'] * item['잔고수량'] * 250000
                    if item['잔고구분'] == '매수':
                        item['평가손익'] = (item['현재가'] - item['평균단가']) * 250000 * item['잔고수량']
                    else:
                        item['평가손익'] = (item['현재가'] - item['평균단가']) * -250000 * item['잔고수량']
                    item['평가수익률'] = (item['평가손익'] / item['매입금액']) * 100


                else:
                    item['현재가'] = get_option_price(item['코드'])
                    item['매입금액'] = item['평균단가']*item['잔고수량']*250000
                    if item['잔고구분'] == '매수':
                        item['평가손익'] = (item['현재가'] - item['평균단가'])*250000*item['잔고수량']
                    else:
                        item['평가손익'] = (item['현재가'] - item['평균단가']) *-250000 * item['잔고수량']
                    item['평가수익률'] = (item['평가손익']/item['매입금액'])*100


                retList.append(item)
                print_item_data(item)

            if self.objRq.Continue == False:
                break
        return True


# CpFutureNContract: 선물 미체결 조회
class CpFutureNContract:
    def __init__(self):
        self.objRq = win32com.client.Dispatch("CpTrade.CpTd5371")
        self.acc = g_objCpTrade.AccountNumber[0]  # 계좌번호
        self.accFlag = g_objCpTrade.GoodsList(self.acc, 2)  # 선물/옵션 계좌구분
        print(self.acc, self.accFlag[0])

    def request(self, retList):
        self.objRq.SetInputValue(0, self.acc)
        self.objRq.SetInputValue(1, self.accFlag[0])
        self.objRq.SetInputValue(6, '3')  # '3' : 미체결

        while True:
            self.objRq.BlockRequest()

            rqStatus = self.objRq.GetDibStatus()
            rqRet = self.objRq.GetDibMsg1()
            if rqStatus != 0:
                print("통신상태", rqStatus, rqRet)
                return False

            cnt = self.objRq.GetHeaderValue(6)

            for i in range(cnt):
                item = {}
                item['주문번호'] = self.objRq.GetDataValue(2, i)
                item['코드'] = self.objRq.GetDataValue(4, i)
                item['종목명'] = self.objRq.GetDataValue(5, i)
                item['주문가격'] = self.objRq.GetDataValue(8, i)
                item['잔량'] = self.objRq.GetDataValue(9, i)
                item['거래구분'] = self.objRq.GetDataValue(6, i)

                retList.append(item)
            # end of for

            if self.objRq.Continue == False:
                break
        # end of while

        for item in retList:
            data = ''
            for key, value in item.items():
                if (type(value) == float):
                    data += '%s:%.2f' % (key, value)
                elif (type(value) == str):
                    data += '%s:%s' % (key, value)
                elif (type(value) == int):
                    data += '%s:%d' % (key, value)

                data += ' '
            print(data)
        return True



class CpFutureOptionCancel:
    def __init__(self):
        self.objCancel = win32com.client.Dispatch("CpTrade.CpTd6833")

    def cancel_order(self, 원주문번호, 종목코드, 취소수량, 상품구분코드="50"):
        self.objCancel.SetInputValue(2, 원주문번호)      # 원주문번호 (long)
        계좌번호 = g_objCpTrade.AccountNumber[0]  # 계좌번호
        self.objCancel.SetInputValue(3, 계좌번호)        # 계좌번호 (string)
        self.objCancel.SetInputValue(4, 종목코드)        # 종목코드 (string)
        self.objCancel.SetInputValue(5, 취소수량)        # 취소수량 (long)
        self.objCancel.SetInputValue(6, 상품구분코드)     # 상품관리구분코드 (default: "50")

        self.objCancel.BlockRequest()

        상태 = self.objCancel.GetHeaderValue(0)  # 상태 코드
        메시지 = self.objCancel.GetHeaderValue(1)  # 상태 메시지

        if 상태 == 0:
            주문번호 = self.objCancel.GetHeaderValue(5)
            return True, f"✅ 취소 성공 - 주문번호: {주문번호}"
        else:
            return False, f"❌ 취소 실패 - {메시지}"





# CpFutureList: 선물 종목 리스트
class CpFutureList:
    def __init__(self):
        self.objRq = win32com.client.Dispatch("CpUtil.CpFutureCode")

    def getCount(self):
        return self.objRq.GetCount()

    def getData(self, index):
        code = self.objRq.GetData(0, index)  # 0: 종목코드
        name = self.objRq.GetData(1, index)  # 1: 종목명
        return code, name

    def request(self):
        count = self.getCount()
        print(f"\n총 {count}개 종목")
        print("\n=== 선물 종목 리스트 ===")
        for i in range(count):
            code, name = self.getData(i)
            print(f"코드: {code} 종목명: {name}")
        return True



# CpOptionList: 옵션 종목 리스트
class CpOptionList:
    def __init__(self):
        self.objRq = win32com.client.Dispatch("CpUtil.CpOptionCode")

    def getCount(self):
        return self.objRq.GetCount()

    def getData(self, index):
        code = self.objRq.GetData(0, index)  # 0: 종목코드
        name = self.objRq.GetData(1, index)  # 1: 종목명
        return code, name

    def request(self):
        count = self.getCount()
        print(f"\n총 {count}개 종목")
        print("\n=== 옵션 종목 리스트 ===")
        for i in range(count):
            code, name = self.getData(i)
            print(f"코드: {code} 종목명: {name}")
        return True

      # 미체결 주문 전체 취소 함수
def cancel_all_unfilled_orders():

    # 미체결 주문 조회
    order_checker = CpFutureNContract()

    unfilled_orders = []
    order_checker.request(unfilled_orders)

    if not unfilled_orders:
        print("✔ 미체결 주문이 없습니다.")
        return

    # 미체결 주문 취소
    order_canceler = CpCancelOrder()
    for order in unfilled_orders:
        order_canceler.cancel(order['주문번호'], order['코드'], order['잔량'])


def get_future_price(code):
    objFutureMst = CpFutureMst()
    retItem = {}
    if objFutureMst.request(code, retItem):
        current_price = retItem.get('현재가', '정보 없음')
        if isinstance(current_price, (int, float)):
            return round(current_price, 2)  # 두 자리로 반올림
        return "선물 현재가 조회 실패"
    else:
        return "선물 현재가 조회 실패"

def get_option_price(code):
    objOptionMst = CpOptionMst()
    retItem = {}
    if objOptionMst.request(code, retItem):
        current_price = retItem.get('현재가', '정보 없음')
        if isinstance(current_price, (int, float)):
            return round(current_price, 2)  # 두 자리로 반올림
        return "옵션 현재가 조회 실패"
    else:
        return "옵션 현재가 조회 실패"





# CpFutureOptionOrderQty: 선물/옵션 신규주문 가능수량 조회
class CpFutureOptionOrderQty:
    def __init__(self):
        self.objRq = win32com.client.Dispatch("CpTrade.CpTd6722")
        self.acc = g_objCpTrade.AccountNumber[0]  # 계좌번호
        self.accFlag = g_objCpTrade.GoodsList(self.acc, 2)[0]  # 선물/옵션 계좌구분

    def request(self, code, price=0, orderType='1', 상품구분코드='50', 수수료포함여부='Y'):
        self.objRq.SetInputValue(0, self.acc)              # 계좌번호
        self.objRq.SetInputValue(1, code)                  # 종목코드
        self.objRq.SetInputValue(2, price)                 # 주문가격 (시장가/최유리 주문은 0)
        self.objRq.SetInputValue(3, orderType)             # 주문유형코드 (1: 지정가, 2: 시장가 등)
        self.objRq.SetInputValue(4, 상품구분코드)            # 상품관리구분코드 (기본 50)
        self.objRq.SetInputValue(5, 수수료포함여부)          # 수수료포함여부 (Y/N)

        self.objRq.BlockRequest()

        rqStatus = self.objRq.GetDibStatus()
        rqRet = self.objRq.GetDibMsg1()

        if rqStatus != 0:
            print("통신상태", rqStatus, rqRet)
            return None

        data = {}
        data['현금주문전주문가능금액'] = self.objRq.GetHeaderValue(2)
        data['대용주문전주문가능금액'] = self.objRq.GetHeaderValue(3)
        data['총액주문전주문가능금액'] = self.objRq.GetHeaderValue(4)

        data['현금매도신규분증거금'] = self.objRq.GetHeaderValue(11)
        data['대용매도신규분증거금'] = self.objRq.GetHeaderValue(12)
        data['총액매도신규분증거금'] = self.objRq.GetHeaderValue(13)

        data['현금매도주문후가능금액'] = self.objRq.GetHeaderValue(14)
        data['대용매도주문후가능금액'] = self.objRq.GetHeaderValue(15)
        data['총액매도주문후가능금액'] = self.objRq.GetHeaderValue(16)

        data['매도보유포지션수량'] = self.objRq.GetHeaderValue(17)
        data['매도청산주문가능수량'] = self.objRq.GetHeaderValue(18)
        data['매도신규주문가능수량'] = self.objRq.GetHeaderValue(19)
        data['매도총주문가능수량'] = self.objRq.GetHeaderValue(20)

        data['현금매수신규분증거금'] = self.objRq.GetHeaderValue(21)
        data['대용매수신규분증거금'] = self.objRq.GetHeaderValue(22)
        data['총액매수신규분증거금'] = self.objRq.GetHeaderValue(23)

        data['현금매수주문후가능금액'] = self.objRq.GetHeaderValue(24)
        data['대용매수주문후가능금액'] = self.objRq.GetHeaderValue(25)
        data['총액매수주문후가능금액'] = self.objRq.GetHeaderValue(26)

        data['매수보유포지션수량'] = self.objRq.GetHeaderValue(27)
        data['매수청산주문가능수량'] = self.objRq.GetHeaderValue(28)
        data['매수신규주문가능수량'] = self.objRq.GetHeaderValue(29)
        data['매수총주문가능수량'] = self.objRq.GetHeaderValue(30)

        return data


if __name__ == "__main__":
    if False == InitPlusCheck():
        exit()

    # 잔고 조회
    print("\n=== 선물/옵션 잔고 조회 ===")
    objBalance = CpFutureBalance()
    balanceList = []
    if objBalance.request(balanceList):
        print("\n잔고 조회 완료")
    else:
        print("\n잔고 조회 실패")

    # 신규 주문 가능 수량 조회 예제
    print("\n=== 선물/옵션 신규 주문 가능 수량 조회 ===")
    # 잔고가 있는 종목이 있다면 그 종목으로 테스트
    if balanceList:
        code = balanceList[0]['코드']  # 잔고 종목 중 첫 번째 코드 사용
        print(f"조회할 종목 코드: {code}")

        objOrderAvail = CpFutureOptionOrderQty()
        orderAvailData = objOrderAvail.request(code)

        if orderAvailData is not None:
            print("\n[신규 주문 가능 수량 결과]")
            for key, value in orderAvailData.items():
                print(f"{key}: {value}")
        else:
            print("신규 주문 가능 수량 조회 실패")
    else:
        print("잔고가 없어 신규 주문 가능 수량 조회를 건너뜀")