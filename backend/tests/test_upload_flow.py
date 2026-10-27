import base64
import csv
import io
import json

from fastapi.testclient import TestClient

from backend.app import main, storage


def _use_temp_data(tmp_path, monkeypatch):
    paths = {
        "DATA_DIR": tmp_path / "data",
        "SAMPLE_DIR": tmp_path / "data" / "sample",
        "RAW_DIR": tmp_path / "data" / "raw" / "originals",
        "PROCESSED_DIR": tmp_path / "data" / "processed",
        "STATE_PATH": tmp_path / "data" / "processed" / "runtime_state.json",
        "COSTS_PATH": tmp_path / "data" / "processed" / "cost_settings.json",
        "SALT_PATH": tmp_path / "data" / "processed" / "pseudonym_salt.bin",
    }
    for key, value in paths.items():
        monkeypatch.setattr(storage, key, value)


def _csv(rows):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _upload(client, source, name, content):
    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
    return client.post(
        "/people-api/datasets/upload",
        json={"source": source, "fileName": name, "contentBase64": encoded},
    )


def test_csv_upload_mapping_validation_and_etl_are_aggregated(tmp_path, monkeypatch):
    _use_temp_data(tmp_path, monkeypatch)
    client = TestClient(main.app)
    ats_rows = []
    payroll_rows = []
    for index in range(40):
        employee_id = f"INTERNAL-TEST-{index:03d}"
        ats_rows.append(
            {
                "employee_id": employee_id,
                "hire_date": "2024-01-01",
                "campaign": "Atención",
                "shift": "Día",
                "supervisor": "Equipo prueba",
                "technical_score": 60 + index,
                "prior_bpo_experience_years": index % 4,
                "preferred_shift": "day",
                "schedule_availability": "flexible",
            }
        )
        payroll_rows.append(
            {
                "employee_id": employee_id,
                "exit_date": "2024-02-01" if index < 10 else "",
                "exit_type": "voluntary" if index < 10 else "",
            }
        )

    ats = _upload(client, "ats", "recruitment.csv", _csv(ats_rows))
    payroll = _upload(client, "payroll", "payroll.csv", _csv(payroll_rows))
    assert ats.status_code == payroll.status_code == 200
    for response in (ats, payroll):
        body = response.json()
        assert "employee_id" in body["detectedMapping"]
        assert body["sampleRows"] == []
        assert "INTERNAL-TEST-000" not in json.dumps(body)
    original = next(storage.RAW_DIR.glob("ats_*_recruitment.csv"))
    assert "INTERNAL-TEST-000" in original.read_text(encoding="utf-8")

    mapping = ats.json()["detectedMapping"]
    saved = client.post(
        "/people-api/datasets/mapping",
        json={"source": "ats", "mapping": mapping},
    )
    assert saved.status_code == 200
    validation = client.post("/people-api/datasets/validate")
    assert validation.status_code == 200
    report = validation.json()
    assert report["totalRecords"] == 80

    etl = client.post("/people-api/datasets/etl")
    assert etl.status_code == 200, etl.text
    result = etl.json()
    assert result["success"] is True
    assert result["records"] == 40
    assert result["earlyResignations"] == 10
    status = client.get("/people-api/datasets/status").json()
    assert status["processed"] is True
    assert status["totalHires"] == 40
    assert status["eligibleEmployees"] == 40
    assert status["earlyResignations"] == 10
    assert "INTERNAL-TEST-000" not in json.dumps(status)
