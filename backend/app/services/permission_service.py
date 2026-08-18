"""权限系统（M6）：权限码目录、默认权限矩阵、幂等种子与查询。

权限以角色（users.role）为基准，权限码通过 role_permissions 关联到角色
（DATABASE.md「表：permissions / role_permissions」）。授权依赖
``require_permission("code")`` 按当前用户角色查生效矩阵；管理员可通过
``PUT /api/admin/permissions/{role}`` 调整矩阵（API.md §11.4）。

种子幂等：permissions 目录缺失的补齐；role_permissions 仅在空表时填充
默认矩阵——管理员调整过的矩阵不会因重启被覆盖。
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.organization import Permission, RolePermission
from app.models.user import USER_ROLES

# 权限码目录：code → (name, description)
PERMISSION_CATALOG: list[tuple[str, str, str]] = [
    ("record.read", "查看业务记录", "查看业务记录列表、详情并下载文书"),
    ("record.create", "创建业务记录", "创建并编辑本人业务记录"),
    ("record.review", "审阅业务记录", "审阅并修改可见范围内他人创建的业务记录"),
    ("record.finalize", "定稿业务记录", "将业务记录状态推进为 finalized"),
    ("knowledge.read", "查询知识库", "查看知识文档与法规问答"),
    ("knowledge.manage", "管理知识库", "上传、删除知识文档并重建索引"),
    ("task.manage", "管理异步任务", "重试与取消异步任务"),
    ("statistics.read", "查看统计", "查看权限范围内的聚合统计"),
    ("admin.users", "用户管理", "管理用户角色、状态与组织归属"),
    ("admin.orgs", "组织管理", "管理组织与部门"),
    ("admin.permissions", "权限管理", "查看与调整角色权限矩阵"),
    ("admin.audit", "审计查询", "查询审计日志"),
    ("admin.prompts", "Prompt 管理", "查看 Prompt 版本、新建版本与激活"),
    ("admin.models", "模型管理", "管理模型配置（路由生效配置）"),
    ("admin.evaluations", "评估管理", "运行与查看问答评估"),
    ("admin.plugins", "插件管理", "查看与启停服务端插件"),
    ("agent.run", "运行 Agent", "执行 Agent / 多智能体目标"),
]

PERMISSION_CODES: tuple[str, ...] = tuple(code for code, _, _ in PERMISSION_CATALOG)

# 默认权限矩阵（specs/_common.md「角色与权限」）：
# viewer 只读；inspector 创建编辑自己记录；supervisor 审阅定稿；admin 全部。
_DEFAULT_MATRIX: dict[str, list[str]] = {
    "viewer": ["record.read", "knowledge.read", "statistics.read"],
    "inspector": [
        "record.read",
        "record.create",
        "knowledge.read",
        "task.manage",
        "statistics.read",
        "agent.run",
    ],
    "supervisor": [
        "record.read",
        "record.create",
        "record.review",
        "record.finalize",
        "knowledge.read",
        "task.manage",
        "statistics.read",
        "agent.run",
    ],
    "admin": list(PERMISSION_CODES),
}

# admin 角色必须始终保留的权限前缀（防止把自己锁死在系统外）
ADMIN_PERMISSION_PREFIX = "admin."


def default_matrix() -> dict[str, list[str]]:
    return {role: list(codes) for role, codes in _DEFAULT_MATRIX.items()}


class PermissionService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def seed(self) -> None:
        """幂等种子：补齐 permissions 目录；role_permissions 空表时填默认矩阵。"""
        existing = set(
            self.session.execute(select(Permission.code)).scalars().all()
        )
        for code, name, description in PERMISSION_CATALOG:
            if code not in existing:
                self.session.add(Permission(code=code, name=name, description=description))
        self.session.flush()

        count = self.session.execute(
            select(func.count()).select_from(RolePermission)
        ).scalar_one()
        if count == 0:
            for role in USER_ROLES:
                for code in _DEFAULT_MATRIX.get(role, []):
                    self.session.add(RolePermission(role=role, permission_code=code))
            self.session.flush()

    def has_permission(self, role: str, code: str) -> bool:
        stmt = select(func.count()).select_from(RolePermission).where(
            RolePermission.role == role, RolePermission.permission_code == code
        )
        return self.session.execute(stmt).scalar_one() > 0

    def codes_for_role(self, role: str) -> list[str]:
        stmt = (
            select(RolePermission.permission_code)
            .where(RolePermission.role == role)
            .order_by(RolePermission.permission_code)
        )
        return list(self.session.execute(stmt).scalars().all())

    def list_permissions(self) -> list[Permission]:
        stmt = select(Permission).order_by(Permission.code)
        return list(self.session.execute(stmt).scalars().all())

    def matrix(self) -> dict[str, list[str]]:
        return {role: self.codes_for_role(role) for role in USER_ROLES}
