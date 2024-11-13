from pydantic import BaseModel, Field
from typing import Optional


class LoginInput(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Username of the user")
    password: str = Field(..., description="Password of the user")