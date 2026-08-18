"""Prompt 管理（M8）：版本化目录、幂等种子、运行时取用。

- 种子：启动时把 ``app/prompts/*.py`` 的常量注册为各 key 的 v1 生效版本
  （已存在该 key 的任何版本则跳过，管理员新建/激活的版本不会被覆盖）。
- 运行时取用 ``get_prompt(key)``：DB 生效版本优先，无生效版本（或表尚
  不可用）时回退代码常量，保证管线永远可用。
- 管理端点见 app/api/routers/ai_platform.py（API.md §12.1）。
"""

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.ai_platform import PromptVersion
from app.prompts import inspection, interview, photo, qa, agent as agent_prompts

logger = get_logger("prompts")

# key → (name, description, 代码常量回退值)
# key 为稳定标识（模块.用途），运行时取用与管理端点均以 key 为准。
PROMPT_SEEDS: dict[str, tuple[str, str, str]] = {
    "qa.QA_SYSTEM": (
        "法规问答系统 Prompt",
        "RAG 问答的系统指令：仅依据检索到的法规依据作答，禁止编造引用",
        qa.QA_SYSTEM_PROMPT,
    ),
    "qa.NO_EVIDENCE_ANSWER": (
        "无依据诚实回答",
        "检索无可靠来源时返回的固定文本（不经 LLM 生成）",
        qa.NO_EVIDENCE_ANSWER,
    ),
    "inspection.EXTRACT_SYSTEM": (
        "检查记录抽取系统 Prompt",
        "检查记录生成管线的结构化抽取系统指令",
        inspection.INSPECTION_EXTRACT_SYSTEM_PROMPT,
    ),
    "inspection.EXTRACT_OUTPUT_SCHEMA": (
        "检查记录输出 JSON 骨架",
        "检查记录结构化输出的 JSON 形状约束（值仅为类型示例）",
        inspection.INSPECTION_EXTRACT_OUTPUT_SCHEMA,
    ),
    "interview.CLEANUP_SYSTEM": (
        "转写清洗系统 Prompt",
        "询问记录管线的机器转写最低限度清洗指令",
        interview.INTERVIEW_CLEANUP_SYSTEM_PROMPT,
    ),
    "interview.STRUCTURE_SYSTEM": (
        "询问记录结构化系统 Prompt",
        "询问记录管线的结构化抽取系统指令",
        interview.INTERVIEW_STRUCTURE_SYSTEM_PROMPT,
    ),
    "interview.STRUCTURE_OUTPUT_SCHEMA": (
        "询问记录输出 JSON 骨架",
        "询问记录结构化输出的 JSON 形状约束（值仅为类型示例）",
        interview.INTERVIEW_STRUCTURE_OUTPUT_SCHEMA,
    ),
    "photo.FRAME_ANALYSIS": (
        "帧图像分析 Prompt",
        "逐帧视觉分析指令（检查记录与拍照报告管线共用）",
        photo.PHOTO_FRAME_ANALYSIS_PROMPT,
    ),
    "photo.REPORT_SYSTEM": (
        "拍照报告系统 Prompt",
        "拍照报告生成管线的报告级结构化抽取系统指令",
        photo.PHOTO_REPORT_SYSTEM_PROMPT,
    ),
    "photo.REPORT_OUTPUT_SCHEMA": (
        "拍照报告输出 JSON 骨架",
        "拍照报告结构化输出的 JSON 形状约束（值仅为类型示例）",
        photo.PHOTO_REPORT_OUTPUT_SCHEMA,
    ),
    "agent.AGENT_SYSTEM": (
        "Agent 系统 Prompt",
        "单角色 Agent 的系统指令：先检索/统计再回答，禁止编造",
        agent_prompts.AGENT_SYSTEM_PROMPT,
    ),
    "agent.PLANNER": (
        "规划器 Prompt",
        "多智能体编排器的目标拆解指令（输出子任务 JSON 数组）",
        agent_prompts.AGENT_PLANNER_PROMPT,
    ),
    "agent.SUMMARIZER": (
        "汇总器 Prompt",
        "多智能体编排器的结果汇总指令",
        agent_prompts.AGENT_SUMMARIZER_PROMPT,
    ),
}

# key → 代码常量（无 DB 生效版本时的回退）
PROMPT_FALLBACKS: dict[str, str] = {
    key: content for key, (_, _, content) in PROMPT_SEEDS.items()
}


def get_prompt(key: str, session: Session | None = None) -> str:
    """取生效 Prompt 内容：DB 生效版本优先，回退代码常量。

    ``session`` 为空时自行开启短会话（管线等无会话上下文处使用）；
    DB 不可用（如建表前）时回退常量，绝不阻断业务。
    """
    if key not in PROMPT_FALLBACKS:
        raise KeyError(f"未知 Prompt key: {key}")
    content = _active_content(key, session)
    if content is not None:
        return content
    return PROMPT_FALLBACKS[key]


def _active_content(key: str, session: Session | None) -> str | None:
    try:
        if session is not None:
            return _query_active(session, key)
        from app.db import SessionLocal

        with SessionLocal() as own_session:
            return _query_active(own_session, key)
    except SQLAlchemyError as exc:
        logger.info("Prompt %s 查询失败，回退代码常量: %s", key, type(exc).__name__)
        return None


def _query_active(session: Session, key: str) -> str | None:
    stmt = select(PromptVersion.content).where(
        PromptVersion.key == key, PromptVersion.is_active.is_(True)
    )
    return session.execute(stmt).scalars().first()


class PromptService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def seed(self) -> None:
        """幂等种子：某 key 尚无任何版本时插入 v1 生效版本。"""
        existing = set(
            self.session.execute(select(PromptVersion.key).distinct()).scalars().all()
        )
        for key, (name, description, content) in PROMPT_SEEDS.items():
            if key in existing:
                continue
            self.session.add(
                PromptVersion(
                    key=key,
                    name=name,
                    description=description,
                    content=content,
                    version=1,
                    is_active=True,
                )
            )
        self.session.flush()

    def list_versions(self) -> list[PromptVersion]:
        stmt = select(PromptVersion).order_by(PromptVersion.key, PromptVersion.version)
        return list(self.session.execute(stmt).scalars().all())

    def create_version(
        self,
        key: str,
        *,
        content: str,
        name: str | None,
        description: str | None,
        created_by,
    ) -> PromptVersion:
        """新建草稿版本（version 递增，is_active=false，需显式激活）。"""
        if key not in PROMPT_FALLBACKS:
            from app.core.exceptions import not_found

            raise not_found(f"未知 Prompt key: {key}")
        current_max = self.session.execute(
            select(func.max(PromptVersion.version)).where(PromptVersion.key == key)
        ).scalar_one()
        row = PromptVersion(
            key=key,
            name=name,
            description=description,
            content=content,
            version=(current_max or 0) + 1,
            is_active=False,
            created_by=created_by,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def activate(self, prompt_id) -> PromptVersion:
        """激活指定版本；同 key 其他版本同事务失效。"""
        from app.core.exceptions import not_found

        row = self.session.get(PromptVersion, prompt_id)
        if row is None:
            raise not_found("Prompt 版本不存在")
        stmt = select(PromptVersion).where(
            PromptVersion.key == row.key, PromptVersion.id != row.id
        )
        for other in self.session.execute(stmt).scalars().all():
            other.is_active = False
        row.is_active = True
        self.session.commit()
        self.session.refresh(row)
        return row
