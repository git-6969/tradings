import sys
from PyQt5.QtWidgets import *
import win32com.client
import locale
import os
import time
import datetime
import csv

locale.setlocale(locale.LC_ALL, '')

# cp object
g_objCodeMgr = win32com.client.Dispatch('CpUtil.CpCodeMgr')
g_objCpStatus = win32com.client.Dispatch('CpUtil.CpCybos')
g_objCpTrade = win32com.client.Dispatch('CpTrade.CpTdUtil')
g_objOptionMgr = win32com.client.Dispatch("CpUtil.CpOptionCode")

gCSVFile = 'market_data.csv'

# CpEvent: 실시간 이벤트 수신 클래스
class CpEvent:
    def set_params(self, client, name, caller):
        self.client = client  # CP 실시간 통신 object
        self.name = name  # 서비스가 다른 이벤트를 구분하기 위한 이름
        self.caller = caller  # callback 을 위해 보관

    def OnReceived(self):
        if self.name == 'optioncur':
            code = self.client.GetHeaderValue(0)
            data = next((item for item in self.caller.marketData if item['code'] == code), None)

            if data:
                data['time'] = self.client.GetHeaderValue(1)  # 초
                data['시가'] = self.client.GetHeaderValue(4)
                data['고가'] = self.client.GetHeaderValue(5)
                data['저가'] = self.client.GetHeaderValue(6)
                data['매도호가'] = self.client.GetHeaderValue(17)
                data['매수호가'] = self.client.GetHeaderValue(18)
                data['현재가'] = self.client.GetHeaderValue(2)  # 현재가
                data['대비'] = self.client.GetHeaderValue(3)  # 대비
                data['거래량'] = self.client.GetHeaderValue(7)  # 거래량
                data['미결제'] = self.client.GetHeaderValue(16)
                lastday = data['전일종가']
                diff = data['대비']
                if lastday:
                    diffp = (diff / lastday) * 100
                    data['대비율'] = diffp

# CpPublish: 실시간 데이터 요청 클래스
class CpPublish:
    def __init__(self, name, serviceID):
        self.name = name
        self.obj = win32com.client.Dispatch(serviceID)
        self.bIsSB = False

    def Subscribe(self, var, caller):
        if self.bIsSB:
            self.Unsubscribe()

        if len(var) > 0:
            self.obj.SetInputValue(0, var)

        handler = win32com.client.WithEvents(self.obj, CpEvent)
        handler.set_params(self.obj, self.name, caller)
        self.obj.Subscribe()
        self.bIsSB = True

    def Unsubscribe(self):
        if self.bIsSB:
            self.obj.Unsubscribe()
        self.bIsSB = False

# CpPBStockCur: 실시간 현재가 요청 클래스
class CpPBStockCur(CpPublish):
    def __init__(self):
        super().__init__('optioncur', 'CpSysDib.OptionCurOnly')

# CpMarketEye: 복수종목 현재가 통신 서비스
class CpMarketEye:
    def Request(self, codes, caller):
        # 연결 여부 체크
        objCpCybos = win32com.client.Dispatch('CpUtil.CpCybos')
        bConnect = objCpCybos.IsConnect
        if bConnect == 0:
            print('PLUS가 정상적으로 연결되지 않음.')
            return False

        # 관심종목 객체 구하기
        objRq = win32com.client.Dispatch('CpSysDib.MarketEye')
        # 필드
        rqField = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 23, 27]  # 요청 필드
        objRq.SetInputValue(0, rqField)  # 요청 필드
        objRq.SetInputValue(1, codes)  # 종목코드 or 종목코드 리스트
        objRq.BlockRequest()

        # 현재가 통신 및 통신 에러 처리
        rqStatus = objRq.GetDibStatus()
        rqRet = objRq.GetDibMsg1()
        print('통신상태', rqStatus, rqRet)
        if rqStatus != 0:
            return False

        cnt = objRq.GetHeaderValue(2)

        caller.marketData = []
        for i in range(cnt):
            item = {}
            item['code'] = objRq.GetDataValue(0, i)  # 코드
            item['종목명'] = g_objCodeMgr.CodeToName(item['code'])
            item['time'] = objRq.GetDataValue(1, i)  # 시간
            item['대비'] = objRq.GetDataValue(3, i)  # 전일대비
            item['현재가'] = objRq.GetDataValue(4, i)  # 현재가
            item['시가'] = objRq.GetDataValue(5, i)  # 시가
            item['고가'] = objRq.GetDataValue(6, i)  # 고가
            item['저가'] = objRq.GetDataValue(7, i)  # 저가
            item['매도호가'] = objRq.GetDataValue(8, i)  # 매도호가
            item['매수호가'] = objRq.GetDataValue(9, i)  # 매수호가
            item['거래량'] = objRq.GetDataValue(10, i)  # 거래량
            item['전일종가'] = objRq.GetDataValue(11, i)  # 전일종가
            item['미결제'] = objRq.GetDataValue(12, i)
            if item['전일종가'] != 0:
                item['대비율'] = (item['대비'] / item['전일종가']) * 100
            else:
                item['대비율'] = 0
            item['행사가'] = caller.codeToPrice[item['code']]
            caller.marketData.append(item)

        print(caller.marketData)
        return True

class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PLUS API TEST')
        self.setGeometry(300, 300, 300, 240)
        self.isSB = False
        self.objCur = []
        self.marketData = []
        self.codeToPrice = {}

        btnStart = QPushButton('요청 시작', self)
        btnStart.move(20, 20)
        btnStart.clicked.connect(self.btnStart_clicked)

        btnCSV = QPushButton('CSV 내보내기', self)
        btnCSV.move(20, 70)
        btnCSV.clicked.connect(self.btnCSV_clicked)

        btnPrint = QPushButton('DF Print', self)
        btnPrint.move(20, 120)
        btnPrint.clicked.connect(self.btnPrint_clicked)

        btnExit = QPushButton('종료', self)
        btnExit.move(20, 190)
        btnExit.clicked.connect(self.btnExit_clicked)

    def StopSubscribe(self):
        if self.isSB:
            cnt = len(self.objCur)
            for i in range(cnt):
                self.objCur[i].Unsubscribe()
            print(cnt, '종목 실시간 해지되었음')
        self.isSB = False
        self.objCur = []

    def btnStart_clicked(self):
        codes = []
        months = {}
        count = g_objOptionMgr.GetCount()
        for i in range(0, count):
            code = g_objOptionMgr.GetData(0, i)
            name = g_objOptionMgr.GetData(1, i)
            mon = g_objOptionMgr.GetData(3, i)
            opprice = g_objOptionMgr.GetData(4, i)  # 행사가
            if not (mon in months.keys()):
                months[mon] = []
            # 튜플()을 이용해서 데이터를 저장.
            months[mon].append((code, name, mon, opp