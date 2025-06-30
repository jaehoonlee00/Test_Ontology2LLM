from rdflib import Graph, Namespace, Literal
from langgraph.graph import StateGraph
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
import os
import getpass
from dotenv import load_dotenv


# .env 로딩
load_dotenv()

# LLM 초기화
def init_llm():
    if not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter OpenAI API Key: ")
    return ChatOpenAI(model="gpt-4o", temperature=0.3)

# 사용
llm = init_llm()

# ==== 온톨로지 로딩 ====
g = Graph()
g.parse("security_ontology.ttl", format="turtle")
SEC = Namespace("http://example.org/security#")


# ==== 노드 함수 정의 ====

def receive_event(state):
    print(f"📩 Event received: {state['event']}")
    return {"event": state["event"], "location": state.get("location", "HQ"), "severity": state.get("severity", "low")}

def reason_action(state):
    event_name = Literal(state["event"])
    severity = Literal(state["severity"])

    print(f"🧪 Querying for eventName={event_name}, severity={severity}")

    for s in g.subjects(predicate=SEC.eventName, object=event_name):
        if (s, SEC.hasSeverity, severity) in g and (s, SEC.triggers, None) in g:
            action_uri = g.value(subject=s, predicate=SEC.triggers)
            action_impl = g.value(subject=action_uri, predicate=SEC.hasImplementation)
            print("🔍 쿼리 결과:")
            print(f"  ▶ ({action_uri}, {action_impl})")
            return {
                **state,
                "action_uri": str(action_uri),
                "action_impl": str(action_impl)
            }

    print("⚠️ No matching action implementation found.")
    return {**state, "status": "no_action"}

def lockdown_activate(state):
    print(f"🔒 Lockdown procedure activated at {state.get('location', 'UNKNOWN')}!")
    return {"status": "locked_down"}

def execute_action(state):
    impl = state.get("action_impl")
    if impl == "lockdown.activate":
        return {**state, **lockdown_activate(state)}
    else:
        print("⚠️ No matching action implementation found.")
        return {**state, "status": "no_action"}

def summarize(state):
    action_result = state.get("status", "")
    severity = state.get("severity", "")
    event = state.get("event", "")

    prompt = f"""
    다음 이벤트에 대한 요약을 작성해 주세요.
    이벤트: {event}
    심각도: {severity}
    조치 결과: {action_result}

    한 문장으로 설명해주세요.
    """

    result = llm.invoke(prompt)
    print("📝 Summary:", result.content)
    return {**state, "summary": result.content}

# ==== LangGraph 구성 ====
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
        "event": "UnauthorizedAccessDetected",
        "location": "HQ",
        "severity": "high"
    })
    print("✅ FINAL RESULT:", result)
