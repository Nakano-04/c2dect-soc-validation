"""Prototipo extendido: medicion de deteccion TTD/TTC y comparacion de brazos.

No depende de C2-DECT. Consume registros sinteticos de ejecuciones de tecnicas
y alertas del SOC. Permite (1) medir por tecnica, (2) comparar un brazo de
control contra un brazo de tratamiento con intervalos de confianza y (3)
generar un informe en Markdown.

Contrato de datos
-----------------
execuciones: {"session": str, "technique": str, "t": float}
alertas:     {"session": str, "technique": str, "t": float,
              "true_positive": bool, "contained_t": float | None}

TTD = t_alerta - t_ejecucion. TTC = contained_t - t_ejecucion.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
from pathlib import Path


def load_jsonl(path: str | Path) -> list[dict]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def bootstrap(values: list[float], seed: int = 7, n: int = 2000) -> dict:
    """Media e IC95% por remuestreo bootstrap con semilla determinista."""
    if not values:
        return {"mean": None, "ci95": [None, None], "n": 0}
    rng = random.Random(seed)
    means = sorted(
        statistics.mean(rng.choice(values) for _ in values) for _ in range(n)
    )
    return {
        "mean": round(statistics.mean(values), 4),
        "ci95": [round(means[int(0.025 * n)], 4), round(means[int(0.975 * n) - 1], 4)],
        "n": len(values),
    }


def compute(
    executions: list[dict],
    alerts: list[dict],
    benign_hours: float = 1.0,
    seed: int = 7,
) -> dict:
    """Calcula metricas agregadas y desglosadas por tecnica."""
    if benign_hours <= 0:
        raise ValueError("benign_hours debe ser > 0")

    ttds: list[float] = []
    tcs: list[float] = []
    by_technique: dict[str, dict] = {}

    for ex in executions:
        tech = ex["technique"]
        matching = [
            a
            for a in alerts
            if a.get("session") == ex["session"]
            and a.get("technique") == tech
            and a["t"] >= ex["t"]
        ]
        ttd = min((a["t"] - ex["t"] for a in matching), default=None)
        ttc_values = [
            a["contained_t"] - ex["t"]
            for a in matching
            if a.get("contained_t") is not None
            and a["contained_t"] >= ex["t"]
            and a["contained_t"] >= a["t"]
        ]
        ttc = min(ttc_values, default=None)

        if ttd is not None:
            ttds.append(ttd)
        if ttc is not None:
            tcs.append(ttc)

        bucket = by_technique.setdefault(
            tech, {"executed": 0, "detected": 0, "contained": 0, "ttds": []}
        )
        bucket["executed"] += 1
        if ttd is not None:
            bucket["detected"] += 1
            bucket["ttds"].append(ttd)
        if ttc is not None:
            bucket["contained"] += 1

    tp = sum(1 for a in alerts if a.get("true_positive"))
    fp = len(alerts) - tp

    return {
        "executions": len(executions),
        "detected": len(ttds),
        "contained": len(tcs),
        "recall": round(len(ttds) / len(executions), 4) if executions else None,
        "precision": round(tp / len(alerts), 4) if alerts else None,
        "fp_per_hour": round(fp / benign_hours, 4),
        "ttd": bootstrap(ttds, seed),
        "ttc": bootstrap(tcs, seed),
        "by_technique": {
            tech: {
                "executed": b["executed"],
                "detected": b["detected"],
                "contained": b["contained"],
                "mean_ttd": round(statistics.mean(b["ttds"]), 4) if b["ttds"] else None,
            }
            for tech, b in sorted(by_technique.items())
        },
    }


def compare(control: dict, treatment: dict, seed: int = 11) -> dict:
    """Compara dos resultados `compute` por tecnica comun (pareado)."""
    common = sorted(set(control["by_technique"]) & set(treatment["by_technique"]))
    deltas: list[float] = []
    rows: list[dict] = []
    for tech in common:
        c = control["by_technique"][tech]["mean_ttd"]
        t = treatment["by_technique"][tech]["mean_ttd"]
        if c is None or t is None:
            continue
        delta = round(t - c, 4)
        deltas.append(delta)
        rows.append({"technique": tech, "control": c, "treatment": t, "delta": delta})

    ci = bootstrap(deltas, seed)
    if ci["mean"] is None:
        verdict = "sin-datos"
    elif ci["ci95"][1] is not None and ci["ci95"][1] < 0:
        verdict = "mejora-significativa"
    elif ci["ci95"][0] is not None and ci["ci95"][0] > 0:
        verdict = "retroceso-significativo"
    else:
        verdict = "sin-cambio-significativo"

    return {
        "paired_techniques": len(rows),
        "rows": rows,
        "mean_delta_ttd": ci,
        "verdict": verdict,
    }


def render_markdown(result: dict) -> str:
    lines = [
        "# Informe de medicion de deteccion",
        "",
        "| Metrica | Valor |",
        "|---|---:|",
        f"| Ejecuciones | {result['executions']} |",
        f"| Detectadas | {result['detected']} |",
        f"| Recall | {result['recall']} |",
        f"| Precision | {result['precision']} |",
        f"| FP/hora | {result['fp_per_hour']} |",
        f"| TTD medio | {result['ttd']['mean']} (IC95 {result['ttd']['ci95']}) |",
        f"| TTC medio | {result['ttc']['mean']} (IC95 {result['ttc']['ci95']}) |",
        "",
        "## Por tecnica",
        "",
        "| Tecnica | Ejecutadas | Detectadas | Contenidas | TTD medio |",
        "|---|---:|---:|---:|---:|",
    ]
    for tech, b in result["by_technique"].items():
        lines.append(
            f"| {tech} | {b['executed']} | {b['detected']} | {b['contained']} | {b['mean_ttd']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_compute = sub.add_parser("compute")
    p_compute.add_argument("--executions", required=True)
    p_compute.add_argument("--alerts", required=True)
    p_compute.add_argument("--benign-hours", type=float, default=1.0)
    p_compute.add_argument("--seed", type=int, default=7)
    p_compute.add_argument("--markdown", action="store_true")

    p_compare = sub.add_parser("compare")
    p_compare.add_argument("--control", required=True)
    p_compare.add_argument("--treatment", required=True)
    p_compare.add_argument("--seed", type=int, default=11)

    args = parser.parse_args()
    if args.command == "compute":
        result = compute(
            load_jsonl(args.executions),
            load_jsonl(args.alerts),
            args.benign_hours,
            args.seed,
        )
        print(render_markdown(result) if args.markdown else json.dumps(result, indent=2))
    else:
        print(json.dumps(compare(load_json(args.control), load_json(args.treatment), args.seed), indent=2))


if __name__ == "__main__":
    main()
