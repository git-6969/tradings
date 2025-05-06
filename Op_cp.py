import win32com.client

def get_option_info(option_code):
    """
    대신증권 API를 사용하여 옵션 정보를 조회합니다 (CpSysDib.OptionMst 사용).

    Args:
        option_code (str): 옵션 코드

    Returns:
        dict: 옵션 정보 또는 None (조회 실패 시)
    """
    try:
        # CybosPlus 연결
        inst_option_mst = win32com.client.Dispatch("CpSysDib.OptionMst")

        # 옵션 코드 설정
        inst_option_mst.SetInputValue(1, option_code)

        # 정보 요청
        inst_option_mst.BlockRequest()

        # 에러 처리
        rq_status = inst_option_mst.GetDibStatus()
        rq_ret = inst_option_mst.GetDibMsg1()
        print("통신상태", rq_status, rq_ret)
        if rq_status != 0:
            return None

        # 정보 추출
        option_info = {
            "현재가": inst_option_mst.GetHeaderValue(11),
            "전일대비": inst_option_mst.GetHeaderValue(12),
            "전일대비부호": inst_option_mst.GetHeaderValue(13),
            "거래량": inst_option_mst.GetHeaderValue(18),
            "미결제약정": inst_option_mst.GetHeaderValue(20),
            "이론가": inst_option_mst.GetHeaderValue(41),
            "내재가치": inst_option_mst.GetHeaderValue(42),
            "시간가치": inst_option_mst.GetHeaderValue(43),
            "델타": inst_option_mst.GetHeaderValue(44),
            "감마": inst_option_mst.GetHeaderValue(45),
            "쎄타": inst_option_mst.GetHeaderValue(46),
            "베가": inst_option_mst.GetHeaderValue(47),
            "로": inst_option_mst.GetHeaderValue(48),
        }
        return option_info

    except Exception as e:
        print(f"오류 발생: {e}")
        return None

if __name__ == "__main__":
    option_code = "209DM350"  # 예시 옵션 코드 (실제 옵션 코드로 변경 필요)
    info = get_option_info(option_code)

    if info:
        for key, value in info.items():
            print(f"{key}: {value}")
    else:
        print(f"옵션 {option_code}의 정보 조회에 실패했습니다.")