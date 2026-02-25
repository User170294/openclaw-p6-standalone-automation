# README — OT-1844 · Fabricación Bandejas Agua Lavado Celda

> **Guía de operación para cualquier sesión de asistente.**
> Leer este archivo completo antes de responder cualquier consulta sobre este proyecto.

---

## 1. Identificación del proyecto

| Campo | Valor |
|-------|-------|
| OT interna | **1844** |
| PO cliente (BHP Spence) | **4519143302** |
| ID licitación | **1425** |
| Nombre | Fabricación Bandejas Agua Lavado Celda |
| Empresa | SIMTEXX SPA |
| Cliente | Minera Spence S.A. (BHP) |
| Estado | **En ejecución** |

---

## 2. Decisiones técnicas vigentes (no renegociar sin confirmación de Edgardo)

- **Alcance SIMTEXX**: 10 sistemas de lavado (los otros 5 fueron ejecutados por otra empresa).
- **Material estructura**: Acero **A36**.
- **Tratamiento superficial estructura**: **Esquema de pintura A3** (zinc inorgánico + epóxico + poliuretano). **Sin galvanizado** para este alcance.
- **Material bandejas**: Acero inoxidable **SS316L** (terminación: limpieza, decapado, pasivado).
- **Normativa soldadura referencia**: AWS D1.1.
- **Color RAL estructura**: pendiente confirmar entre RAL 7035 y RAL 5017 (ver RFI-011843).

---

## 3. Hitos de entrega

| Hito | Fecha límite | Descripción |
|------|-------------|-------------|
| 1 | **09-mar-2026** | 2 bandejas en Minera Spence |
| 2 | **16-mar-2026** | 2 bandejas en Minera Spence |
| 3 | **23-mar-2026** | 2 bandejas en Minera Spence |
| 4 | **30-mar-2026** | 2 bandejas en Minera Spence |
| 5 | **06-abr-2026** | 2 bandejas en Minera Spence (hito crítico, float=0) |

---

## 4. Criterio oficial de avance (IMPORTANTE)

- **Método**: Planned Value **Labor Units (HH)** time-phased desde cronograma P6 (XER Rev.B).
- **No usar**: % por calendario lineal ni conteo de actividades.
- **XER activo**: `docs/schedule/SPC-2220-PS-PMS-011840_Fabricación Bandejas Agua Lavado Celdas OT 1844_Rev.B.xer`
- **Referencia W8** (corte 22-feb-2026): **14,00% acumulado** = 1.134 HH de 8.100 HH totales.
- **Referencia W9** (corte 01-mar-2026): **28,33% acumulado** = 2.295 HH.
- Para recalcular avance de otra semana: usar script `workspace/tmp_week9_est.py` ajustando las fechas de corte.

---

## 5. Protocolo de consulta técnica

Cuando Edgardo haga una pregunta técnica sobre el proyecto, seguir este orden:

1. **Buscar en `data/ot-1844_chunks.jsonl`** usando el tag correspondiente al tema:

   | Tema | Tags a usar |
   |------|-------------|
   | Pintura / coating | `pintura`, `coating`, `esquema-pintura`, `A3` |
   | Estructura / soldadura | `estructura`, `calculo-estructural`, `soldadura` |
   | Cronograma / avance | `cronograma`, `PMS`, `P6`, `hitos` |
   | Cambios de diseño | `RFI`, `SDI` |
   | Equipos / bandejas | `equipos`, `datasheet`, `TAG-2225` |
   | Seguridad | `HSE`, `seguridad`, `Spence` |
   | Logística / entrega | `logistica`, `embalaje`, `entrega` |
   | Contrato / PO | `contrato`, `PO`, `terminos-condiciones` |

2. **Si no está en chunks**: revisar `docs/summaries/` del documento candidato.
3. **Si tampoco está**: leer el PDF original desde OneDrive con `pdfplumber`.
4. **Nunca inventar**: si la información no está en el repositorio, decirlo explícitamente y ofrecer buscarlo.

---

## 6. Búsqueda de correos

- Categorías OWA para filtrar correos del proyecto:
  - `category:"OT 1844 Recibidos"`
  - `category:"OT 1844 Enviados"`
- **No usar texto libre** como criterio principal — las categorías son más fiables.
- Correos de referencia disponibles en: `emails/raw/inbox/` y `emails/raw/sent/`

---

## 7. Estructura del repositorio

```
projects/OT-1844/
├── README.md          ← este archivo (leer primero)
├── PROJECT.md         ← ficha maestra del proyecto
├── MEMORY.md          ← decisiones clave y estado vivo
├── LOG.md             ← bitácora cronológica de sesiones
├── MAIL_LOG.md        ← registro de correos relevantes
├── TEAMS_LOG.md       ← hallazgos en canales de Teams
├── INDEX.csv          ← índice transversal de documentos
├── docs/
│   ├── schedule/      ← XER, Gantt, resúmenes de avance
│   └── summaries/     ← resumen de cada PDF indexado
├── emails/
│   ├── raw/           ← correos en texto plano
│   └── processed/     ← datasets limpios
└── plans/             ← planos de fabricación
```

```
workspace/data/
├── ot-1844_chunks.jsonl     ← índice principal (2.200+ chunks, todos los PDFs)
├── ot-1844_chunks.bak.jsonl ← backup
└── ot-1844_docs.jsonl       ← metadata por documento
```

---

## 8. Scripts disponibles

| Script | Función |
|--------|---------|
| `scripts/retag_chunks.py` | Re-etiqueta todos los chunks con tags temáticos |
| `scripts/ingest_project_pdfs.py` | Indexa PDFs nuevos al JSONL |
| `tmp_week9_est.py` | Calcula PV HH acumulado para cualquier corte de semana |
| `tmp_xer_parse.py` / `tmp_xer_parse2.py` | Parseo del XER Rev.B |

---

## 9. Preferencias de Edgardo para este proyecto

- Respuestas técnicas con fuente explícita (documento + página si aplica).
- Cuando haya ambigüedad: preguntar antes de asumir.
- Avance semanal: siempre en base a curva S HH, nunca estimación lineal.
- Si algo no está en los documentos indexados: decirlo directo, no inventar.

---

## 10. Formato OBLIGATORIO para consultas de programa / actividades

Cuando Edgardo pida actividades por semana, cronograma o estado de avance, la respuesta debe seguir **siempre** esta estructura y no otra:

```
## Entrega N (hito DD-MMM) — TAG X
### WBS: [nombre WBS]
- [Código] — [Nombre actividad] — [Estado: ✅ Completada / 🔄 En proceso]
```

**Nunca** responder con WBS genérico (como "Bastidor" suelto sin agrupar por entrega).
**Nunca** inventar agrupaciones que no estén en el XER.
**Siempre** respetar la jerarquía del programa: Entrega → WBS → Actividad.

---

## 11. Bitácora de errores recurrentes (actualizar al detectar)

Ver: `workspace/.learnings/ERRORS.md`

Antes de responder sobre cronograma o WBS: revisar ese archivo para no repetir el mismo error.

---

*Última actualización: 2026-02-22 — Sesión de configuración y mejora de repositorio.*
