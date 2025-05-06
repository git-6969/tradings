import sys
import schedule
import time
from datetime import datetime
from Comms_Class import InitPlusCheck, CpOptionMst, CpFutureOptionOrder

# 매도 비율 설정 (예: 62% 먼저 매도, 38% 나중에 매도)
SELL_FIRST_PERCENT = 0.62
SELL_SECOND_PERCENT = 1.0 - SELL_FIRST_PERCENT

class FutureOptionApp:
    def __init__(self, option_code, target_sell_amount):
        self.option_code = option_code
        self.target_sell_amount = target_sell_amount

    def execute_option_sell(self):
        # 옵션 현재가 조회
        option_price = self.get_option_price(self.option_code)

        # 전체 매도 수량 계산
        total_sell_qty = self.calculate_sell_quantity(option_price, self.target_sell_amount)

        # 설정된 비율에 따라 매도 개수 나누기
        first_sell_qty = round(total_sell_qty * SELL_FIRST_PERCENT)
        second_sell_qty = total_sell_qty - first_sell_qty

        print(f"[주문 스냅샷] 옵션 코드: {self.option_code}, 현재가: {option_price}")
        print(f"1차 매도 수량({SELL_FIRST_PERCENT*100}%): {first_sell_qty}, 2차 매도 수량({SELL_SECOND_PERCENT*100}%): {second_sell_qty}")

        # 매도 실행
        self.place_option_order(self.option_code, option_price, first_sell_qty)
        self.place_option_order(self.option_code, option_price, second_sell_qty)

    def place_option_order(self, option_code, price, sell_quantity):
        if sell_quantity > 0:
            print(f"[주문 실행] {option_code} 옵션 {sell_quantity}개 매도 (매도 가격: {price})")
            retData = {}
            objOrder = CpFutureOptionOrder()
            success = objOrder.sellOrder(option_code, price, sell_quantity, retData)
            if success:
                print(f"[주문 성공] {option_code} {sell_quantity}개 매도 완료 (매도 가격: {price})")
            else:
                print(f"[주문 실패] {option_code} 매도 실패")
        else:
            print(f"[주문 오류] {option_code} 매도 수량이 0개 이하입니다.")

    def get_option_price(self, option_code):
        objOptionMst = CpOptionMst()
        retItem = {}
        if objOptionMst.request(option_code, retItem):
            return retItem.get('현재가', 0)
        else:
            print("[오류] 옵션 가격 조회 실패")
            return 0

    def calculate_sell_quantity(self, option_price, target_sell_amount):
        cost_per_option = option_price * 250000
        return target_sell_amount // cost_per_option if cost_per_option > 0 else 0

if __name__ == "__main__":
    if not InitPlusCheck():
        sys.exit(0)

    option_code_1 = "209DQ332"
    target_sell_amount_1 = 5000000
    option_code_2 = "309DQ320"
    target_sell_amount_2 = 5000000

    app_1 = FutureOptionApp(option_code_1, target_sell_amount_1)
    app_2 = FutureOptionApp(option_code_2, target_sell_amount_2)

    schedule.every().day.at("11:00:00").do(lambda: (app_1.execute_option_sell(), app_2.execute_option_sell()))

    print("옵션 매도 스케줄링 시작 (11:00:00 실행 대기 중...)")
    while True:
        now = datetime.now()
        print(f"현재 시간: {now.strftime('%H:%M:%S')} - 11:00:00 실행 대기 중...")
        schedule.run_pending()
        if now.hour == 10 and now.minute == 31:
            print("[주문 실행] 11:00:00 옵션 매도 시작")
            app_1.execute_option_sell()
            app_2.execute_option_sell()
            print("[주문 완료] 옵션 매도 작업 완료")
            break
        time.sleep(5)
