# Proyecto: Bodega Simtexx

## Identificación
- Nombre: Bodega Simtexx
- Tipo: Gestión operativa interna
- Estado: En diseño
- Responsable: Edgardo + Lilit

## Objetivo
Diseñar e implementar un sistema práctico para la **cuadratura de insumos** y la **trazabilidad de entrada/salida** en bodegas de Simtexx.

## Alcance inicial
1. Estandarizar cómo se registra entrada y salida por bodega.
2. Definir reglas de cuadratura (físico vs sistema).
3. Implementar trazabilidad por lote/ítem/movimiento.
4. Diseñar reportes operativos (diario/semanal/mensual).

## Entregables esperados
- Mapa de proceso actual (AS-IS).
- Proceso objetivo (TO-BE) con roles y validaciones.
- Diccionario de datos mínimo viable.
- Plantillas de registro y control.
- Tablero de control con KPIs base.

## KPIs propuestos (base)
- Exactitud inventario (% coincidencia físico/sistema)
- Diferencia de cuadratura (CLP y unidades)
- Tasa de movimientos sin respaldo (%)
- Tiempo de cierre de cuadratura (horas)
- Trazabilidad completa por movimiento (%)

## Estructura sugerida
- `docs/` documentación funcional y de procesos
- `data/` extractos y datos de prueba
- `reports/` reportes y cortes de avance
- `templates/` formatos de recepción/salida/ajuste

## Próximo paso inmediato
Levantar el proceso actual por bodega y definir el dato mínimo obligatorio por movimiento.