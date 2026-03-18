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
if "eps_structure" not in st.session_state:
    st.session_state.eps_structure = {}  # {eps_id: [rama1, rama2, ...]}
if "eps_list" not in st.session_state:
    st.session_state.eps_list = []  # [(eps_id, eps_name), ...]


# ============================================================================
# Funciones auxiliares
# ============================================================================

def load_eps_structure(db_path: str) -> tuple[list, dict]:
    """
    Carga la estructura EPS → Ramas desde la DB.
    Retorna: (lista_eps, dict_ramas)
    """
    con = open_db(db_path)
    cur = con.cursor()

    # Obtener todas las EPS (proyectos raíz)
    eps_rows = cur.execute(
        "SELECT PROJ_ID, PROJ_SHORT_NAME FROM PROJECT WHERE ORIG_PROJ_ID IS NULL OR ORIG_PROJ_ID = PROJ_ID ORDER BY PROJ_SHORT_NAME"
    ).fetchall()

    eps_list = [(r[0], r[1]) for r in eps_rows]
    eps_structure = {}

    # Para cada EPS, obtener sus ramas (proyectos hijos)
    for eps_id, eps_name in eps_list:
        rama_rows = cur.execute(
            "SELECT PROJ_ID, PROJ_SHORT_NAME FROM PROJECT WHERE ORIG_PROJ_ID = ? ORDER BY PROJ_SHORT_NAME",
            (eps_id,)
        ).fetchall()
        eps_structure[eps_id] = [(r[0], r[1]) for r in rama_rows]

    con.close()
    return eps_list, eps_structure


# ============================================================================
# Sidebar — DB Connection & EPS Selection
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
            st.error("Ingresa una ruta valida")
        elif not Path(db_path).exists():
            st.error(f"Archivo no encontrado: {db_path}")
        else:
            try:
                eps_list, eps_structure = load_eps_structure(db_path)
                st.session_state.eps_list = eps_list
                st.session_state.eps_structure = eps_structure
                st.session_state.connected = True
                st.success(f"Conectado | {len(eps_list)} EPS")
            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.session_state.connected = False

    # Status indicator
    if st.session_state.connected:
        st.markdown("**🟢 Conectado**")
        st.divider()

        # EPS Selection
        st.subheader("EPS disponibles")

        for eps_id, eps_name in st.session_state.eps_list:
            with st.expander(f"📦 {eps_name} ({eps_id})"):
                ramas = st.session_state.eps_structure.get(eps_id, [])

                if ramas:
                    st.write("**Ramas/Programas:**")
                    for rama_id, rama_name in ramas:
                        st.caption(f"  • {rama_name} ({rama_id})")
                else:
                    st.write("*(Sin ramas)*")
    else:
        st.markdown("**🔴 No conectado**")


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

        # EPS + Rama selection
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Baseline (PV)")
            eps_names_pv = [f"{name} ({eid})" for eid, name in st.session_state.eps_list]
            selected_eps_pv = st.selectbox("EPS", eps_names_pv, key="eps_pv")
            pv_eps_id = int(selected_eps_pv.split("(")[-1].rstrip(")"))

            ramas_pv = st.session_state.eps_structure.get(pv_eps_id, [(pv_eps_id, "Raiz")])
            rama_names_pv = [f"{name} ({rid})" for rid, name in ramas_pv] if ramas_pv else [f"Raiz ({pv_eps_id})"]

            if rama_names_pv:
                selected_rama_pv = st.selectbox("Rama/Programa", rama_names_pv, key="rama_pv")
                pv_proj_id = int(selected_rama_pv.split("(")[-1].rstrip(")"))
            else:
                pv_proj_id = pv_eps_id
                st.write("(Raiz)")

        with col2:
            st.subheader("Actualizado (EV)")
            eps_names_ev = [f"{name} ({eid})" for eid, name in st.session_state.eps_list]
            selected_eps_ev = st.selectbox("EPS", eps_names_ev, key="eps_ev", index=0)
            ev_eps_id = int(selected_eps_ev.split("(")[-1].rstrip(")"))

            ramas_ev = st.session_state.eps_structure.get(ev_eps_id, [(ev_eps_id, "Raiz")])
            rama_names_ev = [f"{name} ({rid})" for rid, name in ramas_ev] if ramas_ev else [f"Raiz ({ev_eps_id})"]

            if rama_names_ev:
                # Por defecto seleccionar la primera rama (generalmente la más reciente)
                selected_rama_ev = st.selectbox("Rama/Programa", rama_names_ev, key="rama_ev", index=0)
                ev_proj_id = int(selected_rama_ev.split("(")[-1].rstrip(")"))
            else:
                ev_proj_id = ev_eps_id
                st.write("(Raiz)")

        # Otros parámetros
        col3, col4 = st.columns(2)
        with col3:
            cutoff_date = st.date_input(
                "Corte (cutoff)",
                value=datetime.now().date() - timedelta(days=3),
            )
        with col4:
            mode = st.selectbox("Modo", ["logic", "p6_visual"])

        col5, col6 = st.columns(2)
        with col5:
            out_format = st.selectbox("Formato reporte", ["xlsx", "md"])
        with col6:
            project_name = st.text_input("Nombre proyecto", value="P6-Report")

        # Calcular button
        if st.button("🚀 Calcular EVM", use_container_width=True, type="primary"):
            try:
                # Crear args para load()
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
                st.subheader("📈 Metricas Principales")
                kpis = enrich_report(report)['kpis']

                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    st.metric("BAC (HH)", f"{kpis['bac']:,.1f}")
                with m2:
                    st.metric("EV (HH)", f"{kpis['ev']:,.1f}")
                with m3:
                    spi_val = kpis['spi'] or 0
                    st.metric("SPI", f"{spi_val:.4f}", delta="On Track" if spi_val >= 0.9 else "Behind")
                with m4:
                    forecast = report.get('forecast_week', 'N/A')
                    st.metric("Forecast", f"W{forecast}" if forecast != 'N/A' else "N/A")

                # Weekly table
                st.subheader("Tabla Semanal")
                rows = report.get('rows', [])
                if rows:
                    df = pd.DataFrame(rows)
                    st.dataframe(df, use_container_width=True, height=300)

                # S-curve chart
                st.subheader("Curva S (PV vs EV)")
                if rows:
                    chart_data = pd.DataFrame({
                        'Week': [r['week'] for r in rows],
                        'PV': [r['pv_cum'] for r in rows],
                        'EV': [r['ev_cum'] for r in rows],
                    })
                    st.line_chart(chart_data.set_index('Week'))

                # Download report
                st.subheader("Descargar Reporte")
                with tempfile.TemporaryDirectory() as tmpdir:
                    out_path = generate_report(report, tmpdir, out_format, {'project_name': project_name})
                    with open(out_path, 'rb') as f:
                        st.download_button(
                            label=f"Descargar {out_format.upper()}",
                            data=f.read(),
                            file_name=out_path.name,
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if out_format == 'xlsx' else 'text/markdown',
                            use_container_width=True
                        )

                st.success("Calculo completado!")

            except Exception as e:
                st.error(f"Error: {str(e)}")
                import traceback
                st.write(traceback.format_exc())

    # ========================================================================
    # Tab 2: Captura
    # ========================================================================
    with tab_capture:
        st.header("Generar Captura de Avances")
        st.info("Script de captura no configurado aun")

    # ========================================================================
    # Tab 3: Carga
    # ========================================================================
    with tab_load:
        st.header("Cargar Avances")
        st.info("Script de carga no configurado aun")

    # ========================================================================
    # Tab 4: Auditoría
    # ========================================================================
    with tab_audit:
        st.header("Auditoria de Proyecto")
        st.info("Script de auditoria no configurado aun")


# ============================================================================
# Footer
# ============================================================================

st.divider()
st.markdown(
    """
    P6-Standalone-Automation | rama: master | tests: 60/60
    """
)
