"""认证接口：注册 / 登录 / 鉴权。"""
import os
from datetime import datetime, timedelta, timezone

import allure
import jwt
import pytest

from conftest import Client, new_user, unique

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me-at-least-32-bytes!")


@allure.feature("认证接口")
class TestAuth:

    @allure.story("注册")
    @allure.title("注册成功返回 token，且可访问 /auth/me")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_register_success(self, client):
        username = unique("user")
        resp = client.register(username=username)
        assert resp.status_code == 201
        assert resp.json()["access_token"]
        body = client.me().json()
        assert body["username"] == username
        assert isinstance(body["id"], int)
        assert "password" not in body  # 响应不回显密码

    @allure.story("注册")
    @allure.title("重复用户名注册返回 409")
    def test_register_duplicate_username(self, client):
        username = unique("dup")
        assert client.register(username=username).status_code == 201
        again = Client(client.base_url).register(username=username)
        assert again.status_code == 409
        assert "已存在" in again.json()["detail"]

    @allure.story("注册")
    @allure.title("用户名不合法（{username!r}）返回 422")
    @pytest.mark.parametrize("username", ["", "ab", "u" * 51])
    def test_register_invalid_username(self, client, username):
        assert client.register(username=username).status_code == 422

    @allure.story("注册")
    @allure.title("密码长度不合法返回 422")
    @pytest.mark.parametrize("password", ["", "12345", "p" * 65])
    def test_register_invalid_password(self, client, password):
        assert client.register(password=password).status_code == 422

    @allure.story("登录")
    @allure.title("登录成功返回可用的 token")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_login_success(self, base_url):
        owner = new_user(base_url)
        fresh = Client(base_url)
        resp = fresh.login(owner.username, owner.password)
        assert resp.status_code == 200 and resp.json()["access_token"]
        assert fresh.me().json()["username"] == owner.username

    @allure.story("登录")
    @allure.title("密码错误返回 401")
    def test_login_wrong_password(self, base_url):
        owner = new_user(base_url)
        resp = Client(base_url).login(owner.username, "wrong-password")
        assert resp.status_code == 401
        assert resp.json()["detail"] == "用户名或密码错误"

    @allure.story("登录")
    @allure.title("用户不存在返回 401（不泄露用户是否存在）")
    def test_login_unknown_user(self, client):
        resp = client.login("ghost_user_0000", "secret123")
        assert resp.status_code == 401
        assert resp.json()["detail"] == "用户名或密码错误"

    @allure.story("鉴权")
    @allure.title("无 token 访问受保护接口返回 401")
    @pytest.mark.parametrize("method, path", [
        ("GET", "/auth/me"), ("POST", "/vote/create"),
        ("POST", "/vote/1/cast"), ("GET", "/vote/1/results"),
    ])
    def test_anonymous_401(self, client, method, path):
        assert client.request(method, path, json={}).status_code == 401

    @allure.story("鉴权")
    @allure.title("过期 token 返回 401")
    def test_expired_token_401(self, client):
        expired = jwt.encode(
            {"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(minutes=5)},
            JWT_SECRET, algorithm="HS256")
        client.token = expired
        assert client.me().status_code == 401

    @allure.story("鉴权")
    @allure.title("伪造签名的 token 返回 401")
    def test_forged_token_401(self, client):
        forged = jwt.encode({"sub": "1", "username": "hacker"},
                            "attacker-secret-key-with-32-bytes!!", algorithm="HS256")
        client.token = forged
        assert client.me().status_code == 401
