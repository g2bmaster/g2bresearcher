import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import io

# 페이지 설정
st.set_page_config(page_title="홍보/마케팅 용역 공고 알리미", layout="wide")

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 검색 설정")
    # 요청하신 키워드 목록
    target_keywords = [
        "SNS", "뉴미디어", "온라인홍보", "캠페인", "신뢰 제고", 
        "홍보", "마케팅", "브랜딩", "브랜드", "관광", 
        "유튜브", "영상", "서포터즈"
    ]
    
    selected_category = st.multiselect(
        "관심 키워드 선택 (미선택 시 전체 검색)",
        options=target_keywords,
        default=[]
    )
    
    days_to_look = st.slider("조회 기간 (최근 며칠?)", 1, 7, 7)
    
    st.divider()
    st.caption("공고명에 위 키워드가 포함된 용역만 추출합니다.")

# 제목 섹션
st.title("📢 뉴미디어·홍보 마케팅 입찰공고")
st.subheader(f"최근 {days_to_look}일 이내 업로드된 공고 리스트")

# API 키 설정
API_KEY = st.secrets.get("G2B_API_KEY", "61203561a5f6b1757e496997889aa776c9484657a36d4aaea2de18b25192393b")

def fetch_service_bids():
    url = "http://apis.data.go.kr/1230000/BidPublicInfoService05/getBidPblancListInfoServc01"
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_to_look)
    
    params = {
        'serviceKey': API_KEY,
        'type': 'json',
        'numOfRows': '999', # 최대한 많이 가져온 후 파이썬으로 필터링
        'pageNo': '1',
        'bidNtceDtFrom': start_date.strftime('%Y%m%d%H%M'),
        'bidNtceDtTo': end_date.strftime('%Y%m%d%H%M')
    }

    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            items = data.get('response', {}).get('body', {}).get('items', [])
            return pd.DataFrame(items) if items else pd.DataFrame()
        else:
            return None
    except:
        return None

if API_KEY == "인증키를 등록해주세요":
    st.warning("⚠️ 앱 설정(Secrets)에서 G2B_API_KEY를 등록해야 데이터가 표시됩니다.")
else:
    with st.spinner('나라장터 서버에서 공고를 분석 중입니다...'):
        df_raw = fetch_service_bids()

    if df_raw is not None and not df_raw.empty:
        # 컬럼 정리
        cols = {
            'bidNtceNm': '공고명',
            'ntceInsttNm': '공고기관',
            'demandInsttNm': '수요기관',
            'bidNtceDt': '게시일시',
            'bidClseDt': '마감일시',
            'bidNtceUrl': '공고링크'
        }
        df = df_raw[cols.keys()].rename(columns=cols)

        # 키워드 필터링 로직 (요청하신 키워드 기준)
        search_list = selected_category if selected_category else target_keywords
        pattern = '|'.join(search_list)
        df_filtered = df[df['공고명'].str.contains(pattern, case=False, na=False)].reset_index(drop=True)

        if not df_filtered.empty:
            st.success(f"총 {len(df_filtered)}건의 관련 공고를 찾았습니다.")
            
            # 테이블 출력
            st.dataframe(
                df_filtered, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "공고링크": st.column_config.LinkColumn("공고링크", display_text="바로가기🔗")
                }
            )

            # 엑셀 다운로드
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_filtered.to_excel(writer, index=False, sheet_name='홍보공고_리스트')
            
            st.download_button(
                label="📥 필터링된 결과 엑셀로 저장하기",
                data=output.getvalue(),
                file_name=f"PR_Bids_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("선택하신 키워드와 일치하는 공고가 현재 없습니다.")
    elif df_raw is not None and df_raw.empty:
        st.info("해당 기간 내에 등록된 전체 용역 공고가 없습니다.")
    else:
        st.error("데이터를 불러올 수 없습니다. API 키를 확인해 주세요.")
