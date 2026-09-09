import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="홈쇼핑 실적 & 시장 분석 시뮬레이터", layout="wide")
st.title("📊 데이즈온 홈쇼핑 실적 & 시장 벤치마크 시뮬레이터")

# 1. 엑셀 데이터 로드 (Days_on & Home_all)
@st.cache_data
def load_all_data():
    file_path = "HOME_DATA.xlsx"
    xls = pd.ExcelFile(file_path)
    
    # 자사 실적 로드
    df_days = pd.read_excel(xls, sheet_name="Days_on")
    num_cols_days = ['주문금액', '홈쇼핑 목표', '이익금', 'PPL 비용', '홈쇼핑 광고비']
    for col in num_cols_days:
        if col in df_days.columns:
            df_days[col] = df_days[col].astype(str).str.replace(',', '').str.replace('-', '0')
            df_days[col] = pd.to_numeric(df_days[col], errors='coerce').fillna(0)
            
    # 전체 시장 데이터 로드 (Home_all이 있는 경우)
    df_market = None
    if "Home_all" in xls.sheet_names:
        df_market = pd.read_excel(xls, sheet_name="Home_all")
        for col in df_market.columns:
            if '주문' in col or '매출' in col or '금액' in col:
                df_market[col] = df_market[col].astype(str).str.replace(',', '').str.replace('-', '0')
                df_market[col] = pd.to_numeric(df_market[col], errors='coerce').fillna(0)

    return df_days, df_market

try:
    df_days, df_market = load_all_data()
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()

# 2. 사이드바 편성 조건 입력
st.sidebar.header("🎯 편성 조건 설정")

items = sorted(df_days['상품명'].dropna().unique().tolist())
selected_item = st.sidebar.selectbox("상품 선택", items)

channels = sorted(df_days[df_days['상품명'] == selected_item]['홈쇼핑 채널'].dropna().unique().tolist())
selected_channel = st.sidebar.selectbox("홈쇼핑 채널", channels)

times = sorted(df_days['시간'].dropna().unique().tolist())
selected_time = st.sidebar.selectbox("방송 시간대", times)

st.sidebar.markdown("---")
st.sidebar.subheader("💰 비용 및 마진 구조")
ppl_options = ["미진행", "진행"]
selected_ppl = st.sidebar.radio("PPL 집행 여부", ppl_options)
ppl_cost = 0
if selected_ppl == "진행":
    ppl_cost = st.sidebar.number_input("PPL 비용 (원)", value=20000000, step=5000000)

fixed_ad_cost = st.sidebar.number_input("홈쇼핑 정액 광고비 (원)", value=0, step=5000000)
commission_rate = st.sidebar.slider("홈쇼핑 수수료율 (%)", min_value=10.0, max_value=60.0, value=45.0, step=0.5) / 100.0
cogs_rate = st.sidebar.slider("원가율 (%)", min_value=10.0, max_value=50.0, value=25.0, step=1.0) / 100.0

# 3. 데이터 연산 (Days_on 자사 + Home_all 시장 벤치마크)
# 자사 데이터 필터링
sample_days = df_days[(df_days['상품명'] == selected_item) & (df_days['홈쇼핑 채널'] == selected_channel) & (df_days['시간'] == selected_time)]

if len(sample_days) >= 2:
    days_sales_avg = sample_days['주문금액'].mean()
    fallback_level = "자사 1순위 (동일 상품 + 채널 + 시간대)"
    sample_count = len(sample_days)
else:
    sample_days_sub = df_days[(df_days['상품명'] == selected_item) & (df_days['홈쇼핑 채널'] == selected_channel)]
    if len(sample_days_sub) >= 2:
        days_sales_avg = sample_days_sub['주문금액'].mean()
        fallback_level = "자사 2순위 (동일 상품 + 채널 전체)"
        sample_count = len(sample_days_sub)
    else:
        sample_days_sub2 = df_days[df_days['상품명'] == selected_item]
        days_sales_avg = sample_days_sub2['주문금액'].mean()
        fallback_level = "자사 3순위 (동일 상품 전체)"
        sample_count = len(sample_days_sub2)

# 시장 전체(Home_all) 벤치마크 산출
market_sales_avg = 0
market_info = "Home_all 참조 데이터 없음"

if df_market is not None:
    # 홈쇼핑 채널 및 시간 매칭 컬럼 검색
    m_ch_col = next((c for c in df_market.columns if '채널' in c or '홈쇼핑' in c or '홈사' in c), None)
    m_time_col = next((c for c in df_market.columns if '시간' in c), None)
    m_amt_col = next((c for c in df_market.columns if '주문' in c or '매출' in c or '금액' in c), None)
    
    if m_ch_col and m_amt_col:
        cond = (df_market[m_ch_col].astype(str) == str(selected_channel))
        if m_time_col:
            cond_time = cond & (df_market[m_time_col].astype(str).str.contains(str(selected_time)[:2], na=False))
            m_filtered = df_market[cond_time]
            if len(m_filtered) >= 3:
                market_sales_avg = m_filtered[m_amt_col].mean()
                market_info = f"{selected_channel} {selected_time}대 전체 평균 ({len(m_filtered)}건)"
            else:
                m_filtered = df_market[cond]
                market_sales_avg = m_filtered[m_amt_col].mean() if len(m_filtered) > 0 else 0
                market_info = f"{selected_channel} 전체 평균 ({len(m_filtered)}건)"
        else:
            m_filtered = df_market[cond]
            market_sales_avg = m_filtered[m_amt_col].mean() if len(m_filtered) > 0 else 0
            market_info = f"{selected_channel} 전체 평균 ({len(m_filtered)}건)"

# 통합 예측치 산출 (시장 지표와 자사 실적 결합 가중치 적용)
if market_sales_avg > 0 and sample_count < 2:
    # 자사 표본이 적을 땐 시장 평균 데이터 40% 반영
    pred_base = (days_sales_avg * 0.6) + (market_sales_avg * 0.4)
    model_note = f"자사 표본 부족으로 시장 벤치마크({market_info}) 40% 가중 반영"
else:
    # 자사 표본이 충분할 땐 자사 위주 반영
    pred_base = days_sales_avg
    model_note = f"자사 데이터 기반 모델 ({fallback_level})"

# 4. 손익/BEP 산출
margin_rate = 1.0 - commission_rate - cogs_rate
bep_sales = (fixed_ad_cost + ppl_cost) / margin_rate if margin_rate > 0 else 0

pred_low = pred_base * 0.85
pred_mid = pred_base * 1.0
pred_high = pred_base * 1.15
est_profit = (pred_mid * margin_rate) - fixed_ad_cost - ppl_cost

# 5. 결과 대시보드 렌더링
st.subheader("📈 실적 & 시장 통합 시뮬레이션 결과")
st.caption(f"분석 기준: **{model_note}** (자사 표본 {sample_count}건)")

c1, c2, c3, c4 = st.columns(4)
c1.metric("예상 주문액 (기준 100%)", f"{int(pred_mid):,} 원")
c2.metric("예상 주문액 범위", f"{int(pred_low):,} ~ {int(pred_high):,} 원")
c3.metric("손익분기점 (BEP)", f"{int(bep_sales):,} 원")
c4.metric("예상 영업손익", f"{int(est_profit):,} 원", delta=f"{int(est_profit):,} 원")

# 시장 벤치마크 대비 성과 지표
if market_sales_avg > 0:
    st.markdown("---")
    mc1, mc2 = st.columns(2)
    diff_rate = ((pred_mid - market_sales_avg) / market_sales_avg) * 100
    mc1.metric("해당 채널/시간대 시장 평균 매출 (Home_all)", f"{int(market_sales_avg):,} 원")
    mc2.metric("시장 평균 대비 자사 예상치", f"{diff_rate:+.1f}%", delta=f"{int(pred_mid - market_sales_avg):,} 원")

st.markdown("---")

if pred_mid < bep_sales:
    st.error(f"🚨 **[손실 위험 경고]** 예상 주문액({int(pred_mid):,}원)이 BEP({int(bep_sales):,}원) 미만입니다. 결손 예상액 약 **{abs(int(est_profit)):,}원**.")
else:
    st.success(f"🎉 **[수익 달성 예상]** BEP 초과 달성 가능. 예상 영업이익 약 **{int(est_profit):,}원**.")

# 상세 과거 데이터
with st.expander("🔍 자사 과거 실적 데이터 (Days_on) 확인"):
    ref_df = sample_days if len(sample_days) >= 2 else (sample_days_sub if len(sample_days_sub) >= 2 else sample_days_sub2)
    disp_cols = [c for c in ['일자', '상품명', '홈쇼핑 채널', '시작시간', '주문금액', '달성율', '이익금', 'PPL PGM'] if c in ref_df.columns]
    st.dataframe(ref_df[disp_cols])
