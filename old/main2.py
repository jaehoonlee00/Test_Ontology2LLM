
from rdflib import Graph
from langgraph.graph import StateGraph
from langchain_core.runnables import RunnableLambda

# ==== 온톨로지 로딩 및 질의 ====
ONTOLOGY_PATH = "D:/Test_Ontology2LangGraph/ontology/security_ontology.ttl"
g = Graph()
g.parse(ONTOLOGY_PATH, format="turtle")

# ==== 액션 실행 함수 ====
def lockdown_activate(context):
    print(f"🔒 Lockdown procedure activated at {context.get('location', 'UNKNOWN')}!")
    return {"status": "locked_down"}

# ==== LangGraph 구성 ====
def receive_event(state):
    print(f"📩 Event received: {state['event']}")
    return {"event": state["event"], "location": state.get("location", "HQ"), "severity": state.get("severity", "low")}

def reason_action(state):
    severity = state.get("severity", "low")
    event_name = state.get("event")

    query = f'''
    PREFIX : <http://example.org/security#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    SELECT ?action ?impl WHERE {{
      ?rule :triggers ?action .
      ?rule :hasSeverity "{severity}"^^xsd:string .
      ?rule :eventName "{event_name}"^^xsd:string .
      ?action :hasImplementation ?impl .
    }}
    '''
    result = g.query(query)
    for row in result:
        return {
            **state,
            "action_uri": str(row.action),
            "action_impl": str(row.impl)
        }
    print("⚠️ No matching action implementation found.")
    return {**state, "status": "no_matching_action"}

def execute_action(state):
    impl = state.get("action_impl")
    if impl == "lockdown.activate":
        return lockdown_activate(state)
    else:
        print("⚠️ No matching action implementation found.")
        return {"status": "no_action"}

# ==== LangGraph 생성 ====
builder = StateGraph(dict)
builder.add_node("receive_event", RunnableLambda(receive_event))
builder.add_node("reason_action", RunnableLambda(reason_action))
builder.add_node("execute_action", RunnableLambda(execute_action))

builder.set_entry_point("receive_event")
builder.add_edge("receive_event", "reason_action")
builder.add_edge("reason_action", "execute_action")
builder.set_finish_point("execute_action")

app = builder.compile()

# ==== 실행 예시 ====
if __name__ == "__main__":
    result = app.invoke({"event": "UnauthorizedAccessDetected", "location": "HQ", "severity": "high"})
    print("✅ FINAL RESULT:", result)
