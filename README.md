# Legal Intelligence Engine

A multi-tenant, cloud-native Retrieval-Augmented Generation (RAG) system designed to act as an automated, 24/7 paralegal and lead qualification tool for high-volume law firms.

## Architecture
* **Frontend:** Streamlit Community Cloud (with dynamic URL routing per client)
* **Backend:** FastAPI on Render
* **Vector Database:** Pinecone
* **LLM Core:** Llama-3.1-8b via Groq API
* **Embeddings:** Nomic-Embed-Text via HuggingFace

## Features
* **Strict Data Grounding:** Prevents hallucinated legal advice; refuses questions outside of the ingested firm's proprietary data.
* **Contextual Memory:** Handles multi-turn conversational follow-ups.
* **Namespace Isolation:** Mathematically partitions firm data preventing cross-contamination.
