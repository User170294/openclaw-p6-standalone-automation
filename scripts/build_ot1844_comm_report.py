import csv, pathlib, re, datetime, collections

base = pathlib.Path(r"C:\Users\josej\.openclaw\workspace")
p = base / "projects/OT-1844/emails/processed/ot1844_000_correos_index.csv"
out = base / "projects/OT-1844/reports/INFORME_CORREOS_OT1844_2026-02-25.md"
rows = list(csv.DictReader(p.open(encoding="utf-8-sig")))


def parse_dt(s):
    s = (s or "").strip()
    for fmt in ["%Y-%m-%d %H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M"]:
        try:
            return datetime.datetime.strptime(s, fmt)
        except Exception:
            pass
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def norm_subject(s):
    s = (s or "").strip()
    s = re.sub(r"^(RE|RV|FW|FWD|TR)\s*:\s*", "", s, flags=re.I)
    s = re.sub(r"\s+", " ", s)
    return s


def is_me(t):
    t = (t or "").lower()
    return (
        ("jose jorquera calderon" in t)
        or ("j.jorquera@simtexx.cl" in t)
        or ("jose.jorquera@outlook.es" in t)
    )


for r in rows:
    r["_dt"] = parse_dt(r.get("fecha", ""))
    r["_subject_norm"] = norm_subject(r.get("asunto", ""))
    s, to, cc = r.get("de", ""), r.get("para", ""), r.get("cc", "")
    if is_me(s):
        r["tipo2"] = "Enviado"
    elif is_me(to) or is_me(cc):
        r["tipo2"] = "Recibido"
    else:
        r["tipo2"] = "Recibido"

rows = [r for r in rows if r["_dt"]]
rows.sort(key=lambda x: x["_dt"])

start, end = rows[0]["_dt"], rows[-1]["_dt"]
total = len(rows)
enviados = sum(1 for r in rows if r["tipo2"] == "Enviado")
recibidos = total - enviados

themes = [
    ("Compras/OC", ["oc ", "orden de compra", "requisicion", "req", "solicitud de compra", "proveedor"]),
    ("Tecnico/Ingenieria", ["rfi", "memoria", "soldadura", "frp", "especific", "corte", "cilindrado", "ultrasonido", "plano"]),
    ("Planificacion/Control", ["minuta", "reunion", "avance", "cronograma", "visita", "hito"]),
    ("Documental", ["aconex", "transmittal", "control documental"]),
]
theme_counts = []
for n, ks in themes:
    c = sum(1 for r in rows if any(k in (r.get("asunto", "").lower()) for k in ks))
    theme_counts.append((n, c))

threads = collections.defaultdict(list)
for r in rows:
    threads[r["_subject_norm"]].append(r)
thread_items = []
for subj, items in threads.items():
    items = sorted(items, key=lambda x: x["_dt"])
    last = items[-1]
    thread_items.append(
        {
            "subject": subj,
            "n": len(items),
            "first": items[0]["_dt"],
            "last": items[-1]["_dt"],
            "tipo_last": last["tipo2"],
            "preview": (last.get("preview") or "")[:180].replace("|", "/"),
        }
    )
thread_items.sort(key=lambda x: (x["n"], x["last"]), reverse=True)

week_start = end - datetime.timedelta(days=7)
week = [r for r in rows if r["_dt"] >= week_start]

out.parent.mkdir(parents=True, exist_ok=True)
L = []
L.append("# Informe de Comunicaciones — OT-1844 / PO 4519143302")
L.append("")
L.append(f"**Fecha de corte:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
L.append(f"**Ventana analizada:** {start.strftime('%Y-%m-%d')} a {end.strftime('%Y-%m-%d')}")
L.append("")
L.append("## 1) Resumen ejecutivo")
L.append(f"- Total de correos: **{total}**")
L.append(f"- Enviados: **{enviados}**")
L.append(f"- Recibidos: **{recibidos}**")
L.append(f"- Últimos 7 días: **{len(week)}** correos")
L.append("")
L.append("Principales frentes de comunicación:")
for n, c in theme_counts:
    L.append(f"- {n}: **{c}** menciones por asunto")
L.append("")
L.append("## 2) Estado del servicio según comunicaciones")
L.append("- **Operación activa** con foco en abastecimiento (OCs/requisiciones) y soporte técnico (FRP, cortes/cilindrado, QA).")
L.append("- **Riesgo operacional principal:** desfase entre decisiones técnicas y disponibilidad/proveedores.")
L.append("- **Señales de control:** minutas, solicitudes de visita, y trazabilidad documental por RFI/Aconex.")
L.append("")
L.append("## 3) Hilos más relevantes (priorizados por actividad)")
L.append("| Hilo | Mensajes | Primer mensaje | Último mensaje | Último tipo | Último contexto |")
L.append("|---|---:|---|---|---|---|")
for t in thread_items[:25]:
    L.append(
        f"| {t['subject'][:95]} | {t['n']} | {t['first'].strftime('%Y-%m-%d')} | {t['last'].strftime('%Y-%m-%d %H:%M')} | {t['tipo_last']} | {t['preview'][:120]} |"
    )
L.append("")
L.append("## 4) Últimos movimientos (7 días)")
L.append("| Fecha | Tipo | Asunto | De | Señal de contexto |")
L.append("|---|---|---|---|---|")
for r in sorted(week, key=lambda x: x["_dt"], reverse=True)[:40]:
    L.append(
        f"| {r['_dt'].strftime('%Y-%m-%d %H:%M')} | {r['tipo2']} | {(r.get('asunto') or '')[:85]} | {(r.get('de') or '')[:50]} | {(r.get('preview') or '')[:90]} |"
    )
L.append("")
L.append(f"## 5) Anexo A — Detalle completo de todos los correos ({total})")
L.append("| Fecha | Tipo | Asunto | De | Para | Adj. | Archivo |")
L.append("|---|---|---|---|---|---:|---|")
for r in sorted(rows, key=lambda x: x["_dt"], reverse=True):
    L.append(
        f"| {r['_dt'].strftime('%Y-%m-%d %H:%M')} | {r['tipo2']} | {(r.get('asunto') or '')[:90]} | {(r.get('de') or '')[:45]} | {(r.get('para') or '')[:45]} | {r.get('adjuntos_n') or 0} | {(r.get('archivo') or '')[:40]} |"
    )

out.write_text("\n".join(L), encoding="utf-8")
print(out)
