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
    
    # 1) 자사 데이터 (Days_on)
    df_days = pd.read_excel(xls, sheet_name="Days_on")
    num_cols_days = ['주문금액', '홈쇼핑 목표', '이익금', 'PPL 비용', '홈쇼핑 광고비']
    for col in num_cols_days:
        if col in df_days.columns:
            df_days[col] = df_days[col].astype(str).str.replace(',', '').str.replace('-', '0')
            df_days[col] = pd.to_numeric(df_days[col], errors='coerce').fillna(0)
            
    # 2) 시장 전체 데이터 (Home_all)
    df_market = None
    if "Home_all" in xls.sheet_names:
        df_market = pd.read_excel(xls, sheet_name="Home_all")
        # 모든 숫자형 후보 컬럼 전처리
        for col in df_market.columns:
            df_market[col] = df_market[col].astype(str).str.replace(',', '').str.replace('-', '0')
            converted = pd.to_numeric(df_market[col], errors='coerce')
            if converted.notnull().sum() > len(df_market) * 0.3:
                df_market[col] = converted.fillna(0)

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

# 3. 자사 데이터(Days_on) 예측 연산
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
        days_sales_avg = sample_days_sub2['주문금액'].mean() if len(sample_days_sub2) > 0 else 0
        fallback_level = "자사 3순위 (동일 상품 전체)"
        sample_count = len(sample_days_sub2)

# 4. 전체 시장 데이터(Home_all) 연산
market_sales_avg = 0
market_status = "Home_all 데이터 확인 필요"

if df_market is not None:
    # 채널 컬럼 찾기
    ch_col = next((c for c in df_market.columns if any(k in str(c) for k in ['채널', '홈쇼핑', '방송사', '매체'])), None)
    # 금액 컬럼 찾기
    amt_col = next((c for c in df_market.columns if any(k in str(c) for k in ['주문금액', '취급액', '매출', '금액', '실적'])), None)
    # 시간 컬럼 찾기
    time_col = next((c for c in df_market.columns if any(k in str(c) for k in ['시간', '시작', '타임'])), None)

    if ch_col and amt_col:
        # 채널 필터링
        m_filtered = df_market[df_market[ch_col].astype(str).str.contains(str(selected_channel), na=False)]
        
        # 시간대 필터링 시도
        if time_col and len(m_filtered) > 0:
            time_filtered = m_filtered[m_filtered[time_col].astype(str).str.contains(str(selected_time)[:2], na=False)]
            if len(time_filtered) >= 2:
                market_sales_avg = time_filtered[amt_col].mean()
                market_status = f"{selected_channel} {selected_time}시대 전체 평균 ({len(time_filtered)}건)"
            else:
                market_sales_avg = m_filtered[amt_col].mean()
                market_status = f"{selected_channel} 전체 평균 ({len(m_filtered)}건)"
        elif len(m_filtered) > 0:
            market_sales_avg = m_filtered[amt_col].mean()
            market_status = f"{selected_channel} 전체 평균 ({len(m_filtered)}건)"

# 5. 예측치 및 손익/BEP 산출
pred_mid = days_sales_avg
pred_low = pred_mid * 0.85
pred_high = pred_mid * 1.15

margin_rate = 1.0 - commission_rate - cogs_rate
bep_sales = (fixed_ad_cost + ppl_cost) / margin_rate if margin_rate > 0 else 0
est_profit = (pred_mid * margin_rate) - fixed_ad_cost - ppl_cost

# 6. 결과 출력 대시보드
st.subheader("📈 실적 & 시장 통합 시뮬레이션 결과")
st.caption(f"자사 분석 기준: **{fallback_level}** (표본 {sample_count}건)")

c1, c2, c3, c4 = st.columns(4)
c1.metric("예상 주문액 (기준 100%)", f"{int(pred_mid):,} 원")
c2.metric("예상 주문액 범위", f"{int(pred_low):,} ~ {int(pred_high):,} 원")
c3.metric("손익분기점 (BEP)", f"{int(bep_sales):,} 원")
c4.metric("예상 영업손익", f"{int(est_profit):,} 원", delta=f"{int(est_profit):,} 원")

# 7. 시장 벤치마크 (Home_all) 상시 표시 영역
st.markdown("---")
st.subheader("🌐 홈쇼핑 시장 전체 벤치마크 (Home_all 비교)")

if market_sales_avg > 0:
    mc1, mc2, mc3 = st.columns(3)
    diff_val = pred_mid - market_sales_avg
    diff_pct = (diff_val / market_sales_avg) * 100
    
    mc1.metric("시장 평균 주문액", f"{int(market_sales_avg):,} 원", help=market_status)
    mc2.metric("시장 평균 대비 자사 예상", f"{diff_pct:+.1f}%", delta=f"{int(diff_val):,} 원")
    mc3.metric("데이터 참조 기준", market_status)
else:
    st.info(f"ℹ️ Home_all 시트에서 '{selected_channel}' 채널에 매칭되는 시장 데이터를 검색 중입니다. (시트 내 채널명/매출 컬럼 확인 필요)")

st.markdown("---")

# 리스크 판정
if pred_mid < bep_sales:
    st.error(f"🚨 **[손실 위험 경고]** 예상 주문액({int(pred_mid):,}원)이 BEP({int(bep_sales):,}원) 미만입니다. 예상 결손: 약 {abs(int(est_profit)):,}원")
else:
    st.success(f"🎉 **[수익 달성 예상]** BEP 초과 달성 가능. 예상 영업이익: 약 {int(est_profit):,}원")

# 과거 유사 데이터
with st.expander("🔍 자사 과거 실적 데이터 (Days_on) 확인"):
    ref_df = sample_days if len(sample_days) >= 2 else (sample_days_sub if len(sample_days_sub) >= 2 else sample_days_sub2)
    disp_cols = [c for c in ['일자', '상품명', '홈쇼핑 채널', '시작시간', '주문금액', '달성율', '이익금', 'PPL PGM'] if c in ref_df.columns]
    st.dataframe(ref_df[disp_cols])
