"""Generate fictional, reproducible BPO sources for local demonstrations."""

from __future__ import annotations

import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path


AS_OF = date(2026, 10, 20)
SEED = 741_2026
EMPLOYEES = 720
CAMPAIGNS = ("Atención digital", "Soporte técnico", "Ventas", "Retención")
SHIFTS = ("Día", "Tarde", "Noche")
SUPERVISORS = tuple(f"Sup. {letter}" for letter in "ABCDEFGH")
EXIT_REASONS = (
    "Horario incompatible",
    "Expectativas del cargo",
    "Oferta laboral externa",
    "Transporte y desplazamiento",
    "Motivos personales",
    "Compensación",
)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def generate_demo(output_dir: Path) -> dict[str, object]:
    """Write four synthetic source files and a metadata marker."""
    rng = random.Random(SEED)
    ats: list[dict[str, object]] = []
    payroll: list[dict[str, object]] = []
    performance: list[dict[str, object]] = []
    surveys: list[dict[str, object]] = []
    start = date(2024, 1, 1)
    last_hire_day = AS_OF - timedelta(days=4)

    for index in range(1, EMPLOYEES + 1):
        employee_id = f"SYN-{index:05d}"
        hire_date = start + timedelta(days=rng.randint(0, (last_hire_day - start).days))
        campaign = rng.choice(CAMPAIGNS)
        shift = rng.choices(SHIFTS, weights=(0.42, 0.34, 0.24))[0]
        supervisor = SUPERVISORS[(index - 1) % len(SUPERVISORS)]
        prior_experience = max(0.0, min(12.0, rng.gauss(1.4, 1.7)))
        technical_score = round(max(30.0, min(100.0, rng.gauss(74, 12))), 1)
        schedule = "flexible" if rng.random() < 0.62 else "fixed"

        # A deterministic synthetic signal supports real model training; it is
        # not a claim about actual employees or a causal relationship.
        logit = (
            0.30
            + (0.78 if shift == "Noche" else 0.0)
            + (0.42 if campaign == "Ventas" else 0.0)
            + (0.36 if schedule == "fixed" and shift == "Noche" else 0.0)
            - (0.035 * (technical_score - 70))
            - (0.28 * prior_experience)
        )
        probability = 1 / (1 + pow(2.718281828, -logit))
        follow_up_days = (AS_OF - hire_date).days
        early_exit = follow_up_days >= 1 and rng.random() < probability * 0.62
        involuntary_exit = not early_exit and follow_up_days >= 20 and rng.random() < 0.045
        exit_date: date | None = None
        exit_type = ""
        reason = ""

        if early_exit:
            exit_date = hire_date + timedelta(days=rng.randint(1, min(180, follow_up_days)))
            exit_type = "voluntary"
            reason = rng.choices(
                EXIT_REASONS,
                weights=(24, 22, 19, 13, 12, 10),
            )[0]
        elif involuntary_exit:
            exit_date = hire_date + timedelta(days=rng.randint(20, min(330, follow_up_days)))
            exit_type = "involuntary"

        ats.append(
            {
                "employee_id": employee_id,
                "hire_date": hire_date.isoformat(),
                "campaign": campaign,
                "shift": shift,
                "supervisor": supervisor,
                "technical_score": technical_score if rng.random() > 0.035 else "",
                "prior_bpo_experience_years": round(prior_experience, 1)
                if rng.random() > 0.04
                else "",
                "preferred_shift": {"Día": "day", "Tarde": "evening", "Noche": "night"}[shift],
                "schedule_availability": schedule,
                "synthetic_data": "true",
            }
        )
        payroll.append(
            {
                "employee_id": employee_id,
                "exit_date": exit_date.isoformat() if exit_date else "",
                "exit_type": exit_type,
                "recruitment_cost": rng.randint(170_000, 340_000),
                "training_cost": rng.randint(320_000, 690_000),
                "idle_time_cost": rng.randint(80_000, 250_000),
                "synthetic_data": "true",
            }
        )
        performance.append(
            {
                "employee_id": employee_id,
                "performance_score": round(max(35, min(100, rng.gauss(77, 10))), 1),
                "synthetic_data": "true",
            }
        )
        if reason:
            surveys.append(
                {
                    "employee_id": employee_id,
                    "reason": reason,
                    "synthetic_data": "true",
                }
            )

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "ats.csv", ats)
    _write_csv(output_dir / "payroll.csv", payroll)
    _write_csv(output_dir / "performance.csv", performance)
    _write_csv(output_dir / "exit_surveys.csv", surveys or [{"employee_id": "", "reason": ""}])
    metadata = {
        "synthetic_data": True,
        "seed": SEED,
        "as_of": AS_OF.isoformat(),
        "employee_count": EMPLOYEES,
        "sources": ["ats", "payroll", "performance", "exit_surveys"],
        "notice": "Datos totalmente ficticios para demostración; no son evidencia empresarial.",
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return metadata


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    generate_demo(project_root / "data" / "sample")
