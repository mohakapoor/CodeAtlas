from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs before the server starts accepting requests
    print("Loading Embedding models and initializing vectorstore...")
    
    from src.chat import CodeAtlasChat
    app.state.chat_engine = CodeAtlasChat()
    
    print("Ready!")
    yield
    # Clean up on shutdown
    print("Shutting down")

app = FastAPI(
    title="CodeAtlas API",
    description="Agentic Engineering Assistant Backend",
    version="0.1.0",
    lifespan=lifespan
)

# Allow CORS for potential Streamlit or React frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    # Make sure to run this file from the root directory: python -m src.api.main
    uvicorn.run("src.api.main:app", host="127.0.0.1", port=5000, reload=True)
