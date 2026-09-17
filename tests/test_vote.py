"""投票接口：创建问卷 / 投票 / 查看结果。"""
import allure
import pytest

from conftest import new_user, unique


@allure.feature("创建问卷")
class TestCreateSurvey:

    @allure.story("创建问卷")
    @allure.title("创建成功返回 201 与问卷信息")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_create_success(self, user):
        title = unique("满意度调查")
        resp = user.create_survey(title)
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == title
        assert isinstance(body["id"], int) and body["id"] > 0

    @allure.story("创建问卷")
    @allure.title("问卷的 creator_id 等于当前登录用户")
    def test_creator_is_current_user(self, user):
        assert user.create_survey().json()["creator_id"] == user.me().json()["id"]

    @allure.story("创建问卷")
    @allure.title("标题为空返回 422")
    def test_empty_title_422(self, user):
        assert user.create_survey("").status_code == 422

    @allure.story("创建问卷")
    @allure.title("标题超过 100 字返回 422")
    def test_too_long_title_422(self, user):
        assert user.create_survey("标" * 101).status_code == 422

    @allure.story("创建问卷")
    @allure.title("含中文与空格的标题可正常创建")
    def test_chinese_title_ok(self, user):
        title = unique("中文 标题 带空格")
        assert user.create_survey(title).json()["title"] == title


@allure.feature("投票")
class TestCastVote:

    @allure.story("投票")
    @allure.title("投票成功返回 200 与投票详情")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_cast_success(self, user, survey):
        resp = user.cast(survey["id"], "A")
        assert resp.status_code == 200
        body = resp.json()
        assert body["survey_id"] == survey["id"]
        assert body["option"] == "A"
        assert body["message"] == "投票成功"

    @allure.story("投票")
    @allure.title("投票记录的 user_id 为当前用户")
    def test_cast_records_current_user(self, user, survey):
        assert user.cast(survey["id"], "A").json()["user_id"] == user.me().json()["id"]

    @allure.story("投票")
    @allure.title("选项为空返回 422")
    def test_empty_option_422(self, user, survey):
        assert user.cast(survey["id"], "").status_code == 422

    @allure.story("投票")
    @allure.title("选项超过 50 字返回 422")
    def test_too_long_option_422(self, user, survey):
        assert user.cast(survey["id"], "x" * 51).status_code == 422

    @allure.story("投票")
    @allure.title("给不存在的问卷投票返回 404")
    def test_unknown_survey_404(self, user):
        resp = user.cast(99999999, "A")
        assert resp.status_code == 404 and "不存在" in resp.json()["detail"]

    @allure.story("投票")
    @allure.title("中文选项可正常投票")
    def test_chinese_option(self, user, survey):
        assert user.cast(survey["id"], "支持").status_code == 200

    @allure.story("投票")
    @allure.title("含空格与符号的选项按原样保存")
    def test_special_option_preserved(self, user, survey):
        option = "A 选项 #1"
        user.cast(survey["id"], option)
        results = user.results(survey["id"]).json()
        assert [item["option"] for item in results["options"]] == [option]

    @allure.story("投票")
    @allure.title("多个用户投同一问卷都会计入")
    def test_multiple_users_counted(self, user, base_url, survey):
        for _ in range(3):
            assert new_user(base_url).cast(survey["id"], "A").status_code == 200
        assert user.results(survey["id"]).json()["total"] == 3


@allure.feature("查看结果")
class TestResults:

    @allure.story("结果查询")
    @allure.title("无人投票时 total=0 且 options 为空")
    def test_empty_results(self, user, survey):
        body = user.results(survey["id"]).json()
        assert body["total"] == 0
        assert body["options"] == []
        assert body["title"] == survey["title"]

    @allure.story("结果查询")
    @allure.title("查询不存在的问卷返回 404")
    def test_unknown_survey_404(self, user):
        assert user.results(99999999).status_code == 404

    @allure.story("结果查询")
    @allure.title("单人投票：票数 1、百分比 100")
    def test_single_vote(self, user, survey):
        user.cast(survey["id"], "A")
        body = user.results(survey["id"]).json()
        assert body["total"] == 1
        assert body["options"] == [{"option": "A", "count": 1, "percent": 100.0}]

    @allure.story("结果查询")
    @allure.title("多人多选项：计数与百分比正确")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_counts_and_percent(self, user, base_url, survey):
        for option in ["A", "A", "B"]:
            new_user(base_url).cast(survey["id"], option)
        body = user.results(survey["id"]).json()
        assert body["total"] == 3
        assert {item["option"]: item["count"] for item in body["options"]} == {"A": 2, "B": 1}
        assert {item["option"]: item["percent"] for item in body["options"]} == {
            "A": 66.67, "B": 33.33}

    @allure.story("结果查询")
    @allure.title("结果按票数从高到低排序")
    def test_sorted_by_count_desc(self, user, base_url, survey):
        for option in ["B", "A", "A", "C"]:
            new_user(base_url).cast(survey["id"], option)
        options = user.results(survey["id"]).json()["options"]
        assert options[0]["option"] == "A"
        assert [item["count"] for item in options] == [2, 1, 1]

    @allure.story("结果查询")
    @allure.title("百分比保留两位小数")
    def test_percent_two_decimals(self, user, base_url, survey):
        for option in ["A", "B", "C"]:
            new_user(base_url).cast(survey["id"], option)
        for item in user.results(survey["id"]).json()["options"]:
            assert item["percent"] == 33.33

    @allure.story("结果查询")
    @allure.title("新增投票后结果实时变化")
    def test_results_updated_after_new_vote(self, user, base_url, survey):
        assert user.results(survey["id"]).json()["total"] == 0
        new_user(base_url).cast(survey["id"], "A")
        assert user.results(survey["id"]).json()["total"] == 1
