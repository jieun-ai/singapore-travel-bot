import streamlit as st
from anthropic import Anthropic
from datetime import datetime
import json
import os
from pathlib import Path

# ===== 페이지 설정 =====
st.set_page_config(
    page_title="🇸🇬 싱가포르 여행 도우미",
    page_icon="🇸🇬",
    layout="centered",
)

# ===== 싱가포르 시간 =====
from datetime import timezone, timedelta
SGT = timezone(timedelta(hours=8))

# ===== 여행 일정 데이터 로드 =====
@st.cache_data
def load_trip_data():
    with open("trip_data.md", "r", encoding="utf-8") as f:
        return f.read()

TRIP_DATA = load_trip_data()

# ===== 시스템 프롬프트 =====
def get_system_prompt():
    now_sgt = datetime.now(SGT)
    now_str = now_sgt.strftime("%Y-%m-%d %A %H:%M")
    return f"""너는 싱가포르 여행 전문 AI 도우미야. 사용자의 여행을 실시간으로 돕는 것이 역할이다.

## 현재 싱가포르 시간
{now_str}

## 사용자의 여행 일정
{TRIP_DATA}

## 너의 역할과 행동 원칙
1. **현실적이고 구체적인 답변**: 이동시간, 거리, 영업시간 등을 정확하게 알려줘
2. **일정 변경 제안 가능**: 사용자가 피곤하거나 시간이 남으면 적극적으로 대안을 제시
3. **한국어로 대답**: 사용자는 한국인이다
4. **짧고 명확하게**: 여행 중이라 긴 글은 읽기 힘들다. 핵심만 전달
5. **현지 팁 공유**: 환전, MRT 카드, 더위 대처, 화장실 위치 등 실용 정보
6. **맛집/장소는 구체적 정보**: 주소, 가격대, 영업시간, 예약 필요 여부까지
7. **모르면 모른다고**: 추측하지 말고 "확실치 않아요, 구글에서 확인해보세요"

## 이동수단 참고 (주요 구간)
- Hotel Waterloo → Gardens by the Bay: MRT로 약 15분 (Bras Basah → Bayfront)
- Hotel Waterloo → Botanic Gardens: MRT로 약 20분
- Clarke Quay → Marina Bay Sands: MRT 7분, 도보 20~25분
- Chinatown → Jewel Changi: MRT로 약 40~50분
- 도보 1km = 약 15분 (단, 더위 고려하면 체감 20분)

## 답변 스타일
- 이모지는 적당히 사용 (너무 많이 쓰지 않기)
- 목록/표를 활용해서 빠르게 스캔 가능하게
- 시간이 급한 상황이면 결론부터, 여유 있으면 선택지 제시
"""

# ===== 대화 기록 저장/로드 =====
HISTORY_FILE = "chat_history.json"

def save_history(messages):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def load_history():
    if Path(HISTORY_FILE).exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

# ===== Anthropic 클라이언트 =====
def get_client():
    api_key = st.secrets.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        st.error("API 키가 설정되지 않았어요. Streamlit Secrets에 ANTHROPIC_API_KEY를 추가해주세요.")
        st.stop()
    return Anthropic(api_key=api_key)

# ===== UI =====
st.title("🇸🇬 싱가포르 여행 도우미")
st.caption(f"현지시간: {datetime.now(SGT).strftime('%Y-%m-%d %H:%M')} (SGT)")

# 사이드바
with st.sidebar:
    st.header("⚙️ 설정")
    if st.button("🗑️ 대화 기록 초기화"):
        st.session_state.messages = []
        save_history([])
        st.rerun()
    st.divider()
    st.markdown("### 💡 이렇게 물어보세요")
    st.markdown("""
    - 지금 시간에 뭐 할지 추천해줘
    - 클락키에서 MBS까지 얼마나 걸려?
    - 라우파삿에서 뭐 먹는게 좋아?
    - 일정이 너무 빡빡해, 하나 빼줘
    - 비 오면 대체 일정 줘
    - 환전은 어디서 해야 해?
    """)
    st.divider()
    st.caption("Claude Haiku 4.5 모델 사용")

# 세션 초기화
if "messages" not in st.session_state:
    st.session_state.messages = load_history()

# 기존 대화 렌더링
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 입력
if prompt := st.chat_input("질문을 입력하세요... (예: 지금 시간 남는데 뭐 할까?)"):
    # 사용자 메시지 추가
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # AI 응답
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""

        try:
            client = get_client()
            with client.messages.stream(
                model="claude-haiku-4-5",
                max_tokens=2048,
                system=get_system_prompt(),
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
            ) as stream:
                for text in stream.text_stream:
                    full_response += text
                    placeholder.markdown(full_response + "▌")
            placeholder.markdown(full_response)
        except Exception as e:
            full_response = f"⚠️ 에러 발생: {str(e)}"
            placeholder.error(full_response)

    # 저장
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    save_history(st.session_state.messages)
