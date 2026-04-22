import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import io
from urllib.parse import unquote

# 1. 페이지 기본 설정
st.set_page_config(page_title="나라장터 용역공고 리스터", layout="wide")

# ---------------- [수정구간: 본인의 인증키를 입력하세요] ----------------
# 공공데이터포털에서 발급받은 '일반 인증키(Decoding)'를 입력하는 것이 가장 안전합니다.
MY_API_KEY = "61203561a5f6b1757e496997889aa776c9484657a36d4aaea2de18b25192393b"
# ------------------------------------------------------------------

st.title("🏛️ 나라장터 용역 입찰공고 리스팅")
st.caption("www.g2b.go.kr의 용역 카테고리 실시간 공고를 불러옵니다.")

# 홍보/마케팅 관련 키워드 자동 세팅
target_keywords = [
    "뉴미디어", "홍보", "온라인 홍보", "서포터즈", "서울창업허브", 
    "농촌관광", "관광", "여행", "브랜딩", "SNS", "캠페인", "영상", "마케팅"
]

st.info(f"📋 **필터링 키워드:** {', '.join(target_keywords)}")

@st.cache_data(ttl=600) # 10분간 결과 유지
def fetch_g2b_data():
    # 용역 입찰공고조회 서비스 엔드포인트
    url = "http://apis.data.go.kr/1230000/BidPublicInfoService05/getBidPblancListInfoServc01"
    
    # 500 에러 방지: 인증키 디코딩 상태 확인
    decoded_key = unquote(MY_API_KEY)
    
    # 날짜 설정: 정확히 12자리(YYYYMMDDHHMM) 포맷 준수
    now = datetime.now()
    start_dt = (now - timedelta(days=7)).strftime('%Y%m%d0000')
    end_dt = now.strftime('%Y%m%d2359')
    
    params = {
        'serviceKey': decoded_key,
        'type': 'json',
        'numOfRows': '999',  # 검색 결과가 많을 수 있으므로 넉넉히 설정
        'pageNo': '1',
        'bidNtceDtFrom': start_dt,
        'bidNtceDtTo': end_dt,
        'inprogrsWbidPblancYn': 'Y' # 현재 진행중인 공고만
    }

    try:
        # 에러 방지: 파라미터를 dict로 넘겨 requests가 처리하게 함
        response = requests.get(url, params=params, timeout=20)
        
        if response.status_code == 200:
            try:
                content = response.json()
                items = content.get('response', {}).get('body', {}).get('items', [])
                if not items:
                    return pd.DataFrame()
                return pd.DataFrame(items)
            except:
                # 서버가 JSON이 아닌 XML 에러메시지를 보낼 경우
                return f"API 응답 분석 오류 (키 권한이나 활성화 여부 확인 필요): {response.text[:100]}"
        else:
            return f"서버 응답 오류 (코드: {response.status_code})"
    except Exception as e:
        return f"연결 오류: {str(e)}"

if st.button('🚀 최신 공고 리스팅 시작'):
    if MY_API_KEY == "여기에_인증키를_붙여넣으세요":
        st.warning("⚠️ 코드 상단의 `MY_API_KEY` 변수에 실제 인증키를 입력해야 작동합니다.")
    else:
        with st.spinner('나라장터 서버에서 데이터를 수집 중입니다...'):
            result = fetch_g2b_data()

        if isinstance(result, pd.DataFrame):
            if not result.empty:
                # 가독성을 위한 컬럼명 변경
                cols = {
                    'bidNtceNm': '공고명',
                    'ntceInsttNm': '공고기관',
                    'demandInsttNm': '수요기관',
                    'bidNtceDt': '게시일시',
                    'bidClseDt': '마감일시',
                    'bidNtceUrl': '공고링크'
                }
                
                # 필요한 데이터만 필터링
                df = result[list(cols.keys())].rename(columns=cols)

                # 키워드 필터링 (공고명 기준)
                pattern = '|'.join(target_keywords)
                df_filtered = df[df['공고명'].str.contains(pattern, case=False, na=False)].reset_index(drop=True)

                if not df_filtered.empty:
                    st.success(f"✅ 총 {len(df_filtered)}건의 맞춤 공고를 리스팅했습니다.")
                    
                    # 데이터 테이블 표시
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
                        df_filtered.to_excel(writer, index=False, sheet_name='G2B_Listing')
                    
                    st.download_button(
                        label="📥 리스트 엑셀 다운로드",
                        data=output.getvalue(),
                        file_name=f"G2B_Listing_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.warning("일치하는 키워드의 공고가 없습니다.")
            else:
                st.info("최근 7일간 등록된 용역 공고가 없습니다.")
        else:
            st.error(f"❌ {result}")
