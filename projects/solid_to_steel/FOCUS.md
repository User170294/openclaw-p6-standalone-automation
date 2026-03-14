# FOCUS — solid_to_steel

## Estado actual
Proyecto activo con integración local a Advance Steel ya migrada a Named Pipe y pendiente de estabilizar diagnóstico `/status` y extracción de geometría.

## Datos clave
- Objetivo: desarrollo, pruebas y documentación de automatizaciones relacionadas con Advance Steel.
- Canal oficial actual: Named Pipe `\\.\pipe\LilitASPluginPipe`.
- Cliente Python oficial: `scripts/as_query.py`.
- Entrada oficial para levantar entorno correcto: `C:\Users\Public\Desktop\Advance Steel 2025 - English.lnk`
- Archivo base de trabajo: `projects/solid_to_steel/Prueba_1.dwg`
- Launcher estandarizado: `projects/solid_to_steel/launch_advs_project.ps1`
- Estado validado hoy:
  - `/ping` operativo por pipe
  - lectura de elementos desde modelo activo ya validada
  - `/status` todavía con error de estado interno

## Decisiones técnicas vigentes
- Transporte oficial migrado a Named Pipe; HTTP queda solo como fallback temporal.
- El servidor pipe del plugin se expone con `PipeSecurity` abierto para permitir conexiones desde procesos no elevados.
- No arrancar Advance Steel con `acad.exe` genérico; usar siempre el contexto del acceso directo oficial con parámetros `en-US / ADVS / <<ADVS>>`.
- Mantener como base el DWG del proyecto para pruebas reproducibles.
- Tratar despliegues del DLL en `Program Files` como operación sensible por permisos/bloqueos.

## Brechas pendientes (priorizadas)
1. Corregir endpoint `/status` para exponer documento activo y título de ventana de forma confiable.
2. Completar prueba de humo estable por pipe (`/ping`, `/status`, `/elementos`).
3. Continuar Phase 1 del roadmap: extracción de geometría (`/geometria/{handle}`).
4. Reducir dependencia del fallback HTTP y consolidar Named Pipe como único camino.
5. Asegurar flujo reproducible de despliegue del plugin cuando haya que tocar DLL.

## Instrucción de arranque para Lilit
1. Leer `README.md`, `MEMORY.md`, `LOG.md` e `INDEX.csv`.
2. Asumir Named Pipe como canal primario y el acceso directo oficial de Advance Steel como forma correcta de arranque.
3. Si el problema parece de conectividad, validar primero `/ping` y el contexto de inicio de ADVS antes de culpar el cliente Python.
4. Si el pedido toca plugin/DLL en `Program Files`, tratarlo como cambio sensible con riesgo de permisos y bloqueo de archivos.
5. Priorizar estabilizar `/status` antes de ampliar automatizaciones de diagnóstico.
