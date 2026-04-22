import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import io

# 1. 페이지 설정
st.set_page_config(page_title="G2B 마케팅 큐레이터", layout="wide")

# 2. Secrets 보안 설정 확인
# 반드시 Streamlit Cloud Secrets에 API_KEY = "내_디코딩_키"가 입력되어 있어야 합니다.
try:
    MY_API_KEY = st.secrets["API_KEY"]
except KeyError:
    st.error("🔑 Secrets 설정에서 'API_KEY'를 먼저 등록해주세요. (따옴표 포함 필수)")
    st.stop()

st.title("🏛️ 나라장터 마케팅/뉴미디어 공고 큐레이션")

# 3. 타겟 키워드 (OR 조건: 이 중 하나라도 공고명에 있으면 검색)
TARGET_KEYWORDS = [
    "뉴미디어", "홍보", "온라인 홍보", "서포터즈", "서울창업허브", 
    "농촌관광", "관광", "여행", "브랜딩", "SNS", "캠페인", "영상", "마케팅"
]

st.info(f"📋 **현재 감시 키워드:** {', '.join(TARGET_KEYWORDS)}")

@st.cache_data(ttl=600)
def fetch_g2b_data():
    # 사용자가 제공한 새로운 통합 엔드포인트 반영
    # 용역 공고 조회를 위해 엔드포인트 뒤에 구체적인 서비스명 부착
    endpoint = "https://apis.data.go.kr/1230000/BidPublicInfoService05/getBidPblancListInfoServc01"
    
    # 날짜 범위 (최근 7일)
    now = datetime.now()
    start_dt = (now - timedelta(days=7)).strftime('%Y%m%d0000')
    end_dt = now.strftime('%Y%m%d2359')

    # 핵심: 500 에러 방지를 위한 '생(Raw) 주소' 조립 방식
    # requests.get(params=...)을 쓰면 키의 특수문자가 변형되어 500 에러가 날 수 있음
    full_url = (
        f"{endpoint}?serviceKey={MY_API_KEY}"
        f"&numOfRows=999&pageNo=1&type=json"
        f"&bidNtceDtFrom={start_dt}&bidNtceDtTo={end_dt}"
        f"&inprogrsWbidPblancYn=Y"
    )

    try:
        # 브라우저 요청처럼 보이게 헤더 추가 (차단 방지)
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(full_url, headers=headers, timeout=20)
        
        if response.status_code == 200:
            # 정상 응답인데 XML 에러 메시지가 섞여오는 경우 처리
            if response.text.startswith("<?xml"):
                return None, f"인증키 유효성 에러 (XML 응답): {response.text[:150]}"
            
            data = response.json()
            items = data.get('response', {}).get('body', {}).get('items', [])
            return pd.DataFrame(items) if items else pd.DataFrame(), None
        else:
            # 500 에러 시 서버가 뱉는 구체적인 메시지 확인
            return None, f"서버 응답 오류 (HTTP {response.status_code}): {response.text[:150]}"
            
    except Exception as e:
        return None, f"시스템 연결 예외: {str(e)}"

# --- 실행 UI ---
if st.button("🚀 실시간 공고 분석 시작"):
    with st.spinner("전문가 엔진이 나라장터 통신 규격에 맞춰 데이터를 수집 중입니다..."):
        df_raw, err = fetch_g2b_data()

    if err:
        st.error(f"❌ {err}")
        st.info("💡 **최종 해결책:** 디코딩 키로 계속 500이 난다면, Secrets의 값을 '인코딩(Encoding) 키'로 교체해 보세요.")
    elif df_raw is not None:
        if not df_raw.empty:
            # 컬럼 매핑
            cols = {'bidNtceNm': '공고명', 'ntceInsttNm': '공고기관', 'bidNtceDt': '게시일시', 'bidClseDt': '마감일시', 'bidNtceUrl': '공고링크'}
            df = df_raw[list(cols.keys())].rename(columns=cols)

            # 정교한 필터링 (OR 조건: 키워드 중 하나라도 포함되면 표시)
            # 정규식 패턴: "뉴미디어|홍보|관광..."
            pattern = '|'.join(TARGET_KEYWORDS)
            df_filtered = df[df['공고명'].str.contains(pattern, case=False, na=False, regex=True)].reset_index(drop=True)

            if not df_filtered.empty:
                st.success(f"🎯 맞춤 공고 {len(df_filtered)}건을 발견했습니다.")
                st.dataframe(
                    df_filtered,
                    use_container_width=True,
                    hide_index=True,
                    column_config={"공고링크": st.column_config.LinkColumn("상세보기 🔗")}
                )
                
                # 엑셀 보고서 생성
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_filtered.to_excel(writer, index=False)
                st.download_button("📥 검색결과 엑셀 다운로드", output.getvalue(), f"G2B_Result_{datetime.now().strftime('%Y%m%d')}.xlsx")
            else:
                st.warning("분석 결과, 현재 기준 필터링된 공고가 없습니다.")
        else:
            st.info("최근 7일간 나라장터에 등록된 용역 데이터 자체가 없습니다.")
