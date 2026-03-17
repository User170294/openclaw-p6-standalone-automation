# openclaw-p6-standalone-automation

Automatización de Primavera P6 Professional Standalone.

## Estructura

```
projects/P6-Standalone-Automation/   # Proyecto principal
├── scripts/
│   ├── core/          # Flujo productivo (pv_engine, report_generator, etc.)
│   ├── support/       # Inspección y validación
│   ├── mutations/     # Operaciones de escritura controlada
│   └── prototypes/    # Experimentos (no tocar)
├── tests/             # Tests unitarios
└── docs/              # Documentación operativa
```

## Instalación

```bash
pip install -r requirements.txt
python scripts/check_env.py
```

## Uso básico

```bash
# Generar curva PV/EV semanal
python projects/P6-Standalone-Automation/scripts/core/pv_engine.py \
  --db path/to/P6.db \
  --proj-id 26432 \
  --cutoff 2026-03-08 \
  --mode logic \
  --format csv
```

## Tests

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

## Licencia

Uso interno SIMTEXX / OpenClaw.
