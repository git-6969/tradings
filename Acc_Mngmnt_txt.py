import sys
import time
from Comms_Class import InitPlusCheck, CpFutureBalance, CpFutureNContract, CpFutureOptionOrder

# 주문 가격 선택 (True: 현재가, False: 0원)
# USE_MARKET_PRICE = False  # 마켓 프라이스 사용 여부 (True: 현재가, False: 0원)
USE_MARKET_PRICE = True

count = 0


def close_all_positions():
    print("\n=== 계좌 내 모든 종목 청산 ===")
    objBalance = CpFutureBalance()
    balanceList = []

    if not objBalance.request(balanceList):
        print("\n잔고 조회 실패, 청산 불가")
        return

    objOrder = CpFutureOptionOrder()

    for item in balanceList:
        code = item['코드']
        qty = item['잔고수량']
        price = item['현재가'] if USE_MARKET_PRICE else 0  # 현재가 또는 0원 선택
        position_type = item['잔고구분']  # '매수' 또는 '매도'

        if qty <= 0:
            continue

        retData = {}
        if position_type == '매수':  # 매수 포지션 → 매도로 청산
            success = objOrder.sellOrder(code, price, qty, retData)
            action = "매도"
        elif position_type == '매도':  # 매도 포지션 → 매수로 청산
            success = objOrder.buyOrder(code, price, qty, retData)
            action = "매수"
        else:
            continue

        status = "✅ 성공" if success else "❌ 실패"
        print(f"{status}: {code} {qty}개 {action} 주문 (가격: {price})")


if __name__ == "__main__":
    if not InitPlusCheck():
        exit()

    while True:
        # 1. 선물 잔고 조회
        print("\n=== 선물 잔고 조회 ===")
        objBalance = CpFutureBalance()
        balanceList = []
        if objBalance.request(balanceList):
            print("\n잔고 조회 완료")
        else:
            print("\n잔고 조회 실패")

        # 2. 종목 정산 실행
        close_all_positions()

        # 3. 잔고 조회 재확인
        print("\n=== 선물 잔고 조회 (재확인) ===")
        balanceList = []
        if objBalance.request(balanceList):
            print("\n잔고 재확인 완료")
        else:
            print("\n잔고 재확인 실패")

        # 4. 미체결 조회
        print("\n=== 선물 미체결 조회 ===")
        objNContract = CpFutureNContract()
        nContractList = []
        if objNContract.request(nContractList):
            print("\n미체결 조회 완료")
        else:
            print("\n미체결 조회 실패")

        time.sleep(10)
        count += 1
        print(count)
