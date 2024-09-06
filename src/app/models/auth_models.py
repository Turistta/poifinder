from typing import Annotated, List, Optional

from pydantic import BaseModel
from wtforms import Field


class Token(BaseModel):
    access_token: Annotated[str, Field()]
    token_type: Annotated[str, Field()]


class TokenData(BaseModel):
    username: Annotated[Optional[str], Field(default=None)]
    scopes: Annotated[List[str], Field(default=[])]


class Client(BaseModel):
    name: Annotated[str, Field()]
