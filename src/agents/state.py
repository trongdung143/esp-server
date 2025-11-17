from langchain.agents import AgentState


class State(AgentState):
    client_id: str
