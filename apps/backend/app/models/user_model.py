from datetime import datetime
from importlib.util import find_spec
from typing import Optional

from pydantic import BaseModel, Field

if find_spec("email_validator") is not None:
    from pydantic import EmailStr as EmailField
else:
    EmailField = str

class User(BaseModel):
    id: Optional[str] = None
    email: EmailField = Field(..., min_length=3, max_length=254)
    name: str
    created_at: datetime

class UserInDB(User):
    hashed_password: str

