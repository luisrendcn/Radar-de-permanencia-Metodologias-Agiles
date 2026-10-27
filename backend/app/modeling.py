"""Reproducible scikit-learn training, holdout evaluation and explanations."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

import joblib
import numpy as np
import pandas as pd
from fastapi import HTTPException
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .schemas import CandidateInput
from .storage import MODEL_DIR, PROCESSED_DIR, load_processed

MODEL_PATH = MODEL_DIR / "radar_logistic.joblib"
METADATA_PATH = MODEL_DIR / "metadata.json"
NUMERIC_FEATURES = ["technical_score", "prior_bpo_experience_years"]
CATEGORICAL_FEATURES = ["campaign", "preferred_shift", "schedule_availability"]
MODEL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
EXCLUDED_FEATURES = [
    "supervisor (asignación posterior a la entrevista)",
    "edad, sexo, estado civil y estrato",
    "dirección, barrio y otros proxies personales",
    "nombres, documentos e identificadores",
    "fecha de retiro, desempeño y cualquier dato posterior a contratación",
]
THRESHOLDS = {"low": 0.20, "high": 0.40, "provisional": True}


def _dataset_signature(frame: pd.DataFrame) -> str:
    path = PROCESSED_DIR / "employees_clean.csv"
    if path.exists():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    return hashlib.sha256(frame.to_csv(index=False).encode("utf-8")).hexdigest()


def _normal_shift(value: Any) -> str | None:
    if pd.isna(value):
        return None
    normalized = str(value).strip().lower()
    aliases = {
        "día": "day",
        "dia": "day",
        "day": "day",
        "tarde": "evening",
        "evening": "evening",
        "noche": "night",
        "night": "night",
    }
    return aliases.get(normalized, normalized or None)


def _features(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy()
    for column in MODEL_FEATURES:
        if column not in data:
            data[column] = np.nan if column in NUMERIC_FEATURES else None
    data["technical_score"] = pd.to_numeric(data["technical_score"], errors="coerce")
    data["prior_bpo_experience_years"] = pd.to_numeric(
        data["prior_bpo_experience_years"], errors="coerce"
    )
    data["preferred_shift"] = data["preferred_shift"].map(_normal_shift)
    for column in CATEGORICAL_FEATURES:
        data[column] = data[column].where(data[column].notna(), None)
    return data[MODEL_FEATURES]


def _build_pipeline() -> Pipeline:
    numeric = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("scaler", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent", keep_empty_features=True)),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric, NUMERIC_FEATURES),
            ("cat", categorical, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
        verbose_feature_names_out=True,
    )
    return Pipeline(
        steps=[
            ("preprocess", preprocessor),
            (
                "classifier",
                LogisticRegression(max_iter=2000, random_state=42, class_weight="balanced"),
            ),
        ]
    )


def _read_metadata() -> dict[str, Any] | None:
    if not METADATA_PATH.exists():
        return None
    try:
        return json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def model_status() -> dict[str, Any]:
    frame, _ = load_processed()
    metadata = _read_metadata()
    if frame is None or metadata is None or not MODEL_PATH.exists():
        return {
            "trained": False,
            "readyForPrediction": False,
            "version": None,
            "trainedAt": None,
            "observations": int(len(frame)) if frame is not None else 0,
            "eventCount": int((frame.get("early_resignation", pd.Series(dtype=float)) == 1).sum()) if frame is not None else 0,
            "metrics": None,
            "features": MODEL_FEATURES,
            "excludedFeatures": EXCLUDED_FEATURES,
            "message": "No hay un modelo entrenado. Procesa suficientes datos etiquetados y entrena el modelo.",
            "thresholds": THRESHOLDS,
        }
    eligible = frame[frame["early_resignation"].isin([0, 1])]
    current_signature = _dataset_signature(frame)
    is_current = metadata.get("dataset_signature") == current_signature
    return {
        "trained": True,
        "readyForPrediction": bool(is_current),
        "version": metadata.get("version"),
        "trainedAt": metadata.get("trained_at"),
        "observations": int(metadata.get("observations", len(eligible))),
        "eventCount": int(metadata.get("event_count", (eligible["early_resignation"] == 1).sum())),
        "metrics": metadata.get("metrics"),
        "features": MODEL_FEATURES,
        "excludedFeatures": EXCLUDED_FEATURES,
        "message": (
            "Modelo evaluado en un conjunto de prueba reservado. Umbrales provisionales; probabilidades no calibradas."
            if is_current
            else "El dataset cambió después del entrenamiento. Vuelve a entrenar antes de usar predicciones."
        ),
        "thresholds": THRESHOLDS,
    }


def train_model() -> dict[str, Any]:
    frame, _ = load_processed()
    if frame is None:
        raise HTTPException(409, "Primero carga o genera datos y ejecuta el ETL.")
    eligible = frame[frame["early_resignation"].isin([0, 1])].copy()
    labels = eligible["early_resignation"].astype(int)
    counts = labels.value_counts()
    if len(eligible) < 80 or len(counts) < 2 or int(counts.min()) < 20:
        raise HTTPException(
            409,
            "No hay suficientes casos etiquetados de permanencia y renuncia para entrenar y evaluar el modelo.",
        )

    x_train, x_test, y_train, y_test = train_test_split(
        _features(eligible),
        labels,
        test_size=0.25,
        random_state=42,
        stratify=labels,
    )
    pipeline = _build_pipeline()
    pipeline.fit(x_train, y_train)
    probabilities = pipeline.predict_proba(x_test)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    matrix = confusion_matrix(y_test, predictions, labels=[0, 1])
    tn, fp, fn, tp = (int(value) for value in matrix.ravel())
    majority_class = int(y_train.value_counts().idxmax())
    baseline_predictions = np.full(len(y_test), majority_class, dtype=int)
    baseline_matrix = confusion_matrix(y_test, baseline_predictions, labels=[0, 1])
    baseline_tn, baseline_fp, baseline_fn, baseline_tp = (
        int(value) for value in baseline_matrix.ravel()
    )
    try:
        auc: float | None = round(float(roc_auc_score(y_test, probabilities)), 4)
    except ValueError:
        auc = None
    metrics = {
        "accuracy": round(float(accuracy_score(y_test, predictions)), 4),
        "precision": round(float(precision_score(y_test, predictions, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, predictions, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, predictions, zero_division=0)), 4),
        "rocAuc": auc,
        "falsePositiveRate": round(fp / (fp + tn), 4) if fp + tn else None,
        "baselineRecall": round(
            float(recall_score(y_test, baseline_predictions, zero_division=0)), 4
        ),
        "baselineFalsePositiveRate": (
            round(baseline_fp / (baseline_fp + baseline_tn), 4)
            if baseline_fp + baseline_tn
            else None
        ),
        "confusionMatrix": matrix.astype(int).tolist(),
        "testObservations": int(len(y_test)),
    }
    signature = _dataset_signature(frame)
    version = "lr-v1-" + signature[:10]
    trained_at = datetime.now(timezone.utc).isoformat()
    metadata = {
        "version": version,
        "trained_at": trained_at,
        "dataset_signature": signature,
        "observations": int(len(eligible)),
        "event_count": int((labels == 1).sum()),
        "metrics": metrics,
        "test_size": 0.25,
        "random_state": 42,
        "thresholds": THRESHOLDS,
        "feature_names": MODEL_FEATURES,
        "excluded_features": EXCLUDED_FEATURES,
        "calibration": "No evaluada; las probabilidades no deben interpretarse como certeza.",
    }
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    temp_model = MODEL_PATH.with_suffix(".tmp")
    joblib.dump(pipeline, temp_model)
    temp_model.replace(MODEL_PATH)
    temp_metadata = METADATA_PATH.with_suffix(".tmp")
    temp_metadata.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_metadata.replace(METADATA_PATH)
    return model_status()


def _friendly_feature(name: str) -> str:
    if name == "num__technical_score":
        return "Resultado de la prueba técnica"
    if name == "num__prior_bpo_experience_years":
        return "Experiencia previa en BPO"
    if name.startswith("cat__campaign_"):
        return "Campaña: " + name.removeprefix("cat__campaign_")
    if name.startswith("cat__preferred_shift_"):
        values = {"day": "día", "evening": "tarde", "night": "noche"}
        return "Turno preferido: " + values.get(name.removeprefix("cat__preferred_shift_"), "otra categoría")
    if name.startswith("cat__schedule_availability_"):
        return "Disponibilidad: " + name.removeprefix("cat__schedule_availability_")
    return "Otra variable de entrevista"


def predict(candidate: CandidateInput) -> dict[str, Any]:
    status = model_status()
    if not status["readyForPrediction"] or not MODEL_PATH.exists():
        raise HTTPException(409, status["message"])
    try:
        pipeline: Pipeline = joblib.load(MODEL_PATH)
    except Exception:
        raise HTTPException(500, "No se pudo cargar el artefacto local del modelo. Entrénalo de nuevo.")
    candidate_frame = pd.DataFrame(
        [
            {
                "technical_score": candidate.technicalScore,
                "prior_bpo_experience_years": candidate.priorBpoExperienceYears,
                "campaign": candidate.campaign,
                "preferred_shift": candidate.preferredShift,
                "schedule_availability": candidate.scheduleAvailability,
            }
        ]
    )
    model_input = _features(candidate_frame)
    probability = float(pipeline.predict_proba(model_input)[0, 1])
    if probability < THRESHOLDS["low"]:
        risk = "Bajo"
    elif probability < THRESHOLDS["high"]:
        risk = "Medio"
    else:
        risk = "Alto"

    transformed = pipeline.named_steps["preprocess"].transform(model_input)
    coefficients = pipeline.named_steps["classifier"].coef_[0]
    feature_names = pipeline.named_steps["preprocess"].get_feature_names_out()
    contributions = np.asarray(transformed)[0] * coefficients
    factor_rows: list[dict[str, Any]] = []
    for feature_name, contribution in zip(feature_names, contributions):
        value = float(contribution)
        if abs(value) < 1e-5:
            continue
        factor_rows.append(
            {
                "factor": _friendly_feature(str(feature_name)),
                "value": f"{value:+.2f} en escala logarítmica",
                "effect": "increases" if value > 0 else "decreases",
                "contribution": round(value, 4),
            }
        )
    factor_rows.sort(key=lambda item: abs(item["contribution"]), reverse=True)

    actions: list[str] = []
    if risk in {"Medio", "Alto"}:
        actions.append("Aclarar antes de la contratación las funciones, horarios y condiciones reales de la campaña.")
    if candidate.priorBpoExperienceYears < 1:
        actions.append("Ofrecer una inducción estructurada y un punto de contacto durante los primeros 30 y 60 días.")
    if candidate.scheduleAvailability == "fixed":
        actions.append("Confirmar que la disponibilidad acordada coincide con los turnos y descansos del puesto.")
    if candidate.technicalScore < 65:
        actions.append("Identificar necesidades de formación técnica y explicar el acompañamiento disponible.")
    if not actions:
        actions.append("Acordar expectativas y un seguimiento temprano de bienestar y adaptación.")
    metadata = _read_metadata() or {}
    return {
        "probability": round(probability, 4),
        "risk": risk,
        "factors": factor_rows[:3],
        "actions": actions[:3],
        "modelVersion": str(status["version"]),
        "modelDate": str(status["trainedAt"]),
        "uncertainty": "Estimación experimental no calibrada, basada en datos históricos disponibles. No es una probabilidad de certeza ni una evaluación de la persona.",
        "decisionNotice": "Este resultado es solo un insumo para aclarar condiciones y planear acompañamiento. No acepta ni rechaza candidatos; la decisión final es humana.",
    }


def fairness_status() -> dict[str, Any]:
    return {
        "evaluated": False,
        "status": "No evaluable con las fuentes disponibles",
        "groupsAvailable": [],
        "note": "La exclusión de variables protegidas no garantiza equidad. No se dispone de grupos de auditoría con base legítima y autorización documentada; no se calcularon métricas por grupo.",
        "excludedFeatures": EXCLUDED_FEATURES,
    }
