from rdflib import Graph, Namespace
from langgraph.graph import StateGraph
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()

llm = ChatOpenAI(model="gpt-4o", temperature=0.3)

ONTOLOGY_PATH = "security_ontology.ttl"
g = Graph()
g.parse(ONTOLOGY_PATH, format="turtle")

def receive_event(state):
    print(f"📩 Event received: {state['event']}")
    return state

def reason_action(state):
    event = state.get("event")
    severity = state.get("severity", "low")

    print(f"🧪 Reasoning for event={event}, severity={severity}")
    query = f"""
    PREFIX : <http://example.org/security#>
    SELECT ?action ?impl WHERE {{
      ?rule :triggers ?action .
      ?rule :hasSeverity "{severity}" .
      ?rule :eventName "{event}" .
      ?action :hasImplementation ?impl .
    }}
    """
    result = g.query(query)
    for row in result:
        return {
            **state,
            "action_uri": str(row.action),
            "action_impl": str(row.impl)
        }
    return {**state, "status": "no_action"}

def execute_action(state):
    impl = state.get("action_impl")
    if impl == "lockdown.activate":
        print("🔒 Lockdown procedure activated.")
        summary = llm.invoke("비인가된 출입이 감지되었습니다. 높은 심각도로 판단하여 잠금 조치를 수행했습니다.")
        return {"status": "locked_down", "llm_summary": summary.content}
    elif impl == "alert.access":
        print("📢 Access alert issued.")
        summary = llm.invoke("정상 출입이 감지되었습니다. 알림 조치를 수행했습니다.")
        return {"status": "alerted", "llm_summary": summary.content}
    else:
        print("⚠️ No matching action implementation found.")
        return {"status": "no_action"}

builder = StateGraph(dict)
builder.add_node("receive_event", RunnableLambda(receive_event))
builder.add_node("reason_action", RunnableLambda(reason_action))
builder.add_node("execute_action", RunnableLambda(execute_action))
builder.set_entry_point("receive_event")
builder.add_edge("receive_event", "reason_action")
builder.add_edge("reason_action", "execute_action")
builder.set_finish_point("execute_action")
app = builder.compile()

if __name__ == "__main__":
    result = app.invoke({"event": "AccessDetected", "location": "HQ", "severity": "low"})
    print("✅ FINAL RESULT:", result)