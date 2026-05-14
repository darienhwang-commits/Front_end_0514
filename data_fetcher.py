import os
from datetime import datetime

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

ECOS_BASE_URL = "https://ecos.bok.or.kr/api"
STAT_CODE = "901Y067"        # 경기종합지수
TARGET_ITEM_CODE = "I16E"    # 선행지수순환변동치


def _check_result(data: dict, service: str) -> dict:
    # 오류 응답은 최상위에 "RESULT" 키로 반환됨
    if "RESULT" in data:
        r = data["RESULT"]
        raise RuntimeError(f"ECOS API 오류 [{r.get('CODE', '')}]: {r.get('MESSAGE', '')}")
    service_data = data.get(service)
    if service_data is None:
        raise RuntimeError(f"ECOS API 응답에 '{service}' 키가 없습니다: {data}")
    return service_data


def get_leading_indicator(
    start_period: str = "200001",
    end_period: str | None = None,
) -> pd.DataFrame:
    """ECOS에서 '선행지수 순환변동치'를 가져와 DataFrame으로 반환합니다.

    Args:
        start_period: 조회 시작 기간 (YYYYMM, 기본값 '200001')
        end_period:   조회 종료 기간 (YYYYMM, 기본값 현재 월)

    Returns:
        index: date (YYYYMM str), columns: value (float)
    """
    api_key = os.getenv("KOSIS_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "KOSIS_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요."
        )

    if end_period is None:
        end_period = datetime.now().strftime("%Y%m")

    url = (
        f"{ECOS_BASE_URL}/StatisticSearch"
        f"/{api_key}/json/kr/1/10000"
        f"/{STAT_CODE}/M/{start_period}/{end_period}"
    )

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    data = response.json()
    service_data = _check_result(data, "StatisticSearch")

    rows = service_data.get("row", [])
    if not rows:
        raise ValueError(f"데이터가 없습니다. 기간 {start_period}~{end_period}을 확인하세요.")

    filtered = [r for r in rows if r.get("ITEM_CODE1") == TARGET_ITEM_CODE]

    if not filtered:
        all_items = {r.get("ITEM_CODE1"): r.get("ITEM_NAME1") for r in rows}
        raise ValueError(
            f"ITEM_CODE1='{TARGET_ITEM_CODE}' 항목을 찾을 수 없습니다.\n"
            f"사용 가능한 항목: {all_items}"
        )

    df = pd.DataFrame(filtered)[["TIME", "DATA_VALUE"]].copy()
    df.columns = ["date", "value"]
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"])
    df = df.set_index("date").sort_index()
    df.index.name = "date"

    return df


# 하위 호환성 alias
get_kosis_leading_indicator = get_leading_indicator


if __name__ == "__main__":
    df = get_leading_indicator()
    print(f"rows  : {len(df)}")
    print(f"period: {df.index[0]} ~ {df.index[-1]}")
    print(df.tail(10))
