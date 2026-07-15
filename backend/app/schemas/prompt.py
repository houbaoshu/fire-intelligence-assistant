"""Prompt version schema definitions."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PromptVersionResponse(BaseModel):
    """Response body for prompt version endpoints."""

    id: str = Field(..., description="Prompt version UUID")
    name: str = Field(..., description="Prompt name identifier")
    version: int = Field(..., description="Version number")
    template: str = Field(..., description="Prompt template with {variable} placeholders")
    variables: list[str] = Field(
        default_factory=list, description="List of variable names used in the template"
    )
    description: str | None = Field(None, description="Description of the prompt")
    is_active: bool = Field(..., description="Whether this version is the active one")
    created_by: str = Field(..., description="User who created this version")

    model_config = ConfigDict(from_attributes=True)


class PromptVersionCreate(BaseModel):
    """Request body for creating a new prompt version."""

    name: str = Field(..., min_length=1, max_length=100, description="Prompt name identifier")
    template: str = Field(
        ..., min_length=1, description="Prompt template with {variable} placeholders"
    )
    variables: list[str] = Field(
        default_factory=list, description="List of variable names used in the template"
    )
    description: str | None = Field(None, max_length=500, description="Description of the prompt")


class PromptRenderRequest(BaseModel):
    """Request body for rendering a prompt with variables."""

    variables: dict[str, str] = Field(
        ..., description="Key-value pairs to fill in the prompt template variables"
    )


class PromptRenderResponse(BaseModel):
    """Response body for a rendered prompt."""

    name: str = Field(..., description="Prompt name")
    version: int = Field(..., description="Version used for rendering")
    rendered: str = Field(..., description="The rendered prompt text")
