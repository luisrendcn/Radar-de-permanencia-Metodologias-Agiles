from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from backend.app import main, modeling, storage


def _redirect_storage(tmp_path: Path, monkeypatch) -> None:
    paths = {
        "DATA_DIR": tmp_path / "data",
        "SAMPLE_DIR": tmp_path / "data" / "sample",
        "RAW_DIR": tmp_path / "data" / "raw" / "originals",
        "PROCESSED_DIR": tmp_path / "data" / "processed",
        "STATE_PATH": tmp_path / "data" / "processed" / "runtime_state.json",
        "COSTS_PATH": tmp_path / "data" / "processed" / "cost_settings.json",
        "SALT_PATH": tmp_path / "data" / "processed" / "pseudonym_salt.bin",
        "MODEL_DIR": tmp_path / "models",
    }
    for name, value in paths.items():
        monkeypatch.setattr(storage, name, value)
    monkeypatch.setattr(modeling, "PROCESSED_DIR", paths["PROCESSED_DIR"])
    monkeypatch.setattr(modeling, "MODEL_DIR", paths["MODEL_DIR"])
    monkeypatch.setattr(modeling, "MODEL_PATH", paths["MODEL_DIR"] / "radar_logistic.joblib")
    monkeypatch.setattr(modeling, "METADATA_PATH", paths["MODEL_DIR"] / "metadata.json")


def test_demo_etl_model_and_analytics_api(tmp_path, monkeypatch):
    _redirect_storage(tmp_path, monkeypatch)
    monkeypatch.setattr(main, "COSTS_PATH", tmp_path / "data" / "processed" / "cost_settings.json")
    client = TestClient(main.app)
    health = client.get("/people-api/healthz").json()
    assert health == {"status": "ok", "syntheticData": False}

    result = client.post("/people-api/datasets/demo")
    assert result.status_code == 200, result.text
    result = result.json()
    assert result["syntheticData"] is True
    frame = pd.read_csv(storage.PROCESSED_DIR / "employees_clean.csv")
    payroll = pd.read_csv(storage.SAMPLE_DIR / "payroll.csv")
    observed_exits = pd.to_datetime(payroll["exit_date"], errors="coerce").dropna()

    assert result["totalHires"] == 720
    assert result["eligibleEmployees"] > 500
    assert observed_exits.max().date().isoformat() <= "2026-10-20"
    assert "employee_id" not in frame.columns
    assert frame["employee_key"].str.len().eq(20).all()

    overview = client.get("/people-api/analytics/overview")
    assert overview.status_code == 200
    assert overview.json()["syntheticData"] is True
    diagnostic = client.get("/people-api/analytics/diagnostic")
    assert diagnostic.status_code == 200
    assert diagnostic.json()["technicalConclusion"] == "No es concluyente"
    evidence = diagnostic.json()["technicalEvidence"]
    assert evidence["sampleSize"] > 100
    assert evidence["method"] == "Correlación de rangos de Spearman"
    assert abs(evidence["correlation"]) < 0.20
    assert overview.json()["previousRate"] is None
    assert all(row["sampleSize"] >= 20 for row in diagnostic.json()["reasonContext"])
    costs = client.put(
        "/people-api/settings/costs",
        json={
            "recruitment": 100,
            "training": 200,
            "idleTime": 50,
            "currency": "COP",
            "source": "real",
        },
    )
    assert costs.status_code == 200
    assert costs.json()["source"] == "real"
    assert costs.json()["replacementCost"] == 350
    assert costs.json()["totalCost"] == 230 * 350

    trained = client.post("/people-api/model/train")
    assert trained.status_code == 200, trained.text
    status = trained.json()
    assert status["readyForPrediction"] is True
    assert status["metrics"]["testObservations"] > 0
    assert len(status["metrics"]["confusionMatrix"]) == 2
    assert all(len(row) == 2 for row in status["metrics"]["confusionMatrix"])
    assert modeling.model_status()["version"] == status["version"]

    prediction = client.post(
        "/people-api/model/predict",
        json={
            "technicalScore": 78,
            "priorBpoExperienceYears": 1.5,
            "campaign": "Ventas",
            "preferredShift": "night",
            "scheduleAvailability": "fixed",
        },
    )
    assert prediction.status_code == 200, prediction.text
    prediction_body = prediction.json()
    assert prediction_body["risk"] in {"Bajo", "Medio", "Alto"}
    assert len(prediction_body["factors"]) <= 3
    assert "No acepta ni rechaza" in prediction_body["decisionNotice"]
    assert client.get("/people-api/model/fairness").json()["evaluated"] is False
