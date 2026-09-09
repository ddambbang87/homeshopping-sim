import streamlit as st
import pandas as pd

st.set_page_config(page_title="홈쇼핑 실적 시뮬레이터", layout="wide")
st.title("📊 홈쇼핑 방송 실적 & 손익 예측 시뮬레이터")

# 1. 엑셀 파일(.xlsx)의 Days_on 시트 불러오기
@st.cache_data
def load_data():
    file_path = "HOME_DATA.xlsx"
    # Days_on 시트 지정해서 읽기
    df = pd.read_excel(file_path, sheet_name="Days_on")
    
    # 숫자 컬럼 내 쉼표(,) 및 특수문자 제거 후 수치형 변환
    num_cols = ['주문금액', '홈쇼핑 목표', '이익금', 'PPL 비용', '홈쇼핑 광고비']
    for col in num_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '').str.replace('-', '0')
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"HOME_DATA.xlsx 파일을 불러올 수 없습니다. 오류: {e}")
    st.stop()

# 2. 사이드바 - 편성 및 조건 입력
st.sidebar.header("🎯 편성 조건 설정")

items = sorted(df['상품명'].dropna().unique().tolist())
selected_item = st.sidebar.selectbox("상품 선택", items)

channels = sorted(df[df['상품명'] == selected_item]['홈쇼핑 채널'].dropna().unique().tolist())
selected_channel = st.sidebar.selectbox("홈쇼핑 채널", channels)

# 방송 시간대
times = sorted(df['시간'].dropna().unique().tolist())
selected_time = st.sidebar.selectbox("방송 시간대", times)

# PPL 및 비용 조건
st.sidebar.markdown("---")
st.sidebar.subheader("💰 비용 및 수수료 조건")
ppl_options = ["미진행", "진행"]
selected_ppl = st.sidebar.radio("PPL 집행 여부", ppl_options)
ppl_cost = 0
if selected_ppl == "진행":
    ppl_cost = st.sidebar.number_input("PPL 비용 (원)", value=20000000, step=5000000)

fixed_ad_cost = st.sidebar.number_input("홈쇼핑 정액 광고비 (원)", value=0, step=5000000)
commission_rate = st.sidebar.slider("홈쇼핑 수수료율 (%)", min_value=10.0, max_value=60.0, value=45.0, step=0.5) / 100.0
cogs_rate = st.sidebar.slider("원가율 (%)", min_value=10.0, max_value=50.0, value=25.0, step=1.0) / 100.0

# 3. 다단계 Fallback 예측 연산
sample_1 = df[(df['상품명'] == selected_item) & (df['홈쇼핑 채널'] == selected_channel) & (df['시간'] == selected_time)]

if len(sample_1) >= 2:
    pred_base = sample_1['주문금액'].mean()
    fallback_desc = "1순위 (상품 + 채널 + 시간대 일치)"
    sample_count = len(sample_1)
else:
    sample_2 = df[(df['상품명'] == selected_item) & (df['홈쇼핑 채널'] == selected_channel)]
    if len(sample_2) >= 2:
        pred_base = sample_2['주문금액'].mean()
        fallback_desc = "2순위 (상품 + 채널 일치)"
        sample_count = len(sample_2)
    else:
        sample_3 = df[df['상품명'] == selected_item]
        pred_base = sample_3['주문금액'].mean()
        fallback_desc = "3순위 (상품 전체 평균)"
        sample_count = len(sample_3)

# 4. 손익 및 BEP 연산
margin_rate = 1.0 - commission_rate - cogs_rate
bep_sales = (fixed_ad_cost + ppl_cost) / margin_rate if margin_rate > 0 else 0

pred_low = pred_base * 0.85
pred_mid = pred_base * 1.0
pred_high = pred_base * 1.15

est_profit = (pred_mid * margin_rate) - fixed_ad_cost - ppl_cost

# 5. 결과 출력 대시보드
st.subheader("📈 실적 시뮬레이션 예측 결과")
st.caption(f"적용 기준: **{fallback_desc}** (유사 표본 데이터 {sample_count}건 분석)")

col1, col2, col3, col4 = st.columns(4)
col1.metric("예상 주문액 (기준 100%)", f"{int(pred_mid):,} 원")
col2.metric("예상 주문액 범위 (보수 ~ 공격)", f"{int(pred_low):,} ~ {int(pred_high):,} 원")
col3.metric("손익분기점 (BEP)", f"{int(bep_sales):,} 원")
col4.metric("예상 영업손익", f"{int(est_profit):,} 원", delta=f"{int(est_profit):,} 원")

st.markdown("---")

# 리스크 및 판정 메시지
if pred_mid < bep_sales:
    st.error(f"🚨 **[손실 위험]** 예상 주문액({int(pred_mid):,}원)이 BEP({int(bep_sales):,}원)에 미치지 못해 약 **{abs(int(est_profit)):,}원**의 결손이 예상됩니다.")
else:
    st.success(f"🎉 **[수익 달성]** BEP를 초과하여 약 **{int(est_profit):,}원**의 안정적인 영업이익 달성이 가능할 것으로 예측됩니다.")

# 과거 유사 데이터 테이블 표시
with st.expander("🔍 분석에 사용된 과거 유사 방송 실적 보기"):
    ref_df = sample_1 if len(sample_1) >= 2 else (sample_2 if len(sample_2) >= 2 else sample_3)
    display_cols = [col for col in ['일자', '상품명', '홈쇼핑 채널', '시작시간', '주문금액', '달성율', '이익금', 'PPL PGM'] if col in ref_df.columns]
    st.dataframe(ref_df[display_cols])
