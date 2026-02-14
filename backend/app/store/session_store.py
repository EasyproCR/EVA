from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.memory import Memory

class SessionStore:

    def __init__(self, llm, tools, session_id: str):

        self.memory = Memory.from_defaults(
            session_id=session_id,
            token_limit=20000
        )

        self.agent = FunctionAgent(
            llm=llm,
            tools=tools
        )

    def get_agent(self):
        return self.agent

    def get_memory(self):
        return self.memory

    async def run(self, message: str):
        return await self.agent.run(
            message,
            memory=self.memory
        )

    async def clear_memory(self):
        await self.memory.reset()   
