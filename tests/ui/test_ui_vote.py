"""UI 自动化：创建问卷 / 投票 / 查看结果。"""
import allure
from playwright.sync_api import expect

from conftest import register_and_login, unique


def create_survey_via_ui(page) -> str:
    """在页面上创建问卷，返回自动填入的问卷 ID。"""
    page.fill("#survey-title", unique("UI问卷"))
    page.click("#btn-create")
    expect(page.locator("#create-msg")).to_contain_text("创建成功")
    return page.input_value("#survey-id")


@allure.feature("UI-投票流程")
class TestUIVote:

    @allure.story("创建问卷")
    @allure.title("创建问卷成功提示，并把问卷 ID 填入投票区")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_ui_create_survey(self, page, ui_base_url):
        register_and_login(page, ui_base_url)
        survey_id = create_survey_via_ui(page)
        assert survey_id.isdigit()
        expect(page.locator("#create-msg")).to_contain_text(f"问卷 #{survey_id}")

    @allure.story("投票")
    @allure.title("投票成功提示「投票成功」")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_ui_cast_vote(self, page, ui_base_url):
        register_and_login(page, ui_base_url)
        create_survey_via_ui(page)
        page.fill("#option", "A")
        page.click("#btn-cast")
        expect(page.locator("#vote-msg")).to_contain_text("投票成功")

    @allure.story("投票")
    @allure.title("重复投票提示「你已经投过票了」")
    def test_ui_duplicate_vote(self, page, ui_base_url):
        register_and_login(page, ui_base_url)
        create_survey_via_ui(page)
        page.fill("#option", "A")
        page.click("#btn-cast")
        expect(page.locator("#vote-msg")).to_contain_text("投票成功")
        page.fill("#option", "B")
        page.click("#btn-cast")
        expect(page.locator("#vote-msg")).to_contain_text("你已经投过票了")

    @allure.story("结果")
    @allure.title("查看结果展示票数与百分比")
    def test_ui_results(self, page, ui_base_url):
        register_and_login(page, ui_base_url)
        create_survey_via_ui(page)
        page.fill("#option", "A")
        page.click("#btn-cast")
        page.click("#btn-results")
        expect(page.locator("#results")).to_contain_text("共 1 票")
        expect(page.locator("#results")).to_contain_text("A：1 票")

    @allure.story("结果")
    @allure.title("加载问卷显示标题与当前票数")
    def test_ui_load_survey(self, page, ui_base_url):
        register_and_login(page, ui_base_url)
        create_survey_via_ui(page)
        page.click("#btn-load")
        expect(page.locator("#survey-info")).to_contain_text("当前 0 票")
