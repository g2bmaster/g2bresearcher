import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import io

# [설정]
st.set_page_config(page_title="G2B 마케팅 큐레이터", layout="wide")

MY_API_KEY = "61203561a5f6b1757e496997889aa776c9484657a36d4aaea2de18b25192393b"
# --------------------------------------------

st.title("🚀 나라장터 마케팅/뉴미디어 공고 큐레이션")

# 모니터링 키워드
TARGET_KEYWORDS = [
    "뉴미디어", "홍보", "온라인 홍보", "서포터즈", "서울창업허브", 
    "농촌관광", "관광", "여행", "브랜딩", "SNS", "캠페인", "영상", "마케팅"
]

st.info(f"📋 **모니터링 키워드:** {', '.join(TARGET_KEYWORDS)}")

def fetch_g2b_clean():
    """인코딩 문제를 원천 차단하는 정밀 호출 함수"""
    # 500 에러의 주범인 requests 자동 인코딩을 피하기 위한 설정
    endpoint = "http://apis.data.go.kr/1230000/BidPublicInfoService05/getBidPblancListInfoServc01"
    
    now = datetime.now()
    start_dt = (now - timedelta(days=7)).strftime('%Y%m%d0000')
    end_dt = now.strftime('%Y%m%d2359')

    # 파라미터를 딕셔너리가 아닌 '생 문자열'로 직접 조립 (이게 핵심입니다)
    full_url = (
        f"{endpoint}?serviceKey={MY_API_KEY}"
        f"&numOfRows=999&pageNo=1&type=json"
        f"&bidNtceDtFrom={start_dt}&bidNtceDtTo={end_dt}"
        f"&inprogrsWbidPblancYn=Y"
    )

    try:
        # params 인자를 쓰지 않고 완성된 URL만 보냅니다.
        response = requests.get(full_url, timeout=15)
        
        if response.status_code == 200:
            # 서버가 XML로 에러를 보냈는지 확인 (정상일 땐 JSON)
            if response.text.startswith("<?xml"):
                if "SERVICE_KEY_IS_NOT_REGISTERED" in response.text:
                    return None, "인증키 미등록 에러 (승인 대기 중이거나 키 오타)"
                return None, f"API 서버 에러: XML 응답 발생"
            
            data = response.json()
            items = data.get('response', {}).get('body', {}).get('items', [])
            return pd.DataFrame(items) if items else pd.DataFrame(), None
        else:
            return None, f"HTTP {response.status_code} 에러 발생"
            
    except Exception as e:
        return None, f"시스템 오류: {str(e)}"

if st.button("🔄 최신 공고 실시간 분석 시작"):
    if "여기에" in MY_API_KEY:
        st.warning("⚠️ 상단 MY_API_KEY 변수에 실제 인증키를 입력해주세요.")
    else:
        with st.spinner("전문가 엔진이 나라장터 데이터를 정밀 수집 중..."):
            df_raw, err = fetch_g2b_clean()

        if err:
            st.error(f"❌ {err}")
            st.info("💡 **해결 방법:**\n1. 발급받은지 1시간 이내라면 조금 더 기다려주세요.\n2. '디코딩' 키 대신 '인코딩' 키를 넣어보세요.\n3. 공공데이터포털 마이페이지에서 해당 API가 '승인' 상태인지 확인하세요.")
        elif df_raw is not None:
            if not df_raw.empty:
                # 데이터 매핑 및 필터링
                df = df_raw[['bidNtceNm', 'ntceInsttNm', 'bidNtceDt', 'bidNtceUrl']].copy()
                df.columns = ['공고명', '발주기관', '공고일', '링크']
                
                pattern = '|'.join(TARGET_KEYWORDS)
                df_filtered = df[df['공고명'].str.contains(pattern, case=False, na=False)].reset_index(drop=True)

                if not df_filtered.empty:
                    st.success(f"🎯 총 {len(df_filtered)}건의 맞춤 공고를 발견했습니다.")
                    st.dataframe(df_filtered, use_container_width=True, hide_index=True,
                                 column_config={"링크": st.column_config.LinkColumn("상세보기")})
                    
                    # 엑셀 다운로드
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df_filtered.to_excel(writer, index=False)
                    st.download_button("📥 분석 결과 엑셀 저장", output.getvalue(), "G2B_Result.xlsx")
                else:
                    st.warning("분석 결과 일치하는 키워드가 없습니다.")
            else:
                st.info("조회된 데이터가 없습니다.")
