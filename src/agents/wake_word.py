from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.messages import RemoveMessage, AIMessage

from src.config.setup import GOOGLE_API_KEY
from src.agents.state import State
from src.db.redis_operation import ClientRedis

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            Khi người dùng gọi bạn là {wake_word}.

            Nếu người dùng gọi bạn thì bạn đáp lại. Nếu không thì chỉ trả ra một từ duy nhất là 'false'
            """,
        ),
        (
            "user",
            """
            Người dùng nói:
            {user_wake_word}
            """,
        ),
    ]
)


model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=GOOGLE_API_KEY,
    disable_streaming=True,
)

chain = prompt | model


async def check_wake_word(state: State) -> State:
    redis = ClientRedis(state.get("client_id"))
    last_message = state.get("messages")[-1]
    user_wake_word = last_message.content
    wake_word = await redis.get_wake_word()
    message_id = last_message.id
    response = await chain.ainvoke(
        {"wake_word": wake_word, "user_wake_word": user_wake_word}
    )
    if response.content.strip() == "false":
        state.update(messages=[RemoveMessage(id=message_id)])
    else:
        state.update(messages=[AIMessage(content=response.content.strip())])
    return state
