from pydantic import BaseModel


class RequestTokenBody(BaseModel):
    request_token: str


class MessageResponse(BaseModel):
    message: str
