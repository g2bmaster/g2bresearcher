import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import io

st.set_page_config(page_title="G2B 마케팅 큐레이터", layout="wide")

# --- Streamlit Secrets에서 키 불러오기 ---
# 설정한 이름(API_KEY)과 동일해야 합니다.
try:
    MY_API_KEY = st.secrets["API_KEY"]
except:
    st.error("🔑 Secrets 설정에서 'API_KEY'를 먼저 등록해주세요.")
    st.stop()

st.title("🏛️ 나라장터 마케팅/뉴미디어 공고 리스팅")

TARGET_KEYWORDS = [
    "뉴미디어", "홍보", "온라인 홍보", "서포터즈", "서울창업허브", 
    "농촌관광", "관광", "여행", "브랜딩", "SNS", "캠페인", "영상", "마케팅"
]

def fetch_data():
    # 이미지에서 확인하신 용역조회 API 사용
    url = "http://apis.data.go.kr/1230000/BidPublicInfoService05/getBidPblancListInfoServc01"
    
    end_dt = datetime.now().strftime('%Y%m%d2359')
    start_dt = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d0000')

    # 500 에러 방어: URL 직접 강제 조립
    full_url = (
        f"{url}?serviceKey={MY_API_KEY}"
        f"&numOfRows=999&pageNo=1&type=json"
        f"&bidNtceDtFrom={start_dt}&bidNtceDtTo={end_dt}"
        f"&inprogrsWbidPblancYn=Y"
    )

    try:
        response = requests.get(full_url, timeout=20)
        
        if response.status_code != 200:
            return None, f"서버 오류 (HTTP {response.status_code})"

        if response.text.startswith("<?xml"):
            return None, "인증키 거부 혹은 서버 점검 중입니다. (XML 에러 응답)"

        data = response.json()
        items = data.get('response', {}).get('body', {}).get('items', [])
        return pd.DataFrame(items) if items else pd.DataFrame(), None

    except Exception as e:
        return None, f"연결 실패: {str(e)}"

if st.button("🚀 공고 리스팅 시작"):
    with st.spinner("Secrets 키를 사용하여 데이터를 분석 중입니다..."):
        df_raw, err = fetch_data()

    if err:
        st.error(f"❌ {err}")
    elif df_raw is not None:
        if not df_raw.empty:
            cols = {'bidNtceNm': '공고명', 'ntceInsttNm': '공고기관', 'bidNtceDt': '게시일시', 'bidClseDt': '마감일시', 'bidNtceUrl': '링크'}
            df = df_raw[list(cols.keys())].rename(columns=cols)

            # OR 조건 필터링: 키워드 중 하나라도 포함되면 표시
            pattern = '|'.join(TARGET_KEYWORDS)
            df_filtered = df[df['공고명'].str.contains(pattern, case=False, na=False, regex=True)].reset_index(drop=True)

            if not df_filtered.empty:
                st.success(f"🎯 총 {len(df_filtered)}건의 매칭 공고 발견")
                st.dataframe(df_filtered, use_container_width=True, hide_index=True,
                             column_config={"링크": st.column_config.LinkColumn("상세보기 🔗")})
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_filtered.to_excel(writer, index=False)
                st.download_button("📥 엑셀 저장", output.getvalue(), "G2B_List.xlsx")
            else:
                st.warning("일치하는 키워드의 공고가 없습니다.")
        else:
            st.info("현재 등록된 새 공고가 없습니다.")
