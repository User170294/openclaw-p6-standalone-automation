# MEMORY — SOLID_TO_STEEL

## Decisiones vigentes
- Integración local con Advance Steel migrada a transporte **Named Pipe** (`\\.\pipe\LilitASPluginPipe`) para eliminar dependencia de puertos HTTP, URLACL y reglas de firewall.
- Cliente Python oficial del proyecto (`scripts/as_query.py`) usa Named Pipe como canal primario y fallback HTTP solo por compatibilidad temporal.
- El endpoint `/ping` del plugin quedó operativo por pipe.
- El servidor Named Pipe del plugin se crea con `PipeSecurity` abierto (WorldSid / Everyone) para permitir conexión desde procesos no elevados.
- **Arranque oficial del proyecto**: usar el mismo contexto del acceso directo `C:\Users\Public\Desktop\Advance Steel 2025 - English.lnk` (`/language "en-US" /product "ADVS" /p "<<ADVS>>"`). No usar arranque genérico de `acad.exe` sin esos parámetros.

## Convenciones
- Archivo de trabajo base del proyecto: `C:\Users\josej\.openclaw\workspace\projects\solid_to_steel\Prueba_1.dwg`

## Riesgos / bloqueos
- El despliegue del DLL del plugin en `Program Files` requiere permisos de administrador y cierre de Advance Steel para evitar bloqueos de escritura.
- Endpoint `/status` devuelve error interno ("Operation is not valid due to the current state of the object") y debe estabilizarse para diagnóstico automático de documento activo.

## Próximos pasos
- Corregir endpoint `/status` para exponer con fiabilidad `documento_activo` y `titulo_ventana`.
- Validar lectura del modelo activo por pipe con prueba de humo (`/ping`, `/status`, `/elementos`).
- Continuar Phase 1 del roadmap SolidToSteel: extracción de geometría (`/geometria/{handle}`) sobre objetos detectados.
