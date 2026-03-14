# FOCUS — finanzas

## Estado actual
Proyecto iniciado pero con contexto operativo todavía incompleto; la estructura está limpia y lista para recargar fuentes autorizadas.

## Datos clave
- Objetivo: construir un flujo confiable para gestionar datos financieros, estandarizarlos y automatizar informes.
- Fecha de inicio registrada: 2026-02-25.
- Estado actual registrado: iniciado.
- Fuentes detectadas hoy: ninguna activa registrada.
- `INDEX.csv` fue vaciado deliberadamente para eliminar referencias residuales.
- Riesgos ya identificados:
  - inconsistencia de nombres de cuentas entre hojas/fuentes
  - dependencia de BUSCARX con claves no siempre existentes

## Decisiones técnicas vigentes
- Se ejecutó limpieza de registros sensibles y rutas el 2026-02-26.
- No reutilizar referencias antiguas de fuentes; partir solo desde fuentes autorizadas nuevas.
- El proyecto debe avanzar primero por inventario de datos, diccionario y métricas prioritarias antes de diseñar automatización.
- Mantener foco en confiabilidad de datos antes que en reporting visual.

## Brechas pendientes (priorizadas)
1. Definir y autorizar las fuentes de datos oficiales del proyecto.
2. Levantar inventario completo de tablas, medidas y columnas.
3. Definir métricas financieras prioritarias del negocio.
4. Diseñar arquitectura objetivo de automatización/reporting.
5. Reconstruir `INDEX.csv` con fuentes reales y vigentes.

## Instrucción de arranque para Lilit
1. Leer `README.md`, `MEMORY.md`, `LOG.md` e `INDEX.csv`.
2. Asumir que el proyecto está en fase de discovery; no asumir fuentes históricas ni rutas previas como válidas.
3. Si el usuario pide análisis o automatización, partir por pedir/validar las fuentes autorizadas actuales.
4. Tratar cualquier referencia antigua de archivos o rutas como potencialmente obsoleta hasta confirmación.
5. Si no hay fuentes nuevas, limitar la respuesta a diseño de estructura, métricas y plan de levantamiento.
