from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.services.ai import OpenAICompatibleClient


def test_qwen_asr_uses_chat_completions_input_audio(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = Settings(
        environment="test",
        ai_base_url="https://example.com/compatible-mode/v1",
        ai_api_key=SecretStr("test-key"),
        speech_model="qwen3-asr-flash",
    )
    client = OpenAICompatibleClient(settings)
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"test-wave-data")
    captured: dict[str, Any] = {}

    def fake_chat_request(payload: dict[str, Any]) -> str:
        captured.update(payload)
        return "测试转写内容"

    monkeypatch.setattr(client, "_chat_request", fake_chat_request)

    assert client.transcribe(audio) == "测试转写内容"
    assert captured["model"] == "qwen3-asr-flash"
    assert captured["stream"] is False
    assert captured["asr_options"] == {"enable_itn": False}
    content = captured["messages"][0]["content"][0]
    assert content["type"] == "input_audio"
    data_url = content["input_audio"]["data"]
    prefix, encoded = data_url.split(",", 1)
    assert prefix == "data:audio/wav;base64"
    assert base64.b64decode(encoded) == b"test-wave-data"
