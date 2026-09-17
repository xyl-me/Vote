"""请求 / 响应模型：User、Survey、Vote 三组。"""
from pydantic import BaseModel, ConfigDict, Field


# ---------------- 用户 ----------------
class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=64)


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


# ---------------- 问卷 ----------------
class SurveyIn(BaseModel):
    title: str = Field(min_length=1, max_length=100)


class SurveyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    creator_id: int


# ---------------- 投票 ----------------
class CastIn(BaseModel):
    option: str = Field(min_length=1, max_length=50)


class VoteOut(BaseModel):
    survey_id: int
    user_id: int
    option: str
    message: str = "投票成功"


class OptionResult(BaseModel):
    option: str
    count: int
    percent: float


class ResultsOut(BaseModel):
    survey_id: int
    title: str
    total: int
    options: list[OptionResult]
