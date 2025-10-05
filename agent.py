import os
from typing import TypedDict
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langchain_google_genai.chat_models import ChatGoogleGenerativeAI

load_dotenv()

llm = ChatGoogleGenerativeAI(api_key = os.getenv('api_key'), model = 'gemini-2.5-flash')

class ChatGraph(TypedDict):
    user_query: str
    llm_response: str

graph = StateGraph(ChatGraph)

def generate_chat(state: ChatGraph) -> ChatGraph:
    query = state['user_query']
    prompt = f'You are helpful assitant. Reply the answer of question: {query} in markdown format in max 100 words'
    state['llm_response'] = llm.invoke(prompt).content
    return state


graph.add_node('generate', generate_chat)

graph.add_edge(START, 'generate')
graph.add_edge('generate', END)

agent_run = graph.compile()