from pydantic import BaseModel
from typing import Optional


class ForeignWord(BaseModel):
    id: int
    page_id: int
    word: str
    count: int
    language_guess: Optional[str] = None

    class Config:
        from_attributes = True


class ForeignWordResponse(BaseModel):
    word: str
    count: int
    language_guess: Optional[str] = None