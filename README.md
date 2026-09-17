# 极简投票系统（FastAPI + MySQL）+ 接口 / UI 自动化测试

一个"够用就好"的投票系统：**注册登录 → 创建问卷 → 投票 → 查看结果**。
配套两层自动化测试：接口自动化（pytest + requests + Allure）与 UI 自动化（Playwright）。

## 1. 项目背景

投票类业务的核心风险是三点：**重复投票**、**并发超投**、**结果统计不准**。
本项目用最少的组件实现功能（FastAPI + MySQL，无 Redis、无消息队列），
把"防重复"直接落在**数据库唯一约束**上，再用接口与 UI 两层自动化把行为固化、回归可重复。

## 2. 技术栈

| 层 | 选型 |
| --- | --- |
| 后端 | FastAPI、SQLAlchemy 2.0、MySQL 8 |
| 测试 | Python、pytest、requests、Playwright、Allure |
| 部署 | Docker Compose、GitHub Actions |

## 3. 快速开始（clone 后一键跑通）

```bash
git clone https://github.com/xyl-me/Vote.git
cd Vote

docker compose up -d --build          # 一键起 MySQL 8 + 应用
docker compose ps                     # 等两个服务都变 healthy
curl http://localhost:8000/health     # {"status":"ok"}
```

服务就绪后：

| 入口 | 地址 |
| --- | --- |
| 前端页面 | http://localhost:8000 |
| Swagger 文档 | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/health |

> - Windows PowerShell 用户：`curl` 换成 `Invoke-WebRequest -UseBasicParsing http://localhost:8000/health`；
> - 首次启动需拉取镜像并初始化 MySQL，约 30~60 秒（`app` 容器会等 MySQL healthy 后启动，并自动重试建表）；
> - 停止：`docker compose down`；连数据一起清掉重来：`docker compose down -v`；
> - 端口冲突时可改 `docker-compose.yml` 中的 `8000:8000` / `3307:3306`。

### 跑测试（可选）

```bash
pip install -r requirements-dev.txt   # 运行依赖 + 测试依赖（生产镜像只需 requirements.txt）
playwright install chromium           # UI 用例需要浏览器

pytest                                # 接口 47 + UI 10 用例，结果写入 allure-results
allure serve allure-results           # 查看 Allure 报告

# 若浏览器二进制未能下载（网络受限），可直接复用本机已装的 Chrome / Edge：
pytest --browser-channel=chrome       # 或 --browser-channel=msedge
```

> MySQL 映射到宿主机 **3307**（避免与本机已装的 3306 冲突）。
> 测试前置条件：被测服务已在运行；可用环境变量 `BASE_URL` 指向其他地址。

## 4. 接口一览

| 方法 | 路径 | 说明 | 主要返回码 |
| --- | --- | --- | --- |
| POST | `/auth/register` | 注册，返回 token | 201 / 409 / 422 |
| POST | `/auth/login` | 登录，返回 token | 200 / 401 |
| GET | `/auth/me` | 当前用户 | 200 / 401 |
| POST | `/vote/create` | 创建问卷 | 201 / 401 / 422 |
| POST | `/vote/{id}/cast` | 投票 | 200 / 401 / 404 / 409 / 422 |
| GET | `/vote/{id}/results` | 查看结果（票数 + 百分比，按票数倒序） | 200 / 401 / 404 |

投票请求体：

```json
{"option": "A"}
```

结果响应体：

```json
{"survey_id": 1, "title": "满意度调查", "total": 3,
 "options": [{"option": "A", "count": 2, "percent": 66.67},
             {"option": "B", "count": 1, "percent": 33.33}]}
```

## 5. 数据库设计

```sql
users   (id, username, password)            -- password 存 PBKDF2 哈希，非明文
surveys (id, title, creator_id)
votes   (id, survey_id, user_id, option)
        UNIQUE (survey_id, user_id)         -- uq_vote_once：防重复的唯一手段
```

**防重复设计**：投票接口先查是否已投（命中即 409），再插入；
并发穿透时由 `uq_vote_once` 唯一约束兜底（捕获 `IntegrityError` 同样返回 409）。
因此同一用户对同一问卷永远只有 1 行记录 —— 不依赖 Redis，也不需要额外计数。

## 6. 测试策略

### 6.1 分层与用例分布

| 层次 | 文件 | 关注点 | 用例数 |
| --- | --- | --- | --- |
| 接口-认证 | `tests/test_auth.py` | 注册、登录、鉴权（无/过期/伪造 token） | 17 |
| 接口-投票 | `tests/test_vote.py` | 创建问卷、投票、结果统计与百分比 | 20 |
| 接口-防重复 | `tests/test_duplicate.py` | 重复投票、隔离维度、并发不超投 | 10 |
| UI-登录注册 | `tests/ui/test_ui_login.py` | 页面注册/登录/错误提示/退出 | 5 |
| UI-投票流程 | `tests/ui/test_ui_vote.py` | 页面建问卷/投票/重复投票/看结果 | 5 |
| **合计** | | | **57** |

### 6.2 fixture 设计（接口层）

| fixture | 作用域 | 职责 |
| --- | --- | --- |
| `base_url` | session | 被测服务地址；启动前探测 `/health`，不可达直接终止并提示 |
| `client` | function | 一个 `requests.Session`（未登录），自动注入 token |
| `user` | function | 注册 + 登录 + token 注入的会话 |
| `survey` | function | 创建一份问卷（不清理，靠用户隔离） |

- **数据隔离**：每个用例注册独立用户（`unique()` 随机后缀）+ 自建问卷，用例之间零顺序依赖；
- **多用户场景**：`new_user(base_url)` 便捷函数按需造第二个用户（验证隔离维度、并发）；
- **UI 层**：复用 pytest-playwright 的 `page`（每用例独立浏览器上下文），`ui_base_url` 负责可达性检查与跳过。

### 6.3 用例设计要点

- **正负双向**：每个接口既有成功路径，也有 401 / 404 / 409 / 422 的负向断言；
  负向用例同时验证"失败后数据没被写脏"（如重复投票后票数仍为 1）。
- **边界值**：标题 100 字上限、选项 50 字上限、用户名/密码长度、空串等。
- **并发**：`ThreadPoolExecutor` 让同一用户并发 6 次投票，断言"只有 1 次 200，其余 409，最终票数 1"。

## 7. 量化数据

| 指标 | 数值 |
| --- | --- |
| 接口用例 | **47** 个（认证 17 + 投票 20 + 防重复 10） |
| UI 用例 | **10** 个（登录注册 5 + 投票流程 5） |
| 用例合计 | **57** 个 |
| 通过率 | **57 / 57 = 100%** |
| 执行耗时 | 约 **25 秒**（接口 + UI 串行，本机 Chrome 运行 UI） |
| 并发用例 | 同一用户并发 6 次投票：仅 1 次成功，票数保持 1 |

## 8. CI

`.github/workflows/ci.yml`：push / PR 触发，链路如下

1. `docker compose up -d --build` 一键起服务，轮询 `/health` 探活（失败则打印容器日志并中止）
   —— 等于把「clone 后一键跑通」这条路径也纳入 CI 验证
2. `pip install -r requirements-dev.txt` + `playwright install --with-deps chromium`
3. 执行接口 + UI 用例：**用例失败 → 本步骤失败 → CI 变红（阻断）**，同时带
   `--screenshot=only-on-failure --tracing=retain-on-failure` 保留 UI 失败现场
4. `allure generate` 生成 **HTML 报告**
5. 收集容器日志，上传产物（保留 14 天），最后 `docker compose down -v`

产物内容：

| 目录/文件 | 用途 |
| --- | --- |
| `allure-report/` | 可直接打开的 HTML 报告（`index.html`：总览 + 用例明细 + 请求响应附件） |
| `allure-results/` | Allure 原始结果，供二次分析或本地重新生成 |
| `test-results/` | UI 失败截图（`test-failed-*.png`）与 Playwright trace（`trace.zip`，可拖到 trace.playwright.dev 回放） |
| `compose-logs.txt` | 容器日志，服务启动异常时用于定位 |

> 说明：仅上传 `allure-results` 是不够的 —— 那是一堆 uuid 命名的 JSON/附件，必须本地装 Allure CLI + Java
> 才能生成报告；因此 CI 内直接产出 HTML，评审/同事点开即可看。

## 9. 目录结构

```
voting-system/
├── app/
│   ├── main.py             # 入口：建表（等 MySQL 就绪）+ 挂载路由与前端
│   ├── models.py           # 3 张表 + uq_vote_once 唯一约束
│   ├── schemas.py          # User / Survey / Vote 请求响应模型
│   ├── auth.py             # 注册、登录、JWT 鉴权
│   ├── vote.py             # 创建问卷、投票、查看结果
│   └── static/index.html   # 极简前端（登录 / 建问卷 / 投票 / 看结果）
├── tests/
│   ├── conftest.py         # base_url / client / user / survey
│   ├── test_auth.py
│   ├── test_vote.py
│   ├── test_duplicate.py
│   └── ui/
│       ├── conftest.py     # Playwright 相关夹具与页面辅助
│       ├── test_ui_login.py
│       └── test_ui_vote.py
├── docker-compose.yml      # MySQL + app（无 Redis，healthcheck 就绪依赖）
├── Dockerfile
├── requirements.txt        # 运行依赖（生产镜像）
├── requirements-dev.txt    # 测试依赖（pytest / requests / allure / playwright）
├── pytest.ini              # testpaths + --alluredir
└── README.md
```

## 10. 已知限制

- 问卷只有一个自由文本选项字段（`option`），没有题目/选项表，适合单题投票场景；
- 无问卷列表接口，投票页需先创建问卷（页面会自动回填问卷 ID）；
- 生产部署请通过环境变量覆盖 `JWT_SECRET`（默认值为开发用途）。
