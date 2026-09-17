"""UI 自动化夹具：复用 pytest-playwright 的 page，补齐服务可达性检查与登录辅助。"""
import os
import uuid

import pytest
import requests

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
PASSWORD = "secret123"


def unique(prefix: str = "ui") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="session")
def ui_base_url() -> str:
    """前端地址（环境变量 BASE_URL 可覆盖）；服务不可达则跳过 UI 套件。"""
    url = os.getenv("BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    try:
        requests.get(f"{url}/health", timeout=3)
    except Exception:
        pytest.skip(f"被测服务不可达：{url}", allow_module_level=True)
    return url


def register_via_api(base_url: str, username: str = None) -> str:
    """用接口造用户（UI 用例里避免重复走注册流程）。"""
    username = username or unique("ui")
    resp = requests.post(f"{base_url}/auth/register",
                         json={"username": username, "password": PASSWORD}, timeout=10)
    assert resp.status_code == 201, resp.text
    return username


def register_and_login(page, base_url: str) -> str:
    """通过页面完成注册并登录，返回用户名。"""
    username = unique("ui_user")
    page.goto(base_url)
    page.fill("#username", username)
    page.fill("#password", PASSWORD)
    page.click("#btn-register")
    page.wait_for_selector("#main-panel", state="visible")
    return username


def login_via_ui(page, base_url: str, username: str, password: str = PASSWORD) -> None:
    page.goto(base_url)
    page.fill("#username", username)
    page.fill("#password", password)
    page.click("#btn-login")
