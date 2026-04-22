import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import io
import re

# [설정] 페이지 레이아웃 및 테마
st.set_page_config(page_title="G2B 마케팅 공고 큐레이터", layout="wide", page_icon="🚀")

# ------------------------------------------------------------------
# [필독] 보안 및 공유를 위해 인증키는 직접 입력하거나 아래 변수에 넣으세요.
# 공공데이터포털에서 발급받은 'Decoding' 키 사용을 강력 권장합니다.
# ------------------------------------------------------------------
MY_API_KEY = "61203561a5f6b1757e496997889aa776c9484657a36d4aaea2de18b25192393b"

# 전문가 선정 핵심 타겟 키워드 (정규식 최적화)
TARGET_KEYWORDS = [
    "뉴미디어", "홍보", "온라인 홍보", "서포터즈", "서울창업허브", 
    "농촌관광", "관광", "여행", "브랜딩", "SNS", "캠페인", "영상", "마케팅"
]

def get_safe_data():
    """나라장터 API 호출 및 500 에러 방어 로직"""
    base_url = "http://apis.data.go.kr/1230000/BidPublicInfoService05/getBidPblancListInfoServc01"
    
    # 날짜 범위 설정 (최근 7일)
    now = datetime.now()
    start_dt = (now - timedelta(days=7)).strftime('%Y%m%d0000')
    end_dt = now.strftime('%Y%m%d2359')

    # URL 직접 조립 (requests의 내부 인코딩 간섭 배제)
    query_params = (
        f"?serviceKey={MY_API_KEY}"
        f"&numOfRows=999&pageNo=1&type=json"
        f"&bidNtceDtFrom={start_dt}&bidNtceDtTo={end_dt}"
        f"&inprogrsWbidPblancYn=Y"
    )
    
    try:
        full_url = base_url + query_params
        response = requests.get(full_url, timeout=15)
        
        # HTTP 상태 코드 확인
        if response.status_code != 200:
            return None, f"서버 응답 오류 (HTTP {response.status_code})"

        # JSON 파싱 시도 (비정상 키일 경우 XML로 응답이 오는 경우 대비)
        try:
            json_data = response.json()
            items = json_data.get('response', {}).get('body', {}).get('items', [])
            if not items:
                return pd.DataFrame(), None
            return pd.DataFrame(items), None
        except Exception:
            if "<returnAuthMsg>" in response.text:
                return None, "인증키 거부 (Key 유효성 또는 활성화 대기 시간 확인)"
            return None, "데이터 형식 오류 (서버 점검 중일 수 있습니다)"
            
    except requests.exceptions.RequestException as e:
        return None, f"네트워크 연결 실패: {str(e)}"

# --- UI 레이아웃 ---
st.title("🚀 나라장터 마케팅/뉴미디어 공고 큐레이션")
st.markdown(f"""
    <div style="background-color:#f0f2f6; padding:15px; border-radius:10px; margin-bottom:20px;">
        <strong>현재 모니터링 키워드:</strong> {', '.join(TARGET_KEYWORDS)}
    </div>
    """, unsafe_allow_html=True)

if st.button("🔄 최신 공고 실시간 분석 시작"):
    if MY_API_KEY == "여기에_디코딩_인증키를_입력하세요":
        st.warning("⚠️ 코드 내 MY_API_KEY 변수에 실제 인증키를 입력해야 합니다.")
    else:
        with st.spinner("전문가 엔진이 나라장터 데이터를 정밀 분석 중입니다..."):
            df_raw, error_msg = get_safe_data()

        if error_msg:
            st.error(f"❌ {error_msg}")
        elif df_raw is not None:
            if not df_raw.empty:
                # 데이터 전처리 및 매핑
                display_cols = {
                    'bidNtceNm': '공고명',
                    'ntceInsttNm': '발주기관',
                    'demandInsttNm': '수요기관',
                    'bidNtceDt': '공고일',
                    'bidClseDt': '마감일',
                    'bidNtceUrl': '공고링크'
                }
                df = df_raw[list(display_cols.keys())].rename(columns=display_cols)

                # 정규식 기반 고성능 키워드 매칭
                pattern = '|'.join(TARGET_KEYWORDS)
                mask = df['공고명'].str.contains(pattern, case=False, na=False, regex=True)
                df_filtered = df[mask].reset_index(drop=True)

                if not df_filtered.empty:
                    st.success(f"🎯 분석 완료: 총 {len(df_filtered)}건의 핵심 공고를 선별했습니다.")
                    
                    # 인터랙티브 데이터 테이블
                    st.dataframe(
                        df_filtered,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "공고링크": st.column_config.LinkColumn("링크", display_text="나라장터 🔗")
                        }
                    )

                    # 엑셀 보고서 생성
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df_filtered.to_excel(writer, index=False, sheet_name='Curated_Bids')
                    
                    st.download_button(
                        label="📥 분석 보고서(Excel) 다운로드",
                        data=output.getvalue(),
                        file_name=f"G2B_Marketing_Bids_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.warning("분석 결과, 현재 기준 필터링된 공고가 없습니다.")
            else:
                st.info("최근 7일간 나라장터에 등록된 전체 용역 건수가 없습니다.")
