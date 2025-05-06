import sys
import win32com.client
import ctypes
import time
import socket

g_objCodeMgr = win32com.client.Dispatch('CpUtil.CpCodeMgr')
g_objCpStatus = win32com.client.Dispatch('CpUtil.CpCybos')
g_objCpTrade = win32com.client.Dispatch('CpTrade.CpTdUtil')
g_objFutureMgr = win32com.client.Dispatch("CpUtil.CpFutureCode")


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




# CpFutureOrderAvail: 선물/옵션 신규주문 가능수량 조회
class CpFutureOrderAvail:
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

        objOrderAvail = CpFutureOrderAvail()
        orderAvailData = objOrderAvail.request(code)

        if orderAvailData is not None:
            print("\n[신규 주문 가능 수량 결과]")
            for key, value in orderAvailData.items():
                print(f"{key}: {value}")
        else:
            print("신규 주문 가능 수량 조회 실패")
    else:
        print("잔고가 없어 신규 주문 가능 수량 조회를 건너뜀")