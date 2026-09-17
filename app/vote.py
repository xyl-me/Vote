"""投票核心 3 个接口：创建问卷 / 投票 / 查看结果。

防重复：数据库唯一约束 uq_vote_once(survey_id, user_id) —— 先查后插，并发时由唯一约束兜底。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import schemas
from .auth import current_user
from .models import Survey, User, Vote, get_db

router = APIRouter(prefix="/vote", tags=["vote"])


@router.post("/create", response_model=schemas.SurveyOut, status_code=201)
def create_survey(body: schemas.SurveyIn, user: User = Depends(current_user),
                  db: Session = Depends(get_db)):
    """创建问卷（登录即可）。"""
    survey = Survey(title=body.title, creator_id=user.id)
    db.add(survey)
    db.commit()
    return survey


@router.post("/{survey_id}/cast", response_model=schemas.VoteOut)
def cast_vote(survey_id: int, body: schemas.CastIn, user: User = Depends(current_user),
              db: Session = Depends(get_db)):
    """投票：问卷不存在 404；已投过 409；成功 200。"""
    if db.get(Survey, survey_id) is None:
        raise HTTPException(404, "问卷不存在")
    voted = db.scalar(select(Vote.id).where(Vote.survey_id == survey_id,
                                            Vote.user_id == user.id).limit(1))
    if voted is not None:
        raise HTTPException(409, "你已经投过票了")
    db.add(Vote(survey_id=survey_id, user_id=user.id, option=body.option))
    try:
        db.commit()
    except IntegrityError:  # 并发穿透时由唯一约束拦下
        db.rollback()
        raise HTTPException(409, "你已经投过票了")
    return schemas.VoteOut(survey_id=survey_id, user_id=user.id, option=body.option)


@router.get("/{survey_id}/results", response_model=schemas.ResultsOut)
def results(survey_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """结果：按选项聚合票数与百分比，按票数倒序。"""
    survey = db.get(Survey, survey_id)
    if survey is None:
        raise HTTPException(404, "问卷不存在")
    rows = db.execute(select(Vote.option, func.count(Vote.id))
                      .where(Vote.survey_id == survey_id)
                      .group_by(Vote.option)).all()
    total = sum(count for _option, count in rows)
    options = [schemas.OptionResult(
        option=option, count=count,
        percent=round(count * 100 / total, 2) if total else 0.0)
        for option, count in sorted(rows, key=lambda row: (-row[1], row[0]))]
    return schemas.ResultsOut(survey_id=survey_id, title=survey.title, total=total,
                              options=options)
