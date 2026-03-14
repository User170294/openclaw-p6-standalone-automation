# FOCUS — Bodega-Simtexx

## Estado actual
Proyecto en diseño con primeros consolidadores de stock ya generados y pendiente de discovery operativo por bodega.

## Datos clave
- Tipo: gestión operativa interna de bodegas SIMTEXX.
- Objetivo central: cuadratura de insumos + trazabilidad de entrada/salida.
- Fuente documental/RAG oficial: `C:\Users\josej\OneDrive - SIMTEXX SPA\OPERACIONES - Documentos\005_Bodega`
- Evidencia operativa ya registrada:
  - consolidado unificado inicial: 528 filas
  - consolidado reprocesado: 914 filas
  - pivote por producto: 490 productos únicos
  - stock enriquecido: 482 productos únicos
- Incidentes relevantes observados: archivos bloqueados intermitentemente (`SM_STOCK CASA MATRIZ.xlsx`, `TE_TERRENO.xlsx`).
- KPIs base definidos: exactitud inventario, diferencia de cuadratura, movimientos sin respaldo, tiempo de cierre, trazabilidad completa.

## Decisiones técnicas vigentes
- Enfoque simple, auditable y escalable.
- Partir con una bodega piloto antes de automatizar a mayor escala.
- Priorizar el dato mínimo obligatorio por movimiento.
- Mantener separación entre proceso AS-IS, proceso TO-BE, plantillas y reportes operativos.
- No asumir estandarización de datos de origen; tratar calidad/inconsistencia como riesgo base.

## Brechas pendientes (priorizadas)
1. Confirmar número de bodegas involucradas y alcance del piloto.
2. Definir sistema origen oficial de datos (ERP, Excel o mixto).
3. Establecer periodicidad de cuadratura por bodega.
4. Asignar responsables por etapa: recepción, despacho, ajuste y aprobación.
5. Formalizar diccionario de datos mínimo viable y reglas de validación.

## Instrucción de arranque para Lilit
1. Leer `README.md`, `MEMORY.md`, `LOG.md` e `INDEX.csv`.
2. Asumir como foco inicial: cuadratura de insumos y trazabilidad de movimientos, no automatización avanzada todavía.
3. Si el pedido implica análisis de datos, verificar primero qué consolidado/reportes existen en `reports/` y si hubo archivos bloqueados en el último corte.
4. No proponer automatización grande antes de cerrar alcance, fuentes oficiales y responsables operativos.
5. Si falta dato estructural del proceso, preguntar por la bodega piloto antes de profundizar.
