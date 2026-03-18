# Auditoría de limpieza del workspace
Fecha: 2026-03-18
Modo: revisión segura, sin borrar ni mover archivos
Workspace: `C:\Users\josej\.openclaw\workspace`

## Resumen ejecutivo
Sí hay ruido real en el workspace, pero no conviene hacer una limpieza ciega.

### Núcleo que debe mantenerse
- `projects/`
- `memory/`, `MEMORY.md`, `MEMORY_BRIEF.md`
- `scripts/`
- `skills/`
- `docs/`
- `artifacts/`
- `data/chroma/`, `data/*chunks*.jsonl`, `data/bm25_cache/` **si se seguirá usando RAG**
- `repos/openclaw-p6-standalone-automation/` **si sigue siendo la fuente Git oficial**
- `as_plugin/` e `integrations/advance-steel-plugin/` **si la integración Advance Steel sigue activa**

### Ruido principal detectado
1. `tmp/` contiene una gran cantidad de scripts y salidas experimentales.
2. La raíz contiene archivos temporales sueltos (`tmp_*`, `.htm`, `.xlsx`, etc.).
3. `downloads/` guarda instaladores/zip pesados que no son parte del flujo operativo diario.
4. `data/` mezcla insumos activos con snapshots/zip históricos.
5. Existe probable solape entre:
   - `projects/P6-Standalone-Automation`
   - `repos/openclaw-p6-standalone-automation`

---

## Inventario por zonas

### 1) Mantener como base operativa
#### `projects/`
Estructura consistente y activa:
- `projects/Bodega-Simtexx`
- `projects/OT-1844`
- `projects/P6-Standalone-Automation`
- `projects/finanzas`
- `projects/solid_to_steel`

Cada proyecto relevante tiene archivos de foco/contexto (`FOCUS.md`, `README.md`, `MEMORY.md`, `LOG.md`, etc.).

**Conclusión:** mantener.

#### `memory/`
Memoria de trabajo, preferencias, pendientes y episodios.

**Conclusión:** mantener.

#### `scripts/`
Contiene utilitarios reutilizables y no se ve, en general, como basura temporal.

**Conclusión:** mantener; revisar solo si algún script de prueba quedó mal ubicado.

#### `skills/`
Se detectan skills activas y específicas del entorno.

**Conclusión:** mantener.

#### `artifacts/` y `docs/`
Sirven para documentación y entregables reutilizables.

**Conclusión:** mantener.

---

### 2) Candidatos fuertes a limpieza o archivado
#### `tmp/`
Contenido detectado:
- decenas de scripts de prueba/inspección (`inspect_*`, `peek_*`, `check_*`, `verify_*`, `compare_*`, `analyze_*`, `apply_*`, `emit_*`)
- reportes CSV temporales
- entregables puntuales como:
  - `tmp/OT1844_W11.pdf`
  - `tmp/OT1844_W11.pptx`

**Diagnóstico:** esta carpeta es la principal fuente de ruido.

**Acción recomendada:**
- no borrar en bloque;
- clasificar en 3 grupos:
  1. scripts descartables,
  2. entregables que deben ir a `projects/<proyecto>/reports/`,
  3. prototipos que deben absorberse en `scripts/` o en un repo proyecto si siguen vigentes.

#### Archivos temporales sueltos en raíz
Detectados, entre otros:
- `tmp_informe.xlsx`
- `tmp_munizaga_reset.xlsx`
- `tmp_generate_excel_report_26483.py`
- `tmp_generate_excel_report_pro.py`
- `tmp_generate_official_report_26483.py`
- `tmp_oracle_activities_window.htm`
- `tmp_read_pdf_style.py`
- `tmp_schema_check.py`
- archivo anómalo `%s` (vacío)

**Diagnóstico:** no deberían vivir en la raíz.

**Acción recomendada:**
- mover a `tmp/archivo_suelto/` o a su proyecto correspondiente;
- eliminar el archivo `%s` con alta confianza cuando se autorice limpieza.

#### `.pytest_cache/`
Basura de ejecución de pruebas.

**Acción recomendada:** eliminar seguro.

#### `downloads/`
Peso aproximado: **33M**
Incluye, por ejemplo:
- `downloads/cocoon/CocoonSuite2025_for_AdvanceSteel2025.zip`
- `downloads/cocoon/extracted/CocoonSuite2025 for AdvanceSteel2025.exe`

**Diagnóstico:** no parece parte del workspace operativo diario.

**Acción recomendada:** mover a archivo externo/instaladores fuera del workspace si todavía se quieren conservar.

#### `backups/`
Peso aproximado: **804K**
No es grande, pero sí agrega desorden conceptual.

**Acción recomendada:** mantener solo si esos respaldos aún son referencia; si no, mover a un archivo histórico externo.

#### `exports/`
Peso aproximado: **104K**
No es grave, pero es zona típica de salida temporal.

**Acción recomendada:** revisar por antigüedad/uso.

---

### 3) Revisar antes de tocar
#### `data/`
Peso aproximado: **128M**

Contiene mezcla de activos y no activos:
- activos probables:
  - `data/chroma/chroma.sqlite3`
  - `data/chroma/...`
  - `data/bm25_cache/*.json`
  - `data/ot-1844_chunks.jsonl`
  - `data/p6-standalone-automation_chunks.jsonl`
  - `data/solid_to_steel_chunks.jsonl`
- históricos o prescindibles según uso:
  - `data/openclaw-code-no-vendor.zip`
  - `data/openclaw-source-2026.2.21-2.zip`
  - `data/ot-1844_chunks.bak.jsonl`
  - `data/pdf_extract_ocr_test/*`
  - `data/ingest_tmp/*`

**Diagnóstico:** no limpiar sin criterio porque aquí vive parte del RAG.

**Acción recomendada:**
- conservar motor RAG (`chroma`, `bm25`, `chunks activos`);
- archivar zips/snapshots y material de pruebas OCR si ya cumplieron su función.

#### `graph-mail/`
Peso aproximado: **416K**
Contiene scripts y caches de correo.

**Diagnóstico:** puede ser útil, pero no es claramente core si esa línea ya no está activa.

**Acción recomendada:** revisar continuidad real antes de mover/eliminar.

#### `as_plugin/` e `integrations/advance-steel-plugin/`
Puede haber solape entre fuente, build y despliegue.

**Acción recomendada:** definir explícitamente:
- fuente oficial del código,
- carpeta de compilación,
- carpeta de despliegue.

#### `repos/openclaw-p6-standalone-automation/` vs `projects/P6-Standalone-Automation`
Se detecta una estructura duplicada o parcialmente espejada.

`repos/openclaw-p6-standalone-automation` contiene:
- `.git`
- `projects/P6-Standalone-Automation`
- `memory/`
- `tests/`
- `README.md`

`projects/P6-Standalone-Automation` en el workspace principal contiene además:
- `app.py`
- `scripts/`
- `docs/`
- `tests/`
- `data/`
- `001_Prueba Externa/`

**Diagnóstico:** hay riesgo de confusión sobre cuál es la fuente de verdad.

**Acción recomendada:** decidir una de estas opciones:
1. `repos/openclaw-p6-standalone-automation` como repo oficial y `projects/P6-Standalone-Automation` como solo documentación/datos;
2. o consolidar todo en un solo repo/proyecto y eliminar duplicación.

---

## Tamaños relevantes detectados
- `data/` ≈ 128M
- `repos/` ≈ 43M
- `downloads/` ≈ 33M
- `tmp/` ≈ 26M
- `projects/` ≈ 26M

Archivos grandes destacados:
- `data/chroma/chroma.sqlite3` ≈ 43.2M
- `data/openclaw-source-2026.2.21-2.zip` ≈ 20.8M
- `data/openclaw-code-no-vendor.zip` ≈ 19.5M
- `tmp/OT1844_W11.pptx` ≈ 18.4M
- `downloads/cocoon/extracted/CocoonSuite2025 for AdvanceSteel2025.exe` ≈ 17.1M
- `downloads/cocoon/CocoonSuite2025_for_AdvanceSteel2025.zip` ≈ 17.0M

---

## Clasificación propuesta

### Mantener
- `projects/`
- `memory/`
- `scripts/`
- `skills/`
- `artifacts/`
- `docs/`
- `repos/` (hasta resolver consolidación)
- `data/chroma/`
- `data/bm25_cache/`
- `data/*chunks*.jsonl` activos
- `as_plugin/`
- `integrations/`

### Archivar o mover fuera del workspace
- `downloads/`
- `data/openclaw-*.zip`
- `backups/` (si solo son históricos)
- `exports/` (si ya no se usan)
- entregables finales que hoy están en `tmp/`

### Eliminar seguro cuando se autorice
- `.pytest_cache/`
- `%s`
- archivos temporales claros en raíz (`tmp_*` sueltos mal ubicados)
- `__pycache__/` dentro de proyectos/repos
- pruebas OCR o ingest temporales ya cerradas (`data/pdf_extract_ocr_test`, parte de `data/ingest_tmp`) **solo tras validar que no dependen de un flujo vigente**

---

## Plan recomendado sin romper nada

### Fase 1 — Limpieza segura mínima
- eliminar caches y basura inequívoca;
- mover temporales de raíz a una carpeta de cuarentena;
- no tocar `projects/`, `memory/`, `scripts/`, `skills/`, `data/chroma`.

### Fase 2 — Reordenamiento
- mover entregables desde `tmp/` a `projects/<proyecto>/reports/`;
- mover instaladores y snapshots zip a almacenamiento externo o `archive/` fuera del workspace principal.

### Fase 3 — Consolidación estructural
- resolver la dualidad entre `projects/P6-Standalone-Automation` y `repos/openclaw-p6-standalone-automation`;
- resolver el modelo fuente/build/deploy de Advance Steel plugin.

---

## Recomendación final
No conviene una poda agresiva todavía. Conviene hacer primero una **limpieza conservadora y reversible**, centrada en:
1. caches,
2. temporales sueltos,
3. `tmp/`,
4. instaladores/snapshots fuera del flujo.

Eso bajará bastante el ruido sin tocar lo que parece estar vivo.
