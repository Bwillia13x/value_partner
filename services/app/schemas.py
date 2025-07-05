from pydantic import BaseModel
from typing import List, Optional

class StrategyHoldingBase(BaseModel):
    symbol: str
    target_weight: float

class StrategyHoldingCreate(StrategyHoldingBase):
    pass

class StrategyHolding(StrategyHoldingBase):
    id: int
    strategy_id: int

    class Config:
        orm_mode = True

class StrategyBase(BaseModel):
    name: str
    description: Optional[str] = None

class StrategyCreate(StrategyBase):
    holdings: List[StrategyHoldingCreate]

class Strategy(StrategyBase):
    id: int
    user_id: int
    holdings: List[StrategyHolding] = []

    class Config:
        orm_mode = True


# --- User Schemas ---

class UserBase(BaseModel):
    email: str
    name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    strategies: List[Strategy] = []

    class Config:
        orm_mode = True


# --- Token Schemas ---

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
