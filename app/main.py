"""应用入口：建表 + 挂载路由与极简前端。"""
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import auth, vote
from .models import Base, engine

STATIC_DIR = Path(__file__).parent / "static"


def init_db(retries: int = 30) -> None:
    """等 MySQL 就绪后建表（首次启动初始化可能需要 30s+）。"""
    for attempt in range(retries):
        try:
            Base.metadata.create_all(engine)
            return
        except Exception as exc:
            if attempt == retries - 1:
                raise
            print(f"[init_db] 数据库未就绪（{exc}），2 秒后重试…")
            time.sleep(2)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Voting System", version="2.0.0", lifespan=lifespan,
              description="极简投票系统：注册登录 / 创建问卷 / 投票 / 查看结果")
app.include_router(auth.router)
app.include_router(vote.router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")
