import streamlit as st
from main import app as langgraph_app

st.set_page_config(page_title="Security Event Handler", layout="centered")
st.title("🔐 보안 이벤트 대응 시뮬레이터")

st.markdown("이벤트를 선택하면 자동으로 심각도를 반영하고 대응 액션을 수행합니다.")

# 1. 이벤트명 선택
event_options = {
    "Access Detected (정상 또는 일반 출입)": "AccessDetected",
    "Unauthorized Access Detected (비인가 출입)": "UnauthorizedAccessDetected"
}
selected_label = st.selectbox("📩 이벤트 유형", list(event_options.keys()))
event = event_options[selected_label]

# 2. 이벤트에 따른 severity 자동 지정
default_severity = "high" if event == "UnauthorizedAccessDetected" else "low"
st.write(f"⚠️ 자동 심각도: **{default_severity.upper()}**")

# 3. 위치 입력
location = st.text_input("📍 출입 위치", "HQ")

# 4. 실행 버튼
if st.button("🚀 대응 시뮬레이션 실행"):
    with st.spinner("시뮬레이션 중..."):
        result = langgraph_app.invoke({
            "event": event,
            "location": location,
            "severity": default_severity
        })
    st.success("✅ 시뮬레이션 완료!")
    st.json(result)
    
    # 5. 요약 출력
    if "summary" in result:
        st.markdown("### 📝 요약 결과")
        st.markdown(result["summary"])
