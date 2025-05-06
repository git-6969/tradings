import sys
import os
from PyQt5.QtWidgets import *
import win32com.client
import ctypes

sys.path.append(os.path.abspath("../Smalls"))
import msg_client

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


# CpFutureMst: 선물 현재가
class CpFutureMst:
    def __init__(self):
        self.objRq = win32com.client.Dispatch("Dscbo1.FutureMst")

    def request(self, code, retItem):
        self.objRq.SetInputValue(0, code)
        self.objRq.BlockRequest()

        rqStatus = self.objRq.GetDibStatus()
        rqRet = self.objRq.GetDibMsg1()
        print("통신상태", rqStatus, rqRet)
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

        for key, value in retItem.items():
            if (type(value) == float):
                print('%s:%.2f' % (key, value))
            else:
                print(key, ':', value)
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


# CpFutureOrder : 선물 주문
class CpFutureOrder:
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
        msg_client.send_message(f"{self.acc} {self.accFlag[0]}");

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
                item['평균단가'] = self.objRq.GetDataValue(5, i)
                item['청산가능수량'] = self.objRq.GetDataValue(9, i)

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
            msg_client.send_message(f"{data}");

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



if __name__ == "__main__":
    if False == InitPlusCheck():
        exit()

    objRq = CpFutureBalance()
    retList = []
    objRq.request(retList)


    objRq = CpFutureNContract()
    retList = []
    objRq.request(retList)
