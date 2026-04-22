import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import io

# 1. 페이지 레이아웃 설정
st.set_page_config(page_title="G2B 마케팅 공고 분석기", layout="wide")

# 2. 보안 설정: Secrets에서 디코딩 키 로드
try:
    # Secrets에 API_KEY = "내_디코딩_키" 형태로 저장 (따옴표 필수)
    MY_API_KEY = st.secrets["API_KEY"]
except Exception:
    st.error("🔑 Streamlit Secrets에서 'API_KEY'를 먼저 설정해주세요.")
    st.stop()

st.title("🏛️ 나라장터 마케팅/뉴미디어 공고 큐레이션")

# 3. 요청하신 11개 핵심 키워드
TARGET_KEYWORDS = [
    "뉴미디어", "온라인 홍보", "SNS", "유튜브", "영상", 
    "홍보 영상", "관광", "브랜딩", "마케팅", "서포터즈", "통합 홍보"
]

@st.cache_data(ttl=600)
def fetch_g2b_data():
    # 가이드 12번: 나라장터검색조건에 의한 입찰공고용역조회
    endpoint = "https://apis.data.go.kr/1230000/BidPublicInfoService05/getBidPblancListInfoServcPPSSrch"
    
    # 기술문서 규격: 오늘부터 15일 전까지 (YYYYMMDDHHMM 형식)
    now = datetime.now()
    start_dt = (now - timedelta(days=15)).strftime('%Y%m%d0000')
    end_dt = now.strftime('%Y%m%d2359')

    # 500 에러 방지: 파이썬 라이브러리의 자동 인코딩을 피하기 위한 URL 수동 조립
    full_url = (
        f"{endpoint}?serviceKey={MY_API_KEY}"
        f"&numOfRows=999&pageNo=1&type=json"
        f"&bidNtceDtFrom={start_dt}&bidNtceDtTo={end_dt}"
    )

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(full_url, headers=headers, timeout=20)
        
        if response.status_code == 200:
            # 에러 코드 확인 (문서상 00이 아닌 경우 에러)
            if response.text.startswith("<?xml"):
                return None, f"API 인증/설정 오류: {response.text[:150]}"
            
            data = response.json()
            header = data.get('response', {}).get('header', {})
            result_code = header.get('resultCode')
            
            # 데이터 없음(03)은 에러가 아닌 정상 케이스로 처리
            if result_code == '03':
                return pd.DataFrame(), None
            elif result_code != '00':
                return None, f"API 에러 ({result_code}): {header.get('resultMsg')}"

            items = data.get('response', {}).get('body', {}).get('items', [])
            return pd.DataFrame(items) if items else pd.DataFrame(), None
        else:
            return None, f"서버 응답 실패 (HTTP {response.status_code})"
    except Exception as e:
        return None, f"시스템 오류: {str(e)}"

# --- 실행 UI ---
st.info(f"📋 **모니터링 키워드:** {', '.join(TARGET_KEYWORDS)}")

if st.button("🚀 최근 15일 공고 실시간 분석 시작"):
    with st.spinner("기술문서 규격에 따라 데이터를 정밀 분석 중입니다..."):
        df_raw, err = fetch_g2b_data()

    if err:
        st.error(f"❌ {err}")
    elif df_raw is not None:
        if not df_raw.empty:
            # 필요한 컬럼 매핑
            cols = {
                'bidNtceNm': '공고명',
                'ntceInsttNm': '공고기관',
                'bidNtceDt': '게시일시',
                'bidClseDt': '마감일시',
                'bidNtceUrl': '상세링크'
            }
            df = df_raw[list(cols.keys())].rename(columns=cols)

            # OR 조건 필터링: 하나라도 포함되면 표시
            pattern = '|'.join(TARGET_KEYWORDS)
            df_filtered = df[df['공고명'].str.contains(pattern, case=False, na=False, regex=True)].reset_index(drop=True)

            if not df_filtered.empty:
                st.success(f"🎯 맞춤 공고 {len(df_filtered)}건 발견")
                st.dataframe(
                    df_filtered,
                    use_container_width=True,
                    hide_index=True,
                    column_config={"상세링크": st.column_config.LinkColumn("나라장터 이동 🔗")}
                )
                
                # 엑셀 다운로드
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_filtered.to_excel(writer, index=False)
                st.download_button("📥 검색결과 엑셀 저장", output.getvalue(), "G2B_Analysis.xlsx")
            else:
                st.warning("분석 결과, 현재 기준 필터링된 공고가 없습니다.")
        else:
            st.info("최근 15일간 등록된 입찰 데이터가 없습니다.")
