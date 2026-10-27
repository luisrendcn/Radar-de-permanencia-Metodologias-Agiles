"""Cohort-safe people analytics. Never returns employee-level rows."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from .storage import load_processed, load_state

MIN_GROUP_SIZE = 20
MIN_CRITICAL_EVENTS = 20
MIN_SCORE_BAND_SIZE = 25


def _empty() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "hire_month",
            "campaign",
            "shift",
            "supervisor",
            "technical_score",
            "prior_bpo_experience_years",
            "early_resignation",
            "tenure_days",
            "exit_type",
            "reason",
            "synthetic_data",
        ]
    )


def _frame() -> tuple[pd.DataFrame, dict[str, Any]]:
    frame, state = load_processed()
    if frame is None:
        return _empty(), state
    if "hire_month" in frame:
        frame["hire_month"] = frame["hire_month"].astype(str)
    for column in ("campaign", "shift", "supervisor", "exit_type", "reason", "preferred_shift", "schedule_availability"):
        if column not in frame:
            frame[column] = ""
    for column in ("early_resignation", "technical_score", "prior_bpo_experience_years", "tenure_days"):
        if column not in frame:
            frame[column] = np.nan
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame, state


def _eligible(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[frame["early_resignation"].isin([0, 1])].copy()


def _rate(events: int, eligible: int) -> float | None:
    return round(events / eligible, 4) if eligible else None


def apply_filters(
    frame: pd.DataFrame,
    start_month: str | None = None,
    end_month: str | None = None,
    campaign: str | None = None,
    shift: str | None = None,
    supervisor: str | None = None,
) -> pd.DataFrame:
    result = frame.copy()
    month = result["hire_month"].fillna("")
    if start_month:
        result = result[month >= start_month[:7]]
        month = result["hire_month"].fillna("")
    if end_month:
        result = result[month <= end_month[:7]]
    if campaign:
        result = result[result["campaign"].astype(str) == campaign]
    if shift:
        result = result[result["shift"].astype(str) == shift]
    if supervisor:
        eligible_counts = _eligible(result).groupby("supervisor")["early_resignation"].count()
        if int(eligible_counts.get(supervisor, 0)) < MIN_GROUP_SIZE:
            return result.iloc[0:0]
        result = result[result["supervisor"].astype(str) == supervisor]
    return result


def _critical_month(frame: pd.DataFrame) -> int | None:
    early = frame[(frame["early_resignation"] == 1) & (frame["tenure_days"].notna())]
    if len(early) < MIN_CRITICAL_EVENTS:
        return None
    months = ((early["tenure_days"].astype(float) - 1).clip(lower=0) // 30 + 1).clip(upper=6)
    counts = months.astype(int).value_counts()
    if counts.empty:
        return None
    winner = int(counts.idxmax())
    return winner if int(counts.max()) >= 5 else None


def _cohorts(frame: pd.DataFrame) -> list[dict[str, Any]]:
    eligible = _eligible(frame)
    if eligible.empty:
        return []
    grouped = eligible.groupby("hire_month", dropna=True)["early_resignation"].agg(["count", "sum"]).sort_index()
    result: list[dict[str, Any]] = []
    for month, row in grouped.iterrows():
        count = int(row["count"])
        events = int(row["sum"])
        result.append({
            "cohort": str(month),
            "hires": int((frame["hire_month"] == month).sum()),
            "eligible": count,
            "earlyResignations": events,
            "rate": _rate(events, count),
            "critical": False,
        })
    return result


def _tenure(frame: pd.DataFrame) -> list[dict[str, Any]]:
    early = frame[(frame["early_resignation"] == 1) & frame["tenure_days"].notna()]
    if early.empty:
        return []
    month_num = ((early["tenure_days"].astype(float) - 1).clip(lower=0) // 30 + 1).clip(upper=6).astype(int)
    counts = month_num.value_counts().sort_index()
    total = int(counts.sum())
    return [
        {"month": int(month), "resignations": int(count), "share": round(int(count) / total, 4)}
        for month, count in counts.items()
    ]


def _supervisors(frame: pd.DataFrame) -> list[dict[str, Any]]:
    eligible = _eligible(frame)
    if eligible.empty or not eligible["supervisor"].astype(str).str.strip().any():
        return []
    grouped = eligible.groupby("supervisor")["early_resignation"].agg(["count", "sum"]).sort_values("sum", ascending=False)
    result: list[dict[str, Any]] = []
    for supervisor, row in grouped.iterrows():
        sample = int(row["count"])
        if not str(supervisor).strip() or str(supervisor).lower() == "nan":
            continue
        suppressed = sample < MIN_GROUP_SIZE
        if suppressed:
            continue
        retained = sample - int(row["sum"])
        result.append({
            "supervisor": str(supervisor),
            "sampleSize": sample,
            "retained": retained,
            "retentionRate": _rate(retained, sample),
            "suppressed": False,
        })
    return result


def _score_bands(frame: pd.DataFrame) -> list[dict[str, Any]]:
    eligible = _eligible(frame)
    scores = pd.to_numeric(eligible["technical_score"], errors="coerce")
    valid = eligible[scores.notna()].copy()
    if valid.empty:
        return []
    valid["score_band"] = pd.cut(
        pd.to_numeric(valid["technical_score"], errors="coerce"),
        bins=[-0.01, 59.99, 69.99, 79.99, 89.99, 100.01],
        labels=["0–59", "60–69", "70–79", "80–89", "90–100"],
    )
    grouped = valid.groupby("score_band", observed=True)["early_resignation"].agg(["count", "sum"])
    return [
        {
            "band": str(band),
            "sampleSize": int(row["count"]),
            "events": int(row["sum"]),
            "rate": _rate(int(row["sum"]), int(row["count"])),
        }
        for band, row in grouped.iterrows()
        if int(row["count"]) >= MIN_SCORE_BAND_SIZE
    ]


def _profile_rates(frame: pd.DataFrame) -> list[dict[str, Any]]:
    eligible = _eligible(frame)
    if eligible.empty:
        return []
    groups: list[dict[str, Any]] = []
    dimensions = [
        ("Turno", "shift"),
        ("Campaña", "campaign"),
    ]
    experience = pd.to_numeric(eligible["prior_bpo_experience_years"], errors="coerce")
    eligible = eligible.copy()
    eligible["experience_group"] = pd.cut(
        experience,
        bins=[-0.01, 0.01, 1.99, 5.99, 60],
        labels=["Sin experiencia previa", "Menos de 2 años", "2 a 5 años", "Más de 5 años"],
    )
    dimensions.append(("Experiencia BPO", "experience_group"))
    for label, column in dimensions:
        valid = eligible[eligible[column].notna() & (eligible[column].astype(str).str.strip() != "")]
        grouped = valid.groupby(column, observed=True)["early_resignation"].agg(["count", "sum"])
        for value, row in grouped.iterrows():
            size = int(row["count"])
            if size < MIN_GROUP_SIZE:
                continue
            events = int(row["sum"])
            groups.append({
                "dimension": label,
                "value": str(value),
                "sampleSize": size,
                "events": events,
                "rate": round(events / size, 4),
            })
    groups.sort(key=lambda item: (item["rate"], item["sampleSize"]), reverse=True)
    return groups[:3]


def _exit_reasons(frame: pd.DataFrame) -> list[dict[str, Any]]:
    early = frame[(frame["early_resignation"] == 1) & frame["reason"].fillna("").astype(str).str.strip().ne("")]
    if early.empty:
        return []
    counts = early["reason"].astype(str).value_counts()
    total = int(counts.sum())
    return [
        {"reason": str(reason), "count": int(count), "percentage": round(int(count) / total, 4)}
        for reason, count in counts.items()
        if int(count) >= MIN_GROUP_SIZE
    ][:5]


def _reason_context(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Contextualize aggregated exit reasons without exposing small groups."""
    early = frame[
        (frame["early_resignation"] == 1)
        & frame["reason"].fillna("").astype(str).str.strip().ne("")
    ]
    results: list[dict[str, Any]] = []
    for reason, group in early.groupby("reason", dropna=True):
        if len(group) < MIN_GROUP_SIZE:
            continue

        def top_group(column: str) -> str | None:
            values = group[column].fillna("").astype(str).str.strip()
            values = values[values.ne("")]
            if values.empty:
                return None
            value, count = values.value_counts().index[0], int(values.value_counts().iloc[0])
            return str(value) if count >= MIN_GROUP_SIZE else None

        score = pd.to_numeric(group["technical_score"], errors="coerce").dropna()
        results.append(
            {
                "reason": str(reason),
                "sampleSize": int(len(group)),
                "topCampaign": top_group("campaign"),
                "topShift": top_group("shift"),
                "topSupervisor": top_group("supervisor"),
                "averageTechnicalScore": round(float(score.mean()), 1) if len(score) >= MIN_GROUP_SIZE else None,
                "limitation": "Contexto descriptivo dentro de respuestas válidas; no demuestra causa ni representa a quienes no respondieron.",
            }
        )
    results.sort(key=lambda item: item["sampleSize"], reverse=True)
    return results[:5]


def turnover(
    start_month: str | None = None,
    end_month: str | None = None,
    campaign: str | None = None,
    shift: str | None = None,
    supervisor: str | None = None,
) -> dict[str, Any]:
    frame, state = _frame()
    filtered = apply_filters(frame, start_month, end_month, campaign, shift, supervisor)
    eligible = _eligible(filtered)
    events = int((eligible["early_resignation"] == 1).sum())
    tenure = _tenure(filtered)
    critical = _critical_month(filtered)
    filters = {
        "startMonth": start_month,
        "endMonth": end_month,
        "campaign": campaign,
        "shift": shift,
        "supervisor": supervisor,
    }
    return {
        "syntheticData": bool(state.get("synthetic_data")),
        "filters": filters,
        "availableFilters": {
            "campaigns": sorted(value for value in frame["campaign"].dropna().astype(str).unique() if value),
            "shifts": sorted(value for value in frame["shift"].dropna().astype(str).unique() if value),
            "supervisors": sorted(row["supervisor"] for row in _supervisors(frame)),
        },
        "eligible": int(len(eligible)),
        "earlyResignations": events,
        "turnoverRate": _rate(events, len(eligible)),
        "cohorts": _cohorts(filtered),
        "tenureDistribution": tenure,
        "supervisors": _supervisors(filtered),
        "criticalMonth": critical,
        "notes": [
            "La cohorte corresponde al mes de ingreso; la tasa usa empleados con 180 días de seguimiento o una renuncia voluntaria temprana observada.",
            "Los activos con seguimiento incompleto y los retiros involuntarios antes de 180 días no cuentan como permanencias exitosas.",
            f"Se omiten los grupos de supervisor con menos de {MIN_GROUP_SIZE} casos elegibles; el filtro también impide consultarlos.",
            "Una asociación observada no demuestra causalidad.",
        ],
    }


def overview() -> dict[str, Any]:
    frame, state = _frame()
    eligible = _eligible(frame)
    events = int((eligible["early_resignation"] == 1).sum())
    current_rate = _rate(events, len(eligible))
    cohorts = _cohorts(frame)
    # Do not compare an all-history eligible rate against a tiny/latest cohort.
    # No prior rate is shown until a comparable period definition is supplied.
    previous = None
    critical = _critical_month(frame)
    highlights: list[str] = []
    if not frame.empty and current_rate is not None:
        highlights.append(f"{events} renuncias voluntarias tempranas entre {len(eligible)} casos con seguimiento suficiente.")
    if critical:
        highlights.append(f"El período de mayor concentración observado corresponde al mes {critical} de antigüedad.")
    if len(eligible) < 100:
        highlights.append("El volumen actual no permite conclusiones sólidas para grupos pequeños.")
    if not highlights:
        highlights.append("Carga datos o genera el conjunto sintético para iniciar el análisis.")
    return {
        "syntheticData": bool(state.get("synthetic_data")),
        "datasetReady": not frame.empty,
        "totalHires": int(len(frame)),
        "earlyResignations": events,
        "eligibleEmployees": int(len(eligible)),
        "censoredEmployees": int(frame["early_resignation"].isna().sum()),
        "involuntaryExits": int(
            (
                frame["exit_type"].fillna("").astype(str).str.lower().isin(
                    ["involuntary", "despido", "terminacion", "terminación", "dismissal", "fired"]
                )
                & (pd.to_numeric(frame["tenure_days"], errors="coerce") < 180)
            ).sum()
        ),
        "turnoverRate": current_rate,
        "previousRate": previous,
        "modelTrained": False,
        "criticalMonth": critical,
        "highlights": highlights,
    }


def diagnostics(
    start_month: str | None = None,
    end_month: str | None = None,
    campaign: str | None = None,
    shift: str | None = None,
    supervisor: str | None = None,
) -> dict[str, Any]:
    frame, state = _frame()
    filtered = apply_filters(frame, start_month, end_month, campaign, shift, supervisor)
    eligible = _eligible(filtered)
    sample = int(len(eligible))
    findings: list[dict[str, Any]] = []
    scores = _score_bands(filtered)
    profiles = _profile_rates(filtered)
    reasons = _exit_reasons(filtered)
    reason_context = _reason_context(filtered)
    tenure = _tenure(filtered)
    critical = _critical_month(filtered)

    if critical:
        month_row = next((row for row in tenure if row["month"] == critical), None)
        if month_row:
            findings.append({
                "title": f"Mayor concentración en el mes {critical} de antigüedad",
                "evidence": f"{month_row['resignations']} de {int((eligible['early_resignation'] == 1).sum())} renuncias tempranas observadas ocurrieron en ese rango.",
                "sampleSize": int((eligible["early_resignation"] == 1).sum()),
                "limitation": "La concentración temporal no identifica por sí sola una causa.",
                "recommendation": "Revisar los puntos de contacto y el acompañamiento antes de ese mes.",
            })
    if profiles:
        profile = profiles[0]
        findings.append({
            "title": f"Grupo con mayor tasa observada: {profile['value']} ({profile['dimension'].lower()})",
            "evidence": f"{profile['events']} renuncias en {profile['sampleSize']} casos elegibles ({profile['rate']:.1%}).",
            "sampleSize": profile["sampleSize"],
            "limitation": "Comparación descriptiva; puede haber diferencias de campaña y perfil que no se han ajustado.",
            "recommendation": "Validar las condiciones del puesto para ese grupo y ofrecer seguimiento temprano.",
        })
    supervisor_rows = [row for row in _supervisors(filtered) if not row["suppressed"]]
    if supervisor_rows:
        best = max(supervisor_rows, key=lambda row: row["sampleSize"] - row["retained"])
        findings.append({
            "title": "Variación observada entre equipos de supervisión",
            "evidence": f"El grupo {best['supervisor']} registra {best['sampleSize'] - best['retained']} renuncias tempranas de {best['sampleSize']} casos elegibles.",
            "sampleSize": best["sampleSize"],
            "limitation": "No atribuye causalidad al supervisor; diferencias de campañas o turnos pueden influir.",
            "recommendation": "Ofrecer acompañamiento y revisar carga, turnos y recursos del equipo sin clasificar personas.",
        })
    if scores:
        largest = max((row for row in scores if row["rate"] is not None), key=lambda row: row["rate"], default=None)
        if largest:
            findings.append({
                "title": "Resultados de prueba técnica con distintos niveles observados de permanencia",
                "evidence": f"El rango {largest['band']} presenta {largest['events']} renuncias de {largest['sampleSize']} casos con puntaje disponible.",
                "sampleSize": largest["sampleSize"],
                "limitation": "La prueba no demuestra causalidad; confirmar que la medición haya sido comparable para todas las personas.",
                "recommendation": "Revisar la consistencia de la prueba y usar el puntaje para orientar inducción, no para rechazar candidatos.",
            })
    if reasons:
        top = reasons[0]
        total_reason_responses = int(
            (
                (filtered["early_resignation"] == 1)
                & filtered["reason"].fillna("").astype(str).str.strip().ne("")
            ).sum()
        )
        findings.append({
            "title": f"Motivo declarado más frecuente: {top['reason']}",
            "evidence": f"{top['count']} de {total_reason_responses} respuestas válidas ({top['percentage']:.1%}); solo se muestran grupos con al menos {MIN_GROUP_SIZE} respuestas.",
            "sampleSize": total_reason_responses,
            "limitation": "El motivo es autodeclarado y puede no estar disponible para todas las salidas.",
            "recommendation": "Contrastar el motivo con condiciones de turno y campaña; no inferirlo para personas sin encuesta.",
        })
    findings = findings[:5]
    if not findings:
        limitations = ["No hay suficientes registros elegibles para producir hallazgos respaldados por datos."]
    else:
        limitations = [
            "Las asociaciones son descriptivas, no causales.",
            "Los grupos con menos de 20 observaciones se omiten o se protegen.",
            "Los resultados sintéticos solo demuestran el funcionamiento técnico y no describen a una empresa real."
            if state.get("synthetic_data")
            else "La calidad, comparabilidad y autorización de los datos requieren validación institucional.",
        ]
    if reasons:
        reason_availability = "Disponible: hay respuestas de salida agrupadas."
    else:
        reason_availability = "No disponible: no hay motivos de salida válidos en las fuentes procesadas."

    # A rank association is a screening signal, not evidence of causal or
    # operational usefulness for an automatic hiring rule.
    conclusion = "No es concluyente"
    score_data = eligible[["technical_score", "early_resignation"]].dropna()
    correlation: float | None = None
    p_value: float | None = None
    minimum_sample_size = 100
    if (
        len(score_data) >= minimum_sample_size
        and score_data["technical_score"].nunique() >= 2
        and score_data["early_resignation"].nunique() >= 2
    ):
        result = spearmanr(score_data["technical_score"], score_data["early_resignation"])
        correlation = round(float(result.statistic), 4)
        p_value = round(float(result.pvalue), 6)
        if p_value < 0.05 and correlation <= -0.20:
            conclusion = "Sirve"
        elif p_value < 0.05 and correlation >= 0.20:
            conclusion = "No sirve"
    technical_evidence = {
        "method": "Correlación de rangos de Spearman",
        "correlation": correlation,
        "pValue": p_value,
        "sampleSize": int(len(score_data)),
        "minimumSampleSize": minimum_sample_size,
        "note": "Asociación descriptiva, no causalidad ni prueba de utilidad para selección. La conclusión exige p < 0,05 y |ρ| ≥ 0,20; se requieren cohortes y mediciones comparables.",
    }

    months = [row["cohort"] for row in _cohorts(filtered)]
    period = f"{months[0]} a {months[-1]}" if months else "Sin período disponible"
    return {
        "syntheticData": bool(state.get("synthetic_data")),
        "sampleSize": sample,
        "period": period,
        "findings": findings,
        "technicalBands": scores,
        "technicalConclusion": conclusion,
        "technicalEvidence": technical_evidence,
        "topProfiles": profiles,
        "exitReasons": reasons,
        "reasonContext": reason_context,
        "reasonAvailability": reason_availability,
        "limitations": limitations,
    }
