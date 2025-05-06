import threading
import time

# ✅ 외부 모듈에서 CpFutureOptionOrder 임포트
from Comms_Class import InitPlusCheck
from Comms_Class import CpOptionMst
from Comms_Class import CpFutureOptionOrder


# ✅ 고급 옵션 주문 클래스
class AdvancedOptionTrader:
    def __init__(self, order_api, max_retries=5, retry_delay=2.0, slippage=0.2, split_unit=20):
        self.order_api = order_api
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.slippage = slippage
        self.split_unit = split_unit

    def calculate_quantity(self, order_price, amount, contract_unit):
        if order_price <= 0:
            return 0
        return int(amount // (order_price * contract_unit))

    def adjust_price(self, base_price, order_type):
        delta = base_price * (self.slippage / 100)
        return round(base_price + delta, 2) if order_type == 'buy' else round(base_price - delta, 2)

    def place_order(self, code, base_price, quantity, order_type, logger=None):
        for attempt in range(1, self.max_retries + 1):
            adjusted_price = self.adjust_price(base_price, order_type)
            ret = {}

            if order_type == 'buy':
                success = self.order_api.buyOrder(code, adjusted_price, quantity, ret)
            else:
                success = self.order_api.sellOrder(code, adjusted_price, quantity, ret)

            log_msg = (
                f"[{attempt}차 시도] {order_type.upper()} 주문 → 수량: {quantity}, 가격: {adjusted_price} "
                f"→ {'성공' if success else '실패'}"
            )
            if logger:
                logger(log_msg)

            if success:
                return True, ret

            time.sleep(self.retry_delay)

        return False, ret

    def place_orders_parallel(self, orders, logger=None):
        threads = []
        results = []

        def order_thread(code, price, qty, otype):
            success, response = self.place_order(code, price, qty, otype, logger)
            results.append((code, success, response))

        for code, price, qty, otype in orders:
            t = threading.Thread(target=order_thread, args=(code, price, qty, otype))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        return results

    def place_order_split(self, code, base_price, total_quantity, order_type, logger=None):
        remaining_qty = total_quantity
        success_total = True
        all_responses = []

        while remaining_qty > 0:
            order_qty = min(self.split_unit, remaining_qty)
            success, response = self.place_order(code, base_price, order_qty, order_type, logger)
            all_responses.append((order_qty, success, response))

            if not success:
                success_total = False
                if logger:
                    logger(f"❌ 분할 주문 실패 → 수량: {order_qty}")
            else:
                if logger:
                    logger(f"✅ 분할 주문 성공 → 수량: {order_qty}")

            remaining_qty -= order_qty
            time.sleep(self.retry_delay)

        return success_total, all_responses


# --------------------------------------------
# ✅ 예제 실행 (실제 사용 시만 실행)

if __name__ == "__main__":
    if not InitPlusCheck():
        exit()

    # 🔧 기본 설정 및 준비
    order_api = CpFutureOptionOrder()
    trader = AdvancedOptionTrader(order_api)

    # 🎯 옵션 1 정보
    code1 = '201W4327'
    price1 = 0.2
    amount1 = 12000000
    contract_unit = 250000
    quantity1 = trader.calculate_quantity(price1, amount1, contract_unit)

    # 🎯 옵션 2 정보
    code2 = '301W4285'
    price2 = 0.5
    amount2 = 12000000
    quantity2 = trader.calculate_quantity(price2, amount2, contract_unit)

    # ⚡ 단일 주문 예제 실행
    print("\n✅ [단일 주문 예제]")
    success, result = trader.place_order(code1, price1, quantity1, 'buy', logger=print)

    # ⚡ 병렬 주문 예제 실행
    print("\n✅ [병렬 주문 예제]")
    orders = [
        (code1, price1, quantity1, 'buy'),
        (code2, price2, quantity2, 'sell'),
    ]
    results = trader.place_orders_parallel(orders, logger=print)

    for code, success, res in results:
        print(f"📌 {code} 주문 결과 → {'성공' if success else '실패'}, 응답: {res}")

    # ⚡ 분할 주문 예제 실행
    print("\n✅ [분할 주문 예제]")
    split_success, split_results = trader.place_order_split(code1, price1, quantity1, 'buy', logger=print)
    for qty, success, res in split_results:
        print(f"📦 {qty}계약 주문 결과 → {'성공' if success else '실패'}, 응답: {res}")
