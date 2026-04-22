import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import io
from urllib.parse import urlencode, quote_plus

# ─────────────────────────────────────────
# 1. 페이지 설정
# ─────────────────────────────────────────
st.set_page_config(page_title="G2B 마케팅 공고 분석기", layout="wide")

# ─────────────────────────────────────────
# 2. API 키 로드  (Streamlit Secrets)
#    secrets.toml → API_KEY = "발급받은_원문_키"
# ─────────────────────────────────────────
try:
    MY_API_KEY = st.secrets["API_KEY"]
except Exception:
    st.error("🔑 Streamlit Secrets에서 'API_KEY'를 먼저 설정해주세요.")
    st.stop()

st.title("🏛️ 나라장터 마케팅/뉴미디어 공고 큐레이션")

# ─────────────────────────────────────────
# 3. 핵심 키워드
# ─────────────────────────────────────────
TARGET_KEYWORDS = [
    "뉴미디어", "온라인 홍보", "SNS", "유튜브", "영상",
    "홍보 영상", "관광", "브랜딩", "마케팅", "서포터즈", "통합 홍보"
]

# ─────────────────────────────────────────
# 4. 핵심 수정 포인트
#
#  [문제 1] requests.get(url, params=dict) 사용 시
#           serviceKey 값이 이중 인코딩되어 500 발생
#           → URL 문자열을 직접 조립하되,
#             serviceKey만 quote_plus로 인코딩하지 않고 그대로 붙임
#
#  [문제 2] 공공데이터포털 발급 키는
#           "인코딩된 키"와 "디코딩된 키" 두 가지를 줌
#           → secrets 에는 반드시 "디코딩된(Decoding) 키"를 넣어야 함
#           → 혹시 인코딩 키만 있다면 아래 decode 플래그를 False 로
#
#  [문제 3] 날짜 파라미터를 안 넣거나 범위가 너무 좁으면
#           resultCode '03'(데이터 없음)이 아니라 500 반환하는 경우 있음
#           → 기간을 넉넉하게 30일로 확장
#
#  [문제 4] User-Agent 없이 보내면 차단되는 경우 있음
#           → 브라우저 UA 추가
# ─────────────────────────────────────────

BASE_URL = (
    "https://apis.data.go.kr/1230000/BidPublicInfoService05/"
    "getBidPblancListInfoServcPPSSrch"
)

def build_url(service_key: str, start_dt: str, end_dt: str,
              page: int = 1, rows: int = 999) -> str:
    """
    serviceKey 이중인코딩 방지를 위해
    나머지 파라미터만 urlencode 처리 후 수동으로 조립
    """
    other_params = urlencode({
        "numOfRows": rows,
        "pageNo": page,
        "type": "json",
        "bidNtceDtFrom": start_dt,
        "bidNtceDtTo": end_dt,
    })
    # serviceKey는 인코딩 없이 그대로 맨 앞에 붙임
    return f"{BASE_URL}?serviceKey={service_key}&{other_params}"


@st.cache_data(ttl=600)
def fetch_g2b_data(days_back: int = 30):
    now = datetime.now()
    start_dt = (now - timedelta(days=days_back)).strftime("%Y%m%d0000")
    end_dt = now.strftime("%Y%m%d2359")

    url = build_url(MY_API_KEY, start_dt, end_dt)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
    }

    # ── 디버그: 실제 요청 URL 확인용 (운영 시 주석 처리 가능) ──
    with st.expander("🔍 디버그: 실제 요청 URL 확인", expanded=False):
        # API 키 노출 방지를 위해 키 앞 10자리만 표시
        safe_url = url.replace(MY_API_KEY, MY_API_KEY[:10] + "***")
        st.code(safe_url)

    try:
        resp = requests.get(url, headers=headers, timeout=30)
    except requests.exceptions.Timeout:
        return None, "⏱️ 요청 시간 초과 (30초). 나라장터 서버가 응답하지 않습니다."
    except requests.exceptions.ConnectionError as e:
        return None, f"🌐 네트워크 연결 오류: {e}"

    # ── HTTP 레벨 에러 처리 ──
    if resp.status_code != 200:
        return None, (
            f"❌ HTTP {resp.status_code} 오류\n\n"
            f"응답 내용 (앞 300자):\n{resp.text[:300]}"
        )

    # ── XML 응답 = 인증 실패 또는 잘못된 엔드포인트 ──
    if resp.text.lstrip().startswith("<"):
        return None, (
            "🔑 API 키 인증 실패 또는 엔드포인트 오류입니다.\n\n"
            "**확인 사항:**\n"
            "1. secrets.toml 에 **디코딩(Decoding) 키**가 입력되어 있는지 확인\n"
            "2. 공공데이터포털 → 마이페이지 → 활용신청 목록에서 "
            "해당 API **승인 여부** 확인\n\n"
            f"서버 원문 응답:\n{resp.text[:400]}"
        )

    # ── JSON 파싱 ──
    try:
        data = resp.json()
    except Exception:
        return None, f"JSON 파싱 실패. 원문:\n{resp.text[:400]}"

    header = data.get("response", {}).get("header", {})
    result_code = header.get("resultCode", "")
    result_msg  = header.get("resultMsg", "")

    if result_code == "03":          # 데이터 없음 (정상)
        return pd.DataFrame(), None
    elif result_code != "00":
        return None, f"API 오류 코드 {result_code}: {result_msg}"

    items = data.get("response", {}).get("body", {}).get("items", [])

    # items 가 dict 로 오는 케이스(단건) 방어
    if isinstance(items, dict):
        items = [items]

    return (pd.DataFrame(items) if items else pd.DataFrame()), None


# ─────────────────────────────────────────
# 5. UI
# ─────────────────────────────────────────
st.info(f"📋 **모니터링 키워드:** {', '.join(TARGET_KEYWORDS)}")

col1, col2 = st.columns([2, 1])
with col1:
    days_back = st.slider("조회 기간 (최근 N일)", min_value=7, max_value=60,
                          value=30, step=7)
with col2:
    st.write("")
    run = st.button("🚀 실시간 분석 시작", use_container_width=True)

if run:
    with st.spinner(f"최근 {days_back}일 데이터를 조회 중입니다..."):
        df_raw, err = fetch_g2b_data(days_back=days_back)

    if err:
        st.error(err)
        st.markdown(
            """
            ---
            ### 💡 500 에러 자가 진단 체크리스트
            | # | 확인 항목 | 해결 방법 |
            |---|-----------|-----------|
            | 1 | secrets 에 **디코딩 키** 입력 여부 | 공공데이터포털 마이페이지 → 인코딩/디코딩 키 구분 확인 |
            | 2 | 해당 API **활용 승인** 여부 | 포털에서 승인 상태 '승인'인지 확인 |
            | 3 | IP 차단 여부 | 잠시 후 재시도 또는 VPN 전환 |
            | 4 | 서비스 점검 시간 | 나라장터 공지 확인 (보통 새벽 2~4시) |
            """
        )
    elif df_raw is not None:
        if not df_raw.empty:
            # 컬럼 존재 여부 확인 후 안전하게 선택
            col_map = {
                "bidNtceNm":   "공고명",
                "ntceInsttNm": "공고기관",
                "bidNtceDt":   "게시일시",
                "bidClseDt":   "마감일시",
                "bidNtceUrl":  "상세링크",
            }
            available = {k: v for k, v in col_map.items() if k in df_raw.columns}
            df = df_raw[list(available.keys())].rename(columns=available)

            # 키워드 필터링
            pattern = "|".join(TARGET_KEYWORDS)
            df_filtered = (
                df[df["공고명"].str.contains(pattern, case=False, na=False, regex=True)]
                .reset_index(drop=True)
            )

            if not df_filtered.empty:
                st.success(f"🎯 맞춤 공고 **{len(df_filtered)}건** 발견 (전체 조회: {len(df)}건)")

                col_cfg = {}
                if "상세링크" in df_filtered.columns:
                    col_cfg["상세링크"] = st.column_config.LinkColumn("나라장터 이동 🔗")

                st.dataframe(
                    df_filtered,
                    use_container_width=True,
                    hide_index=True,
                    column_config=col_cfg,
                )

                # 엑셀 다운로드
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                    df_filtered.to_excel(writer, index=False, sheet_name="공고목록")
                st.download_button(
                    "📥 검색결과 엑셀 저장",
                    data=output.getvalue(),
                    file_name=f"G2B_Analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            else:
                st.warning(
                    f"전체 {len(df)}건 중 키워드에 해당하는 공고가 없습니다. "
                    "조회 기간을 늘려보세요."
                )
        else:
            st.info(f"최근 {days_back}일간 등록된 용역 입찰 데이터가 없습니다.")
