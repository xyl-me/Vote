"""UI 自动化：注册 / 登录 / 退出。"""
import allure
from playwright.sync_api import expect

from conftest import PASSWORD, register_and_login, register_via_api, unique


@allure.feature("UI-登录注册")
class TestUILogin:

    @allure.story("注册")
    @allure.title("注册成功后进入主面板并显示用户名")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_ui_register_success(self, page, ui_base_url):
        username = unique("ui_reg")
        page.goto(ui_base_url)
        page.fill("#username", username)
        page.fill("#password", PASSWORD)
        page.click("#btn-register")
        expect(page.locator("#msg")).to_contain_text("注册成功")
        expect(page.locator("#main-panel")).to_be_visible()
        expect(page.locator("#auth-panel")).to_be_hidden()
        expect(page.locator("#who")).to_contain_text(username)

    @allure.story("注册")
    @allure.title("重复用户名注册提示失败")
    def test_ui_register_duplicate(self, page, ui_base_url):
        username = register_via_api(ui_base_url)
        page.goto(ui_base_url)
        page.fill("#username", username)
        page.fill("#password", PASSWORD)
        page.click("#btn-register")
        expect(page.locator("#msg")).to_contain_text("注册失败")
        expect(page.locator("#msg")).to_contain_text("已存在")
        expect(page.locator("#main-panel")).to_be_hidden()

    @allure.story("登录")
    @allure.title("登录成功后进入主面板")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_ui_login_success(self, page, ui_base_url):
        username = register_via_api(ui_base_url)
        page.goto(ui_base_url)
        page.fill("#username", username)
        page.fill("#password", PASSWORD)
        page.click("#btn-login")
        expect(page.locator("#msg")).to_contain_text("登录成功")
        expect(page.locator("#main-panel")).to_be_visible()
        expect(page.locator("#who")).to_contain_text(username)

    @allure.story("登录")
    @allure.title("密码错误提示登录失败且停留在认证面板")
    def test_ui_login_wrong_password(self, page, ui_base_url):
        username = register_via_api(ui_base_url)
        page.goto(ui_base_url)
        page.fill("#username", username)
        page.fill("#password", "wrong-password-123")
        page.click("#btn-login")
        expect(page.locator("#msg")).to_contain_text("登录失败")
        expect(page.locator("#main-panel")).to_be_hidden()

    @allure.story("退出")
    @allure.title("退出登录后回到认证面板")
    def test_ui_logout(self, page, ui_base_url):
        register_and_login(page, ui_base_url)
        page.click("#btn-logout")
        expect(page.locator("#auth-panel")).to_be_visible()
        expect(page.locator("#main-panel")).to_be_hidden()
        expect(page.locator("#msg")).to_have_text("")
