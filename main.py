import streamlit as st
import urllib.request
import json
import pandas as pd
from datetime import datetime, timedelta
import io

st.set_page_config(page_title="G2B 마케팅 큐레이터", layout="wide")

# 1. Secrets 보안 로드 (반드시 따옴표 포함해서 입력되어 있어야 함)
try:
    # API_KEY = "내_디코딩_키"
    MY_API_KEY = st.secrets["API_KEY"]
except:
    st.error("🔑 Streamlit Secrets에서 'API_KEY'를 설정해주세요.")
    st.stop()

st.title("🏛️ 나라장터 마케팅/뉴미디어 공고 리스팅")

# 2. 타겟 키워드 (OR 조건)
TARGET_KEYWORDS = [
    "뉴미디어", "온라인 홍보", "SNS", "유튜브", "영상", 
    "홍보 영상", "관광", "브랜딩", "마케팅", "서포터즈", "통합 홍보"
]

def fetch_data_via_urllib():
    """requests를 버리고 파이썬 표준 라이브러리인 urllib를 사용하여 강제 호출"""
    # 엔드포인트 교정
    base_url = "https://apis.data.go.kr/1230000/BidPublicInfoService05/getBidPblancListInfoServc01"
    
    now = datetime.now()
    start_dt = (now - timedelta(days=15)).strftime('%Y%m%d0000')
    end_dt = now.strftime('%Y%m%d2359')

    # URL 직접 조립 (인코딩 절대 금지)
    query_url = (
        f"{base_url}?serviceKey={MY_API_KEY}"
        f"&numOfRows=900&pageNo=1&type=json"
        f"&bidNtceDtFrom={start_dt}&bidNtceDtTo={end_dt}"
        f"&inprogrsWbidPblancYn=Y"
    )

    try:
        # 헤더를 브라우저와 동일하게 세팅 (핵심)
        req = urllib.request.Request(query_url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        with urllib.request.urlopen(req, timeout=20) as response:
            res_code = response.getcode()
            if res_code == 200:
                res_data = response.read().decode('utf-8')
                
                # XML 에러 체크
                if res_data.startswith("<?xml"):
                    return None, f"인증 오류(XML): {res_data[:100]}"
                
                result = json.loads(res_data)
                items = result.get('response', {}).get('body', {}).get('items', [])
                return pd.DataFrame(items) if items else pd.DataFrame(), None
            else:
                return None, f"서버 응답 오류 (Code {res_code})"
                
    except Exception as e:
        return None, f"통신 예외 발생: {str(e)}"

# --- UI ---
if st.button("🚀 15일치 공고 강제 수집 시작"):
    with st.spinner("서버 보안벽을 우회하여 데이터를 수집 중입니다..."):
        df_raw, err = fetch_data_via_urllib()

    if err:
        st.error(f"❌ {err}")
        st.markdown("---")
        st.write("### 🛠️ 개발자 긴급 진단")
        st.info("만약 여기서도 500이 난다면, 아래 URL을 복사해서 **내 브라우저 주소창**에 직접 넣어보세요.")
        # 디버깅용 URL (민감 정보 가림)
        debug_url = f"https://apis.data.go.kr/1230000/BidPublicInfoService05/getBidPblancListInfoServc01?serviceKey=YOUR_KEY&numOfRows=10&type=json"
        st.code(debug_url)
    elif df_raw is not None:
        if not df_raw.empty:
            df = df_raw[['bidNtceNm', 'ntceInsttNm', 'bidNtceDt', 'bidNtceUrl']].copy()
            df.columns = ['공고명', '공고기관', '게시일시', '링크']

            # OR 조건 필터링
            pattern = '|'.join(TARGET_KEYWORDS)
            df_filtered = df[df['공고명'].str.contains(pattern, case=False, na=False)].reset_index(drop=True)

            if not df_filtered.empty:
                st.success(f"🎯 맞춤 공고 {len(df_filtered)}건 발견")
                st.dataframe(df_filtered, use_container_width=True, hide_index=True,
                             column_config={"링크": st.column_config.LinkColumn("상세보기")})
                
                # 엑셀 다운로드
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_filtered.to_excel(writer, index=False)
                st.download_button("📥 엑셀 저장", output.getvalue(), "Nara_Final.xlsx")
            else:
                st.warning("매칭되는 키워드가 없습니다.")
