# Auditoría de Arquitectura — P6-Standalone-Automation

**Fecha**: 2026-03-12  
**Auditor**: Lilit (OpenClaw)  
**Rama**: `master`  
**Estado de tests**: 7/7 pasando (unittest)

---

## Resumen Ejecutivo

El proyecto tiene una arquitectura sólida con separación clara entre `core/`, `support/`, `mutations/` y `prototypes/`. El motor PV (`pv_engine.py`) está bien diseñado y los tests cubren los casos críticos. Sin embargo, existen inconsistencias de logging, rutas hardcodeadas en scripts de soporte, y ausencia de archivos estándar de proyecto.

---

## Hallazgos

### 🔴 Alta Severidad

| # | Archivo | Descripción |
|---|---------|-------------|
| 1 | `mutations/fix_taskrsrc_type_hh.py` | Ruta hardcodeada a DB. Script ejecuta UPDATE directo sin argparse ni dry-run. **Riesgo**: ejecución accidental sobre DB incorrecta. |
| 2 | `support/analyze_resources_26196.py` | Ruta hardcodeada + PROJ_ID hardcodeado. No usa `p6_utils.open_db()`. |
| 3 | `support/debug_wbs.py` | Ruta hardcodeada + PROJ_ID hardcodeado. No usa `p6_utils.open_db()`. |
| 4 | `support/verify_wbs_crew_split.py` | Ruta hardcodeada + PROJ_ID y WBS_ID hardcodeados. No usa `p6_utils.open_db()`. |

**Ruta problemática común**:
```
C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B - copia_WORK_20260226_145427.db
```

---

### 🟡 Media Severidad

| # | Archivo | Descripción |
|---|---------|-------------|
| 5 | `core/pv_engine.py` | Función `week_label()` genera `ISO2026-W##` para semanas anteriores al ancla. Debería generar `W##` consistente. |
| 6 | `core/*.py` | Mezcla de `print()` para output. No hay uso de `logging`. Dificulta control de verbosidad y redirección. |
| 7 | (raíz) | Ausencia de `requirements.txt`. Dependencias implícitas: `openpyxl`, `sqlite3` (stdlib). |
| 8 | (raíz) | Ausencia de `README.md` en raíz del repo. Solo existe en `projects/P6-Standalone-Automation/`. |
| 9 | (scripts) | Ausencia de `check_env.py` para validar entorno antes de correr scripts. |

---

### 🟢 Baja Severidad

| # | Archivo | Descripción |
|---|---------|-------------|
| 10 | `tests/` | Tests duplicados: `tests/test_pv_engine.py` y `projects/.../tests/test_pv_engine.py` con diferente contenido. Riesgo de divergencia. |
| 11 | `core/report_generator.py` | HTML inline muy extenso (~400 líneas). Considerar extraer a template o archivo separado. |

---

## Propuestas de Cambio

### P1. Corregir `week_label()` (Media)

**Archivo**: `scripts/core/pv_engine.py`

**Antes**:
```python
def week_label(mon: date, anchor: date = DEFAULT_WEEK0) -> str:
    delta = (mon - anchor).days
    if delta < 0:
        iy, iw, _ = mon.isocalendar()
        return f'ISO{iy}-W{iw:02d}'
    return f'W{8 + delta // 7:02d}'
```

**Después**:
```python
def week_label(mon: date, anchor: date = DEFAULT_WEEK0) -> str:
    """Genera etiqueta W## relativa al ancla. W08 = ancla."""
    delta = (mon - anchor).days
    week_num = 8 + delta // 7
    return f'W{week_num:02d}'
```

**Justificación**: Etiquetas consistentes `W05`, `W06`, `W07` para semanas anteriores al ancla en lugar de `ISO2026-W##`.

**Test adicional sugerido**:
```python
def test_week_label_before_anchor(self):
    self.assertEqual(week_label(date(2026, 2, 9)), 'W07')
    self.assertEqual(week_label(date(2026, 2, 2)), 'W06')
```

---

### P2. Refactorizar scripts con rutas hardcodeadas (Alta)

**Patrón propuesto** (ejemplo para `support/debug_wbs.py`):

```python
#!/usr/bin/env python3
"""Inspecciona estructura WBS de un proyecto P6."""

import argparse
import sys
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from p6_utils import open_db


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--db', required=True, help='Ruta a DB SQLite P6')
    ap.add_argument('--proj-id', type=int, required=True, help='PROJ_ID a inspeccionar')
    ap.add_argument('--limit', type=int, default=15, help='Máximo de filas a mostrar')
    args = ap.parse_args()

    con = open_db(args.db)
    cur = con.cursor()
    
    rows = cur.execute(
        'SELECT WBS_ID, PARENT_WBS_ID, WBS_SHORT_NAME, WBS_NAME, SEQ_NUM '
        'FROM PROJWBS WHERE PROJ_ID=? ORDER BY SEQ_NUM, WBS_ID',
        (args.proj_id,)
    ).fetchall()
    
    print(f'COUNT={len(rows)}')
    for r in rows[:args.limit]:
        print(f"{r['WBS_ID']}|{r['PARENT_WBS_ID']}|{r['WBS_SHORT_NAME']}|{r['WBS_NAME']}")
    
    con.close()


if __name__ == '__main__':
    main()
```

**Aplicar a**:
- `mutations/fix_taskrsrc_type_hh.py` — agregar `--dry-run` obligatorio
- `support/analyze_resources_26196.py`
- `support/debug_wbs.py`
- `support/verify_wbs_crew_split.py`

---

### P3. Crear `requirements.txt` (Media)

**Archivo**: `requirements.txt` (raíz)

```
openpyxl>=3.1.0
```

**Nota**: `sqlite3` es stdlib, no requiere instalación.

---

### P4. Crear `check_env.py` (Media)

**Archivo**: `scripts/check_env.py`

```python
#!/usr/bin/env python3
"""Valida entorno antes de correr scripts P6-Standalone-Automation."""

import sys

REQUIRED = ['openpyxl']
OPTIONAL = ['pytest']

def check():
    errors = []
    for pkg in REQUIRED:
        try:
            __import__(pkg)
            print(f'✓ {pkg}')
        except ImportError:
            errors.append(pkg)
            print(f'✗ {pkg} (requerido)')
    
    for pkg in OPTIONAL:
        try:
            __import__(pkg)
            print(f'✓ {pkg} (opcional)')
        except ImportError:
            print(f'○ {pkg} (opcional, no instalado)')
    
    if errors:
        print(f'\nERROR: Instalar paquetes faltantes: pip install {" ".join(errors)}')
        sys.exit(1)
    
    print('\n✓ Entorno OK')


if __name__ == '__main__':
    check()
```

---

### P5. Crear `README.md` en raíz (Media)

**Archivo**: `README.md` (raíz)

```markdown
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
python scripts/core/pv_engine.py \
  --db path/to/P6.db \
  --proj-id 26432 \
  --cutoff 2026-03-08 \
  --mode logic \
  --format csv
```

## Licencia

Uso interno SIMTEXX / OpenClaw.
```

---

### P6. Estandarizar logging (Baja, diferido)

**Propuesta**: Reemplazar `print()` por `logging` en scripts core con nivel configurable.

**Ejemplo de patrón**:
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(message)s'
)
log = logging.getLogger(__name__)

# Uso
log.info(f'MODE={mode}')
log.debug(f'Loaded {len(rows)} rows')
```

**Nota**: Cambio amplio, diferir a sprint posterior para no romper parsers externos que dependen de output actual.

---

## Resumen de Prioridades

| Prioridad | Propuesta | Esfuerzo |
|-----------|-----------|----------|
| 1 | P2: Refactorizar rutas hardcodeadas | ~2h |
| 2 | P1: Corregir `week_label()` | ~15min |
| 3 | P3: Crear `requirements.txt` | ~5min |
| 4 | P4: Crear `check_env.py` | ~10min |
| 5 | P5: Crear `README.md` raíz | ~15min |
| 6 | P6: Estandarizar logging | diferido |

---

## Verificación

Después de aplicar cambios, correr:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

Los 7 tests actuales deben seguir pasando.

---

**Fin del informe.**
