import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# --- 설정 구간 ---
# 공공데이터포털에서 발급받은 '일반 인증키(Decoding)'를 아래 따옴표 안에 넣으세요.
SERVICE_KEY = "61203561a5f6b1757e496997889aa776c9484657a36d4aaea2de18b25192393b"

# 검색 키워드 리스트
KEYWORDS = ['뉴미디어', '홍보', '온라인 홍보', '서포터즈', '서울창업허브', '농촌관광', '관광', '여행', '브랜딩']

# 앱 UI 설정
st.set_page_config(page_title="나라장터 키워드 알리미", layout="wide")

st.header("📢 나라장터 입찰공고 맞춤 리스트")
st.info(f"검색 키워드: {', '.join(KEYWORDS)}")

# 날짜 계산 (오늘 기준 최근 7일)
end_date = datetime.now().strftime('%Y%m%d2359')
start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d0000')

def get_nara_data():
    # 용역 입찰공고 조회 API 주소
    url = "http://apis.data.go.kr/1230000/BidPublicInfoService05/getBidPblancListInfoServcPPSSrch01"
    
    params = {
        'serviceKey': SERVICE_KEY,
        'numOfRows': '999',       # 한 번에 가져올 최대 건수
        'pageNo': '1',
        'inqryDiv': '1',          # 공고일시 기준
        'inqryBgnDt': start_date,
        'inqryEndDt': end_date,
        'type': 'json'
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        
        # API 응답 확인
        if response.status_code != 200:
            st.error(f"API 요청 실패 (코드: {response.status_code})")
            return []

        result = response.json()
        items = result.get('response', {}).get('body', {}).get('items', [])
        
        if not items:
            return []

        # 키워드 필터링 로직
        filtered = []
        for item in items:
            title = item.get('bidNtceNm', '')
            # 제목에 키워드 중 하나라도 포함되어 있는지 확인
            if any(keyword in title for keyword in KEYWORDS):
                filtered.append({
                    "공고명": title,
                    "공고기관": item.get('ntceInsttNm'),
                    "수요기관": item.get('dminsttNm'),
                    "공고일시": item.get('bidNtceDt'),
                    "마감일시": item.get('bidClseDt'),
                    "공고링크": item.get('bidNtceDtlUrl')
                })
        return filtered

    except Exception as e:
        st.error(f"데이터를 가져오는 중 오류 발생: {e}")
        return []

# 실행 버튼
if st.button("최신 공고 불러오기 (최근 1주일)"):
    with st.spinner('나라장터 서버에서 데이터를 긁어오는 중...'):
        data = get_nara_data()
        
        if data:
            df = pd.DataFrame(data)
            st.success(f"총 {len(df)}건의 맞춤 공고를 찾았습니다!")
            
            # 표 출력 (링크를 클릭 가능하게 만들기)
            st.dataframe(
                df, 
                column_config={
                    "공고링크": st.column_config.Link_column("상세보기")
                },
                use_container_width=True
            )
            
            # 엑셀 다운로드 기능
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="결과를 엑셀(CSV)로 저장",
                data=csv,
                file_name=f"나라장터_검색결과_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )
        else:
            st.warning("최근 1주일 내에 해당 키워드가 포함된 공고가 없습니다.")

# 하단 정보
st.markdown("---")
st.caption(f"검색 기간: {start_date[:8]} ~ {end_date[:8]} | 데이터 출처: 조달청 나라장터 API")
