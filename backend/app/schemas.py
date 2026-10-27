"""Validated API inputs. Public responses are assembled from aggregates only."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


SourceName = Literal["ats", "payroll", "performance", "exit_surveys"]


class DatasetUploadInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    source: SourceName
    fileName: str = Field(min_length=1, max_length=180)
    contentBase64: str = Field(min_length=1, max_length=16_000_000)


class ColumnMappingInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    source: SourceName
    mapping: dict[str, str]

    @field_validator("mapping")
    @classmethod
    def validate_columns(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) > 30:
            raise ValueError("El mapeo no puede contener más de 30 columnas.")
        if any(len(key) > 80 or len(column) > 160 for key, column in value.items()):
            raise ValueError("El nombre de columna excede el límite permitido.")
        return value


class CostSettingsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    recruitment: float = Field(ge=0, le=1_000_000_000)
    training: float = Field(ge=0, le=1_000_000_000)
    idleTime: float = Field(ge=0, le=1_000_000_000)
    currency: Literal["COP", "USD"] = "COP"
    source: Literal["real", "estimated"] = "estimated"


class CandidateInput(BaseModel):
    """Only fields available in the interview and approved for the MVP."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    technicalScore: float = Field(ge=0, le=100)
    priorBpoExperienceYears: float = Field(ge=0, le=60)
    campaign: str = Field(min_length=1, max_length=100)
    preferredShift: Literal["day", "evening", "night"]
    scheduleAvailability: Literal["flexible", "fixed"]

    @field_validator("campaign")
    @classmethod
    def validate_campaign(cls, value: str) -> str:
        if not value:
            raise ValueError("Selecciona una campaña.")
        return value
