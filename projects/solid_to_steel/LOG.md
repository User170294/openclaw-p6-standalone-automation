# LOG — SOLID_TO_STEEL

## 2026-03-07
- Proyecto creado en `projects/advance-steel` y renombrado a `projects/solid_to_steel`.
- Integración local del plugin LilitASPlugin migrada a Named Pipe (`LilitASPluginPipe`) en lugar de HTTP/puerto fijo.
- `scripts/as_query.py` actualizado para consumir pipe local y fallback HTTP.
- Validación funcional: `/ping` OK por pipe y lectura de elementos desde modelo activo.
- Hallazgo técnico: `/status` con error de estado interno; pendiente fix en plugin.
