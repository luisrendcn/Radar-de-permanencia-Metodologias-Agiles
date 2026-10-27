"""Portable FastAPI service for Radar de Permanencia."""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from .analytics import diagnostics, overview, turnover
from .modeling import fairness_status, model_status, predict, train_model
from .schemas import CandidateInput, ColumnMappingInput, CostSettingsInput, DatasetUploadInput
from .storage import (
    COSTS_PATH,
    MODEL_DIR,
    PROCESSED_DIR,
    SAMPLE_DIR,
    SOURCE_LABELS,
    SOURCE_REQUIRED_FIELDS,
    ensure_directories,
    generate_demo_sources,
    list_source_status,
    load_processed,
    load_state,
    run_etl,
    save_state,
    set_mapping,
    upload_source,
    validate_sources,
)


def public_demo_enabled() -> bool:
    return os.getenv("RADAR_PUBLIC_DEMO", "false").strip().lower() == "true"


@asynccontextmanager
async def lifespan(_: FastAPI):
    # A public demo starts with fictional data so a cold service can answer
    # status/model requests immediately without asking visitors to seed it.
    if public_demo_enabled() and not dataset_status()["processed"]:
        generate_demo_sources()
        run_etl()
        train_model()
    yield

app = FastAPI(
    title="Radar de Permanencia — People Analytics",
    version="1.0.0",
    description="API local para análisis cohortal, calidad de datos y estimaciones experimentales.",
    docs_url="/people-api/docs",
    openapi_url="/people-api/openapi.json",
    lifespan=lifespan,
)

raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173",
)
origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)


def _empty_totals() -> dict[str, Any]:
    return {
        "totalHires": 0,
        "earlyResignations": 0,
        "eligibleEmployees": 0,
        "censoredEmployees": 0,
        "involuntaryExits": 0,
        "turnoverRate": None,
    }


def dataset_status() -> dict[str, Any]:
    ensure_directories()
    state = load_state()
    frame, _ = load_processed()
    totals = _empty_totals()
    if frame is not None:
        eligible = frame[frame["early_resignation"].isin([0, 1])]
        events = int((eligible["early_resignation"] == 1).sum())
        rate = events / len(eligible) if len(eligible) else None
        involuntary = 0
        if "exit_type" in frame and "tenure_days" in frame:
            normalized = frame["exit_type"].fillna("").astype(str).str.lower()
            tenure = frame["tenure_days"].fillna(9999)
            involuntary = int(
                (
                    normalized.isin(
                        ["involuntary", "despido", "terminacion", "terminación", "dismissal", "fired"]
                    )
                    & (tenure < 180)
                ).sum()
            )
        totals = {
            "totalHires": int(len(frame)),
            "earlyResignations": events,
            "eligibleEmployees": int(len(eligible)),
            "censoredEmployees": int(frame["early_resignation"].isna().sum()),
            "involuntaryExits": involuntary,
            "turnoverRate": round(rate, 4) if rate is not None else None,
        }
    return {
        "syntheticData": bool(state.get("synthetic_data")),
        "processed": frame is not None,
        "lastUpdated": state.get("processed_at"),
        "sources": list_source_status(state),
        **totals,
    }


def _cost_settings() -> dict[str, Any]:
    default = {
        "recruitment": 250_000.0,
        "training": 500_000.0,
        "idleTime": 150_000.0,
        "currency": "COP",
        "source": "estimated",
    }
    if COSTS_PATH.exists():
        try:
            stored = json.loads(COSTS_PATH.read_text(encoding="utf-8"))
            default.update(stored)
        except (OSError, json.JSONDecodeError):
            pass
    count = dataset_status()["earlyResignations"]
    replacement_cost = round(
        float(default["recruitment"])
        + float(default["training"])
        + float(default["idleTime"]),
        2,
    )
    return {
        **default,
        "replacementCost": replacement_cost,
        "totalCost": round(replacement_cost * count, 2),
        "earlyResignations": count,
    }


@app.get("/people-api/healthz")
def health_check() -> dict[str, Any]:
    return {"status": "ok", "syntheticData": bool(load_state().get("synthetic_data"))}


@app.get("/people-api/datasets/status")
def get_dataset_status() -> dict[str, Any]:
    return dataset_status()


@app.post("/people-api/datasets/demo")
def generate_demo_data() -> dict[str, Any]:
    generate_demo_sources()
    run_etl()
    return dataset_status()


@app.post("/people-api/datasets/upload")
def upload_dataset(payload: DatasetUploadInput) -> dict[str, Any]:
    if public_demo_enabled():
        raise HTTPException(403, "La demo pública solo acepta datos sintéticos; la carga de archivos está deshabilitada.")
    return upload_source(payload.source, payload.fileName, payload.contentBase64)


@app.post("/people-api/datasets/mapping")
def save_dataset_mapping(payload: ColumnMappingInput) -> dict[str, Any]:
    return set_mapping(payload.source, payload.mapping)


@app.post("/people-api/datasets/validate")
def validate_dataset() -> dict[str, Any]:
    return validate_sources()


@app.post("/people-api/datasets/etl")
def run_dataset_etl() -> dict[str, Any]:
    result = run_etl()
    return result


@app.get("/people-api/analytics/overview")
def get_analytics_overview() -> dict[str, Any]:
    result = overview()
    result["modelTrained"] = bool(model_status()["trained"])
    return result


@app.get("/people-api/analytics/turnover")
def get_turnover_analytics(
    startMonth: str | None = Query(default=None, max_length=20),
    endMonth: str | None = Query(default=None, max_length=20),
    campaign: str | None = Query(default=None, max_length=100),
    shift: str | None = Query(default=None, max_length=60),
    supervisor: str | None = Query(default=None, max_length=100),
) -> dict[str, Any]:
    return turnover(startMonth, endMonth, campaign, shift, supervisor)


@app.get("/people-api/analytics/diagnostic")
def get_diagnostic_analytics(
    startMonth: str | None = Query(default=None, max_length=20),
    endMonth: str | None = Query(default=None, max_length=20),
    campaign: str | None = Query(default=None, max_length=100),
    shift: str | None = Query(default=None, max_length=60),
    supervisor: str | None = Query(default=None, max_length=100),
) -> dict[str, Any]:
    return diagnostics(startMonth, endMonth, campaign, shift, supervisor)


@app.get("/people-api/settings/costs")
def get_cost_settings() -> dict[str, Any]:
    return _cost_settings()


@app.put("/people-api/settings/costs")
def update_cost_settings(payload: CostSettingsInput) -> dict[str, Any]:
    ensure_directories()
    values = payload.model_dump()
    temp = COSTS_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(values, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(COSTS_PATH)
    return _cost_settings()


@app.get("/people-api/model/status")
def get_model_status() -> dict[str, Any]:
    return model_status()


@app.post("/people-api/model/train")
def post_train_model() -> dict[str, Any]:
    return train_model()


@app.post("/people-api/model/predict")
def post_predict_candidate(payload: CandidateInput) -> dict[str, Any]:
    return predict(payload)


@app.get("/people-api/model/fairness")
def get_fairness_status() -> dict[str, Any]:
    return fairness_status()
