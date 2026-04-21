import os
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

load_dotenv()

app = FastAPI(title="Multi-Tenant RAG Inference API")

embeddings = HuggingFaceEmbeddings(
    model_name="nomic-ai/nomic-embed-text-v1.5", 
    model_kwargs={'trust_remote_code': True}
)

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.5
)

# --- Schema ---
class MessageDict(BaseModel):
    role: str
    content: str

class QueryRequest(BaseModel):
    query: str
    chat_history: List[MessageDict] = []

# --- Cloud Database Routing ---
def get_vector_store(client_id: str):
    """Connects to Pinecone and restricts queries to the specific client's namespace."""
    return PineconeVectorStore(
        index_name=os.getenv("PINECONE_INDEX_NAME"),
        embedding=embeddings,
        namespace=client_id
    )

def format_docs(docs):
    return "\n\n".join([doc.page_content for doc in docs])

# --- Endpoints ---
@app.post("/api/v1/{client_id}/query")
async def query_data(client_id: str, request: QueryRequest):
    try:
        formatted_history = []
        for msg in request.chat_history:
            if msg.role == "user":
                formatted_history.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                formatted_history.append(AIMessage(content=msg.content))

        # Access Cloud Vector Store
        vector_store = get_vector_store(client_id)
        retriever = vector_store.as_retriever(search_kwargs={"k": 4})

        # 1. Memory Contextualization
        condense_q_system_prompt = (
            "Given a chat history and the latest user question "
            "which might reference context in the chat history, "
            "formulate a standalone question which can be understood "
            "without the chat history. Do NOT answer the question, "
            "just reformulate it if needed and otherwise return it as is."
        )
        condense_q_prompt = ChatPromptTemplate.from_messages([
            ("system", condense_q_system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{user_query}"),
        ])
        
        def contextualize_question(input_dict):
            if input_dict.get("chat_history"):
                chain = condense_q_prompt | llm | StrOutputParser()
                return chain.invoke(input_dict)
            return input_dict["user_query"]

        # 2. Strict QA Prompt
        qa_system_prompt = """You are a highly accurate AI assistant acting on behalf of a specific company. 
        
        CRITICAL INSTRUCTION: You must answer the user's question relying EXCLUSIVELY on the Context provided below. You are strictly forbidden from using any outside factual knowledge or assumptions.
        
        If the user asks you to format, shorten, summarize, or elaborate, you must do so using ONLY the provided Context.
        
        If the Context below does not contain the facts needed to address the user's core topic, you MUST reply with this exact phrase: "I don't know based on the provided documentation."
        
        Context:
        {context}"""
        
        qa_prompt = ChatPromptTemplate.from_messages([
            ("system", qa_system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{user_query}"),
        ])
        
        # 3. Chain Execution
        rag_chain = (
            RunnablePassthrough.assign(
                context=RunnableLambda(contextualize_question) | retriever | format_docs
            )
            | qa_prompt
            | llm
            | StrOutputParser()
        )
        
        response = rag_chain.invoke({
            "user_query": request.query,
            "chat_history": formatted_history
        })

        return {"answer": response}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))