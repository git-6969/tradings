import sys
from Comms_Class import InitPlusCheck, CpOptionMst, CpFutureOptionOrder

# 매도 비율 설정 (예: 62% 먼저 매도, 38% 나중에 매도)
SELL_FIRST_PERCENT = 0.62
SELL_SECOND_PERCENT = 1.0 - SELL_FIRST_PERCENT


class FutureOptionApp:
    def __init__(self, option_code, target_sell_amount):
        self.option_code = option_code
        self.target_sell_amount = target_sell_amount
        self.execute_option_sell()  # 옵션 매도 실행

    def execute_option_sell(self):
        # 옵션 현재가 조회
        option_price = self.get_option_price(self.option_code)

        # 전체 매도 수량 계산
        total_sell_qty = self.calculate_sell_quantity(option_price, self.target_sell_amount)

        # 설정된 비율에 따라 매도 개수 나누기
        first_sell_qty = round(total_sell_qty * SELL_FIRST_PERCENT)  # 첫 번째 매도 비율 적용
        second_sell_qty = total_sell_qty - first_sell_qty  # 나머지 수량

        print(f"옵션 코드: {self.option_code}, 현재가: {option_price}, 1차 매도 수량({SELL_FIRST_PERCENT*100}%): {first_sell_qty}, 2차 매도 수량({SELL_SECOND_PERCENT*100}%): {second_sell_qty}")

        # 첫 번째 매도 실행
        self.place_option_order(self.option_code, option_price, first_sell_qty)

        # 두 번째 매도 실행
        self.place_option_order(self.option_code, option_price, second_sell_qty)

    def place_option_order(self, option_code, price, sell_quantity):
        if sell_quantity > 0:
            print(f"{option_code} 옵션 {sell_quantity}개 매도 실행 (매도 가격: {price})")
            retData = {}
            objOrder = CpFutureOptionOrder()
            success = objOrder.sellOrder(option_code, price, sell_quantity, retData)  # 옵션 현재가로 매도
            if success:
                print(f"{option_code} 매도 주문 성공: {sell_quantity}개 (매도 가격: {price})")
            else:
                print(f"{option_code} 매도 주문 실패")
        else:
            print(f"{option_code} 매도 수량이 0개 이하입니다.")

    def get_option_price(self, option_code):
        # 옵션 가격 조회 로직
        objOptionMst = CpOptionMst()
        retItem = {}
        if objOptionMst.request(option_code, retItem):
            return retItem.get('현재가', 0)
        else:
            print("옵션 가격 조회 실패")
            return 0

    def calculate_sell_quantity(self, option_price, target_sell_amount):
        # 1옵션 가격 × 250,000원을 기준으로 매도 가능한 수량을 계산
        cost_per_option = option_price * 250000
        if cost_per_option > 0:
            return target_sell_amount // cost_per_option
        else:
            return 0


if __name__ == "__main__":
    if not InitPlusCheck():
        sys.exit(0)

    # 첫 번째 옵션 코드와 매도 금액 설정
    option_code_1 = "209DP342"
    target_sell_amount_1 = 7000000

    # 두 번째 옵션 코드와 매도 금액 설정
    option_code_2 = "309DP330"
    target_sell_amount_2 = 7000000

    # 첫 번째 옵션 매도
    app_1 = FutureOptionApp(option_code_1, target_sell_amount_1)

    # 두 번째 옵션 매도
    app_2 = FutureOptionApp(option_code_2, target_sell_amount_2)