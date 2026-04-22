import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import io

# 1. 페이지 설정
st.set_page_config(page_title="G2B 마케팅 큐레이터", layout="wide")

# --- [필독] 이 부분에 발급받으신 '디코딩' 키를 정확히 입력하세요 ---
MY_API_KEY = "61203561a5f6b1757e496997889aa776c9484657a36d4aaea2de18b25192393b"
# -----------------------------------------------------------

st.title("🏛️ 나라장터 마케팅/뉴미디어 공고 리스팅")

# 타겟 키워드 (이 중 하나라도 공고명에 있으면 추출)
TARGET_KEYWORDS = [
    "뉴미디어", "홍보", "온라인 홍보", "서포터즈", "서울창업허브", 
    "농촌관광", "관광", "여행", "브랜딩", "SNS", "캠페인", "영상", "마케팅"
]

st.info(f"🔍 **필터링 규칙:** 아래 키워드 중 **하나라도 포함된** 공고를 리스팅합니다.\n\n`{'`, `'.join(TARGET_KEYWORDS)}`")

@st.cache_data(ttl=600)
def fetch_data():
    # 500 에러를 피하기 위한 가장 안정적인 엔드포인트 (용역입찰공고조회)
    url = "http://apis.data.go.kr/1230000/BidPublicInfoService05/getBidPblancListInfoServc01"
    
    # 날짜: 최근 7일간의 공고
    end_dt = datetime.now().strftime('%Y%m%d2359')
    start_dt = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d0000')

    # 500 에러 방어의 핵심: URL 직접 강제 조립
    # 파이썬이 키를 변형하지 못하도록 f-string으로 묶어버립니다.
    full_url = (
        f"{url}?serviceKey={MY_API_KEY}"
        f"&numOfRows=999&pageNo=1&type=json"
        f"&bidNtceDtFrom={start_dt}&bidNtceDtTo={end_dt}"
        f"&inprogrsWbidPblancYn=Y"
    )

    try:
        response = requests.get(full_url, timeout=20)
        
        # HTTP 에러 시 상세 내용 출력
        if response.status_code != 200:
            return None, f"서버 응답 오류 (HTTP {response.status_code})"

        # 응답이 XML인 경우 (보통 인증키 에러 시 XML로 옵니다)
        if response.text.startswith("<?xml"):
            if "SERVICE_KEY_IS_NOT_REGISTERED" in response.text:
                return None, "인증키가 등록되지 않았습니다. (승인 대기 중이거나 오타)"
            return None, f"API 점검 또는 키 에러 발생\n(내용: {response.text[:100]})"

        # 정상 JSON 파싱
        data = response.json()
        items = data.get('response', {}).get('body', {}).get('items', [])
        return pd.DataFrame(items) if items else pd.DataFrame(), None

    except Exception as e:
        return None, f"연결 실패: {str(e)}"

# 실행 UI
if st.button("🚀 공고 리스팅 시작"):
    if "여기에" in MY_API_KEY:
        st.warning("⚠️ 코드 상단의 `MY_API_KEY`에 실제 인증키를 입력해주세요.")
    else:
        with st.spinner("나라장터 서버에서 실시간 데이터를 분석 중입니다..."):
            df_raw, err = fetch_data()

        if err:
            st.error(f"❌ {err}")
        elif df_raw is not None:
            if not df_raw.empty:
                # 1. 컬럼 매핑 및 정리
                cols = {
                    'bidNtceNm': '공고명',
                    'ntceInsttNm': '공고기관',
                    'bidNtceDt': '게시일시',
                    'bidClseDt': '마감일시',
                    'bidNtceUrl': '링크'
                }
                df = df_raw[list(cols.keys())].rename(columns=cols)

                # 2. OR 조건 필터링 (하나의 키워드라도 포함되면 OK)
                # 정규식 패턴 생성: "키워드1|키워드2|키워드3"
                pattern = '|'.join(TARGET_KEYWORDS)
                df_filtered = df[df['공고명'].str.contains(pattern, case=False, na=False, regex=True)].reset_index(drop=True)

                if not df_filtered.empty:
                    st.success(f"🎯 총 {len(df_filtered)}건의 매칭 공고를 찾았습니다.")
                    st.dataframe(
                        df_filtered,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "링크": st.column_config.LinkColumn("상세보기 🔗", display_text="나라장터 이동")
                        }
                    )

                    # 엑셀 다운로드
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df_filtered.to_excel(writer, index=False)
                    st.download_button("📥 엑셀 다운로드", output.getvalue(), "G2B_List.xlsx")
                else:
                    st.warning("조회된 데이터 중 키워드와 일치하는 공고가 없습니다.")
            else:
                st.info("현재 나라장터에 등록된 새 공고가 없습니다.")
