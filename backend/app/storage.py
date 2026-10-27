"""Local source-file storage and repeatable data preparation."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import secrets
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import HTTPException

from .demo import generate_demo

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("RADAR_DATA_DIR", ROOT_DIR / "data")).expanduser().resolve()
SAMPLE_DIR = DATA_DIR / "sample"
RAW_DIR = DATA_DIR / "raw" / "originals"
PROCESSED_DIR = DATA_DIR / "processed"
MODEL_DIR = Path(os.getenv("RADAR_MODEL_DIR", ROOT_DIR / "models")).expanduser().resolve()
STATE_PATH = PROCESSED_DIR / "runtime_state.json"
COSTS_PATH = PROCESSED_DIR / "cost_settings.json"
SALT_PATH = PROCESSED_DIR / "pseudonym_salt.bin"

SOURCE_LABELS = {
    "ats": "Contratación (ATS)",
    "payroll": "Nómina y retiros",
    "performance": "Desempeño",
    "exit_surveys": "Encuestas de salida",
}
SOURCE_REQUIRED_FIELDS = {
    "ats": [
        "employee_id",
        "hire_date",
        "campaign",
        "shift",
        "supervisor",
        "technical_score",
        "prior_bpo_experience_years",
        "preferred_shift",
        "schedule_availability",
    ],
    "payroll": ["employee_id", "exit_date", "exit_type"],
    "performance": ["employee_id", "performance_score"],
    "exit_surveys": ["employee_id", "reason"],
}
SOURCE_OPTIONAL_FIELDS = {
    "ats": [],
    "payroll": ["recruitment_cost", "training_cost", "idle_time_cost"],
    "performance": [],
    "exit_surveys": [],
}
ALIASES: dict[str, dict[str, list[str]]] = {
    "ats": {
        "employee_id": ["employee_id", "id_empleado", "id", "identificador"],
        "hire_date": ["hire_date", "fecha_ingreso", "fecha_contratacion"],
        "campaign": ["campaign", "campana", "campaña"],
        "shift": ["shift", "turno"],
        "supervisor": ["supervisor", "supervisor_asignado"],
        "technical_score": ["technical_score", "puntaje_tecnico", "prueba_tecnica"],
        "prior_bpo_experience_years": [
            "prior_bpo_experience_years",
            "experiencia_bpo",
            "experiencia_call_center",
        ],
        "preferred_shift": ["preferred_shift", "turno_preferido"],
        "schedule_availability": ["schedule_availability", "disponibilidad_horaria"],
    },
    "payroll": {
        "employee_id": ["employee_id", "id_empleado", "id", "identificador"],
        "exit_date": ["exit_date", "fecha_retiro", "fecha_salida"],
        "exit_type": ["exit_type", "tipo_retiro", "tipo_salida"],
        "recruitment_cost": ["recruitment_cost", "costo_reclutamiento"],
        "training_cost": ["training_cost", "costo_formacion", "costo_capacitacion"],
        "idle_time_cost": ["idle_time_cost", "costo_tiempo_improductivo"],
    },
    "performance": {
        "employee_id": ["employee_id", "id_empleado", "id", "identificador"],
        "performance_score": ["performance_score", "puntaje_desempeno", "desempeno"],
    },
    "exit_surveys": {
        "employee_id": ["employee_id", "id_empleado", "id", "identificador"],
        "reason": ["reason", "motivo", "motivo_retiro", "motivo_renuncia"],
    },
}
PROTECTED_OR_PROXY_FIELDS = {
    "name",
    "full_name",
    "nombre",
    "document",
    "document_number",
    "cedula",
    "identification",
    "age",
    "edad",
    "sex",
    "gender",
    "sexo",
    "genero",
    "marital_status",
    "estado_civil",
    "socioeconomic_level",
    "estrato",
    "address",
    "direccion",
    "neighborhood",
    "barrio",
    "email",
    "phone",
    "telefono",
}


def ensure_directories() -> None:
    for path in (SAMPLE_DIR, RAW_DIR, PROCESSED_DIR, MODEL_DIR):
        path.mkdir(parents=True, exist_ok=True)


def load_state() -> dict[str, Any]:
    ensure_directories()
    if not STATE_PATH.exists():
        return {"active_files": {}, "mappings": {}, "synthetic_data": False, "as_of": None}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        raise HTTPException(500, "No se pudo leer el estado local del dataset.")


def save_state(state: dict[str, Any]) -> None:
    ensure_directories()
    temp = STATE_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(STATE_PATH)


def normalized_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def read_source_file(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    if path.suffix.lower() == ".xlsx":
        return pd.read_excel(path, dtype=str, keep_default_na=False, engine="openpyxl")
    raise HTTPException(400, "Formato no permitido. Usa un archivo CSV o XLSX.")


def auto_mapping(source: str, columns: list[str]) -> dict[str, str]:
    normalized = {normalized_name(column): column for column in columns}
    detected: dict[str, str] = {}
    for canonical, aliases in ALIASES[source].items():
        for alias in aliases:
            if normalized_name(alias) in normalized:
                detected[canonical] = normalized[normalized_name(alias)]
                break
    return detected


def upload_source(source: str, file_name: str, encoded: str) -> dict[str, Any]:
    ensure_directories()
    safe_name = Path(file_name.replace("\\", "/")).name
    suffix = Path(safe_name).suffix.lower()
    if suffix not in {".csv", ".xlsx"}:
        raise HTTPException(400, "Solo se admiten archivos CSV o XLSX.")
    try:
        content = base64.b64decode(encoded, validate=True)
    except (ValueError, base64.binascii.Error):
        raise HTTPException(400, "El archivo recibido no tiene una codificación válida.")
    if not content or len(content) > 10_000_000:
        raise HTTPException(413, "El archivo debe pesar entre 1 byte y 10 MB.")

    destination = RAW_DIR / f"{source}_{uuid.uuid4().hex}_{safe_name}"
    destination.write_bytes(content)
    try:
        frame = read_source_file(destination)
    except Exception as error:
        destination.unlink(missing_ok=True)
        if isinstance(error, HTTPException):
            raise error
        raise HTTPException(400, "No se pudo leer el archivo. Verifica que el CSV o XLSX esté íntegro.")
    if len(frame.columns) > 100:
        destination.unlink(missing_ok=True)
        raise HTTPException(400, "El archivo contiene demasiadas columnas (máximo 100).")

    state = load_state()
    state["active_files"][source] = _stored_path(destination)
    state["mappings"][source] = auto_mapping(source, [str(column) for column in frame.columns])
    state["synthetic_data"] = False
    state["as_of"] = None
    save_state(state)
    return {
        "source": source,
        "fileName": safe_name,
        "records": int(len(frame)),
        "columns": [str(column) for column in frame.columns],
        # Raw row previews are intentionally omitted to avoid exposing PII.
        "sampleRows": [],
        "detectedMapping": state["mappings"][source],
        "message": "Original conservado localmente. Las filas individuales no se muestran.",
    }


def set_mapping(source: str, mapping: dict[str, str]) -> dict[str, Any]:
    state = load_state()
    relative = state["active_files"].get(source)
    if not relative:
        raise HTTPException(409, f"Primero carga una fuente para {SOURCE_LABELS[source]}.")
    frame = read_source_file(ROOT_DIR / relative)
    valid_columns = {str(column) for column in frame.columns}
    unknown = sorted(set(mapping.values()) - valid_columns)
    if unknown:
        raise HTTPException(422, "El mapeo contiene columnas que no existen en el archivo.")
    allowed = set(SOURCE_REQUIRED_FIELDS[source] + SOURCE_OPTIONAL_FIELDS[source])
    disallowed = sorted(set(mapping) - allowed)
    if disallowed:
        raise HTTPException(422, "El mapeo contiene campos no permitidos para este análisis.")
    state["mappings"][source] = mapping
    save_state(state)
    required = SOURCE_REQUIRED_FIELDS[source]
    missing = [field for field in required if field not in mapping]
    return {
        "source": source,
        "mappedFields": sorted(mapping),
        "requiredFields": required,
        "ready": not missing,
        "message": "Mapeo listo." if not missing else "Faltan campos obligatorios: " + ", ".join(missing),
    }


def read_active_sources(state: dict[str, Any]) -> dict[str, pd.DataFrame]:
    sources: dict[str, pd.DataFrame] = {}
    for source, relative in state.get("active_files", {}).items():
        path = _resolve_stored_path(relative)
        frame = read_source_file(path).copy()
        mapping = state.get("mappings", {}).get(source, {})
        # Keep only explicitly mapped fields; source columns not in the schema
        # (including protected attributes and proxies) never reach analytics.
        selected = {column: canonical for canonical, column in mapping.items()}
        frame = frame.rename(columns=selected)
        frame = frame[[column for column in selected.values() if column in frame.columns]]
        if "employee_id" in frame:
            frame["employee_id"] = frame["employee_id"].astype(str).str.strip()
        sources[source] = frame
    return sources


def validate_sources() -> dict[str, Any]:
    state = load_state()
    sources = read_active_sources(state)
    issues: list[dict[str, Any]] = []
    missing_by_field: dict[str, int] = {}
    total_records = 0
    duplicate_ids = 0
    invalid_dates = 0
    unmatched_records = 0

    for source in ("ats", "payroll", "performance", "exit_surveys"):
        if source not in sources:
            if source in {"ats", "payroll"}:
                issues.append({
                    "code": "MISSING_SOURCE",
                    "severity": "error",
                    "source": source,
                    "message": f"Falta la fuente requerida: {SOURCE_LABELS[source]}.",
                    "count": 0,
                })
            continue
        frame = sources[source]
        total_records += len(frame)
        for field in SOURCE_REQUIRED_FIELDS[source]:
            if field not in frame.columns:
                missing_by_field[f"{source}.{field}"] = len(frame)
                issues.append({
                    "code": "MISSING_COLUMN",
                    "severity": "error",
                    "source": source,
                    "message": f"Falta mapear el campo obligatorio {field}.",
                    "count": len(frame),
                })
            else:
                count = int(frame[field].isna().sum() + (frame[field].astype(str).str.strip() == "").sum())
                if count:
                    missing_by_field[f"{source}.{field}"] = count
                    issues.append({
                        "code": "MISSING_VALUES",
                        "severity": "warning",
                        "source": source,
                        "message": f"Hay valores faltantes en {field}.",
                        "count": count,
                    })
        if "employee_id" in frame:
            duplicates = int(frame["employee_id"].duplicated(keep=False).sum())
            duplicate_ids += duplicates
            if duplicates:
                issues.append({
                    "code": "DUPLICATE_ID",
                    "severity": "error",
                    "source": source,
                    "message": "Hay identificadores duplicados dentro de la fuente.",
                    "count": duplicates,
                })

    ats = sources.get("ats")
    payroll = sources.get("payroll")
    if ats is not None and payroll is not None and "employee_id" in ats and "employee_id" in payroll:
        unmatched_records = len(set(payroll["employee_id"]) - set(ats["employee_id"]))
        if unmatched_records:
            issues.append({
                "code": "UNMATCHED_ID",
                "severity": "warning",
                "source": "payroll",
                "message": "Hay retiros sin una contratación correspondiente.",
                "count": unmatched_records,
            })
        if "hire_date" in ats and "exit_date" in payroll:
            joined = ats[["employee_id", "hire_date"]].merge(
                payroll[["employee_id", "exit_date"]],
                on="employee_id",
                how="inner",
            )
            hires = pd.to_datetime(joined["hire_date"], errors="coerce")
            exits = pd.to_datetime(joined["exit_date"], errors="coerce")
            invalid = exits.notna() & hires.notna() & (exits < hires)
            invalid_dates = int(invalid.sum())
            if invalid_dates:
                issues.append({
                    "code": "INVALID_DATE_ORDER",
                    "severity": "error",
                    "source": "payroll",
                    "message": "Hay fechas de retiro anteriores a la fecha de ingreso.",
                    "count": invalid_dates,
                })

    errors = any(issue["severity"] == "error" for issue in issues)
    return {
        "valid": not errors,
        "totalRecords": int(total_records),
        "duplicateIds": int(duplicate_ids),
        "missingValues": int(sum(missing_by_field.values())),
        "invalidDates": int(invalid_dates),
        "unmatchedRecords": int(unmatched_records),
        "issues": issues,
        "missingByField": missing_by_field,
    }


def _pseudonymize(value: str) -> str:
    ensure_directories()
    if not SALT_PATH.exists():
        SALT_PATH.write_bytes(secrets.token_bytes(32))
    salt = SALT_PATH.read_bytes()
    return hashlib.sha256(salt + value.encode("utf-8")).hexdigest()[:20]


def generate_demo_sources() -> dict[str, Any]:
    ensure_directories()
    generate_demo(SAMPLE_DIR)
    state = load_state()
    state["active_files"] = {
        source: _stored_path(SAMPLE_DIR / f"{source}.csv")
        for source in ("ats", "payroll", "performance", "exit_surveys")
    }
    state["mappings"] = {
        source: {field: field for field in SOURCE_REQUIRED_FIELDS[source] + SOURCE_OPTIONAL_FIELDS[source]}
        for source in SOURCE_REQUIRED_FIELDS
    }
    state["synthetic_data"] = True
    state["as_of"] = date.fromisoformat("2026-10-20").isoformat()
    save_state(state)
    return state


def _stored_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT_DIR))
    except ValueError:
        return str(path.resolve())


def _resolve_stored_path(value: str) -> Path:
    supplied = Path(value)
    path = supplied.resolve() if supplied.is_absolute() else (ROOT_DIR / supplied).resolve()
    allowed_roots = (DATA_DIR, RAW_DIR, SAMPLE_DIR)
    if not any(path == allowed or allowed in path.parents for allowed in allowed_roots):
        raise HTTPException(400, "La fuente configurada está fuera del directorio de datos permitido.")
    return path


def run_etl() -> dict[str, Any]:
    state = load_state()
    sources = read_active_sources(state)
    for required in ("ats", "payroll"):
        if required not in sources:
            raise HTTPException(409, f"Carga primero la fuente {SOURCE_LABELS[required]}.")
        mapping = state.get("mappings", {}).get(required, {})
        missing = [field for field in SOURCE_REQUIRED_FIELDS[required] if field not in mapping]
        if missing:
            raise HTTPException(409, f"Completa el mapeo de {required}: " + ", ".join(missing))
    report = validate_sources()
    if report["duplicateIds"] or report["invalidDates"]:
        raise HTTPException(409, "Corrige los identificadores duplicados y las fechas inconsistentes antes del ETL.")
    ats = sources["ats"]
    payroll = sources["payroll"]
    merged = ats.merge(payroll, on="employee_id", how="left", suffixes=("", "_payroll"), validate="one_to_one")
    for optional_source in ("performance", "exit_surveys"):
        if optional_source in sources:
            other = sources[optional_source]
            if "employee_id" in other and other["employee_id"].duplicated().any():
                raise HTTPException(409, f"La fuente {SOURCE_LABELS[optional_source]} tiene identificadores duplicados.")
            merged = merged.merge(other, on="employee_id", how="left", suffixes=("", f"_{optional_source}"), validate="one_to_one")

    as_of_value = state.get("as_of") if state.get("synthetic_data") else None
    as_of = date.fromisoformat(as_of_value) if as_of_value else date.today()
    from .business_rules import EARLY_WINDOW_DAYS, INVOLUNTARY_EXIT_TYPES, early_resignation_label

    hire_dates = pd.to_datetime(merged["hire_date"], errors="coerce")
    exit_dates = pd.to_datetime(merged.get("exit_date", pd.Series(index=merged.index, dtype="object")), errors="coerce")
    exit_types = merged.get("exit_type", pd.Series("", index=merged.index)).fillna("").astype(str).str.lower()
    labels: list[int | None] = []
    tenures: list[int | None] = []
    for hire, exit_date, exit_type in zip(hire_dates, exit_dates, exit_types):
        if pd.isna(hire):
            labels.append(None)
            tenures.append(None)
            continue
        hire_day = hire.date()
        exit_day = exit_date.date() if not pd.isna(exit_date) else None
        days = (exit_day - hire_day).days if exit_day else (as_of - hire_day).days
        tenures.append(max(0, days) if days >= 0 else None)
        labels.append(early_resignation_label(hire_day, exit_day, exit_type, as_of))
    merged["early_resignation"] = labels
    merged["tenure_days"] = tenures
    merged["hire_month"] = hire_dates.dt.strftime("%Y-%m")
    merged["employee_key"] = merged["employee_id"].astype(str).map(_pseudonymize)
    merged = merged.drop(columns=["employee_id"], errors="ignore")
    merged = merged.drop(columns=[column for column in merged.columns if column.lower() in PROTECTED_OR_PROXY_FIELDS], errors="ignore")
    merged["synthetic_data"] = bool(state.get("synthetic_data"))

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    destination = PROCESSED_DIR / "employees_clean.csv"
    temp = destination.with_suffix(".tmp")
    merged.to_csv(temp, index=False, encoding="utf-8-sig")
    temp.replace(destination)
    state["processed_at"] = datetime.now().astimezone().isoformat()
    save_state(state)

    indeterminate = int(merged["early_resignation"].isna().sum())
    early = int((merged["early_resignation"] == 1).sum())
    eligible = int(merged["early_resignation"].notna().sum())
    involuntary_early = int(
        (exit_types.isin(INVOLUNTARY_EXIT_TYPES) & (pd.Series(tenures).fillna(9999) < EARLY_WINDOW_DAYS)).sum()
    )
    return {
        "success": True,
        "records": int(len(merged)),
        "eligibleEmployees": eligible,
        "earlyResignations": early,
        "indeterminate": indeterminate,
        "involuntaryExits": involuntary_early,
        "syntheticData": bool(state.get("synthetic_data")),
        "message": "ETL completado. Las fuentes originales se conservaron y los identificadores fueron seudonimizados.",
    }


def load_processed() -> tuple[pd.DataFrame | None, dict[str, Any]]:
    state = load_state()
    path = PROCESSED_DIR / "employees_clean.csv"
    if not path.exists():
        return None, state
    try:
        return pd.read_csv(path), state
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as error:
        raise HTTPException(500, f"No se pudo leer el dataset procesado: {error}")


def list_source_status(state: dict[str, Any]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for source, label in SOURCE_LABELS.items():
        relative = state.get("active_files", {}).get(source)
        if not relative:
            sources.append({
                "source": source,
                "label": label,
                "state": "missing",
                "records": 0,
                "filename": None,
                "columns": [],
            })
            continue
        path = _resolve_stored_path(relative)
        if ROOT_DIR not in path.parents or not path.exists():
            sources.append({
                "source": source,
                "label": label,
                "state": "missing",
                "records": 0,
                "filename": None,
                "columns": [],
            })
            continue
        frame = read_source_file(path)
        sources.append({
            "source": source,
            "label": label,
            "state": "ready" if all(field in state.get("mappings", {}).get(source, {}) for field in SOURCE_REQUIRED_FIELDS[source]) else "needs_mapping",
            "records": int(len(frame)),
            "filename": path.name,
            "columns": [str(column) for column in frame.columns],
        })
    return sources
