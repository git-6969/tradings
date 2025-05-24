import sys
import win32com.client
import ctypes
import time
import socket

g_objCodeMgr = win32com.client.Dispatch('CpUtil.CpCodeMgr')
g_objCpStatus = win32com.client.Dispatch('CpUtil.CpCybos')
g_objCpTrade = win32com.client.Dispatch('CpTrade.CpTdUtil')
g_objFutureMgr = win32com.client.Dispatch("CpUtil.CpFutureCode")


import redis
import json
import requests

from abc import ABC, abstractmethod


# 서버 정보 변수 (전역 변수 유지)
REDIS_HOST = "192.168.55.13"
REDIS_PORT = 6379
REDIS_OPTION_TICKS_KEY_FORMAT = "option:{}:ticks"
REDIS_FUTURE_TICKS_KEY_FORMAT = "future:{}:ticks"

API_URL = "http://192.168.55.13:8000"
API_TICK_ENDPOINT = "/ticks/{}"
API_PRICE_KEY = "price"

class CodePriceFetcher(ABC):
    @abstractmethod
    def fetch_price(self, code: str) -> float | None:
        """
        주어진 코드로 현재 가격을 조회합니다.

        Args:
            code: 조회할 코드 (옵션 또는 선물)

        Returns:
            현재 가격 (float) 또는 조회 실패 시 None
        """
        pass

class RedisPriceFetcher(CodePriceFetcher):
    def __init__(self, host=REDIS_HOST, port=REDIS_PORT,
                 option_ticks_key_format=REDIS_OPTION_TICKS_KEY_FORMAT,
                 future_ticks_key_format=REDIS_FUTURE_TICKS_KEY_FORMAT):
        self.redis_client = redis.StrictRedis(host=host, port=port, decode_responses=True)
        self.option_ticks_key_format = option_ticks_key_format
        self.future_ticks_key_format = future_ticks_key_format

    def fetch_price(self, code: str) -> float | None:
        try:
            if code.startswith("101"):
                key = self.future_ticks_key_format.format(code)
            else:
                key = self.option_ticks_key_format.format(code)
            latest_tick_json = self.redis_client.lindex(key, -1)
            if latest_tick_json:
                try:
                    latest_tick = json.loads(latest_tick_json)
                    price = latest_tick.get('price')
                    if isinstance(price, (int, float)):
                        return float(price)
                    else:
                        print(f"Redis: {code} 마지막 틱에 가격 정보 없음 - {price}")
                        return None
                except json.JSONDecodeError as e:
                    print(f"Redis: {code} 마지막 틱 JSON 파싱 오류: {e}")
                    return None
            else:
                print(f"Redis: {code} 틱 데이터 없음")
                return None
        except redis.exceptions.ConnectionError as e:
            print(f"Redis 연결 오류: {e}")
            return None

class APIServerPriceFetcher(CodePriceFetcher):
    def __init__(self, api_url=API_URL, tick_endpoint=API_TICK_ENDPOINT, price_key=API_PRICE_KEY):
        self.api_url = api_url
        self.tick_endpoint = tick_endpoint
        self.price_key = price_key

    def fetch_price(self, code: str) -> float | None:
        processed_code = code.strip().upper()
        url = f"{self.api_url}{self.tick_endpoint.format(processed_code)}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            try:
                response_data = response.json()
                tick_data = response_data.get("tick", {})  # "tick" 키의 딕셔너리 가져오기
                price = tick_data.get(self.price_key)
                if isinstance(price, (int, float)):
                    return float(price)
                else:
                    print(f"API 서버: {processed_code} 틱 데이터에 가격 정보 없음 - {price}")
                    return None
            except json.JSONDecodeError as e:
                print(f"API 서버: {processed_code} 응답 JSON 파싱 오류: {e}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"API 서버 요청 실패 ({url}): {e}")
            return None

class CodePriceManager:
    def __init__(self, fetchers: list[CodePriceFetcher]):
        self.fetchers = fetchers

    def get_price(self, code: str, use_priority: bool = False) -> float | None:
        if use_priority:
            for fetcher in self.fetchers:
                price = fetcher.fetch_price(code)
                if price is not None:
                    return price
            return None
        else:
            prices = {}
            for i, fetcher in enumerate(self.fetchers):
                price = fetcher.fetch_price(code)
                prices[f"source_{i}"] = price
#                print(f"조회된 가격: {prices}") # 모든 소스에서 조회된 가격 정보 확인 (디버깅 용도)
                for fetched_price in prices.values():
                    if fetched_price is not None:
                        return fetched_price
            return None

    def add_fetcher(self, fetcher: CodePriceFetcher):
        self.fetchers.append(fetcher)


# CodePriceManager를 전역 변수로 생성
redis_fetcher = RedisPriceFetcher()
api_fetcher = APIServerPriceFetcher()
price_manager = CodePriceManager(fetchers=[redis_fetcher, api_fetcher])


# 현재가를 조회하는 함수 (전역 함수)
def get_current_price(code: str, use_priority: bool = False) -> float | None:
    """
    주어진 코드로 현재가를 조회합니다.

    Args:
        code: 조회할 코드 (옵션 또는 선물)
        use_priority: 가격 조회 우선순위 사용 여부 (True: 첫 번째 성공한 가격 반환, False: 모든 소스 조회 후 첫 번째 성공한 가격 반환)

    Returns:
        현재 가격 (float) 또는 조회 실패 시 None
    """
    return price_manager.get_price(code, use_priority)


BOT_TOKEN = '5994386382:AAGM0b3mKFwIjXfSGHhscJCg8FCX7oIu8yM'
CHAT_ID = 1017525086  # 이전에 받은 chat.id 값

def send_telegram_message(message):
    """주어진 chat_id로 텔레그램 메시지 보내는 함수"""
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}'
    response = requests.get(url)
    return response.json()  # 응답 결과 반환





class LoggerMixin:
    def __init__(self, use_qt=False, use_terminal=True, use_telegram=False):
        self.use_qt = use_qt
        self.use_terminal = use_terminal
        self.use_telegram = use_telegram

        # Qt용 시그널은 상속받는 클래스(QThread 등)에서 정의해야 함
        if self.use_qt and not hasattr(self, 'log_signal'):
            raise AttributeError("Qt 로그를 사용하려면 'log_signal'이 정의되어 있어야 합니다.")

    def emit_log(self, message, bold=False):
        current_time = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{current_time}] {message}"

        # 1. Qt UI로 로그 전송
        if self.use_qt:
            self.log_signal.emit(formatted, bold)

        # 2. 터미널 출력
        if self.use_terminal:
            print(formatted)

        # 3. 텔레그램 전송
        if self.use_telegram:
            try:
                send_telegram_message(formatted)  # 그냥 직접 호출!
            except Exception as e:
                print(f"[텔레그램 오류] {e}")

def fetch_last_price(code):
    resp = requests.get(f"http://192.168.55.13:8000/ticks/{code}", params={"n": -1})
    if resp.status_code != 200:
        return None
    data = resp.json()
    tick = data.get("tick")
    if tick:
        return tick.get("price")
    return None


class OptionTickReader:
    def __init__(self, host='localhost', port=6379, db=0):
        self.redis = redis.Redis(host=host, port=port, db=db, decode_responses=True)

    def get_latest_tick(self, option_code):
        """지정한 옵션 코드의 가장 최근 Tick 데이터 반환"""
        key = f"option:{option_code}:ticks"
        data = self.redis.lindex(key, -1)
        return json.loads(data) if data else None

    def get_all_ticks(self, option_code):
        """지정한 옵션 코드의 전체 Tick 데이터 리스트 반환"""
        key = f"option:{option_code}:ticks"
        data = self.redis.lrange(key, 0, -1)
        return [json.loads(item) for item in data]

    def list_option_codes(self):
        """현재 Redis에 저장된 옵션 코드 리스트 반환"""
        keys = self.redis.keys("option:*:ticks")
        return sorted({key.split(":")[1] for key in keys})  # 중복 제거 후 정렬



# option_client.py


class OptionClient:
    def __init__(self, server_url="http://192.168.55.13:8000"):
        self.server_url = server_url

    def get_option_info(self, code):
        try:
            response = requests.get(f"{self.server_url}/option/{code}")
            if response.status_code == 200:
                return response.json()
            else:
                raise ValueError(f"오류: 상태 코드 {response.status_code} - {response.text}")
        except Exception as e:
            raise RuntimeError(f"요청 실패: {e}")



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

    def request(self, code):
        self.objRq.SetInputValue(0, code)
        self.objRq.BlockRequest()

        rqStatus = self.objRq.GetDibStatus()
        rqRet = self.objRq.GetDibMsg1()
        if rqStatus != 0:
            print("통신 오류:", rqRet)
            return None

        # 전체 필드 매핑
        fields = {
            0: "option_code",
            1: "listing_date",
            2: "item_seq_number",
            4: "underlying_asset",
            5: "expiry_year_month",
            6: "strike_price",
            8: "item_name_kor",
            9: "item_name_eng",
            10: "item_name_short",
            11: "option_type",
            12: "base_days",
            13: "days_to_expiry",
            14: "near_term_flag",
            15: "atm_flag",
            16: "listed_date",
            17: "first_trade_date",
            18: "last_trade_date",
            19: "last_trade_flag",
            22: "dividend_index_pv",
            24: "prev_open",
            25: "prev_high",
            26: "prev_low",
            27: "prev_close",
            28: "prev_close_flag",
            29: "margin_base_price",
            30: "margin_base_flag",
            31: "upper_limit_price",
            32: "lower_limit_price",
            36: "cd_rate",
            37: "prev_oi",
            38: "prev_volume",
            39: "prev_value",
            40: "ytd_high_date",
            41: "ytd_high_price",
            42: "ytd_low_date",
            43: "ytd_low_price",
            44: "all_time_high_date",
            45: "all_time_high_price",
            46: "all_time_low_date",
            47: "all_time_low_price",
            48: "market_order_flag",
            51: "base_price",
            52: "base_price_flag",
            53: "implied_volatility",
            54: "market_time",
            55: "last_trade_time",
            58: "ask_price1",
            59: "bid_price1",
            60: "ask_volume1",
            61: "bid_volume1",
            62: "ask_price2",
            63: "bid_price2",
            64: "ask_volume2",
            65: "bid_volume2",
            66: "ask_price3",
            67: "bid_price3",
            68: "ask_volume3",
            69: "bid_volume3",
            70: "ask_price4",
            71: "bid_price4",
            72: "ask_volume4",
            73: "bid_volume4",
            74: "ask_price5",
            75: "bid_price5",
            76: "ask_volume5",
            77: "bid_volume5",
            78: "total_ask_volume",
            79: "total_bid_volume",
            80: "ask_count1",
            81: "ask_count2",
            82: "ask_count3",
            83: "ask_count4",
            84: "ask_count5",
            85: "total_ask_count",
            86: "bid_count1",
            87: "bid_count2",
            88: "bid_count3",
            89: "bid_count4",
            90: "bid_count5",
            91: "total_bid_count",
            92: "trade_volume",
            93: "current_price",
            94: "open_price",
            95: "high_price",
            96: "low_price",
            97: "accum_volume",
            98: "accum_value_million",
            99: "open_interest",
            100: "open_interest_flag",
            101: "settlement_price",
            102: "settlement_flag",
            106: "kospi200_index",
            107: "kospi200_diff",
            108: "greek_iv",
            109: "greek_delta",
            110: "greek_gamma",
            111: "greek_theta",
            112: "greek_vega",
            113: "greek_rho",
            114: "greek_tv",
            115: "volatility",
            116: "expected_price",
            117: "expected_diff",
            118: "market_status"
        }

        # 결과 딕셔너리 구성
        retItem = {}
        for key, name in fields.items():
            try:
                retItem[name] = self.objRq.GetHeaderValue(key)
            except:
                retItem[name] = None

        return retItem




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

    # 미체결 조회
    print("\n=== 선물/옵션 미체결 조회 ===")
    objNContract = CpFutureNContract()
    nContractList = []
    if objNContract.request(nContractList):
        print("\n미체결 조회 완료")
    else:
        print("\n미체결 조회 실패")

    # 선물 현재가 조회
    print("\n=== 선물 현재가 조회 ===")
    objFutureMst = CpFutureMst()
    retItem = {}
    if objFutureMst.request("101W6000", retItem):
        print("\n선물 현재가 조회 완료")
    else:
        print("\n선물 현재가 조회 실패")

    # # 선물 종목 리스트 조회
    # print("\n=== 선물 종목 리스트 조회 ===")
    # objFutureList = CpFutureList()
    # if objFutureList.request():
    #     print("\n선물 종목 리스트 조회 완료")
    # else:
    #     print("\n선물 종목 리스트 조회 실패")

    # # 옵션 종목 리스트 조회
    # print("\n=== 옵션 종목 리스트 조회 ===")
    # objOptionList = CpOptionList()
    # if objOptionList.request():
    #     print("\n옵션 종목 리스트 조회 완료")
    # else:
    #     print("\n옵션 종목 리스트 조회 실패")



#########################
#############################





