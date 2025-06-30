import streamlit as st
from main import app

st.title("🚨 보안 이벤트 대응 시스템")

event_type = st.selectbox("📩 이벤트명", ["AccessDetected", "UnauthorizedAccessDetected"])
severity = "high" if event_type == "UnauthorizedAccessDetected" else "low"
location = st.text_input("📍 위치", "HQ")

if st.button("이벤트 전송"):
    with st.spinner("처리 중..."):
        result = app.invoke({"event": event_type, "severity": severity, "location": location})
        st.success(f"✅ 결과 상태: {result.get('status')}")
        if "llm_summary" in result:
            st.markdown(f"🧠 **LLM 요약:** {result['llm_summary']}")