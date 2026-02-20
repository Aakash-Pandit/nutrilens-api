from pydantic import BaseModel


class QNARequestBody(BaseModel):
    question: str
    session_id: str | None = None


class QNAResponseBody(BaseModel):
    question: str
    response: str
    session_id: str | None = None
    messages: list[dict[str, str]] | None = None
