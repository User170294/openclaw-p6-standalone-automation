# Proyecto: P6 Standalone Automation

## Identificación
- Nombre: P6-Standalone-Automation
- Entorno: Primavera P6 Professional Standalone
- Objetivo: Automatizar revisiones y acciones operativas en P6 con control y trazabilidad.
- Estado: Activo

## Alcance
1. Lectura de estado de proyectos/actividades.
2. Validaciones automáticas (fechas, relaciones, restricciones, recursos).
3. Ejecución controlada de cambios pequeños (con logs y rollback definido).
4. Reportes operativos periódicos.
5. Comparación y validación cruzada entre **XER** y **DB SQLite**.

## Principios de operación
- Ejecutar primero en modo dry-run.
- Registrar cada acción relevante en `LOG.md`.
- Confirmación manual para cambios masivos.
- Backup previo a cada corrida con cambios.
- No dar por equivalentes XER y DB sin validación explícita.

## Estado actual
- Base SQLite activa confirmada en `MEMORY.md`.
- Existen scripts productivos para inspección, auditoría, reasignación de recursos, carga segura de avances y reportes semanales.
- El proyecto ya tiene aprendizaje validado para cálculo PV/EV semanal, manejo seguro de cambios sobre XER y carga robusta de avances directo a DB.
- Hay fixtures externos disponibles en `001_Prueba Externa/` para pruebas iniciales.

## Estructura útil
- `scripts/` → automatizaciones, validaciones y utilitarios del proyecto.
- `data/` → salidas, snapshots y reportes de corridas.
- `docs/` → resúmenes y documentación operativa.
- `001_Prueba Externa/` → XER externos para pruebas comparativas.

## Documentos clave
- `MEMORY.md` → decisiones, criterios y aprendizajes vigentes.
- `LOG.md` → bitácora operativa.
- `docs/XER_DB_VALIDATION_FLOW.md` → flujo recomendado para pruebas conjuntas XER + DB.

## Próximo paso recomendado
Ejecutar pruebas controladas del cargador seguro `Excel -> DB` sobre casos acotados y luego cerrar la segunda pieza reusable pendiente: comparador `XER vs DB` totalmente parametrizable.
