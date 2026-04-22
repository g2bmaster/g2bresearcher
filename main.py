import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import io

st.set_page_config(page_title="나라장터 맞춤 알리미", layout="wide")

# --- [수정] 공공데이터포털의 'Decoding' 키를 넣으세요 ---
MY_API_KEY = "61203561a5f6b1757e496997889aa776c9484657a36d4aaea2de18b25192393b"
# --------------------------------------------------

st.title("📢 나라장터 입찰공고 맞춤 리스트")

# 요청하신 키워드들
target_keywords = ["뉴미디어", "홍보", "온라인 홍보", "서포터즈", "서울창업허브", "농촌관광", "관광", "여행", "브랜딩", "SNS", "캠페인", "영상"]

@st.cache_data(ttl=3600)
def fetch_data():
    # 1. 날짜 설정 (최근 7일)
    now = datetime.now()
    start_dt = (now - timedelta(days=7)).strftime('%Y%m%d0000')
    end_dt = now.strftime('%Y%m%d2359')
    
    # 2. 500 에러 방지의 핵심: URL 직접 조립
    # requests가 키를 멋대로 인코딩하지 못하게 f-string으로 주소를 만듭니다.
    base_url = "http://apis.data.go.kr/1230000/BidPublicInfoService05/getBidPblancListInfoServc01"
    full_url = (
        f"{base_url}?serviceKey={MY_API_KEY}"
        f"&numOfRows=999&pageNo=1&type=json"
        f"&bidNtceDtFrom={start_dt}&bidNtceDtTo={end_dt}"
        f"&inprogrsWbidPblancYn=Y"
    )

    try:
        # params 인자를 쓰지 않고 주소를 통째로 넘깁니다.
        response = requests.get(full_url, timeout=20)
        
        if response.status_code == 200:
            try:
                data = response.json()
                items = data.get('response', {}).get('body', {}).get('items', [])
                return pd.DataFrame(items) if items else pd.DataFrame()
            except:
                # 서버에서 XML 에러 메시지를 보낸 경우 (키 오류 등)
                return f"서버 응답 오류 내용: {response.text[:150]}"
        else:
            return f"HTTP 에러 발생: {response.status_code}"
            
    except Exception as e:
        return f"접속 실패: {str(e)}"

if st.button('🚀 최신 공고 리스팅 시작'):
    with st.spinner('데이터를 수집 중입니다...'):
        result = fetch_data()

    if isinstance(result, pd.DataFrame):
        if not result.empty:
            cols = {'bidNtceNm': '공고명', 'ntceInsttNm': '공고기관', 'bidNtceDt': '게시일시', 'bidClseDt': '마감일시', 'bidNtceUrl': '링크'}
            df = result[list(cols.keys())].rename(columns=cols)
            
            pattern = '|'.join(target_keywords)
            df_filtered = df[df['공고명'].str.contains(pattern, case=False, na=False)].reset_index(drop=True)

            if not df_filtered.empty:
                st.success(f"✅ {len(df_filtered)}건의 맞춤 공고 발견")
                st.dataframe(df_filtered, use_container_width=True, hide_index=True,
                             column_config={"링크": st.column_config.LinkColumn("링크", display_text="상세보기 🔗")})
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_filtered.to_excel(writer, index=False)
                st.download_button("📥 엑셀 다운로드", output.getvalue(), "나라장터_리스트.xlsx")
            else:
                st.warning("키워드와 일치하는 공고가 없습니다.")
        else:
            st.info("조회된 공고가 없습니다.")
    else:
        st.error(f"❌ {result}")
        st.info("팁: 계속 오류가 나면 'Encoding 키'로도 한 번 바꿔서 테스트해 보세요.")
