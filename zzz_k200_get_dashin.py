import win32com.client
import time
import datetime


def print_ohlcv_last_n_days(target_code="U201", days_to_fetch=60):  # 함수 이름을 좀 더 일반적으로 변경
    """
    대신증권 CybosPlus API를 사용하여 특정 지수/종목의 최근 N일치
    시고종저거래량(OHLCV) 데이터를 가져와 출력합니다.

    :param target_code: 조회할 지수/종목 코드 (기본값: "U201" - KOSPI 200)
    :param days_to_fetch: 조회할 최근 일수 (기본값: 60)
    """
    try:
        # 1. CybosPlus 연결 상태 확인
        cpCybos = win32com.client.Dispatch("CpUtil.CpCybos")
        if cpCybos.IsConnect == 0:
            print("CybosPlus가 연결되어 있지 않습니다. 프로그램을 종료합니다.")
            return

        # 2. StockChart 객체 생성
        instStockChart = win32com.client.Dispatch("CpSysDib.StockChart")

        # 3. 입력값 설정
        instStockChart.SetInputValue(0, target_code)  # 조회할 종목/지수 코드
        instStockChart.SetInputValue(1, ord('2'))  # 요청 구분: '2' - 개수로 요청
        instStockChart.SetInputValue(2, 0)  # 요청종료일: 0 (Default - 최근거래날짜 기준)
        instStockChart.SetInputValue(4, days_to_fetch)  # 요청 개수

        requested_field_codes = [0, 2, 3, 4, 5, 8]
        instStockChart.SetInputValue(5, requested_field_codes)

        instStockChart.SetInputValue(6, ord('D'))
        instStockChart.SetInputValue(9, ord('1'))

        # 4. 데이터 요청
        instStockChart.BlockRequest()

        # 5. 요청 결과 수신 상태 확인
        rqStatus = instStockChart.GetDibStatus()
        rqMsg = instStockChart.GetDibMsg1()

        if rqStatus != 0:
            print(f"데이터 요청 실패 (요청 코드: {target_code}): status={rqStatus}, msg='{rqMsg}'")
            return

        # 6. 수신된 데이터의 실제 종목 코드와 개수 확인
        retrieved_code_from_header = instStockChart.GetHeaderValue(0)  # API가 실제로 응답한 종목 코드
        count = instStockChart.GetHeaderValue(3)

        # CpUtil.CpStockCode를 사용하여 코드에 해당하는 이름 가져오기
        cpStockCode = win32com.client.Dispatch("CpUtil.CpStockCode")
        retrieved_name = cpStockCode.CodeToName(retrieved_code_from_header)

        print(f"--- API 응답 데이터 정보 ---")
        print(f"요청한 코드: {target_code}")
        print(f"수신된 코드: {retrieved_code_from_header} (이름: {retrieved_name})")
        print(f"수신된 데이터 개수: {count}")
        print("---------------------------")

        if count == 0:
            print(f"수신된 데이터가 없습니다.")
            return

        print(f"--- {retrieved_name} ({retrieved_code_from_header}) 최근 {count}일 데이터 (가장 최근 데이터부터 표시) ---")
        header = f"{'날짜':<10} {'시가':>10} {'고가':>10} {'저가':>10} {'종가':>10} {'거래량':>15}"
        print(header)
        print("-" * len(header))

        # 7. 수신된 데이터 출력
        for i in range(count):
            date = instStockChart.GetDataValue(0, i)
            open_price = instStockChart.GetDataValue(1, i)
            high_price = instStockChart.GetDataValue(2, i)
            low_price = instStockChart.GetDataValue(3, i)
            close_price = instStockChart.GetDataValue(4, i)
            volume = instStockChart.GetDataValue(5, i)

            print(
                f"{date:<10} {open_price:>10.2f} {high_price:>10.2f} {low_price:>10.2f} {close_price:>10.2f} {int(volume):>15,}")

    except Exception as e:
        print(f"오류 발생: {e}")


if __name__ == '__main__':
    # KOSPI 200 데이터 요청
    print(">>> KOSPI 200 (U201) 조회 시작")
    print_ohlcv_last_n_days(target_code="U201", days_to_fetch=60)
    print("\n")  # 구분선

    # 만약 코스닥 종합 지수를 보고 싶으시다면:
    # print(">>> KOSDAQ 종합 (U301) 조회 시작")
    # print_ohlcv_last_n_days(target_code="U301", days_to_fetch=60)