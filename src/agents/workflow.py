from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver

from src.agents.state import State
from src.agents.chat.chat import ChatAgent

VALID_AGENTS = ["chat"]


def start(state: State) -> State:
    return state


def end(state: State) -> State:
    return state


chat = ChatAgent()
workflow = StateGraph(State)


workflow.add_node("start", start)
workflow.add_node("end", end)
workflow.add_node("chat", chat.process)
workflow.set_entry_point("start")
workflow.add_edge("start", "chat")
workflow.add_edge("chat", "end")

graph = workflow.compile(checkpointer=MemorySaver())
