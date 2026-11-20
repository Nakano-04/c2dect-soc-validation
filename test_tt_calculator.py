"""Tests del prototipo extendido de medicion (datos sinteticos)."""

import unittest
from pathlib import Path

from tt_calculator import bootstrap, compare, compute, load_json, load_jsonl, render_markdown

HERE = Path(__file__).resolve().parent

EXECUTIONS = [
    {"session": "s1", "technique": "T1059", "t": 0.0},
    {"session": "s2", "technique": "T1059", "t": 10.0},
    {"session": "s3", "technique": "T1021", "t": 20.0},
    {"session": "s4", "technique": "T1071", "t": 30.0},
]

ALERTS = [
    {"session": "s1", "technique": "T1059", "t": 3.0, "true_positive": True, "contained_t": None},
    {"session": "s3", "technique": "T1021", "t": 25.0, "true_positive": True, "contained_t": 28.0},
    {"session": "s4", "technique": "T1071", "t": 31.0, "true_positive": True, "contained_t": 33.0},
    {"session": "sX", "technique": "T1059", "t": 99.0, "true_positive": False, "contained_t": None},
]


class TestCompute(unittest.TestCase):
    def test_metricas_agregadas(self):
        r = compute(EXECUTIONS, ALERTS, benign_hours=4.0)
        self.assertEqual(r["executions"], 4)
        self.assertEqual(r["detected"], 3)
        self.assertEqual(r["contained"], 2)
        self.assertEqual(r["recall"], 0.75)
        self.assertEqual(r["precision"], 0.75)
        self.assertEqual(r["fp_per_hour"], 0.25)
        self.assertEqual(r["ttd"]["mean"], 3.0)
        self.assertEqual(r["ttc"]["mean"], 5.5)

    def test_por_tecnica(self):
        r = compute(EXECUTIONS, ALERTS)
        self.assertEqual(r["by_technique"]["T1021"]["mean_ttd"], 5.0)
        self.assertEqual(r["by_technique"]["T1059"]["detected"], 1)
        self.assertEqual(r["by_technique"]["T1059"]["contained"], 0)

    def test_contencion_anterior_a_ejecucion_no_cuenta(self):
        alerts = [{"session": "s1", "technique": "T1059", "t": 3.0,
                   "true_positive": True, "contained_t": 0.5}]
        r = compute([EXECUTIONS[0]], alerts)
        self.assertEqual(r["contained"], 0)
        self.assertEqual(r["detected"], 1)

    def test_benign_hours_invalido(self):
        with self.assertRaises(ValueError):
            compute(EXECUTIONS, ALERTS, benign_hours=0)

    def test_sin_alertas(self):
        r = compute(EXECUTIONS, [])
        self.assertEqual(r["recall"], 0.0)
        self.assertIsNone(r["ttd"]["mean"])


class TestEstadisticaYReporte(unittest.TestCase):
    def test_bootstrap_determinista(self):
        a = bootstrap([1.0, 2.0, 3.0, 4.0], seed=42)
        b = bootstrap([1.0, 2.0, 3.0, 4.0], seed=42)
        self.assertEqual(a, b)
        self.assertLessEqual(a["ci95"][0], a["mean"])
        self.assertGreaterEqual(a["ci95"][1], a["mean"])

    def test_render_markdown(self):
        md = render_markdown(compute(EXECUTIONS, ALERTS))
        self.assertIn("# Informe de medicion de deteccion", md)
        self.assertIn("| T1059 |", md)
        self.assertIn("IC95", md)


class TestComparacion(unittest.TestCase):
    def test_compara_brazos(self):
        result = compare(
            load_json(HERE / "fixtures" / "control.json"),
            load_json(HERE / "fixtures" / "treatment.json"),
        )
        self.assertEqual(result["paired_techniques"], 2)
        self.assertEqual(result["mean_delta_ttd"]["mean"], -4.0)
        self.assertEqual(result["verdict"], "mejora-significativa")

    def test_sin_tecnicas_comunes(self):
        result = compare(
            {"by_technique": {"T1": {"mean_ttd": 1.0}}},
            {"by_technique": {"T2": {"mean_ttd": 2.0}}},
        )
        self.assertEqual(result["verdict"], "sin-datos")

    def test_fixtures_jsonl_validas(self):
        self.assertEqual(len(load_jsonl(HERE / "fixtures" / "executions.jsonl")), 4)
        self.assertEqual(len(load_jsonl(HERE / "fixtures" / "alerts.jsonl")), 4)


if __name__ == "__main__":
    unittest.main()
