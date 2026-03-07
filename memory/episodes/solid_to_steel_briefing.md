# SolidToSteel — Briefing inicial

Fecha: 2026-03-07 (UTC-3)

## Problema
Los modelos DWG de AutoCAD puro usan sólidos 3D genéricos (AcDb3dSolid), muchas veces dentro de bloques. En Advance Steel 2025 esos elementos no se reconocen como estructurales nativos (sin perfil, material, peso ni integración con BOM/fabricación), forzando recreación manual lenta, propensa a errores y poco escalable.

## Objetivo del proyecto
Desarrollar un motor de conversión automática que:
1. Detecte bloques con sólidos 3D.
2. Explote bloques para exponer sólidos individuales.
3. Analice geometría (bounding box, volumen, sección transversal).
4. Clasifique elementos (placa, viga, columna, tubo RHS/SHS, ángulo, canal, perno).
5. Busque perfil más cercano en catálogo ICHA o ASTM.
6. Permita asignar material por elemento.
7. Reemplace el sólido genérico por objeto nativo de Advance Steel con perfil, material y peso correctos.

## Stack técnico actual
- Plugin LilitASPlugin (.NET 8) embebido en Advance Steel.
- Endpoint base: http://localhost:18850
- Endpoints operativos: /ping, /elementos, /elemento/{handle}
- Scripts Python: workspace/scripts/as_query.py
- Próximos endpoints: /geometria/{handle}, /explotar/{handle}

## Fases
- Phase 0: Infraestructura HTTP — COMPLETA
- Phase 1: Extracción de geometría — PENDIENTE
- Phase 2: Motor de clasificación — PENDIENTE
- Phase 3: Catálogos de perfiles ICHA/ASTM — PENDIENTE
- Phase 4: Motor de conversión — PENDIENTE
- Phase 5: BOM y reportes — PENDIENTE

## Ruta oficial del proyecto
C:\Users\josej\.openclaw\workspace\projects\solid_to_steel\

## Modo de trabajo acordado
Cuando José indique avanzar una fase, se ejecutará la instrucción específica, se reportarán resultados y se registrará progreso en memoria episódica.