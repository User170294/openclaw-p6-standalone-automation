# Streamlit Web App — Setup & Verification

## Instalación de dependencias

```bash
pip install -r requirements.txt
```

Verifica que se instalen:
- `streamlit>=1.32.0`
- `openpyxl>=3.1.0`
- `pandas>=2.0.0`
- `pytest>=7.0.0` (ya existía)

## Ejecución

```bash
streamlit run app.py
```

Abre http://localhost:8501 en el navegador.

## Verificación de funcionalidad

### Tab EVM (✓ Completamente funcional)

1. **Sidebar**: Conectar DB
   - Input: Ruta de base de datos SQLite
   - Botón "Conectar" valida archivo y consulta proyectos desde tabla `PROJECT`
   - Muestra lista de proyectos disponibles (PROJ_ID + nombre)

2. **Tab 1 — EVM**: Calcular métricas
   - Inputs: PV proj_id (default 26258), EV proj_id (default 26485), cutoff date, modo (logic/p6_visual), formato reporte (xlsx/md)
   - Botón "Calcular EVM": Integración directa con módulo `pv_engine.py`
   - Outputs:
     - 4 métricas (BAC, EV, SPI, Forecast) en cards
     - Tabla semanal con DataFrame
     - Gráfico de curva S (PV acum vs EV acum)
     - Botón de descarga de reporte (xlsx o md)

**Caso de prueba OT-1844:**
```
- PV proj_id: 26258
- EV proj_id: 26485
- Cutoff: 2026-03-15
- Esperado: EV ~4669.2 HH, SPI ~0.884
```

### Tab 2 — Captura (ℹ️ Placeholder — requiere script)

Placeholder para `generate_progress_capture_excel.py` (no existe aún en esta rama).
Interfaz lista; requiere que el script sea creado e integrado via subprocess.

### Tab 3 — Carga (ℹ️ Placeholder — requiere script)

Placeholder para `load_progress_excel_to_p6db.py` (no existe aún en esta rama).
Interfaz de 2 pasos (preview dry-run + apply) lista; requiere que el script sea creado.

### Tab 4 — Auditoría (ℹ️ Placeholder — requiere script)

Placeholder para `pilot_audit.py` (no existe aún en esta rama).
Interfaz lista; requiere que el script sea creado.

## Arquitectura

```
app.py
├── Imports:
│   ├── p6_utils.open_db
│   ├── pv_engine: load, compute, compare
│   └── report_generator: generate_report, enrich_report
├── Sidebar (persistente):
│   ├── st.text_input: DB path
│   ├── st.button: Conectar → query PROJECT table
│   └── Status + project list
└── Tabs:
    ├── Tab 1 (EVM):       pv_engine integration
    ├── Tab 2 (Captura):   subprocess stub
    ├── Tab 3 (Carga):     subprocess stub
    └── Tab 4 (Auditoría): subprocess stub
```

## Notas técnicas

- **Paths**: app.py agrega automáticamente `scripts/` y `scripts/core/` a `sys.path` para importar módulos core.
- **Session State**: Persiste `db_path`, `connected`, `projects` en `st.session_state`.
- **Modo**: Compatible con lógica de dos programas (PV baseline ≠ EV actualizado).
- **Reportes**: Usa `generate_report()` de `report_generator.py` con soporte xlsx/md.

## Próximos pasos

1. Crear/portar scripts: `generate_progress_capture_excel.py`, `load_progress_excel_to_p6db.py`, `pilot_audit.py`
2. Integrar via subprocess en Tabs 2-4 con parseo de stdout
3. Agregar validación preflight (si existe en rama actualizada)
4. Test end-to-end contra DB de referencia (OT-1844)

---

**Última actualización**: 2026-03-18
**Estado**: Tab EVM funcional | Tabs 2-4 placeholder
**Tests**: 60/60 core ✓
