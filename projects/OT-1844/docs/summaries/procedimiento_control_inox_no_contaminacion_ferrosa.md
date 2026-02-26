# OT-1844 — Procedimiento de Control para Evitar Contaminación Ferrosa en Acero Inoxidable (316L)

**Código sugerido:** PROC-QC-INOX-OT1844-01  
**Proyecto:** OT-1844 / PO-4519143302 / ID-1425  
**Solicitante:** Producción + Calidad  
**Aplicación:** Taller, fabricación, terminaciones y pre-entrega en componentes inoxidables 316L

---

## 1) Objetivo
Establecer controles obligatorios para prevenir contaminación ferrosa en acero inoxidable 316L durante fabricación, limpieza, terminación y despacho.

## 2) Alcance
Aplica a todo componente de acero inoxidable (principalmente bandejas y elementos asociados) desde recepción de material hasta liberación final de calidad.

## 3) Referencias técnicas
- ASTM A380/A380M-25 — Cleaning, Descaling, Pickling and Passivation of Stainless Steel Parts
- ASTM A967/A967M — Chemical Passivation Treatments for Stainless Steel Parts
- SSPC SP1 — Solvent Cleaning (como limpieza previa de contaminantes)
- AWS D1.1 (soldadura estructural, cuando corresponda)

> Nota: Si existe especificación contractual más exigente del cliente, prevalece esa especificación.

---

## 4) Riesgos a controlar
1. Contacto de inox con acero carbono (mesas, prensas, rodillos, estanterías, eslingas, grilletes, herramientas).
2. Uso de abrasivos/cepillos/discos previamente usados en acero carbono.
3. Proyección de partículas ferrosas en áreas mixtas.
4. Limpieza final insuficiente antes de pasivado.

---

## 5) Requisitos obligatorios en taller

### 5.1 Segregación física
- Delimitar **zona exclusiva inox** (piso, bancadas y almacenamiento).
- Prohibido procesar acero carbono dentro de zona inox.
- Si no hay segregación total, ejecutar barreras + ventanas horarias exclusivas + limpieza validada antes de trabajar inox.

### 5.2 Herramientas y consumibles dedicados
- Cepillos, discos flap, lijas, paños, ruedas, mordazas, eslingas y grilletes: **uso exclusivo inox**.
- Identificación por color/etiqueta: **“INOX ONLY”**.
- Prohibido reutilizar consumibles que tocaron acero carbono.

### 5.3 Manipulación y almacenamiento
- Mantener lámina protectora el mayor tiempo posible.
- Apoyos con goma/madera/plástico limpio (sin viruta metálica).
- Evitar arrastre directo sobre superficies metálicas.
- Almacenamiento en racks limpios y cubiertos.

### 5.4 Corte, esmerilado y soldadura
- Limpieza SSPC SP1 previa a soldar o terminar superficies.
- Remover salpicaduras, tintes térmicos y óxidos por método compatible con inox.
- No usar herramientas contaminadas por carbono.

---

## 6) Secuencia de limpieza y pasivado (estándar)

1. **Prelimpieza:** retiro de polvo/aceite/grasa (SSPC SP1).  
2. **Limpieza mecánica fina:** sólo abrasivo dedicado inox (A380 7.2.8).  
3. **Limpieza de zonas de soldadura:** remover tintes térmicos/óxidos/salpicaduras antes del pasivado (A380 7.3).  
4. **Decapado (si aplica):** según instrucción técnica aprobada por Calidad (producto, concentración, tiempo, temperatura).  
5. **Neutralización (si aplica al químico usado):** seguida de enjuague para remover todo residuo neutralizante (A380).  
6. **Enjuague intermedio/final:** agua limpia, preferible desmineralizada, hasta ausencia de residuos químicos.  
7. **Pasivado:** conforme ASTM A967 / práctica A380 según criticidad definida por Calidad.  
8. **Secado completo:** paño limpio dedicado o aire limpio libre de aceite, sin humedad retenida.  
9. **Protección final:** film o embalaje limpio; proteger superficie limpia para evitar recontaminación durante manejo y despacho (A380 9.5).

> Importante: Todo químico debe tener FDS y aprobación HSE/Calidad antes de uso.  
> Para limpieza en circuitos/líneas (si aplica), asegurar recirculación/arrastre suficiente para remover residuos (referencia A380; típicamente 0,9–1,2 m/s como guía de flushing).

---

## 7) Criterios de aceptación
- Superficie sin óxido libre, sin partículas ferrosas visibles, sin manchas de contaminación.
- Acabado uniforme de limpieza/pasivado según estándar visual acordado.
- Trazabilidad completa del proceso en registro QC.

### 7.1 Verificación recomendada (alineada a ASTM A380)
- Inspección visual 100%.
- Ensayo de detección de hierro libre (ferroxyl, copper sulfate u otro método cualitativo aprobado por Calidad).
- Verificar efectividad del pasivado con criterios de aceptación definidos por Calidad (métodos cualitativos tipo A380 §§8.2.5 / 8.3.4).
- Registrar evidencia de secado total y condición superficial final antes de embalaje.

---

## 8) Puntos de hold y liberación QC

**H1 (Previo fabricación inox):** validación de área y herramientas dedicadas.  
**H2 (Previo pasivado):** aceptación de limpieza preliminar.  
**H3 (Post pasivado):** aceptación final + liberación a embalaje/despacho.

Sin firma de Calidad en H3, el ítem queda **NO LIBERADO**.

---

## 9) Registro obligatorio (formato mínimo)
Para cada lote/ítem:
- Fecha y hora
- OT / PO / ID
- Código pieza / spool / bandeja
- Operador y supervisor
- Inspector QC
- Método de limpieza aplicado
- Químico (si aplica), concentración, tiempo, temperatura
- Control de baño/solución: fecha de preparación, horas de uso, criterio de reposición/reemplazo
- Resultado inspección visual
- Resultado test contaminación ferrosa (si aplica)
- Resultado verificación cualitativa de pasivado
- Estado final: Aprobado / Rechazado
- Observaciones y acciones correctivas

---

## 10) Acciones ante no conformidad
1. Aislar pieza afectada.
2. Emitir NCR interna.
3. Repetir ciclo de limpieza/pasivado según instrucción QC.
4. Reinspección y nueva liberación documentada.

---

## 11) Implementación inmediata en OT-1844 (plan corto)
**Día 1**
- Delimitar zona inox + identificar herramientas “INOX ONLY”.
- Charla de 20 min a taller y supervisión.

**Día 2**
- Iniciar registro QC por lote y controles H1/H2/H3.
- Ejecutar primera auditoría interna de cumplimiento.

**Día 3 en adelante**
- Revisión diaria de desvíos y cierre de brechas.

---

## 12) Aprobaciones (para completar)
- Jefe de Calidad: ____________________  Fecha: __________
- Jefe de Taller: _____________________  Fecha: __________
- Producción OT-1844: ________________  Fecha: __________
- HSE (si aplica): ____________________  Fecha: __________
