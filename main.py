import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import io
import re

# 1. 페이지 레이아웃 설정
st.set_page_config(page_title="G2B 공고 큐레이터", layout="wide")

# --- [중요] 발급받으신 '디코딩' 인증키를 입력하세요 ---
MY_API_KEY = "61203561a5f6b1757e496997889aa776c9484657a36d4aaea2de18b25192393b"
# --------------------------------------------------

st.title("🏛️ 나라장터 맞춤형 입찰공고 리스팅")

# 타겟 키워드 리스트 (이 중 하나라도 포함되면 검색됨)
TARGET_KEYWORDS = [
    "뉴미디어", "홍보", "온라인 홍보", "서포터즈", "서울창업허브", 
    "농촌관광", "관광", "여행", "브랜딩", "SNS", "캠페인", "영상", "마케팅"
]

st.info(f"🔍 **필터링 조건:** 공고명에 아래 키워드 중 **하나라도 포함**되면 표시합니다.\n\n`{'`, `'.join(TARGET_KEYWORDS)}`")

def fetch_g2b_data():
    """500 에러 방어 및 데이터 수집 함수"""
    # 용역 입찰공고조회 서비스 엔드포인트
    base_url = "http://apis.data.go.kr/1230000/BidPublicInfoService05/getBidPblancListInfoServc01"
    
    # 날짜 범위 (최근 7일)
    now = datetime.now()
    start_dt = (now - timedelta(days=7)).strftime('%Y%m%d0000')
    end_dt = now.strftime('%Y%m%d2359')

    # 500 에러의 주범인 '이중 인코딩'을 방지하기 위해 URL 직접 조립
    request_url = (
        f"{base_url}?serviceKey={MY_API_KEY}"
        f"&numOfRows=999&pageNo=1&type=json"
        f"&bidNtceDtFrom={start_dt}&bidNtceDtTo={end_dt}"
        f"&inprogrsWbidPblancYn=Y"
    )

    try:
        response = requests.get(request_url, timeout=20)
        
        # HTTP 500 에러 발생 시 서버가 보낸 메시지 확인
        if response.status_code != 200:
            return None, f"서버 응답 오류 (코드: {response.status_code})\n메시지: {response.text[:200]}"

        # 정상 응답이나 XML 에러(인증키 문제 등)가 섞여 오는 경우 처리
        if response.text.startswith("<?xml"):
            if "SERVICE_KEY_IS_NOT_REGISTERED" in response.text:
                return None, "인증키가 등록되지 않았습니다. (복사 오류 또는 활성화 대기)"
            return None, f"API 점검 중이거나 XML 에러가 발생했습니다.\n내용: {response.text[:100]}"

        data = response.json()
        items = data.get('response', {}).get('body', {}).get('items', [])
        
        if not items:
            return pd.DataFrame(), None
            
        return pd.DataFrame(items), None

    except Exception as e:
        return None, f"시스템 오류: {str(e)}"

# 실행 버튼
if st.button("🚀 공고 리스팅 시작"):
    if "여기에" in MY_API_KEY:
        st.warning("⚠️ 코드 상단의 `MY_API_KEY`에 실제 인증키를 입력해주세요.")
    else:
        with st.spinner("나라장터에서 데이터를 수집하여 키워드 매칭 중..."):
            df_raw, err = fetch_g2b_data()

        if err:
            st.error(f"❌ 데이터 호출 실패\n\n{err}")
            st.info("💡 **조치 방법:**\n1. 키 발급 후 1~2시간이 지났는지 확인\n2. '디코딩' 키 대신 '인코딩' 키로 교체 시도\n3. 공공데이터포털에서 해당 API 승인 여부 확인")
        elif df_raw is not None:
            if not df_raw.empty:
                # 필요한 컬럼만 추출 및 이름 변경
                cols = {
                    'bidNtceNm': '공고명',
                    'ntceInsttNm': '공고기관',
                    'bidNtceDt': '게시일시',
                    'bidClseDt': '마감일시',
                    'bidNtceUrl': '공고링크'
                }
                df = df_raw[list(cols.keys())].rename(columns=cols)

                # --- 핵심: OR 조건 키워드 필터링 (하나라도 포함되면 검색) ---
                # 정규식 패턴 생성 (예: "홍보|마케팅|영상")
                pattern = '|'.join(TARGET_KEYWORDS)
                # 공고명 컬럼에서 패턴 찾기 (대소문자 구분 안 함)
                df_filtered = df[df['공고명'].str.contains(pattern, case=False, na=False, regex=True)].reset_index(drop=True)

                if not df_filtered.empty:
                    st.success(f"✅ 총 {len(df_filtered)}건의 맞춤 공고를 발견했습니다.")
                    st.dataframe(
                        df_filtered,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "공고링크": st.column_config.LinkColumn("상세보기 🔗", display_text="나라장터 이동")
                        }
                    )

                    # 엑셀 다운로드 기능
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df_filtered.to_excel(writer, index=False)
                    st.download_button("📥 검색결과 엑셀 다운로드", output.getvalue(), f"G2B_List_{datetime.now().strftime('%Y%m%d')}.xlsx")
                else:
                    st.warning("조회된 전체 공고 중 설정하신 키워드를 포함하는 공고가 없습니다.")
            else:
                st.info("최근 7일간 등록된 입찰 공고가 없습니다.")
