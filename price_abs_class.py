from abc import ABC, abstractmethod
import redis
import requests
import json

# 서버 정보 변수
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
                print(f"조회된 가격: {prices}") # 모든 소스에서 조회된 가격 정보 확인 (디버깅 용도)
                for fetched_price in prices.values():
                    if fetched_price is not None:
                        return fetched_price
                return None

    def add_fetcher(self, fetcher: CodePriceFetcher):
        self.fetchers.append(fetcher)

if __name__ == "__main__":
    # Redis 연결 설정
    redis_fetcher = RedisPriceFetcher()

    # API 서버 URL 설정
    api_fetcher = APIServerPriceFetcher()

    price_manager = CodePriceManager(fetchers=[redis_fetcher, api_fetcher])

    option_code_to_check = "209DT350"
    future_code_to_check = "101W6"

    print("--- 옵션 코드 조회 ---")
    option_price = price_manager.get_price(option_code_to_check)
    if option_price is not None:
        print(f"{option_code_to_check} 현재가 (우선순위 없음): {option_price}")
    else:
        print(f"{option_code_to_check} 가격 조회 실패 (우선순위 없음)")

    print("-" * 20)

    print("--- 선물 코드 조회 ---")
    future_price = price_manager.get_price(future_code_to_check)
    if future_price is not None:
        print(f"{future_code_to_check} 현재가 (우선순위 없음): {future_price}")
    else:
        print(f"{future_code_to_check} 가격 조회 실패 (우선순위 없음)")