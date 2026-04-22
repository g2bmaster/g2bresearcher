import streamlit as st
import pandas as pd
import io
import json
from datetime import datetime, timedelta
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError

# ────────────────────────────────────────────────────────────
# ✅ 인코딩 키 사용 버전
#    인코딩 키는 특수문자가 없으므로 urlencode() 에 그냥 넣어도 됨
#    단, 공공데이터포털 서버는 인코딩 키를 받으면 내부에서
#    자동으로 디코딩 처리하므로 정상 동작함
# ────────────────────────────────────────────────────────────

st.set_page_config(page_title="G2B 마케팅 공고 분석기", layout="wide")
st.title("🏛️ 나라장터 마케팅/뉴미디어 공고 큐레이션")

# ── API 키 로드 ──────────────────────────────────────────────
try:
    MY_API_KEY = st.secrets["API_KEY"]
except Exception:
    st.error("🔑 Streamlit Secrets에서 'API_KEY'를 먼저 설정해주세요.")
    st.stop()

# ── 타겟 키워드 ──────────────────────────────────────────────
TARGET_KEYWORDS = [
    "뉴미디어", "온라인 홍보", "SNS", "유튜브", "영상",
    "홍보 영상", "관광", "브랜딩", "마케팅", "서포터즈", "통합 홍보"
]

BASE_URL = (
    "https://apis.data.go.kr/1230000/BidPublicInfoService05/"
    "getBidPblancListInfoServcPPSSrch"
)

# ────────────────────────────────────────────────────────────
# 인코딩 키는 urlencode() 에 함께 넣어도 이중인코딩 문제 없음
# (영문+숫자만으로 구성되어 변환될 특수문자가 없기 때문)
# ────────────────────────────────────────────────────────────

def build_url(api_key: str, start_dt: str, end_dt: str,
              page: int = 1, rows: int = 999) -> str:
    params = urlencode({
        "serviceKey":    api_key,
        "numOfRows":     rows,
        "pageNo":        page,
        "type":          "json",
        "bidNtceDtFrom": start_dt,
        "bidNtceDtTo":   end_dt,
    })
    return f"{BASE_URL}?{params}"


@st.cache_data(ttl=600)
def fetch_g2b_data(days_back: int = 30):
    now      = datetime.now()
    start_dt = (now - timedelta(days=days_back)).strftime("%Y%m%d0000")
    end_dt   = now.strftime("%Y%m%d2359")
    url      = build_url(MY_API_KEY, start_dt, end_dt)

    req = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
        }
    )

    # 디버그: 키 앞 10자리만 노출
    with st.expander("🔍 디버그: 요청 URL 확인 (키 일부 마스킹)", expanded=False):
        safe = url.replace(MY_API_KEY, MY_API_KEY[:10] + "****")
        st.code(safe, language="text")

    try:
        with urlopen(req, timeout=30) as resp:
            raw_bytes = resp.read()
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        return None, (
            f"❌ HTTP {e.code} 오류\n\n"
            f"서버 응답:\n```\n{body}\n```\n\n"
            + _checklist()
        )
    except URLError as e:
        return None, f"🌐 네트워크 오류: {e.reason}"
    except Exception as e:
        return None, f"🔧 알 수 없는 오류: {e}"

    raw_text = raw_bytes.decode("utf-8", errors="replace")

    # XML 응답 = 인증 실패
    if raw_text.lstrip().startswith("<"):
        return None, (
            "🔑 API 인증 실패 (XML 오류 응답)\n\n"
            f"서버 원문:\n```xml\n{raw_text[:400]}\n```\n\n"
            + _checklist()
        )

    # JSON 파싱
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        return None, f"JSON 파싱 실패. 원문:\n```\n{raw_text[:400]}\n```"

    header      = data.get("response", {}).get("header", {})
    result_code = header.get("resultCode", "")
    result_msg  = header.get("resultMsg", "알 수 없음")

    if result_code == "03":      # 정상이지만 데이터 없음
        return pd.DataFrame(), None
    if result_code != "00":
        return None, f"API 오류 [{result_code}]: {result_msg}"

    items = data.get("response", {}).get("body", {}).get("items", [])
    if isinstance(items, dict):  # 단건 응답 방어
        items = [items]

    return (pd.DataFrame(items) if items else pd.DataFrame()), None


def _checklist() -> str:
    return """
**🔎 자가 진단 체크리스트**

| # | 확인 항목 | 조치 |
|---|-----------|------|
| 1 | secrets 에 **인코딩(Encoding) 키** 입력 여부 | 포털 마이페이지 → 인코딩 탭의 키 확인 |
| 2 | 해당 API **활용 승인** 완료 여부 | 포털 → 마이페이지 → 활용신청 목록 확인 |
| 3 | API 신청 후 **1~2시간** 경과 여부 | 승인 직후엔 키가 활성화되지 않음 |
| 4 | 나라장터 **서버 점검 시간** 여부 | 보통 새벽 02:00~04:00 |
"""


# ────────────────────────────────────────────────────────────
# UI
# ────────────────────────────────────────────────────────────
st.info(f"📋 **모니터링 키워드:** {', '.join(TARGET_KEYWORDS)}")

c1, c2 = st.columns([3, 1])
with c1:
    days_back = st.slider("조회 기간 (최근 N일)", 7, 60, 30, step=7)
with c2:
    st.write("")
    run = st.button("🚀 분석 시작", use_container_width=True)

if run:
    with st.spinner(f"최근 {days_back}일 데이터 조회 중..."):
        df_raw, err = fetch_g2b_data(days_back=days_back)

    if err:
        st.error(err)

    elif df_raw is not None:
        if df_raw.empty:
            st.info(f"최근 {days_back}일간 용역 입찰 데이터가 없습니다.")
        else:
            col_map = {
                "bidNtceNm":   "공고명",
                "ntceInsttNm": "공고기관",
                "bidNtceDt":   "게시일시",
                "bidClseDt":   "마감일시",
                "bidNtceUrl":  "상세링크",
            }
            available = {k: v for k, v in col_map.items() if k in df_raw.columns}
            df = df_raw[list(available.keys())].rename(columns=available)

            pattern     = "|".join(TARGET_KEYWORDS)
            df_filtered = (
                df[df["공고명"].str.contains(pattern, case=False, na=False, regex=True)]
                .reset_index(drop=True)
            )

            if df_filtered.empty:
                st.warning(
                    f"전체 {len(df)}건 조회됐으나 키워드 일치 공고가 없습니다. "
                    "조회 기간을 늘려보세요."
                )
            else:
                st.success(f"🎯 맞춤 공고 **{len(df_filtered)}건** 발견  (전체 조회 {len(df)}건)")

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
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
                    df_filtered.to_excel(writer, index=False, sheet_name="공고목록")
                st.download_button(
                    "📥 엑셀 저장",
                    data=buf.getvalue(),
                    file_name=f"G2B_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
