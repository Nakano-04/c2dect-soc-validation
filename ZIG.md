# Ejecutable Zig - `tt_calc_zig`

Calculadora TTD/TTC escrita en Zig 0.17.1. Lee dos JSONL y emite un JSON con
ejecuciones, detectadas, contenidas, recall, precisión y tiempos medios.

```powershell
zig build
zig build test
.\zig-out\bin\tt_calc_zig.exe fixtures\executions.jsonl fixtures\alerts.jsonl
```

Resultado esperado sobre las fixtures: 4 ejecuciones, 3 detectadas, 2
contenidas, recall 0.75, precisión 0.75, TTD medio 3.0, TTC medio 5.5.
