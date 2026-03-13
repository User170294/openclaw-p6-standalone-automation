---
name: lilit-operating-rules
description: Reglas operativas personales para trabajar en repos P6/DB/XER con arranque de sesión consistente, validaciones obligatorias, arquitectura DB-first y prevención de errores repetidos antes de editar, testear, commitear o empujar cambios.
---

# SKILL.md

## Checklist de inicio de sesión

Antes de tocar código o datos, debo completar este checklist en orden:

1. Hacer `git pull` de la rama de trabajo correspondiente.
2. Verificar si existe entorno del proyecto; si no existe, usar el Python activo con las dependencias mínimas necesarias.
3. Correr las suites de tests relevantes del repo, separadas si existe riesgo de conflicto de nombres o de contexto.
4. Exigir verde completo en todas las suites relevantes antes de seguir.
5. Leer la memoria y documentación operativa necesaria antes de tomar decisiones técnicas o cambios sensibles.
6. Revisar el historial reciente de commits para entender contexto, dirección y cambios recientes.
7. Confirmar en qué programa/proyecto estoy trabajando y no mezclar rutas, fixtures, DB ni supuestos.

## Reglas operativas que no puedo violar

### 1) Separación estricta de programas
- No debo mezclar OT, programas de prueba, baseline, XER externos ni DB distintas.
- Si trabajo sobre un programa específico, debo identificar explícitamente `PROJ_ID`, baseline asociada, fuente de datos y carpeta del proyecto.
- Si hay duda de contexto, hago menos: primero verifico, después cambio.

### 2) Arquitectura DB-first
- La fuente primaria es **DB SQLite** cuando existe DB activa confirmada.
- XER es secundario: sirve para interoperabilidad, contraste y validación, no como verdad principal cuando existe DB activa confirmada.
- No debo asumir equivalencia entre XER y DB sin validación explícita.

### 3) Cambios seguros en P6
- Todo cambio con impacto en DB o datos operativos parte con respaldo previo.
- Primero trabajo en clon/WORK cuando corresponda; no intervengo la DB principal sin validación.
- Si un cambio toca recursos, HH, costos, fechas o estado, debo verificar consistencia antes de darlo por bueno.

### 4) Regla técnica de labor en P6
- Al crear o reasignar recursos, debo asegurar `RSRC.RSRC_TYPE='RT_Labor'` y `TASKRSRC.RSRC_TYPE='RT_Labor'`.
- No puedo dejar recursos o asignaciones laborales tipadas como material.

### 5) Time-phasing real, no aproximaciones cómodas
- No debo usar reglas simplistas como “fin de actividad” o prorrateo plano si el caso requiere calendario real.
- Para PV/EV/Remaining debo respetar calendario de actividad, horas efectivas, solape real y fechas tempranas/reales según corresponda.
- Para `Remaining Early`, el inicio efectivo debe respetar la fecha temprana real del trabajo remanente y el calendario operativo aplicable.

### 6) Carga DB: sincronizar detalle y resumen
- Si actualizo `TASKRSRC`, debo revisar también los campos resumen de `TASK` usados por la UI de P6.
- En cierres al 100%, debo sincronizar costos (`ACT_REG_COST`, `REMAIN_COST`) y no dejar remanentes inflados.
- No debo cargar fechas ambiguas desde Excel como `00:00` si eso rompe la duración real.

### 7) Validación antes de afirmar
- No confirmo nada sin evidencia: lectura, salida de script, query, diff, test o archivo generado.
- Si falla algo, reporto fallo concreto, causa probable y siguiente intento.
- Si una herramienta devuelve error, no invento éxito ni lo disfrazo.

### 8) Tests en verde antes de cerrar cambios
- No doy por terminado trabajo de código sin tests relevantes en verde.
- Si hay varias suites separadas, corro cada una por separado.
- Si los tests no corren por entorno, detengo el flujo y resuelvo primero el entorno.

### 9) Validación antes de push o commit sensible
- Antes de commitear debo revisar al menos:
  - `git status --short`
  - tests relevantes en verde
  - archivos afectados correctos
  - que no se cuele output transitorio innecesario
- Antes de push, confirmo que el commit refleja exactamente lo que quedó validado.

### 10) No reserializar formatos frágiles si no es necesario
- En XER y otros formatos frágiles, prefiero parche incremental sobre reconstrucción completa.
- Si preservo envolvente/formato nativo, reduzco riesgo de invalidar importaciones o cabeceras.

### 11) Separación obligatoria de curvas y fuentes
- Debo identificar explícitamente de qué proyecto/fuente salen PV, EV, Remaining y cualquier curva derivada.
- No puedo calcular curvas distintas desde una misma fuente por comodidad si el modelo operativo exige separación.
- Antes de correr el engine, debo confirmar qué fuente corresponde a cada curva.

### 12) Validación numérica obligatoria antes de cerrar cambios sensibles
- Si cambié lógica de PV, EV o Remaining, debo reproducir al menos un valor conocido o validado del sistema de referencia antes de commitear.
- Si no tengo acceso a la DB real o a la evidencia de contraste, debo indicarlo explícitamente.
- No puedo asumir que un resultado es correcto solo porque “se ve razonable”.

### 13) No reportar éxito sin evidencia
- No puedo decir "tests en verde" sin mostrar la salida real.
- No puedo decir "reproduce P6" sin mostrar el valor calculado vs el esperado.
- Si no tengo la evidencia, digo "no pude verificar" y explico por qué.

## Los 3 errores que más se repiten y la regla que los evita

### Error 1: usar una simplificación que rompe la lógica real del programa
Ejemplos: repartir remaining desde el cutoff al fin, asumir un calendario fijo, ignorar fechas tempranas, ignorar horas efectivas o calendario real.

**Regla que lo evita:**
> Debo calcular PV/EV/Remaining con calendario real, horas efectivas y fechas correctas del modelo; no puedo reemplazar esa lógica por atajos cómodos sin validación contra P6 o caso testigo.

### Error 2: asumir que una sola tabla o un solo artefacto basta
Ejemplos: actualizar `TASKRSRC` sin sincronizar `TASK`, tratar XER y DB como equivalentes, dar por suficiente un valor agregado sin revisar el reflejo en UI o tablas resumen.

**Regla que lo evita:**
> Debo validar consistencia entre fuente primaria, tablas resumen y salida visible del sistema antes de cerrar un cambio operativo.

### Error 3: romper el flujo por no verificar entorno o formato antes de ejecutar
Ejemplos: correr tests en un runner incorrecto, dependencias faltantes o errores por formato frágil al reconstruir un artefacto completo.

**Regla que lo evita:**
> Antes de ejecutar o automatizar, debo verificar entorno, comando real, dependencias y formato del artefacto; primero compatibilidad, después ejecución.

## Criterio de cierre
- Si no hay tests en verde, evidencia verificable y consistencia con estas reglas, no debo dar el trabajo por cerrado.
