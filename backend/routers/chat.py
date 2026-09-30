from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse
from schemas.chat import ChatRequest
from services.chat_service import chat_service

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", status_code=status.HTTP_200_OK)
async def chat_endpoint(request: ChatRequest) -> StreamingResponse:
    """Streamable chat endpoint to process user messages and stream assistant responses via Server-Sent Events (SSE)."""
    return StreamingResponse(
        chat_service.stream_chat(
            message=request.message,
            session_id=request.session_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
