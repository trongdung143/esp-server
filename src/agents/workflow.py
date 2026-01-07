from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver

from src.agents.state import State
from src.agents.chat.chat import ChatAgent
from src.db.redis_operation import ClientRedis
from src.agents.wake_word import check_wake_word

VALID_AGENTS = ["chat"]


async def route(state: State):
    redis = ClientRedis(state.get("client_id"))
    is_sleep = await redis.get_is_sleep()
    if is_sleep:
        return "check_wake_word"
    return "chat"


def start(state: State) -> State:
    return state


def end(state: State) -> State:
    # print(state.get("messages"))
    return state


chat = ChatAgent()
workflow = StateGraph(State)


workflow.add_node("start", start)
workflow.add_node("end", end)
workflow.add_node("chat", chat.process)
workflow.add_node("check_wake_word", check_wake_word)
workflow.set_entry_point("start")
workflow.add_conditional_edges(
    "start", route, {"check_wake_word": "check_wake_word", "chat": "chat"}
)

workflow.add_edge("chat", "end")
workflow.add_edge("check_wake_word", "end")

graph = workflow.compile()  # checkpointer=MemorySaver())
