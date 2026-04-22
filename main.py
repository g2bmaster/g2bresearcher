import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import io

# 1. 페이지 레이아웃 및 제목 설정
st.set_page_config(page_title="G2B 마케팅 공고 큐레이터", layout="wide")

# 2. 보안 설정: Secrets에서 API 키 로드
try:
    # Streamlit Cloud 설정 창(Secrets)에 API_KEY = "내_디코딩_키" 형태로 입력해야 합니다.
    MY_API_KEY = st.secrets["API_KEY"]
except Exception:
    st.error("🔑 Streamlit Secrets에서 'API_KEY'를 먼저 등록해주세요.")
    st.stop()

st.title("🏛️ 나라장터 마케팅/뉴미디어 공고 리스팅")

# 3. 요청하신 11개 핵심 키워드 (하나라도 포함되면 리스팅)
TARGET_KEYWORDS = [
    "뉴미디어", "온라인 홍보", "SNS", "유튜브", "영상", 
    "홍보 영상", "관광", "브랜딩", "마케팅", "서포터즈", "통합 홍보"
]

st.info(f"📋 **모니터링 키워드:** {', '.join(TARGET_KEYWORDS)}")

@st.cache_data(ttl=600) # 10분간 데이터 캐싱
def fetch_g2b_data():
    # 사용자가 제공한 입찰공고정보서비스 엔드포인트 활용
    # 용역 공고 조회를 위한 상세 서비스 경로 부착
    endpoint = "https://apis.data.go.kr/1230000/BidPublicInfoService05/getBidPblancListInfoServc01"
    
    # 날짜 범위 설정: 오늘 기준 15일 전까지
    now = datetime.now()
    start_dt = (now - timedelta(days=15)).strftime('%Y%m%d0000')
    end_dt = now.strftime('%Y%m%d2359')

    # 500 에러 방지 핵심: 모든 파라미터를 문자열로 직접 결합 (자동 인코딩 우회)
    full_url = (
        f"{endpoint}?serviceKey={MY_API_KEY}"
        f"&numOfRows=999&pageNo=1&type=json"
        f"&bidNtceDtFrom={start_dt}&bidNtceDtTo={end_dt}"
        f"&inprogrsWbidPblancYn=Y"
    )

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(full_url, headers=headers, timeout=20)
        
        if response.status_code == 200:
            # 인증키 문제로 XML 에러가 오는지 확인
            if response.text.startswith("<?xml"):
                return None, f"인증 에러 (XML 응답): {response.text[:150]}"
            
            data = response.json()
            items = data.get('response', {}).get('body', {}).get('items', [])
            return pd.DataFrame(items) if items else pd.DataFrame(), None
        else:
            return None, f"서버 오류 (HTTP {response.status_code}): {response.text[:100]}"
    except Exception as e:
        return None, f"시스템 예외: {str(e)}"

# --- 실행 버튼 및 결과 출력 ---
if st.button("🚀 최근 15일 공고 실시간 분석 시작"):
    with st.spinner("나라장터 서버와 통신하며 키워드를 매칭 중입니다..."):
        df_raw, err = fetch_g2b_data()

    if err:
        st.error(f"❌ {err}")
        st.info("💡 계속 에러가 난다면 Secrets의 키를 '인코딩 키'로 교체해 보세요.")
    elif df_raw is not None:
        if not df_raw.empty:
            # 필요한 컬럼 필터링 및 이름 변경
            cols = {
                'bidNtceNm': '공고명',
                'ntceInsttNm': '발주기관',
                'bidNtceDt': '게시일시',
                'bidClseDt': '마감일시',
                'bidNtceUrl': '상세링크'
            }
            df = df_raw[list(cols.keys())].rename(columns=cols)

            # OR 조건 필터링: 키워드 리스트 중 하나라도 공고명에 포함되면 추출
            pattern = '|'.join(TARGET_KEYWORDS)
            df_filtered = df[df['공고명'].str.contains(pattern, case=False, na=False, regex=True)].reset_index(drop=True)

            if not df_filtered.empty:
                st.success(f"🎯 맞춤 공고 {len(df_filtered)}건을 발견했습니다.")
                st.dataframe(
                    df_filtered,
                    use_container_width=True,
                    hide_index=True,
                    column_config={"상세링크": st.column_config.LinkColumn("나라장터 이동 🔗")}
                )
                
                # 엑셀 보고서 다운로드 기능
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_filtered.to_excel(writer, index=False)
                st.download_button("📥 검색결과 엑셀 다운로드", output.getvalue(), "G2B_Curation.xlsx")
            else:
                st.warning("조회 기간 내에 해당 키워드가 포함된 공고가 없습니다.")
        else:
            st.info("현재 나라장터에 등록된 용역 공고가 없습니다.")
