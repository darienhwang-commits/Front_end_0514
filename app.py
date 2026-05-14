import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Streamlit Cloud는 .env를 읽지 않으므로 st.secrets → os.environ 으로 주입
if "KOSIS_API_KEY" in st.secrets:
    os.environ["KOSIS_API_KEY"] = st.secrets["KOSIS_API_KEY"]

from data_fetcher import get_leading_indicator

st.set_page_config(
    page_title="한국 경기선행지수 (나침반)",
    page_icon="🧭",
    layout="wide",
)

# ── 제목 ──────────────────────────────────────────────────────────────────────
st.title("🧭 한국 경기선행지수 나침반")
st.caption("출처: 한국은행 ECOS · 경기종합지수 — 선행지수 순환변동치 (통계코드 901Y067)")

st.divider()

# ── 데이터 로드 ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=3_600)
def load_data() -> pd.DataFrame:
    return get_leading_indicator()


with st.spinner("데이터를 불러오는 중..."):
    try:
        df = load_data()
    except Exception as exc:
        st.error(f"데이터를 불러오지 못했습니다: {exc}")
        st.stop()

# ── 최신 3개월 metric ────────────────────────────────────────────────────────
def fmt_date(yyyymm: str) -> str:
    return f"{yyyymm[:4]}년 {int(yyyymm[4:])}월"


recent = df.iloc[-3:]   # 최신 3개월 (오래된 순)

_, c1, c2, c3, _ = st.columns([0.5, 1, 1, 1, 0.5])
for col, i in zip([c1, c2, c3], range(3)):
    row_idx  = -3 + i          # -3, -2, -1
    val      = float(df["value"].iloc[row_idx])
    prev_val = float(df["value"].iloc[row_idx - 1])
    delta    = round(val - prev_val, 1)
    date     = df.index[row_idx]
    is_latest = (i == 2)
    with col:
        st.metric(
            label=f"{'📌 ' if is_latest else ''}{fmt_date(date)}",
            value=f"{val:.1f}",
            delta=f"{delta:+.1f}  전월 대비",
        )

st.divider()

# ── 3년 데이터 슬라이싱 ───────────────────────────────────────────────────────
cutoff = (pd.Timestamp.now() - pd.DateOffset(years=3)).strftime("%Y%m")
df_3y = df[df.index >= cutoff].copy()
df_3y["date_dt"] = pd.to_datetime(df_3y.index, format="%Y%m")

# ── Plotly 꺾은선 그래프 ──────────────────────────────────────────────────────
fig = go.Figure()

# 기준선(100) ─ fill="tonexty" 의 기준이 됨
fig.add_trace(go.Scatter(
    x=df_3y["date_dt"],
    y=[100.0] * len(df_3y),
    mode="lines",
    line=dict(color="rgba(120,120,120,0.35)", width=1.2, dash="dash"),
    name="기준(100)",
    hoverinfo="skip",
))

# 순환변동치 라인 + 기준선과의 면 채우기
fig.add_trace(go.Scatter(
    x=df_3y["date_dt"],
    y=df_3y["value"],
    mode="lines+markers",
    fill="tonexty",
    fillcolor="rgba(31,119,180,0.12)",
    line=dict(color="#1f77b4", width=2.5),
    marker=dict(size=5, color="#1f77b4"),
    name="선행지수 순환변동치",
    hovertemplate="%{x|%Y년 %m월} &nbsp;·&nbsp; <b>%{y:.1f}</b><extra></extra>",
))

fig.update_layout(
    title=dict(
        text="경기선행지수 순환변동치 (최근 3년)",
        font=dict(size=17),
        x=0.0,
    ),
    xaxis=dict(
        showgrid=True,
        gridcolor="#efefef",
        tickformat="%Y.%m",
        tickangle=-30,
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor="#efefef",
        title="지수 (2020=100)",
        tickformat=".1f",
    ),
    hovermode="x unified",
    plot_bgcolor="white",
    paper_bgcolor="white",
    margin=dict(l=60, r=40, t=60, b=50),
    legend=dict(orientation="h", y=-0.18, x=0),
    font=dict(size=13),
)

st.plotly_chart(fig, use_container_width=True)

# ── 설명 ──────────────────────────────────────────────────────────────────────
st.info(
    "💡 **참고:** 이 지표는 향후 3~6개월 뒤의 경기와 코스피 방향을 미리 보여줍니다. "
    "100을 기준으로 상승 중이면 경기 확장 신호, 하락 중이면 경기 둔화 신호로 해석합니다."
)
