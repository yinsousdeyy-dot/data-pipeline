

from datetime import datetime
from typing import Optional 
from pydantic import BaseModel, EmailStr, Field, field_validator

class OrderRecordModel(BaseModel):
    """Data contrast for e-commerce order records"""

    order_id: str = Field(... , min_lenght=1)
    customer_id: int = Field(... , gt=0)
    customer_email: EmailStr 
    amount : float = Field(..., ge=0.0, description = " Order amoutn cannot be negative ")
    status : str
    order_timestamp: datetime

    @field_validator("customer_email", mode = "before")
    @classmethod
    def normalize_email(cls, value:str)-> str:
        if isinstance(value, str): 
            return value.strip().lower() 
        return value 

    @field_validator("status", mode = "before") 
    @classmethod
    def normalied_status(cls, value: Optional[str])-> str:
        if not value or not str(value).strip():
            return "Unknown"
        return str(value).strip().upper()