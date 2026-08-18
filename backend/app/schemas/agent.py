"""Agent / 多智能体 schema（API.md §12.5，M8）。"""

from pydantic import BaseModel, field_validator


class AgentRunRequest(BaseModel):
    goal: str

    @field_validator("goal")
    @classmethod
    def _validate_goal(cls, value: str) -> str:
        goal = value.strip()
        if not goal:
            raise ValueError("目标不能为空")
        return goal


class AgentStepItem(BaseModel):
    tool: str
    summary: str


class AgentRunResponse(BaseModel):
    answer: str
    steps: list[AgentStepItem]
    tools_used: list[str]
