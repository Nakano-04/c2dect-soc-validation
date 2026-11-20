# Plan 4 — Validación de SOC con grupo de control

**Solo información y resultados.** Sin código fuente.

## Hipótesis

El uso estructurado de C2-DECT reduce el tiempo de detección y contención de un
SOC frente a un grupo que no lo usa, con control de falsos positivos.

## Métricas

- **TTD**: desde la marca de ejecución de la técnica hasta la primera alerta
  correlacionada. No confundir con `session_dwell_seconds` (dwell de sesión,
  corregido en `TECH_DEBT.md:212`).
- **TTC**: hasta la contención.
- Recall por técnica, precisión y falsos positivos por hora de telemetría benigna.
- Comparación pareada con intervalos de confianza bootstrap.

## Dependencia

Requiere el dataset etiquetado del Plan 7 y un SOC con telemetría equivalente en
ambos brazos. Estado actual: **pendiente de ejecución real en laboratorio**.

## Prototipo verificable

`tt_calculator.py` — calcula TTD/TTC, recall, precisión, FP/hora e IC95% por
bootstrap; compara dos brazos (control vs. tratamiento) por técnica y genera un
informe Markdown. Sin dependencias externas.

```powershell
python -m unittest discover -v
python tt_calculator.py compute --executions fixtures/executions.jsonl --alerts fixtures/alerts.jsonl --benign-hours 4 --markdown
python tt_calculator.py compare --control fixtures/control.json --treatment fixtures/treatment.json
```

Datos: `fixtures/*.jsonl` sintéticos. Resultado medido en `results.json`, con
los SHA256 de las fixtures. CI (GitHub Actions) ejecuta los tests en cada push.

## Dimensión ofensiva

La medición se hace desde el adversario: cada técnica emulada se ejecuta con
marca de tiempo y se observa cuándo la ve el SOC. El brazo de tratamiento usa
C2-DECT para cerrar brechas; el resultado se comparación contra el control.
Las hipótesis y el protocolo están en `c2dect-investigacion/OFENSIVA/`.

## Ámbito

Laboratorio aislado, alcance declarado y RoE firmada. Uso exclusivamente
autorizado. Ver `PLANES_INVESTIGACION_4-7.md` para el diseño completo.
