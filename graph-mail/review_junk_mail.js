#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

function loadEnv() {
  const envPath = path.join(__dirname, '.env');
  if (!fs.existsSync(envPath)) return;
  for (const line of fs.readFileSync(envPath, 'utf8').split(/\r?\n/)) {
    if (!line || line.trim().startsWith('#')) continue;
    const i = line.indexOf('=');
    if (i < 0) continue;
    const k = line.slice(0, i).trim();
    const v = line.slice(i + 1).trim();
    if (!process.env[k]) process.env[k] = v;
  }
}

function scoreRelevance(from, subject) {
  const txt = `${from} ${subject}`.toLowerCase();

  const relevantHints = [
    'simtexx', 'ot ', 'orden de trabajo', 'factura', 'boleta', 'pago', 'transferencia',
    'banco', 'scotiabank', 'bci', 'santander', 'microsoft', 'security', 'seguridad',
    'verification', 'verificación', 'invoice', 'purchase', 'compra', 'cotización', 'cotizacion'
  ];

  const promoHints = [
    'promoción', 'promocion', 'descuento', 'oferta', 'black friday', 'marketplace',
    'newsletter', 'sale', 'rebaja', 'beneficio', 'viaja', 'vuelo', 'hotel', 'casino',
    'apuesta', 'gana', 'bono', 'cupón', 'cupon'
  ];

  let score = 0;
  for (const h of relevantHints) if (txt.includes(h)) score += 1;
  for (const h of promoHints) if (txt.includes(h)) score -= 1;

  if (txt.includes('account-security-noreply') || txt.includes('accountprotection.microsoft.com')) score += 2;
  if (txt.includes('noreply') || txt.includes('no-reply')) score -= 0.5;

  return score;
}

async function refreshAccessToken() {
  const envClientId = process.env.CLIENT_ID;
  const tenantId = process.env.TENANT_ID || 'consumers';
  if (!envClientId) throw new Error('Falta CLIENT_ID en .env');

  const cachePath = path.join(__dirname, 'token_cache.json');
  if (!fs.existsSync(cachePath)) throw new Error('No existe token_cache.json. Ejecuta graph_device_mail.js primero.');
  const cache = JSON.parse(fs.readFileSync(cachePath, 'utf8'));
  if (!cache.refresh_token) throw new Error('token_cache.json no tiene refresh_token');

  const tokenUrl = `https://login.microsoftonline.com/${tenantId}/oauth2/v2.0/token`;
  const params = new URLSearchParams({
    client_id: envClientId,
    grant_type: 'refresh_token',
    refresh_token: cache.refresh_token,
    scope: process.env.SCOPES || 'offline_access User.Read Mail.ReadWrite Mail.Send',
  });

  const res = await fetch(tokenUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: params,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(`Refresh token error: ${JSON.stringify(data)}`);

  fs.writeFileSync(
    cachePath,
    JSON.stringify({
      createdAt: new Date().toISOString(),
      expires_in: data.expires_in,
      scope: data.scope,
      refresh_token: data.refresh_token || cache.refresh_token,
    }, null, 2)
  );

  return data.access_token;
}

async function graphGet(url, token) {
  const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  const data = await res.json();
  if (!res.ok) throw new Error(`Graph GET error ${res.status}: ${JSON.stringify(data)}`);
  return data;
}

(async () => {
  try {
    loadEnv();
    const token = await refreshAccessToken();

    const top = Number(process.argv[2] || 100);
    const select = encodeURIComponent('id,subject,from,receivedDateTime,bodyPreview');
    const url = `https://graph.microsoft.com/v1.0/me/mailFolders/junkemail/messages?$top=${top}&$orderby=receivedDateTime desc&$select=${select}`;
    const data = await graphGet(url, token);

    const items = (data.value || []).map(m => {
      const from = m?.from?.emailAddress?.address || 'sin-remitente';
      const subject = (m?.subject || '(sin asunto)').replace(/\s+/g, ' ').trim();
      const score = scoreRelevance(from, subject);
      const bucket = score >= 1 ? 'REVISAR' : 'ELIMINAR';
      return {
        id: m.id,
        received: m.receivedDateTime,
        from,
        subject,
        score,
        decision: bucket,
      };
    });

    const outPath = path.join(__dirname, 'junk_review.json');
    fs.writeFileSync(outPath, JSON.stringify(items, null, 2));

    const summary = {
      total: items.length,
      revisar: items.filter(x => x.decision === 'REVISAR').length,
      eliminar: items.filter(x => x.decision === 'ELIMINAR').length,
      output: outPath,
    };

    console.log(JSON.stringify(summary, null, 2));

    const preview = items.slice(0, 25).map((x, i) =>
      `${String(i + 1).padStart(2, ' ')}. [${x.decision}] [${x.received}] ${x.from} -> ${x.subject}`
    );
    console.log('\n--- PREVIEW ---\n' + preview.join('\n'));
  } catch (e) {
    console.error('ERROR:', e.message);
    process.exit(1);
  }
})();