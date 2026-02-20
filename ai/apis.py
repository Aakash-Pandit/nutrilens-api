import uuid

from fastapi import Depends, status

from ai.models import QNARequestBody, QNAResponseBody
from application.app import app
from auth.dependencies import require_authenticated_user
from database.db import get_db


@app.post(
    "/ai_assistant",
    status_code=status.HTTP_200_OK,
    summary="Chat with Documents",
    response_description="Answer from the AI",
)
async def ai_assistant(
    request: QNARequestBody,
    current_user=Depends(require_authenticated_user),
) -> QNAResponseBody:
    """
    Payload for the endpoint:
    {
        "question": "give me date of birth of Dr. ruso lamba"
    }
    """
    session_id = request.session_id or str(uuid.uuid4())
    user_id = current_user.user_id if current_user else None
    return {
        "question": request.question,
        # "response": result["response"],
        # "session_id": result.get("session_id") or session_id,
        # "messages": result.get("messages"),
    }

