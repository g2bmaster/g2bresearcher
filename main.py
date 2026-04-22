import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import io

# 1. 페이지 레이아웃 및 환경 설정
st.set_page_config(page_title="G2B 공고 큐레이터 정밀판", layout="wide")

# 2. Secrets 보안 연동
try:
    # Secrets에 API_KEY = "내_디코딩_키" 형태로 따옴표와 함께 저장해야 함
    MY_API_KEY = st.secrets["API_KEY"]
except Exception:
    st.error("🔑 Streamlit Secrets에서 'API_KEY'를 먼저 등록해주세요.")
    st.stop()

st.title("🏛️ 나라장터 마케팅/뉴미디어 공고 리스팅")

# 3. 요청하신 11개 핵심 키워드 (OR 조건: 하나라도 포함 시 리스팅)
TARGET_KEYWORDS = [
   "용역"
]

@st.cache_data(ttl=600)
def fetch_g2b_data():
    # [교정] 엔드포인트 주소: 루트 주소 뒤에 반드시 '상세 서비스명'이 붙어야 합니다.
    # 이미지에서 확인된 '용역입찰공고조회' 기능을 직접 연결합니다.
    base_url = "https://apis.data.go.kr/1230000/BidPublicInfoService05/getBidPblancListInfoServc01"
    
    # 날짜 범위 설정: 오늘 기준 15일 전까지 (사용자 요청 반영)
    now = datetime.now()
    start_dt = (now - timedelta(days=15)).strftime('%Y%m%d0000')
    end_dt = now.strftime('%Y%m%d2359')

    # 핵심: 500 에러 방어용 'Raw URL' 수동 조립
    # 딕셔너리(params) 형태를 사용하면 requests 라이브러리가 키를 멋대로 인코딩하여 500을 유발함
    full_url = (
        f"{base_url}?serviceKey={MY_API_KEY}"
        f"&numOfRows=999&pageNo=1&type=json"
        f"&bidNtceDtFrom={start_dt}&bidNtceDtTo={end_dt}"
        f"&inprogrsWbidPblancYn=Y"
    )

    try:
        # 차단 방지를 위한 브라우저 위장 헤더
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(full_url, headers=headers, timeout=20)
        
        if response.status_code == 200:
            # 정상 응답이나 XML 에러가 온 경우 처리
            if response.text.startswith("<?xml"):
                return None, f"인증키 오류(XML): {response.text[:150]}"
            
            data = response.json()
            items = data.get('response', {}).get('body', {}).get('items', [])
            return pd.DataFrame(items) if items else pd.DataFrame(), None
        else:
            # 500 에러 시 서버의 원인 메시지 출력
            return None, f"서버 응답 오류 (HTTP {response.status_code}): {response.text[:100]}"
    except Exception as e:
        return None, f"연결 예외: {str(e)}"

# --- 실행 UI 및 필터링 로직 ---
st.info(f"📋 **현재 필터링 키워드:** {', '.join(TARGET_KEYWORDS)}")

if st.button("🚀 최근 15일 공고 분석 시작"):
    with st.spinner("수정된 엔드포인트로 나라장터 서버에 접속 중입니다..."):
        df_raw, err = fetch_g2b_data()

    if err:
        st.error(f"❌ {err}")
        st.info("💡 **최종 체크:** 계속 500 에러가 나면 Secrets의 키를 '인코딩(Encoding) 키'로 교체해 저장해 보세요.")
    elif df_raw is not None:
        if not df_raw.empty:
            # 필요한 컬럼 추출
            cols = {
                'bidNtceNm': '공고명',
                'ntceInsttNm': '발주기관',
                'bidNtceDt': '게시일시',
                'bidClseDt': '마감일시',
                'bidNtceUrl': '상세링크'
            }
            df = df_raw[list(cols.keys())].rename(columns=cols)

            # OR 조건 필터링 (키워드 중 하나라도 포함되면 표시)
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
                st.download_button("📥 검색결과 엑셀 다운로드", output.getvalue(), "G2B_Result.xlsx")
            else:
                st.warning("조회 기간 내에 키워드가 포함된 공고가 없습니다.")
        else:
            st.info("최근 15일간 등록된 데이터가 없습니다.")
