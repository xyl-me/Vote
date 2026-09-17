"""防重复：同一用户对同一问卷只能投一次（靠数据库唯一约束 uq_vote_once）。"""
from concurrent.futures import ThreadPoolExecutor

import allure

from conftest import Client, new_user


def _cast_with_token(base_url: str, token: str, survey_id: int, option: str) -> int:
    client = Client(base_url)
    client.token = token
    return client.cast(survey_id, option).status_code


def _parallel_cast(base_url: str, token: str, survey_id: int, option: str, times: int) -> list[int]:
    with ThreadPoolExecutor(max_workers=times) as pool:
        return list(pool.map(
            lambda _: _cast_with_token(base_url, token, survey_id, option), range(times)))


@allure.feature("防重复（唯一约束）")
class TestDuplicateVote:

    @allure.story("重复投票")
    @allure.title("同一用户第二次投票返回 409")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_second_vote_conflict(self, user, survey):
        assert user.cast(survey["id"], "A").status_code == 200
        second = user.cast(survey["id"], "B")
        assert second.status_code == 409
        assert "已经投过" in second.json()["detail"]

    @allure.story("重复投票")
    @allure.title("重复投票不改变票数（幂等）")
    def test_duplicate_keeps_count(self, user, survey):
        user.cast(survey["id"], "A")
        user.cast(survey["id"], "B")
        body = user.results(survey["id"]).json()
        assert body["total"] == 1
        assert {item["option"]: item["count"] for item in body["options"]} == {"A": 1}

    @allure.story("重复投票")
    @allure.title("连续多次重复提交都返回 409 且票数不变")
    def test_repeated_attempts_all_409(self, user, survey):
        user.cast(survey["id"], "A")
        assert {user.cast(survey["id"], "A").status_code for _ in range(3)} == {409}
        assert user.results(survey["id"]).json()["total"] == 1

    @allure.story("重复投票")
    @allure.title("重新登录（新 token）后仍不能再投")
    def test_still_blocked_after_relogin(self, base_url, user, survey):
        user.cast(survey["id"], "A")
        again = Client(base_url)
        again.login(user.username, user.password)
        assert again.cast(survey["id"], "B").status_code == 409

    @allure.story("隔离维度")
    @allure.title("不同用户可投同一问卷")
    def test_different_users_allowed(self, user, base_url, survey):
        assert new_user(base_url).cast(survey["id"], "A").status_code == 200
        assert user.results(survey["id"]).json()["total"] == 1
        assert user.cast(survey["id"], "B").status_code == 200
        assert user.results(survey["id"]).json()["total"] == 2

    @allure.story("隔离维度")
    @allure.title("同一用户可投不同问卷")
    def test_same_user_other_survey_allowed(self, user, survey):
        other = user.create_survey().json()
        assert user.cast(survey["id"], "A").status_code == 200
        resp = user.cast(other["id"], "A")
        assert resp.status_code == 200 and resp.json()["survey_id"] == other["id"]

    @allure.story("隔离维度")
    @allure.title("不存在的问卷是 404，与重复投票 409 区分")
    def test_unknown_survey_is_404_not_409(self, user, survey):
        user.cast(survey["id"], "A")
        assert user.cast(99999999, "A").status_code == 404
        assert user.cast(survey["id"], "A").status_code == 409

    @allure.story("并发")
    @allure.title("同一用户并发 6 次投票只成功 1 次")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_concurrent_same_user_only_one_success(self, base_url, user, survey):
        codes = _parallel_cast(base_url, user.token, survey["id"], "A", times=6)
        assert codes.count(200) == 1, codes
        assert set(codes) <= {200, 409}, codes

    @allure.story("并发")
    @allure.title("并发投票后票数仍为 1（未超投）")
    def test_concurrent_no_overvote(self, base_url, user, survey):
        _parallel_cast(base_url, user.token, survey["id"], "A", times=6)
        assert user.results(survey["id"]).json()["total"] == 1

    @allure.story("并发")
    @allure.title("4 个用户并发投票全部成功且计数正确")
    def test_concurrent_different_users(self, base_url, user, survey):
        tokens = [new_user(base_url).token for _ in range(4)]
        with ThreadPoolExecutor(max_workers=4) as pool:
            codes = list(pool.map(
                lambda token: _cast_with_token(base_url, token, survey["id"], "A"), tokens))
        assert codes.count(200) == 4, codes
        assert user.results(survey["id"]).json()["total"] == 4
