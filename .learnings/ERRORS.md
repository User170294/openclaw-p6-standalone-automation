# ERRORS.md — Bitácora de errores recurrentes

> Leer antes de ejecutar cualquier tarea en proyectos activos.
> Actualizar cada vez que se detecte un error nuevo o se repita uno existente.

---

## Error #001 — Formato de respuesta WBS/Cronograma (OT 1844)

| Campo | Detalle |
|-------|---------|
| **Fecha** | 2026-02-22 |
| **Proyecto** | OT-1844 |
| **Descripción** | Al responder consultas de actividades por semana, se usó WBS genérico (Bastidor, Bandeja Perimetral, etc.) SIN agrupar primero por Entrega, como indica el programa XER. Edgardo lo corrigió varias veces. |
| **Causa raíz** | No se leyó el README del proyecto ni se aplicó el formato definido. Se improvisó la estructura de respuesta. |
| **Regla correctiva** | SIEMPRE responder cronograma en formato: **Entrega (hito) → WBS → Actividad → Estado**. Ver sección 10 del README de OT-1844. |
| **Reincidencias** | 2 veces en sesión 2026-02-22 |

---

## Plantilla para nuevo error

```
## Error #XXX — [Título descriptivo]

| Campo | Detalle |
|-------|---------|
| **Fecha** | AAAA-MM-DD |
| **Proyecto** | OT-1844 / General |
| **Descripción** | Qué pasó exactamente |
| **Causa raíz** | Por qué pasó |
| **Regla correctiva** | Qué hacer diferente |
| **Reincidencias** | Cuántas veces se repitió |
```
