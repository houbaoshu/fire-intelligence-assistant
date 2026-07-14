from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.ai.openai_compatible import OpenAICompatibleClient
from app.services.ai.prompts import (
    INSPECTION_SYSTEM_PROMPT,
    INTERVIEW_SYSTEM_PROMPT,
    PHOTO_SYSTEM_PROMPT,
    QA_SYSTEM_PROMPT,
)


class AIOrchestrator:
    def __init__(self, client: OpenAICompatibleClient) -> None:
        self.client = client

    def inspection_draft(
        self, frames: list[Path], transcript: str | None, remarks: str | None
    ) -> dict[str, Any]:
        evidence = {
            "transcript": transcript or None,
            "inspector_remarks": remarks or None,
            "frame_count": len(frames),
        }
        return self.client.chat_json(
            capability="vision",
            system=INSPECTION_SYSTEM_PROMPT,
            prompt=f"证据元数据：{json.dumps(evidence, ensure_ascii=False)}",
            images=frames,
        )

    def photo_evidence(self, frame: Path) -> dict[str, Any]:
        return self.client.chat_json(
            capability="vision",
            system=PHOTO_SYSTEM_PROMPT,
            prompt="分析这一张消防检查视频帧。只返回 JSON。",
            images=[frame],
        )

    def interview_draft(self, transcript: str) -> dict[str, Any]:
        return self.client.chat_json(
            capability="llm",
            system=INTERVIEW_SYSTEM_PROMPT,
            prompt=f"机器转写如下：\n{transcript}",
        )

    def grounded_answer(self, question: str, evidence: list[str]) -> str:
        numbered = "\n\n".join(f"[{index}] {text}" for index, text in enumerate(evidence, 1))
        return self.client.chat_text(
            system=QA_SYSTEM_PROMPT,
            prompt=f"问题：{question}\n\n证据：\n{numbered}",
        )
