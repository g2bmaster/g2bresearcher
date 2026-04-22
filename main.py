import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import io

st.set_page_config(
    page_title="홍보·마케팅 용역 공고 알리미", 
    page_icon="📢",
    layout="wide"
)

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 검색 필터링")
    target_keywords = [
        "SNS", "뉴미디어", "온라인홍보", "캠페인", "신뢰 제고", 
        "홍보", "마케팅", "브랜딩", "브랜드", "관광", 
        "유튜브", "영상", "서포터즈"
    ]
    
    selected_category = st.multiselect(
        "관심 키워드 선택",
        options=target_keywords,
        default=target_keywords
    )
    
    days_to_look = st.slider("조회 기간 (최근 며칠?)", 1, 7, 7)

st.title("📢 뉴미디어·홍보 마케팅 입찰공고")

# API 키 설정 (Streamlit Cloud Secrets 필수)
API_KEY = st.secrets.get("61203561a5f6b1757e496997889aa776c9484657a36d4aaea2de18b25192393b", "인증키_미등록")

@st.cache_data(ttl=3600)
def fetch_service_bids(days):
    if API_KEY == "인증키_미등록":
        return None
        
    url = "http://apis.data.go.kr/1230000/BidPublicInfoService05/getBidPblancListInfoServc01"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    params = {
        'serviceKey': API_KEY,
        'type': 'json',
        'numOfRows': '999',
        'pageNo': '1',
        'bidNtceDtFrom': start_date.strftime('%Y%m%d%H%M'),
        'bidNtceDtTo': end_date.strftime('%Y%m%d%H%M')
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            items = data.get('response', {}).get('body', {}).get('items', [])
            return pd.DataFrame(items) if items else pd.DataFrame()
        else:
            return "API_ERROR"
    except:
        return "CONN_ERROR"

if API_KEY == "인증키_미등록":
    st.error("⚠️ Streamlit Cloud의 Settings > Secrets에 G2B_API_KEY를 등록해주세요.")
else:
    with st.spinner('실시간 공고 데이터를 불러오는 중...'):
        df_raw = fetch_service_bids(days_to_look)

    if isinstance(df_raw, pd.DataFrame) and not df_raw.empty:
        cols = {
            'bidNtceNm': '공고명',
            'ntceInsttNm': '공고기관',
            'demandInsttNm': '수요기관',
            'bidNtceDt': '게시일시',
            'bidClseDt': '마감일시',
            'bidNtceUrl': '공고링크'
        }
        df = df_raw[cols.keys()].rename(columns=cols)

        if selected_category:
            pattern = '|'.join(selected_category)
            df_filtered = df[df['공고명'].str.contains(pattern, case=False, na=False)].reset_index(drop=True)
        else:
            df_filtered = pd.DataFrame()

        if not df_filtered.empty:
            st.success(f"총 {len(df_filtered)}건의 맞춤 공고를 발견했습니다.")
            st.dataframe(
                df_filtered, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "공고링크": st.column_config.LinkColumn("공고링크", display_text="상세보기 🔗")
                }
            )

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_filtered.to_excel(writer, index=False, sheet_name='Bid_List')
            
            st.download_button(
                label="📥 엑셀 다운로드",
                data=output.getvalue(),
                file_name=f"G2B_PR_Bids_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("일치하는 공고가 없습니다.")
    elif df_raw == "API_ERROR" or df_raw == "CONN_ERROR":
        st.error("❌ API 서버 통신 실패")
    else:
        st.info("해당 기간 내 등록된 공고가 없습니다.")
