import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import io

# 1. 페이지 인터페이스 설정
st.set_page_config(page_title="G2B 마케팅 큐레이터", layout="wide")

# 2. Secret 설정 (사용자가 입력한 "API_KEY" 사용)
try:
    # Secrets에 API_KEY = "내_디코딩_키" 형태로 저장되어 있어야 함
    MY_API_KEY = st.secrets["API_KEY"]
except Exception:
    st.error("🔑 Streamlit Cloud의 'Secrets' 메뉴에서 API_KEY를 먼저 설정해주세요.")
    st.stop()

st.title("🏛️ 나라장터 마케팅/뉴미디어 공고 리스팅")

# 3. 타겟 키워드 (OR 조건: 하나라도 있으면 검색)
TARGET_KEYWORDS = [
    "뉴미디어", "홍보", "온라인 홍보", "서포터즈", "서울창업허브", 
    "농촌관광", "관광", "여행", "브랜딩", "SNS", "캠페인", "영상", "마케팅"
]

@st.cache_data(ttl=600)
def fetch_data_final():
    # 이미지에서 확인된 '용역입찰공고조회' 엔드포인트
    endpoint = "http://apis.data.go.kr/1230000/BidPublicInfoService05/getBidPblancListInfoServc01"
    
    # 날짜 범위 설정
    now = datetime.now()
    start_dt = (now - timedelta(days=7)).strftime('%Y%m%d0000')
    end_dt = now.strftime('%Y%m%d2359')

    # 핵심: 500 에러 방지를 위해 주소를 완전히 '수동 조립'
    # requests.get(url, params=params) 방식을 쓰면 500 에러가 날 수 있음
    full_url = (
        f"{endpoint}?serviceKey={MY_API_KEY}"
        f"&numOfRows=900&pageNo=1&type=json"
        f"&bidNtceDtFrom={start_dt}&bidNtceDtTo={end_dt}"
        f"&inprogrsWbidPblancYn=Y"
    )

    try:
        # 브라우저인 것처럼 헤더 추가 (차단 방지)
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(full_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            # 서버가 XML로 에러를 뱉었는지 확인
            if response.text.startswith("<?xml"):
                return None, f"인증 에러: {response.text[:100]}"
            
            data = response.json()
            items = data.get('response', {}).get('body', {}).get('items', [])
            return pd.DataFrame(items) if items else pd.DataFrame(), None
        else:
            return None, f"서버 응답 실패 (HTTP {response.status_code})"
    except Exception as e:
        return None, f"통신 오류: {str(e)}"

# --- 실행 UI ---
st.info(f"📋 **모니터링 키워드:** {', '.join(TARGET_KEYWORDS)}")

if st.button("🚀 최신 공고 리스팅 시작"):
    with st.spinner("데이터를 정밀 분석 중입니다..."):
        df_raw, err = fetch_data_final()

    if err:
        st.error(f"❌ {err}")
        st.info("💡 계속 500이 뜨면 Secrets의 키를 '인코딩 키'로 바꿔서 저장해 보세요.")
    elif df_raw is not None:
        if not df_raw.empty:
            # 컬럼 정리
            df = df_raw[['bidNtceNm', 'ntceInsttNm', 'bidNtceDt', 'bidNtceUrl']].copy()
            df.columns = ['공고명', '공고기관', '게시일시', '링크']

            # OR 조건 검색 (키워드 중 하나라도 포함되면 표시)
            pattern = '|'.join(TARGET_KEYWORDS)
            df_filtered = df[df['공고명'].str.contains(pattern, case=False, na=False)].reset_index(drop=True)

            if not df_filtered.empty:
                st.success(f"✅ 총 {len(df_filtered)}건의 맞춤 공고 발견")
                st.dataframe(df_filtered, use_container_width=True, hide_index=True,
                             column_config={"링크": st.column_config.LinkColumn("상세보기")})
                
                # 엑셀 보고서 추출
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_filtered.to_excel(writer, index=False)
                st.download_button("📥 검색결과 엑셀 다운로드", output.getvalue(), "G2B_Result.xlsx")
            else:
                st.warning("키워드와 매칭되는 공고가 없습니다.")
        else:
            st.info("현재 등록된 새로운 용역 공고가 없습니다.")
