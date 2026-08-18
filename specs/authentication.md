# Authentication（认证）

## 目的与范围

在用户访问受保护的消防检查功能前确认其身份，提供清晰的登录体验，并建立后端 API 可校验的认证会话。

范围（v1）：

- 邮箱 + 密码登录；
- 后端开启注册时的用户注册；
- 加载当前认证用户、保护业务页面与 API 请求；
- 用 refresh_token 续期会话，处理过期或无效会话；
- 退出登录（清除本地会话）。

范围外（v1）：社交登录、单点登录（SSO）、无密码认证、多因素认证（MFA）、组织邀请。

## 角色与权限

角色与权限通用规则见 specs/_common.md。本功能是所有角色的入口：认证只证明身份，授权仍由后端对每次受保护操作逐次校验。

## 功能要求

### 登录

- 表单只采集 email 与 password：email 必填且为合法规范化格式；password 必填，不得做 trim 或意外变换。
- 提交 pending 期间禁用提交按钮，重复点击不得产生重复请求。
- 登录成功：保存响应中的 `access_token` / `refresh_token` 与用户信息并建立会话，随后返回用户原本请求的保护路由。
- 登录失败：保留 email 字段，清空或保护 password 字段；展示通用可读错误，不区分「邮箱不存在」与「密码错误」。

### 注册

- 仅当后端开启注册时提供入口；表单字段以 API.md 契约为准，后端确认前 UI 不得暗示注册成功。
- 注册响应直接返回令牌，按登录成功处理。
- 普通注册不得由客户端选择角色，尤不得选择特权角色。

### 会话与令牌

- 受保护 API 请求一律通过集中式 API client 携带 `Authorization: Bearer <access_token>`。
- 应用启动与进入受保护路由时用 `GET /api/auth/me` 校验身份。
- `access_token` 过期时先调用 `POST /api/auth/refresh` 续期；`refresh_token` 无效或过期时清除本地会话并跳转登录页。
- 并发的多个 401 响应必须合并为一次连贯的「会话过期」流程，不得触发多个重定向。
- 认证状态初始化完成前不得短暂闪现受保护内容；必须防止重定向循环。
- 会话过期跳转登录时保留原请求目标，登录成功后恢复。

### 退出登录

- 用户可退出登录：清除本地保存的 token 与用户信息，此后不得再携带旧凭证发起受保护请求。

## 业务规则（本功能独有）

- 后端是账号状态、角色与权限的唯一权威；已停用或已删除的用户不得获得可用会话。
- 前端不得仅凭隐藏导航或按钮做授权，所有授权以后端校验为准（通用规则见 specs/_common.md，本功能为首要执行点）。
- 错误信息不得造成账号枚举风险：不得透露某个邮箱是否已注册。
- 注册密码强度策略以后端为准；前端校验只改善反馈，后端必须复核。
- token 不得出现在 URL、分析事件或错误详情中。v1 契约在响应 body 返回 token（见 API.md §2，无 Set-Cookie 行为），前端须将所选的浏览器存储方式与对应的 XSS 缓解措施显式记录在 `frontend/README.md`；改用 HttpOnly cookie 属于契约变更，须先修订 API.md。

## UI 结构

登录页与注册页为独立页面，共用同一表单结构：带可见 label 的 email / password 输入 → 密码可见性切换 → 带 pending 态的提交按钮 → 字段级校验信息 → 向辅助技术播报的整体错误区；仅注册开启时展示登录 / 注册互链。支持键盘提交。

必备状态：initial / validating / submitting / success redirect / invalid credentials / backend unavailable / session expired。后端不可用时保留表单并提供重试；触发限流时提示稍后再试；认证失败不得导致应用外壳崩溃。

## API 端点

- `POST /api/auth/login`（公开）— 邮箱密码登录，响应含 `access_token` 与 `refresh_token`。
- `POST /api/auth/register`（公开）— 注册并直接返回令牌。
- `GET /api/auth/me` — 返回当前 token 对应的用户。
- `POST /api/auth/refresh` — 用 `refresh_token` 换取新的 `access_token`。

请求/响应 schema 均见 API.md §2，本文件不复制。

## 数据影响

涉及 DATABASE.md 中的表：

- `users`：账号身份与角色；
- `user_profiles`：非认证类个人资料；
- `audit_logs`：记录重要认证事件（登录成功 / 失败等），不得记录密码或 token。

密码只存安全哈希，禁止明文存储（数据库级规则见 DATABASE.md）。

## 验收标准

- [ ] 有效凭证建立认证会话；无效凭证展示安全、可读的通用错误。
- [ ] 未认证访问保护页面被重定向到登录页，登录成功后恢复原始请求路由。
- [ ] `GET /api/auth/me` 判定当前用户；`access_token` 过期后经 `POST /api/auth/refresh` 透明续期。
- [ ] `refresh_token` 失效时只产生一次连贯的重新认证流程。
- [ ] 退出登录后旧会话不得再用于受保护请求。
- [ ] 角色与权限校验由后端执行；普通注册无法获得特权角色。
- [ ] 密码与 token 不出现在日志、URL 或错误详情中。
- [ ] 键盘可用，加载与错误状态可感知；通用验收标准见 specs/_common.md。
