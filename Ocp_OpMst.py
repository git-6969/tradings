import win32com.client
import ctypes
import time

import sys
import os


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
        print("PLUS가 정상적으로 연결되지 않음 ")
        return False

    # 주문 관련 초기화
    ret = g_objCpTrade.TradeInit(0)
    if (ret != 0):
        print("주문 초기화 실패, 오류번호 ", ret)
        return False

    return True


# CpFutureMst: 선물 현재가
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


if __name__ == "__main__":
    if False == InitPlusCheck():
        exit()

    code = "209DN352"

    while True:
        objOptionMst = CpOptionMst()
        retItem = {}
        if objOptionMst.request(code, retItem):
            print("옵션 현재가 정보:")

            if retItem.get("ATM구분") == "1":
                print("ATM")
            if retItem.get("ATM구분") == "2":
                print("ITM")
            if retItem.get("ATM구분") == "3":
                print("OTM")

            for key, value in retItem.items():
                if (type(value) == float):
                    print(f"{key}: {value:.2f}")
                else:
                    print(f"{key}: {value}")


        else:
            print("옵션 코드 조회 실패.")
        time.sleep(2)  # 2초 대기