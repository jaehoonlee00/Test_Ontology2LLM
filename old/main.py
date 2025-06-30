import os
from rdflib import Graph
from langgraph.graph import StateGraph
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# .env 로딩
load_dotenv()

# LLM 초기화
def init_llm():
    return ChatOpenAI(model="gpt-4o", temperature=0.3)

llm = init_llm()

# ==== 온톨로지 로딩 및 질의 ====
ONTOLOGY_PATH = "security_ontology.ttl"
g = Graph()
g.parse(ONTOLOGY_PATH, format="turtle")

# ==== 액션 실행 함수 정의 ====
def lockdown_activate(state):
    print(f"🔒 Lockdown procedure activated at {state.get('location', 'UNKNOWN')}!")
    return {"status": "locked_down"}

def alert_access(state):
    print(f"🔔 Alert issued for access event at {state.get('location', 'UNKNOWN')}!")
    return {"status": "alert_sent"}

# ==== LangGraph 노드 ====
def receive_event(state):
    print(f"📩 Event received: {state['event']}")
    return {
        "event": state["event"],
        "location": state.get("location", "HQ"),
        "severity": state.get("severity", "low")
    }

def reason_action(state):
    event = state["event"]
    severity = state["severity"]
    print(f"🧪 Reasoning for event={event}, severity={severity}")

    query = f"""
    PREFIX : <http://example.org/security#>
    SELECT ?action ?impl WHERE {{
        ?rule :eventName "{event}" .
        ?rule :hasSeverity "{severity}" .
        ?rule :triggers ?action .
        ?action :hasImplementation ?impl .
    }}
    """
    results = g.query(query)
    for row in results:
        print(f"🔍 Action matched: {row.action}, impl={row.impl}")
        return {
            **state,
            "action_uri": str(row.action),
            "action_impl": str(row.impl)
        }

    return {**state, "status": "no_action"}

def execute_action(state):
    impl = state.get("action_impl")
    if impl == "lockdown.activate":
        return lockdown_activate(state)
    elif impl == "alert.access":
        return alert_access(state)
    else:
        print("⚠️ No matching action implementation found.")
        return {"status": "no_action"}

def summarize(state):
    action_result = state.get("status", "")
    severity = state.get("severity", "")
    event = state.get("event", "")

    if action_result == "locked_down":
        prompt = f"비인가 출입({event})이 감지되었고, 심각도는 {severity}로 판단되었습니다. 이에 따라 잠금 조치가 시행되었습니다. 위 상황을 한 문장으로 요약해주세요."
    elif action_result == "alert_sent":
        prompt = f"출입 감지 이벤트({event})가 발생했습니다. 이는 일반적인 상황이며, 알림 조치(alert.access)가 수행되었습니다. 이 상황을 간결하게 설명해주세요."
    else:
        prompt = f"{event} 이벤트에 대해 별도의 조치는 수행되지 않았습니다. 그 이유를 설명해주세요."

    result = llm.invoke(prompt)
    print("📝 Summary:", result.content)
    return {**state, "summary": result.content}

# ==== LangGraph 생성 ====
builder = StateGraph(dict)
builder.add_node("receive_event", RunnableLambda(receive_event))
builder.add_node("reason_action", RunnableLambda(reason_action))
builder.add_node("execute_action", RunnableLambda(execute_action))
builder.add_node("summarize", RunnableLambda(summarize))

builder.set_entry_point("receive_event")
builder.add_edge("receive_event", "reason_action")
builder.add_edge("reason_action", "execute_action")
builder.add_edge("execute_action", "summarize")
builder.set_finish_point("summarize")

app = builder.compile()

# ==== 실행 예시 ====
if __name__ == "__main__":
    result = app.invoke({
        "event": "AccessDetected",
        "location": "HQ",
        "severity": "low"
    })
    print("✅ FINAL RESULT:", result)