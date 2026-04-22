import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import io

# 1. 페이지 설정
st.set_page_config(page_title="G2B 공고 정밀 분석기", layout="wide")

# 2. Secrets에서 안전하게 키 로드
try:
    # TOML 형식: API_KEY = "내_디코딩_키" 가 설정되어 있어야 함
    MY_API_KEY = st.secrets["API_KEY"]
except KeyError:
    st.error("🔑 Streamlit Cloud의 'Secrets' 설정에서 'API_KEY'를 먼저 등록해주세요.")
    st.stop()

st.title("🏛️ 나라장터 마케팅/뉴미디어 공고 큐레이터")

# 3. 타겟 키워드 (OR 조건: 하나라도 포함되면 검색)
TARGET_KEYWORDS = [
    "뉴미디어", "홍보", "온라인 홍보", "서포터즈", "서울창업허브", "외국인"
    "농촌관광", "관광", "여행", "브랜딩", "SNS", "캠페인", "영상", "마케팅"
]

@st.cache_data(ttl=600)
def fetch_bid_data():
    # 이미지에서 확인된 가장 안정적인 '용역입찰공고조회' 엔드포인트 사용
    endpoint = "http://apis.data.go.kr/1230000/BidPublicInfoService05/getBidPblancListInfoServc01"
    
    # 서버 부담을 줄이기 위해 요청 범위를 최근 10일로 소폭 조정
    now = datetime.now()
    start_dt = (now - timedelta(days=10)).strftime('%Y%m%d0000')
    end_dt = now.strftime('%Y%m%d2359')

    # 500 에러 원천 차단: 라이브러리 자동 인코딩을 피하기 위해 쿼리 스트링 수동 조립
    # 핵심: serviceKey를 가장 앞에 두고 다른 파라미터를 뒤로 배치
    params_str = (
        f"serviceKey={MY_API_KEY}"
        f"&numOfRows=100"  
        f"&pageNo=1"
        f"&type=json"
        f"&bidNtceDtFrom={start_dt}"
        f"&bidNtceDtTo={end_dt}"
    )
    
    full_url = f"{endpoint}?{params_str}"

    try:
        # User-Agent를 추가하여 브라우저의 요청처럼 위장 (일부 서버의 봇 차단 방지)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(full_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            # XML 에러 메시지가 섞여 오는지 확인
            if response.text.startswith("<?xml"):
                return None, f"API 키 유효성 오류: {response.text[:100]}"
            
            data = response.json()
            items = data.get('response', {}).get('body', {}).get('items', [])
            return pd.DataFrame(items) if items else pd.DataFrame(), None
        else:
            # 500 에러 시 서버가 남긴 텍스트를 그대로 출력하여 원인 파악
            return None, f"서버 오류 (HTTP {response.status_code}): {response.text[:150]}"
            
    except Exception as e:
        return None, f"통신 예외 발생: {str(e)}"

# 실행 UI
st.write(f"🔍 **필터링 키워드:** {', '.join(TARGET_KEYWORDS)}")

if st.button("🚀 데이터 정밀 수집 시작"):
    with st.spinner("전문가 엔진이 나라장터 통신 규격을 최적화 중입니다..."):
        df_raw, err = fetch_bid_data()

    if err:
        st.error(f"❌ {err}")
        st.info("💡 **최종 점검:**\n1. Secrets에 넣은 키 앞뒤에 공백이나 큰따옴표가 중복되지 않았는지 확인하세요.\n2. 혹시 모르니 '인코딩 키'로도 교체해서 저장해 보세요.")
    elif df_raw is not None:
        if not df_raw.empty:
            # 필요한 데이터 전처리
            display_cols = {
                'bidNtceNm': '공고명',
                'ntceInsttNm': '공고기관',
                'bidNtceDt': '게시일시',
                'bidNtceUrl': '공고링크'
            }
            df = df_raw[list(display_cols.keys())].rename(columns=display_cols)

            # OR 조건 검색: 키워드 중 하나라도 공고명에 포함되면 필터링
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
                st.download_button("📥 분석 결과 엑셀 다운로드", output.getvalue(), "G2B_Analysis.xlsx")
            else:
                st.warning("분석 결과, 현재 기준 필터링된 공고가 없습니다.")
        else:
            st.info("최근 10일간 등록된 입찰 데이터 자체가 없습니다.")
