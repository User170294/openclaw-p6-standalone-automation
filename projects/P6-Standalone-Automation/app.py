"""
P6-Standalone-Automation Web App

Interfaz Streamlit para operar el motor EVM y scripts de carga/captura/auditoría.
"""

import streamlit as st
import sys
import sqlite3
import subprocess
import pandas as pd
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional
import argparse

# Configurar paths para importar módulos
SCRIPTS_ROOT = Path(__file__).parent / "scripts"
CORE_ROOT = SCRIPTS_ROOT / "core"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))
if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))

from p6_utils import open_db
from pv_engine import load as load_pv, compute, compare
from report_generator import generate_report, enrich_report


# ============================================================================
# Configuración de Streamlit
# ============================================================================

st.set_page_config(
    page_title="P6-Standalone-Automation",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📊 P6-Standalone-Automation")
st.markdown("**Motor EVM + Captura + Carga + Auditoría**")


# ============================================================================
# Session State
# ============================================================================

if "db_path" not in st.session_state:
    st.session_state.db_path = ""
if "connected" not in st.session_state:
    st.session_state.connected = False
if "projects" not in st.session_state:
    st.session_state.projects = []


# ============================================================================
# Sidebar — DB Connection & Project Discovery
# ============================================================================

with st.sidebar:
    st.header("⚙️ Configuración")

    # DB path input
    db_path = st.text_input(
        "Ruta de base de datos (.db)",
        value=st.session_state.db_path,
        help="Ruta absoluta a la base de datos SQLite P6"
    )
    st.session_state.db_path = db_path

    # Connect button
    if st.button("🔌 Conectar", use_container_width=True):
        if not db_path:
            st.error("⚠️ Ingresa una ruta válida")
        elif not Path(db_path).exists():
            st.error(f"❌ Archivo no encontrado: {db_path}")
        else:
            try:
                con = open_db(db_path)
                cur = con.cursor()
                rows = cur.execute(
                    "SELECT PROJ_ID, PROJ_SHORT_NAME FROM PROJECT ORDER BY PROJ_SHORT_NAME"
                ).fetchall()
                st.session_state.projects = [(r[0], r[1]) for r in rows]
                st.session_state.connected = True
                con.close()
                st.success(f"✅ Conectado | {len(st.session_state.projects)} proyecto(s)")
            except Exception as e:
                st.error(f"❌ Error al conectar: {str(e)}")
                st.session_state.connected = False

    # Status indicator
    if st.session_state.connected:
        st.markdown("🟢 **Conectado**")
        st.divider()

        # Project selection
        if st.session_state.projects:
            st.subheader("Proyectos")
            for proj_id, proj_short in st.session_state.projects[:10]:
                st.caption(f"**{proj_short}** ({proj_id})")
            if len(st.session_state.projects) > 10:
                st.caption(f"... y {len(st.session_state.projects) - 10} mas")
    else:
        st.markdown("🔴 **No conectado**")


# ============================================================================
# Main Content — Tabs
# ============================================================================

if not st.session_state.connected:
    st.info("📌 Conecta una base de datos desde el sidebar para comenzar")
else:
    tab_evm, tab_capture, tab_load, tab_audit = st.tabs(
        ["🎯 EVM", "📸 Captura", "📥 Carga", "✅ Auditoría"]
    )

    # ========================================================================
    # Tab 1: EVM
    # ========================================================================
    with tab_evm:
        st.header("Motor EVM")
        st.markdown("Calcula PV / EV / Remaining / Forecast")

        col1, col2, col3 = st.columns(3)
        with col1:
            pv_proj_id = st.number_input(
                "PV proj_id (baseline)",
                value=26258,
                help="ID del programa baseline (Planned Value)"
            )
        with col2:
            ev_proj_id = st.number_input(
                "EV proj_id (actualizado)",
                value=26485,
                help="ID del programa actualizado (Earned Value)"
            )
        with col3:
            cutoff_date = st.date_input(
                "Corte (cutoff)",
                value=datetime.now().date() - timedelta(days=3),
            )

        mode_col, fmt_col = st.columns(2)
        with mode_col:
            mode = st.selectbox("Modo", ["logic", "p6_visual"])
        with fmt_col:
            out_format = st.selectbox("Formato reporte", ["xlsx", "md"])

        project_name = st.text_input("Nombre del proyecto (para reporte)", value="OT-1844")

        if st.button("🚀 Calcular EVM", key="btn_evm", use_container_width=True):
            try:
                # Simulación de args para load()
                class Args:
                    def __init__(self):
                        self.mode = mode
                        self.cutoff = cutoff_date.strftime("%Y-%m-%d")
                        self.base_xer = None
                        self.upd_xer = None
                        self.db = st.session_state.db_path
                        self.proj_id = ev_proj_id
                        self.baseline_proj_id = pv_proj_id

                args = Args()

                with st.spinner("Cargando datos y calculando..."):
                    payload = load_pv(args)
                    payload['mode'] = mode
                    payload['proj_name'] = project_name
                    payload['cutoff'] = datetime.strptime(args.cutoff, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                    result = compute(payload)
                    report = compare(result)

                # Display metrics
                st.subheader("📈 Métricas Principales")
                kpis = enrich_report(report)['kpis']

                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    st.metric("BAC (HH)", f"{kpis['bac']:,.1f}")
                with m2:
                    st.metric("EV (HH)", f"{kpis['ev']:,.1f}")
                with m3:
                    spi_val = kpis['spi'] or 0
                    st.metric("SPI", f"{spi_val:.4f}", delta="✓ On Track" if spi_val >= 0.9 else "⚠️ Behind")
                with m4:
                    forecast = report.get('forecast_week', 'N/A')
                    st.metric("Forecast", f"W{forecast}" if forecast != 'N/A' else "N/A")

                # Weekly table
                st.subheader("📊 Tabla Semanal")
                rows = report.get('rows', [])
                if rows:
                    df = pd.DataFrame(rows)
                    st.dataframe(df, use_container_width=True, height=300)

                # S-curve chart
                st.subheader("📉 Curva S (PV vs EV)")
                if rows:
                    chart_data = pd.DataFrame({
                        'Week': [r['week'] for r in rows],
                        'PV': [r['pv_cum'] for r in rows],
                        'EV': [r['ev_cum'] for r in rows],
                    })
                    st.line_chart(chart_data.set_index('Week'))

                # Download report
                st.subheader("📥 Descargar Reporte")
                with tempfile.TemporaryDirectory() as tmpdir:
                    out_path = generate_report(report, tmpdir, out_format, {'project_name': project_name})
                    with open(out_path, 'rb') as f:
                        st.download_button(
                            label=f"📄 Descargar {out_format.upper()}",
                            data=f.read(),
                            file_name=out_path.name,
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if out_format == 'xlsx' else 'text/markdown',
                            use_container_width=True
                        )

                st.success("✅ Cálculo completado")

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.write(e)

    # ========================================================================
    # Tab 2: Captura
    # ========================================================================
    with tab_capture:
        st.header("Generar Captura de Avances")
        st.markdown("Genera un Excel con actividades listas para captura")

        col1, col2, col3 = st.columns(3)
        with col1:
            cap_proj_id = st.number_input(
                "EV proj_id",
                value=26485,
                key="cap_proj_id",
                help="Proyecto de donde extraer actividades"
            )
        with col2:
            iso_week = st.text_input(
                "Semana ISO (ej: 2026-W11)",
                value="2026-W11",
                help="Formato ISO Week: YYYY-WNN"
            )
        with col3:
            cap_filename = st.text_input(
                "Nombre archivo",
                value="capture.xlsx",
                help="Nombre del archivo Excel a generar"
            )

        if st.button("📸 Generar Captura", use_container_width=True):
            st.info("ℹ️ Script de captura (`generate_progress_capture_excel.py`) no configurado aún")
            st.info(f"Parámetros: proj_id={cap_proj_id}, week={iso_week}, out={cap_filename}")

    # ========================================================================
    # Tab 3: Carga
    # ========================================================================
    with tab_load:
        st.header("Cargar Avances")
        st.markdown("Carga datos desde Excel de captura → Base de datos")

        col1, col2 = st.columns(2)
        with col1:
            load_proj_id = st.number_input(
                "EV proj_id",
                value=26485,
                key="load_proj_id"
            )

        uploaded_file = st.file_uploader(
            "Sube Excel de captura (.xlsx)",
            type=['xlsx'],
            help="Archivo generado en la pestaña Captura"
        )

        if uploaded_file:
            st.info(f"📂 Archivo: {uploaded_file.name}")

            with st.expander("⚙️ Opciones avanzadas"):
                def_start_hour = st.number_input("Hora inicio por defecto", value=8, min_value=0, max_value=23)
                def_end_hour = st.number_input("Hora fin por defecto", value=17, min_value=0, max_value=23)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("👁️ Ver Preview (dry-run)", use_container_width=True):
                    st.info("ℹ️ Script de carga (`load_progress_excel_to_p6db.py`) no configurado aún")
                    st.info(f"Parámetros: proj_id={load_proj_id}, archivo={uploaded_file.name}")

            with col2:
                if st.button("✅ Aplicar Carga", use_container_width=True):
                    st.error("❌ Ejecuta primero 'Ver Preview'")

    # ========================================================================
    # Tab 4: Auditoría
    # ========================================================================
    with tab_audit:
        st.header("Auditoría de Proyecto")
        st.markdown("Ejecuta validaciones post-carga")

        audit_proj_id_mode = st.radio(
            "Auditar",
            ["Proyecto específico", "Toda la BD"],
            horizontal=True
        )

        if audit_proj_id_mode == "Proyecto específico":
            audit_proj_id = st.number_input(
                "proj_id",
                value=26485,
                key="audit_proj_id"
            )
        else:
            audit_proj_id = None

        if st.button("✅ Ejecutar Auditoría", use_container_width=True):
            st.info("ℹ️ Script de auditoría (`pilot_audit.py`) no configurado aún")
            st.info(f"Parámetros: proj_id={audit_proj_id or 'todas'}")


# ============================================================================
# Footer
# ============================================================================

st.divider()
st.markdown(
    """
    ---
    **P6-Standalone-Automation** | [FOCUS.md](focus.md) | [MEMORY.md](memory.md) | [CLAUDE.md](CLAUDE.md)

    Rama: `master` | Motor: pv_engine.py | Tests: 60/60 ✓
    """
)
