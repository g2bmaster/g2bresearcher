import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import io

st.set_page_config(page_title="나라장터 맞춤 알리미", layout="wide")

# --- 설정 구간 ---
# 1. 공공데이터포털에서 발급받은 인증키를 아래 따옴표 안에 직접 넣으세요.
API_KEY = "61203561a5f6b1757e496997889aa776c9484657a36d4aaea2de18b25192393ble.c"

# 2. 필터링할 키워드 목록
target_keywords = [
    "뉴미디어", "홍보", "온라인 홍보", "서포터즈", "서울창업허브", 
    "농촌관광", "관광", "여행", "브랜딩", "SNS", "캠페인", "영상"
]
# ----------------

st.title("📢 나라장터 입찰공고 맞춤 리스트")
st.info(f"🔍 검색 키워드: {', '.join(target_keywords)}")

@st.cache_data(ttl=3600)
def fetch_service_bids():
    url = "http://apis.data.go.kr/1230000/BidPublicInfoService05/getBidPblancListInfoServc01"
    
    now = datetime.now()
    start_date = (now - timedelta(days=7)).strftime('%Y%m%d0000')
    end_date = now.strftime('%Y%m%d2359')
    
    params = {
        'serviceKey': API_KEY,
        'type': 'json',
        'numOfRows': '500',
        'pageNo': '1',
        'inprogrsWbidPblancYn': 'Y', 
        'bidNtceDtFrom': start_date,
        'bidNtceDtTo': end_date
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            items = data.get('response', {}).get('body', {}).get('items', [])
            return pd.DataFrame(items) if items else pd.DataFrame()
        else:
            return response.status_code
    except Exception as e:
        return str(e)

if st.button('최신 공고 불러오기 (최근 1주일)'):
    with st.spinner('나라장터 데이터를 분석 중입니다...'):
        result = fetch_service_bids()

    if isinstance(result, pd.DataFrame):
        if not result.empty:
            cols = {
                'bidNtceNm': '공고명',
                'ntceInsttNm': '공고기관',
                'bidNtceDt': '게시일시',
                'bidClseDt': '마감일시',
                'bidNtceUrl': '링크'
            }
            df = result[cols.keys()].rename(columns=cols)

            # 키워드 필터링
            pattern = '|'.join(target_keywords)
            df_filtered = df[df['공고명'].str.contains(pattern, case=False, na=False)].reset_index(drop=True)

            if not df_filtered.empty:
                st.success(f"총 {len(df_filtered)}건의 맞춤 공고를 발견했습니다.")
                st.dataframe(df_filtered, use_container_width=True, hide_index=True,
                             column_config={"링크": st.column_config.LinkColumn("링크", display_text="바로가기🔗")})
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_filtered.to_excel(writer, index=False)
                st.download_button("📥 결과 엑셀 다운로드", output.getvalue(), "G2B_List.xlsx")
            else:
                st.warning("최근 1주일 내에 해당 키워드가 포함된 공고가 없습니다.")
        else:
            st.info("해당 기간 내 등록된 공고가 없습니다.")
    else:
        st.error(f"❌ 접속 오류 (코드: {result}). API 키가 정확한지 확인해 주세요.")
