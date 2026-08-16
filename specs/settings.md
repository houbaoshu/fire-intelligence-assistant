# Settings（设置）

## 目的与范围

设置页提供查看后端连接状态、管理非敏感个人界面偏好的安全场所。禁止成为客户端 secret 仓库，禁止绕过基于环境变量的部署配置。

范围（v1）：展示连接状态与安全形式的 API origin、重试健康检查、管理本地偏好、恢复默认值、展示可用的版本信息。

范围外：录入 API key / provider 凭据、修改数据库与存储配置、运行时修改构建期环境变量、系统级 prompt 与模型管理、用户与角色管理。

## 角色与权限

通用规则见 specs/_common.md。本功能所有已认证用户均可查看连接状态并管理自己的偏好。

## 功能要求

### 连接状态

- 连接状态必须基于 `GET /health` 的真实请求结果，展示 checking / connected / error 状态并提供重试。
- 展示的 API origin 必须去除 query、credentials 等敏感成分。
- 普通用户不得修改 API Base URL：禁止在浏览器中运行时改写 `VITE_API_BASE_URL`。

### 个人偏好

- v1 偏好项清单：主题（light / dark / system）、显示密度（compact / comfortable）、减弱动效（reduced motion）、列表默认 page-size。
- v1 一律存浏览器 localStorage，不做服务端同步；`/api/user/preferences` 与 `/api/system/capabilities` 不进 v1，规格与代码均不写。
- 偏好值必须来自有限取值集合；localStorage 中的非法值安全回退到默认值；读写失败不得阻止应用加载。
- 恢复默认值前须说明将变更哪些值；不得清除认证信息或业务数据。

## 业务规则（本功能独有）

- `VITE_*` 是公开的前端配置，绝不包含 secret；部署配置只由环境变量与后端安全配置控制。
- 偏好不得改变业务规则或后端授权；缺失的系统信息显示为「不可用」，禁止编造。
- 本页面不展示、不存储 API key、token、数据库 URL 等任何凭据，不输出原始环境变量转储。

## UI 结构

页面按 `连接 → 外观与无障碍 → 应用信息` 分区组织；各分区展示当前值与保存状态，恢复默认需确认，状态文案不得仅依赖颜色表达。

## API 端点

- `GET /health` — 健康检查（请求/响应 schema 见 API.md）。

## 数据影响

无新增数据库表；偏好只存浏览器 localStorage，不落库。

## 验收标准

- [ ] 连接状态来自真实 `GET /health` 请求且可重试。
- [ ] 展示的 API origin 不含凭据或 secret。
- [ ] 普通用户无法在浏览器中修改部署配置或 secret。
- [ ] 偏好可修改、可恢复默认，非法存储值安全回退。
- [ ] 后端不可用时设置页仍可使用；通用验收标准见 specs/_common.md。
