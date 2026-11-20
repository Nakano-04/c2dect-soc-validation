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

## Ámbito

Laboratorio aislado, alcance declarado y RoE firmada. Uso exclusivamente
autorizado. Ver `PLANES_INVESTIGACION_4-7.md` para el diseño completo.
