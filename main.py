import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import io

# 1. 페이지 레이아웃 및 환경 설정
st.set_page_config(page_title="G2B 정밀 공고 큐레이터", layout="wide")

# 2. Secrets 보안 연동 (따옴표 필수)
try:
    MY_API_KEY = st.secrets["API_KEY"]
except Exception:
    st.error("🔑 Streamlit Secrets에 'API_KEY'를 먼저 등록해주세요. (예: API_KEY = \"내키\")")
    st.stop()

st.title("🏛️ 나라장터 마케팅/뉴미디어 공고 리스팅")

# 3. 요청하신 11개 핵심 키워드 (OR 조건 필터링)
TARGET_KEYWORDS = [
    "뉴미디어", "온라인 홍보", "SNS", "유튜브", "영상", 
    "홍보 영상", "관광", "브랜딩", "마케팅", "서포터즈", "통합 홍보"
]

@st.cache_data(ttl=600)
def fetch_g2b_advanced():
    # [교정] 이미지 12번에 명시된 '검색조건에 의한 용역조회' 엔드포인트 사용
    base_url = "https://apis.data.go.kr/1230000/BidPublicInfoService05/getBidPblancListInfoServcPPSSrch"
    
    # 오늘 기준 15일 전까지의 범위 설정
    now = datetime.now()
    start_dt = (now - timedelta(days=15)).strftime('%Y%m%d0000')
    end_dt = now.strftime('%Y%m%d2359')

    # 500 에러 방지를 위해 주소를 직접 수동 조립 (가장 확실한 방법)
    full_url = (
        f"{base_url}?serviceKey={MY_API_KEY}"
        f"&numOfRows=999&pageNo=1&type=json"
        f"&bidNtceDtFrom={start_dt}&bidNtceDtTo={end_dt}"
    )

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(full_url, headers=headers, timeout=20)
        
        if response.status_code == 200:
            # XML 에러 응답 확인 (인증키 문제 등)
            if response.text.startswith("<?xml"):
                return None, f"API 키 인증 실패(XML): {response.text[:100]}"
            
            data = response.json()
            items = data.get('response', {}).get('body', {}).get('items', [])
            return pd.DataFrame(items) if items else pd.DataFrame(), None
        else:
            # 서버 응답 오류 발생 시 구체적인 메시지 출력
            return None, f"서버 오류 (HTTP {response.status_code}): {response.text[:100]}"
    except Exception as e:
        return None, f"통신 예외: {str(e)}"

# --- 실행 UI ---
st.info(f"📋 **모니터링 대상:** {', '.join(TARGET_KEYWORDS)}")

if st.button("🚀 상세 검색 API로 15일치 공고 분석"):
    with st.spinner("이미지 12번 상세 기능을 사용하여 수집 중입니다..."):
        df_raw, err = fetch_g2b_advanced()

    if err:
        st.error(f"❌ {err}")
        st.info("💡 계속 500 에러가 나면 Secrets의 키를 '인코딩(Encoding) 키'로 바꿔보세요.")
    elif df_raw is not None:
        if not df_raw.empty:
            # 컬럼 추출 및 정리
            cols = {'bidNtceNm': '공고명', 'ntceInsttNm': '발주기관', 'bidNtceDt': '게시일시', 'bidClseDt': '마감일시', 'bidNtceUrl': '상세링크'}
            df = df_raw[list(cols.keys())].rename(columns=cols)

            # OR 조건 필터링: 키워드 중 하나라도 포함되면 표시
            pattern = '|'.join(TARGET_KEYWORDS)
            df_filtered = df[df['공고명'].str.contains(pattern, case=False, na=False, regex=True)].reset_index(drop=True)

            if not df_filtered.empty:
                st.success(f"🎯 맞춤 공고 {len(df_filtered)}건 발견")
                st.dataframe(df_filtered, use_container_width=True, hide_index=True,
                             column_config={"상세링크": st.column_config.LinkColumn("나라장터 이동 🔗")})
                
                # 엑셀 보고서 생성
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_filtered.to_excel(writer, index=False)
                st.download_button("📥 엑셀 결과 다운로드", output.getvalue(), "G2B_Advanced.xlsx")
            else:
                st.warning("조회 기간 내에 일치하는 키워드의 공고가 없습니다.")
        else:
            st.info("최근 15일간 등록된 입찰 데이터가 없습니다.")
