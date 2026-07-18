import os
from fastapi import APIRouter, HTTPException, Request, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.api.schemas import ChatRequest, ChatResponse

router = APIRouter()
security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verifies the Bearer token against the API_KEY environment variable.
    """
    expected_token = os.getenv("API_KEY")
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API_KEY environment variable is not set."
        )
        
    if credentials.credentials != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

@router.get("/health")
def health_check():
    """Unauthenticated health endpoint."""
    return {"status": 200}

@router.get("/status", dependencies=[Depends(verify_token)])
def status_endpoint(request: Request):
    """Authenticated status endpoint returning model and retriever info."""
    chat_engine = getattr(request.app.state, "chat_engine", None)
    if not chat_engine:
        raise HTTPException(status_code=503, detail="Engine not ready")
        
    return {
        "version": request.app.version,
        "model": "gemini-2.5-flash",  # Default used in CodeAtlasChat
        "retriever": chat_engine.retriever.__class__.__name__
    }

@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_token)])
def chat_endpoint(request: Request, chat_request: ChatRequest):
    """Authenticated RAG chat endpoint."""
    chat_engine = getattr(request.app.state, "chat_engine", None)
    if chat_engine is None:
        raise HTTPException(status_code=503, detail="CodeAtlasChat engine is still initializing.")
        
    try:
        response = chat_engine.ask(chat_request.query)
        return ChatResponse(
            answer=response.get("answer", "No answer generated."),
            sources=response.get("sources", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
