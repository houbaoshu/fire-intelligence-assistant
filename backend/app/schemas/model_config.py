"""Model configuration schema definitions."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelConfigurationResponse(BaseModel):
    """Response body for model configuration endpoints."""

    id: str = Field(..., description="Configuration UUID")
    name: str = Field(..., description="Configuration name, e.g. 'primary_llm'")
    provider: str = Field(..., description="Provider name, e.g. 'openai', 'dashscope'")
    model_name: str = Field(..., description="Model identifier, e.g. 'qwen-plus'")
    config: dict | None = Field(
        None, description="Additional configuration (temperature, max_tokens, etc.)"
    )
    is_active: bool = Field(..., description="Whether this configuration is active")

    model_config = ConfigDict(from_attributes=True)


class ModelConfigurationCreate(BaseModel):
    """Request body for creating a model configuration."""

    name: str = Field(..., min_length=1, max_length=100, description="Configuration name")
    provider: str = Field(..., min_length=1, max_length=50, description="Provider name")
    model_name: str = Field(..., min_length=1, max_length=100, description="Model identifier")
    config: dict | None = Field(None, description="Additional configuration parameters")


class ModelConfigurationUpdate(BaseModel):
    """Request body for updating a model configuration."""

    name: str | None = Field(None, min_length=1, max_length=100, description="Configuration name")
    provider: str | None = Field(None, min_length=1, max_length=50, description="Provider name")
    model_name: str | None = Field(
        None, min_length=1, max_length=100, description="Model identifier"
    )
    config: dict | None = Field(None, description="Additional configuration parameters")
    is_active: bool | None = Field(None, description="Whether this configuration is active")
