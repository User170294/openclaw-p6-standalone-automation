# Proyecto: P6 Standalone Automation

## Identificación
- Nombre: P6-Standalone-Automation
- Entorno: Primavera P6 Professional Standalone
- Estado: Activo — fase de aprendizaje con casos reales de producción

## Visión
Agente IA copiloto especializado en Primavera P6 para planificadores de construcción y minería.

**No reemplaza al planificador** — lo hace significativamente más productivo y le permite operar con confianza desde el primer día, incluso sobre programas que no construyó él mismo.

## Capacidades objetivo
1. **Control por lenguaje natural** — el usuario da instrucciones en texto plano y el agente opera la línea base en P6.
2. **Auditoría de schedules heredados** — analiza programas de terceros, explica su configuración, lógica y supuestos en lenguaje humano.
3. **EVM automatizado** — calcula PV, EV, SPI, CPI y métricas derivadas usando metodología validada.
4. **Propuestas de mejora** — no solo reporta, también sugiere qué mejorar y por qué.
5. **Modo enseñanza** — base de conocimiento P6 para usuarios nuevos.
6. **Auto-setup del entorno** — onboarding guiado para nuevos usuarios.
7. **Aprendizaje continuo** — mejora desde casos reales de producción.

## Alcance técnico actual
1. Lectura de estado de proyectos/actividades desde DB SQLite.
2. Validaciones automáticas (fechas, relaciones, restricciones, recursos).
3. Ejecución controlada de cambios (con logs y rollback definido).
4. Reportes operativos semanales (xlsx, md, csv).
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
- `scripts/core/` → flujo productivo principal (carga segura, auditoría, comparación XER/DB, mutación XER, motor PV dual logic/p6_visual).
- `scripts/support/` → inspección, listados, validaciones y utilitarios de apoyo.
- `scripts/mutations/` → mutaciones DB específicas y operaciones controladas.
- `scripts/prototypes/` → prototipos históricos (no usar en producción, ver README interno).
- `scripts/archive_tmp/` → experimentos históricos `tmp_*` archivados para referencia.
- `data/` → salidas, snapshots y reportes de corridas.
- `docs/` → resúmenes y documentación operativa.
- `001_Prueba Externa/` → XER externos para pruebas comparativas (local, fuera de Git por ahora).

## Documentos clave
- `MEMORY.md` → decisiones, criterios y aprendizajes vigentes.
- `LOG.md` → bitácora operativa.
- `docs/XER_DB_VALIDATION_FLOW.md` → flujo recomendado para pruebas conjuntas XER + DB.

## Estrategia de evolución
- **Fase actual:** aprendizaje con casos reales (OT-1844 y otros programas de producción). Cada caso enseña algo que se generaliza.
- **Fase futura:** agente distribuible a otros planificadores — auto-setup, onboarding guiado, sin dependencias hardcodeadas.
- **Regla:** cada mejora debe acercar al objetivo distribuible, no alejarlo.

## Próximo paso recomendado
Validar flujo end-to-end completo (captura Excel → carga DB → engine EVM → reporte xlsx/md) sobre un corte semanal real en producción.
