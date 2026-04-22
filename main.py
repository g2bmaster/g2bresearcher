import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import io

# 1. 페이지 인터페이스 설정
st.set_page_config(page_title="G2B 마케팅/뉴미디어 공고 큐레이터", layout="wide")

# 2. 보안 설정: Streamlit Secrets로부터 API 키 로드
# GitHub에 올릴 때 키가 유출되지 않도록 st.secrets를 사용합니다.
try:
    # Secrets 관리 메뉴에서 API_KEY = "내_디코딩_키" 형태로 저장하세요.
    MY_API_KEY = st.secrets["API_KEY"]
except Exception:
    st.error("🔑 Streamlit Cloud의 'Secrets' 메뉴에서 'API_KEY'를 먼저 등록해주세요.")
    st.stop()

st.title("🏛️ 나라장터 맞춤형 입찰공고 리스팅")

# 3. 사용자 요청 키워드 구성 (OR 조건)
TARGET_KEYWORDS = [
    "뉴미디어", "온라인 홍보", "SNS", "유튜브", "영상", 
    "홍보 영상", "관광", "브랜딩", "마케팅", "서포터즈", "통합 홍보"
]

st.info(f"🔍 **필터링 조건:** 공고명에 아래 키워드 중 **하나라도 포함**되면 표시합니다.\n\n`{'`, `'.join(TARGET_KEYWORDS)}`")

@st.cache_data(ttl=600)  # 10분간 데이터 캐싱하여 서버 부하 방지
def fetch_g2b_data():
    # 입찰공고목록 정보조회 서비스 (용역) 엔드포인트
    url = "http://apis.data.go.kr/1230000/BidPublicInfoService05/getBidPblancListInfoServc01"
    
    # 날짜 설정: 오늘부터 15일 전까지
    now = datetime.now()
    start_dt = (now - timedelta(days=15)).strftime('%Y%m%d0000')
    end_dt = now.strftime('%Y%m%d2359')

    # 500 에러 방지를 위해 주소를 직접 조립 (라이브러리의 자동 인코딩 간섭 배제)
    full_url = (
        f"{url}?serviceKey={MY_API_KEY}"
        f"&numOfRows=999&pageNo=1&type=json"
        f"&bidNtceDtFrom={start_dt}&bidNtceDtTo={end_dt}"
        f"&inprogrsWbidPblancYn=Y"  # 현재 진행 중인 공고만
    )

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(full_url, headers=headers, timeout=20)
        
        if response.status_code == 200:
            # XML 에러 응답 확인
            if response.text.startswith("<?xml"):
                return None, f"인증 에러: {response.text[:150]}"
            
            data = response.json()
            items = data.get('response', {}).get('body', {}).get('items', [])
            return pd.DataFrame(items) if items else pd.DataFrame(), None
        else:
            return None, f"서버 응답 오류 (HTTP {response.status_code})"
    except Exception as e:
        return None, f"연결 예외 발생: {str(e)}"

# --- 실행 UI ---
if st.button("🚀 공고 리스팅 시작 (최근 15일)"):
    with st.spinner("나라장터 데이터를 분석 중입니다..."):
        df_raw, err = fetch_g2b_data()

    if err:
        st.error(f"❌ {err}")
    elif df_raw is not None:
        if not df_raw.empty:
            # 필요한 컬럼만 추출 및 이름 변경
            cols = {
                'bidNtceNm': '공고명',
                'ntceInsttNm': '공고기관',
                'bidNtceDt': '게시일시',
                'bidClseDt': '마감일시',
                'bidNtceUrl': '공고링크'
            }
            df = df_raw[list(cols.keys())].rename(columns=cols)

            # 키워드 필터링 (OR 조건: 하나라도 포함되면 통과)
            pattern = '|'.join(TARGET_KEYWORDS)
            df_filtered = df[df['공고명'].str.contains(pattern, case=False, na=False, regex=True)].reset_index(drop=True)

            if not df_filtered.empty:
                st.success(f"🎯 총 {len(df_filtered)}건의 맞춤 공고를 찾았습니다.")
                
                # 데이터 출력
                st.dataframe(
                    df_filtered,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "공고링크": st.column_config.LinkColumn("상세보기 🔗", display_text="나라장터 이동")
                    }
                )
                
                # 엑셀 다운로드 기능
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_filtered.to_excel(writer, index=False)
                st.download_button("📥 엑셀로 저장하기", output.getvalue(), "G2B_List.xlsx")
            else:
                st.warning("조회 기간 내 키워드와 일치하는 공고가 없습니다.")
        else:
            st.info("최근 15일간 등록된 새로운 공고 데이터가 없습니다.")
