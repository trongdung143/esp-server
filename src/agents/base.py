from typing import Sequence

from langchain_core.tools.base import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph

from src.agents.state import State
from src.config.setup import GOOGLE_API_KEY


class BaseAgent:
    def __init__(
        self,
        agent_name: str,
        state: type[State] = State,
        tools: Sequence[BaseTool] | None = None,
    ):

        self._tools = list(tools or [])
        self._agent_name = agent_name

        self._model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=GOOGLE_API_KEY,
            disable_streaming=False,
        ).bind_tools(self._tools)

        self._sub_graph = StateGraph(state)

    async def process(self, state: State) -> State:
        return state

    def _set_subgraph(self):
        pass

    def get_subgraph(self) -> CompiledStateGraph:
        return self._sub_graph.compile(name=self._agent_name)
