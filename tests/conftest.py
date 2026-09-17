"""接口测试夹具：base_url / client / user / survey。

前置条件：被测服务已在运行（docker compose up -d 或 uvicorn app.main:app）。
数据隔离靠"每个用例独立注册用户"，因此不做数据清理。
"""
import os
import uuid

import pytest
import requests

DEFAULT_BASE_URL = "http://127.0.0.1:8000"


def unique(prefix: str) -> str:
    """随机后缀，避免用例之间撞用户名。"""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


class Client:
    """requests.Session 的薄封装：自动注入 token，附少量业务便捷方法。"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.token = None
        self.username = None
        self.password = "secret123"

    # ---------------- 底层 ----------------
    def request(self, method: str, path: str, **kwargs):
        url = path if path.startswith("http") else self.base_url + path
        headers = dict(kwargs.pop("headers", None) or {})
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return self.session.request(method, url, headers=headers, timeout=10, **kwargs)

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)

    # ---------------- 业务 ----------------
    def register(self, username=None, password=None):
        self.username = username if username is not None else unique("user")
        self.password = password if password is not None else self.password
        resp = self.post("/auth/register",
                         json={"username": self.username, "password": self.password})
        if resp.status_code == 201:
            self.token = resp.json()["access_token"]
        return resp

    def login(self, username=None, password=None):
        resp = self.post("/auth/login", json={
            "username": username if username is not None else self.username,
            "password": password if password is not None else self.password})
        if resp.status_code == 200:
            self.token = resp.json()["access_token"]
        return resp

    def me(self):
        return self.get("/auth/me")

    def create_survey(self, title=None):
        payload = {"title": title if title is not None else unique("问卷")}
        return self.post("/vote/create", json=payload)

    def cast(self, survey_id, option):
        return self.post(f"/vote/{survey_id}/cast", json={"option": option})

    def results(self, survey_id):
        return self.get(f"/vote/{survey_id}/results")


def new_user(base_url: str, password: str = "secret123") -> Client:
    """快捷造一个已登录用户（多用户场景用）。"""
    client = Client(base_url)
    assert client.register(password=password).status_code == 201
    assert client.login().status_code == 200
    return client


# ---------------------------------------------------------------- fixtures
@pytest.fixture(scope="session")
def base_url() -> str:
    """被测服务地址（可用环境变量 BASE_URL 覆盖）。"""
    url = os.getenv("BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    try:
        requests.get(f"{url}/health", timeout=3)
    except Exception:
        pytest.exit(f"\n被测服务不可达：{url}\n请先启动服务：docker compose up -d"
                    f"  或  uvicorn app.main:app", returncode=1)
    return url


@pytest.fixture
def client(base_url) -> Client:
    """未登录的会话。"""
    return Client(base_url)


@pytest.fixture
def user(client) -> Client:
    """已注册并登录、token 已注入的会话。"""
    assert client.register().status_code == 201
    assert client.login().status_code == 200
    return client


@pytest.fixture
def survey(user) -> dict:
    """创建一份问卷并返回其信息（不清理，靠用户隔离）。"""
    resp = user.create_survey()
    assert resp.status_code == 201, resp.text
    return resp.json()
