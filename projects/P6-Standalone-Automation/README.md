# Proyecto: P6 Standalone Automation

## Identificación
- Nombre: P6-Standalone-Automation
- Entorno: Primavera P6 Professional Standalone
- Objetivo: Automatizar revisiones y acciones operativas en P6 con control y trazabilidad.
- Estado: Inicializado

## Alcance inicial
1. Lectura de estado de proyectos/actividades.
2. Validaciones automáticas (fechas, relaciones, restricciones, recursos).
3. Ejecución controlada de cambios pequeños (con logs y rollback definido).
4. Reportes operativos periódicos.

## Principios de operación
- Ejecutar primero en modo dry-run.
- Registrar cada acción en LOG.md.
- Confirmación manual para cambios masivos.
- Backup previo a cada corrida con cambios.

## Próximo paso
Definir primera rutina piloto (ej: validación de actividades sin predecesoras y hitos vencidos).