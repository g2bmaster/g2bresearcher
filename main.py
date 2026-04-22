import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import io

# 1. 페이지 설정
st.set_page_config(page_title="나라장터 정밀 알리미", layout="wide")

# --- [수정] 본인의 'Decoding' 인증키를 입력하세요 ---
MY_API_KEY = "61203561a5f6b1757e496997889aa776c9484657a36d4aaea2de18b25192393b"
# --------------------------------------------------

st.title("🏛️ 나라장터 홍보·마케팅 용역 정밀 검색")

# 타겟 키워드 설정
target_keywords = [
    "뉴미디어", "홍보", "온라인 홍보", "서포터즈", "서울창업허브", 
    "농촌관광", "관광", "여행", "브랜딩", "SNS", "캠페인", "영상", "마케팅"
]

st.info(f"🔍 **분석 키워드:** {', '.join(target_keywords)}")

@st.cache_data(ttl=1800) # 30분 캐싱
def get_g2b_data():
    # 이미지의 API 목록 중 가장 표준적인 '입찰공고목록 정보에 대한 용역조회' 사용
    endpoint = "http://apis.data.go.kr/1230000/BidPublicInfoService05/getBidPblancListInfoServc01"
    
    now = datetime.now()
    # 500 에러 방지를 위해 날짜 형식을 정확히 YYYYMMDDHHMM으로 맞춤
    start_dt = (now - timedelta(days=7)).strftime('%Y%m%d0000')
    end_dt = now.strftime('%Y%m%d2359')
    
    # 500 에러 방지 핵심: 파라미터를 URL에 직접 결합
    full_url = (
        f"{endpoint}?serviceKey={MY_API_KEY}"
        f"&numOfRows=900&pageNo=1&type=json"
        f"&bidNtceDtFrom={start_dt}&bidNtceDtTo={end_dt}"
        f"&inprogrsWbidPblancYn=Y"
    )

    try:
        response = requests.get(full_url, timeout=20)
        if response.status_code == 200:
            res_data = response.json()
            items = res_data.get('response', {}).get('body', {}).get('items', [])
            return pd.DataFrame(items) if items else pd.DataFrame()
        else:
            return f"Error: {response.status_code}"
    except Exception as e:
        return f"Fail: {str(e)}"

# 실행 버튼
if st.button('🚀 최신 데이터 정밀 분석 시작'):
    with st.spinner('나라장터 시스템에서 데이터를 수집하고 키워드를 매칭 중입니다...'):
        df_raw = get_g2b_data()

    if isinstance(df_raw, pd.DataFrame):
        if not df_raw.empty:
            # 1. 컬럼 정리 및 이름 변경
            cols = {
                'bidNtceNm': '공고명',
                'ntceInsttNm': '발주기관',
                'demandInsttNm': '수요기관',
                'bidNtceDt': '공고일시',
                'bidClseDt': '마감일시',
                'bidNtceUrl': '공고링크'
            }
            df = df_raw[list(cols.keys())].rename(columns=cols)

            # 2. 정교한 필터링 (공고명에 키워드 포함 여부 확인)
            # 공백 제거 및 대소문자 무시로 검색 정확도 향상
            pattern = '|'.join(target_keywords)
            df_filtered = df[df['공고명'].str.contains(pattern, case=False, na=False)].reset_index(drop=True)

            if not df_filtered.empty:
                st.success(f"✅ 조건에 맞는 공고 {len(df_filtered)}건을 찾았습니다.")
                
                # 표 디자인 및 링크 처리
                st.dataframe(
                    df_filtered,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "공고링크": st.column_config.LinkColumn("상세보기 🔗", display_text="나라장터 열기")
                    }
                )

                # 엑셀 다운로드
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_filtered.to_excel(writer, index=False, sheet_name='Search_Result')
                st.download_button("📥 검색결과 엑셀로 저장", output.getvalue(), "G2B_Result.xlsx")
            else:
                st.warning("분석 결과, 해당 키워드가 포함된 공고가 검색되지 않았습니다.")
        else:
            st.info("최근 7일간 등록된 용역 공고가 없습니다.")
    else:
        st.error(f"❌ {df_raw}")
        st.info("인증키 발급 직후라면 2~3시간 후에 다시 시도해보세요.")
