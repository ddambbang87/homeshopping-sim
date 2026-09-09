import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="홈쇼핑 시장 벤치마크 시뮬레이터", layout="wide")
st.title("🌐 홈쇼핑 시장 전체 실적(Home_all) 기반 손익 시뮬레이터")

# 1. Home_all 엑셀 데이터 로드
@st.cache_data
def load_home_all_data():
    file_path = "HOME_DATA.xlsx"
    xls = pd.ExcelFile(file_path)
    
    # Home_all 시트 읽기
    sheet_target = "Home_all" if "Home_all" in xls.sheet_names else xls.sheet_names[0]
    df = pd.read_excel(xls, sheet_name=sheet_target)
    
    # 주요 컬럼 탐색 및 표준화
    ch_col = next((c for c in df.columns if any(k in str(c) for k in ['채널', '홈쇼핑', '방송사', '홈사'])), None)
    amt_col = next((c for c in df.columns if any(k in str(c) for k in ['주문금액', '취급액', '매출', '금액', '실적'])), None)
    time_col = next((c for c in df.columns if any(k in str(c) for k in ['시간대', '시작시간', '시간', '타임'])), None)
    item_col = next((c for c in df.columns if any(k in str(c) for k in ['상품', '품목', '아이템', '카테고리'])), None)

    # 컬럼 표준 이름 부여
    rename_dict = {}
    if ch_col: rename_dict[ch_col] = '채널'
    if amt_col: rename_dict[amt_col] = '주문금액'
    if time_col: rename_dict[time_col] = '시간대'
    if item_col: rename_dict[item_col] = '상품'
    df = df.rename(columns=rename_dict)

    # 주문금액 숫자형 정제
    if '주문금액' in df.columns:
        df['주문금액'] = df['주문금액'].astype(str).str.replace(',', '').str.replace('-', '0')
        df['주문금액'] = pd.to_numeric(df['주문금액'], errors='coerce').fillna(0)

    # 시간대 정제 (예: "06:15" -> "06시", 숫자 6 -> "06시")
    if '시간대' in df.columns:
        def clean_time(x):
            val = str(x).strip()
            if ':' in val:
                return f"{int(val.split(':')[0]):02d}시"
            try:
                return f"{int(float(val)):02d}시"
            except:
                return val
        df['시간대_표준'] = df['시간대'].apply(clean_time)
    else:
        df['시간대_표준'] = "전체"

    return df

try:
    df_market = load_home_all_data()
except Exception as e:
    st.error(f"Home_all 데이터를 읽어오지 못했습니다: {e}")
    st.stop()

# 2. 사이드바 - 편성 및 시뮬레이션 변수 입력
st.sidebar.header("🎯 시장 편성 조건 설정")

# 채널 목록 추출
channels = sorted([str(c) for c in df_market['채널'].dropna().unique().tolist() if str(c) != '0'])
selected_channel = st.sidebar.selectbox("홈쇼핑 채널 선택", channels)

# 해당 채널의 시간대 목록
available_times = sorted([str(t) for t in df_market[df_market['채널'] == selected_channel]['시간대_표준'].dropna().unique().tolist() if str(t) != 'nan'])
if not available_times:
    available_times = sorted(df_market['시간대_표준'].dropna().unique().tolist())
selected_time = st.sidebar.selectbox("방송 시간대 선택", available_times)

# 목표 침투율(자사 목표 가중치)
st.sidebar.markdown("---")
st.sidebar.subheader("📊 목표 달성 가중치")
market_share_ratio = st.sidebar.slider("시장 평균 대비 자사 목표 수준 (%)", min_value=50, max_value=200, value=100, step=5) / 100.0

# 비용 조건
st.sidebar.markdown("---")
st.sidebar.subheader("💰 원가 및 비용 조건")
ppl_options = ["미진행", "진행"]
selected_ppl = st.sidebar.radio("PPL 집행 여부", ppl_options)
ppl_cost = 0
if selected_ppl == "진행":
    ppl_cost = st.sidebar.number_input("PPL 비용 (원)", value=20000000, step=5000000)

fixed_ad_cost = st.sidebar.number_input("홈쇼핑 정액 광고비 (원)", value=0, step=5000000)
commission_rate = st.sidebar.slider("홈쇼핑 수수료율 (%)", min_value=10.0, max_value=60.0, value=40.0, step=0.5) / 100.0
cogs_rate = st.sidebar.slider("원가율 (%)", min_value=10.0, max_value=50.0, value=25.0, step=1.0) / 100.0

# 3. 시장 평균 매출 연산 (Fallback)
sample_exact = df_market[(df_market['채널'] == selected_channel) & (df_market['시간대_표준'] == selected_time)]

if len(sample_exact) >= 3:
    market_sales = sample_exact['주문금액'].mean()
    sample_count = len(sample_exact)
    ref_desc = f"{selected_channel} {selected_time} 방송 실적 평균"
else:
    sample_ch = df_market[df_market['채널'] == selected_channel]
    market_sales = sample_ch['주문금액'].mean() if len(sample_ch) > 0 else df_market['주문금액'].mean()
    sample_count = len(sample_ch)
    ref_desc = f"{selected_channel} 채널 전체 방송 실적 평균 (시간대 표본 부족)"

# 4. 예상 주문액 및 손익 / BEP 연산
pred_sales = market_sales * market_share_ratio
pred_low = pred_sales * 0.85
pred_high = pred_sales * 1.15

margin_rate = 1.0 - commission_rate - cogs_rate
bep_sales = (fixed_ad_cost + ppl_cost) / margin_rate if margin_rate > 0 else 0
est_profit = (pred_sales * margin_rate) - fixed_ad_cost - ppl_cost

# 손익분기 달성을 위해 필요한 시장 대비 달성비율
required_market_ratio = (bep_sales / market_sales * 100) if market_sales > 0 else 0

# 5. 결과 대시보드 출력
st.subheader("📈 시뮬레이션 결과")
st.caption(f"기준 시장 모수: **{ref_desc}** (총 {sample_count:,}건의 시장 데이터 분석)")

c1, c2, c3, c4 = st.columns(4)
c1.metric("시장 평균 매출액 (Home_all)", f"{int(market_sales):,} 원")
c2.metric("자사 예상 주문액", f"{int(pred_sales):,} 원", f"범위: {int(pred_low):,} ~ {int(pred_high):,}")
c3.metric("손익분기점 (BEP)", f"{int(bep_sales):,} 원")
c4.metric("예상 영업손익", f"{int(est_profit):,} 원", delta=f"{int(est_profit):,} 원")

st.markdown("---")

# 6. BEP 침투율 진단 및 리스크 브리핑
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("🎯 손익분기점(BEP) 달성 허들 진단")
    st.write(f"- 해당 시간대 시장 평균 매출: **{int(market_sales):,} 원**")
    st.write(f"- 고정비(광고비+PPL) 회수 필요 BEP: **{int(bep_sales):,} 원**")
    st.write(f"- **필요 시장 달성률: 시장 평균 대비 {required_market_ratio:.1f}% 이상 달성 필요**")
    
    if required_market_ratio > 120:
        st.warning(f"⚠️ **[위험]** BEP를 넘기려면 시장 평균의 **{required_market_ratio:.1f}%**를 팔아야 합니다. 고정 광고비나 PPL 비용 절감이 필수적입니다.")
    elif required_market_ratio > 100:
        st.info(f"ℹ️ **[도전적]** 시장 평균({required_market_ratio:.1f}%)을 약간 상회해야 본전을 넘깁니다. 공격적인 프로모션이 필요합니다.")
    else:
        st.success(f"✅ **[안정권]** 시장 평균의 **{required_market_ratio:.1f}%**만 달성해도 BEP를 넘기며 안정적인 이익 구간에 진입합니다.")

with col_right:
    st.subheader("📋 편성 시뮬레이션 코멘트")
    if est_profit > 0:
        st.success(f"현재 설정된 조건(마진율 {margin_rate*100:.1f}%)에서 방송 시 약 **{int(est_profit):,}원**의 영업이익이 기대됩니다.")
    else:
        st.error(f"현재 조건에서는 약 **{abs(int(est_profit)):,}원**의 결손이 예상됩니다. PPL 비용을 줄이거나 정률 수수료 조건을 협상하세요.")

# 7. 참조된 시장 데이터 미리보기
with st.expander(f"🔍 {selected_channel} 시장 데이터 샘플 확인하기"):
    show_df = sample_exact if len(sample_exact) >= 3 else sample_ch
    display_cols = [c for c in ['채널', '시간대_표준', '상품', '주문금액'] if c in show_df.columns]
    st.dataframe(show_df[display_cols].head(30))
