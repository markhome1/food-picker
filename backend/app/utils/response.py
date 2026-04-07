from typing import Optional, Union, List, Dict
from sqlmodel import SQLModel


class ApiResponse(SQLModel):
    code: int = 200
    message: str = "ok"
    data: Optional[Union[Dict, List]] = None
