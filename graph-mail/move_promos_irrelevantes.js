#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const WORKDIR = __dirname;

function loadEnv() {
  const envPath = path.join(WORKDIR, '.env');
  const env = {};
  if (!fs.existsSync(envPath)) return env;
  for (const line of fs.readFileSync(envPath, 'utf8').split(/\r?\n/)) {
    if (!line || line.trim().startsWith('#')) continue;
    const i = line.indexOf('=');
    if (i < 0) continue;
    env[line.slice(0, i).trim()] = line.slice(i + 1).trim();
  }
  return env;
}

async function getToken(env) {
  const cachePath = path.join(WORKDIR, 'token_cache.json');
  const cache = JSON.parse(fs.readFileSync(cachePath, 'utf8'));

  const tokenRes = await fetch(`https://login.microsoftonline.com/${env.TENANT_ID || 'consumers'}/oauth2/v2.0/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      client_id: env.CLIENT_ID,
      grant_type: 'refresh_token',
      refresh_token: cache.refresh_token,
      scope: env.SCOPES || 'offline_access User.Read Mail.ReadWrite Mail.Send'
    })
  });

  const tokenData = await tokenRes.json();
  if (!tokenRes.ok) throw new Error(`Token error: ${JSON.stringify(tokenData)}`);
  return tokenData.access_token;
}

async function graphGet(url, token) {
  const r = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  const d = await r.json();
  if (!r.ok) throw new Error(`GET ${r.status}: ${JSON.stringify(d)}`);
  return d;
}

async function graphPost(url, token, body) {
  const r = await fetch(url, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  const text = await r.text();
  if (!r.ok) throw new Error(`POST ${r.status}: ${text}`);
  try { return text ? JSON.parse(text) : {}; } catch { return {}; }
}

function isIrrelevante(from, subject) {
  const t = `${from} ${subject}`.toLowerCase();

  const keepHints = [
    'accountprotection.microsoft.com', 'microsoft.com', 'netflix.com', 'email.apple.com',
    'invoice', 'receipt', 'factura', 'boleta', 'otp', 'verificación', 'verificacion',
    'simtexx', 'nuevaatacama', 'copec', 'bancoestado', 'transferencia', 'comprobante'
  ];
  if (keepHints.some(k => t.includes(k))) return false;

  const promoDomains = [
    'facebookmail.com', 'linkedin.com', 'substack.com', 'ted.com', 'grupoaxo.com',
    'scotiabank.cl', 'info.bci.cl', 'buscalibre.com', 'hipodromochile.cl', 'mercadolibre.com',
    'mercadopago.com', 'jumbo.cl', 'tottus.com', 'falabella.com', 'pataguatienda.cl',
    'rankia.com', 'news-mademsa.com', 'oakleychile.cl', 'olympics.com'
  ];
  if (promoDomains.some(d => t.includes(d))) return true;

  const promoWords = [
    'promoción', 'promocion', 'descuento', 'dcto', 'oferta', 'sale', 'newsletter',
    'marketplace', 'concurso', 'beneficio', 'envío a luka', 'envio a luka',
    'sugerencia de amistad', 'perfil ha sido visitado', 'novedades', 'compra hoy', 'rebaja'
  ];
  return promoWords.some(w => t.includes(w));
}

async function ensureFolder(token, displayName) {
  const top = await graphGet('https://graph.microsoft.com/v1.0/me/mailFolders?$top=200&$select=id,displayName', token);
  const existing = (top.value || []).find(f => (f.displayName || '').toLowerCase() === displayName.toLowerCase());
  if (existing) return existing.id;
  const created = await graphPost('https://graph.microsoft.com/v1.0/me/mailFolders', token, { displayName });
  return created.id;
}

(async () => {
  try {
    const env = loadEnv();
    const token = await getToken(env);

    const folderName = process.argv[2] || 'Promos y Noticias Irrelevantes';
    const destinationId = await ensureFolder(token, folderName);

    let next = 'https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages?$top=200&$orderby=receivedDateTime%20desc&$select=id,subject,from,parentFolderId';

    let scanned = 0;
    let candidates = 0;
    let moved = 0;
    let failed = 0;
    let page = 0;

    while (next) {
      page += 1;
      const data = await graphGet(next, token);
      const items = data.value || [];
      scanned += items.length;

      for (const m of items) {
        const from = m?.from?.emailAddress?.address || '';
        const subject = m?.subject || '';
        if (!isIrrelevante(from, subject)) continue;

        candidates += 1;
        try {
          await graphPost(`https://graph.microsoft.com/v1.0/me/messages/${m.id}/move`, token, { destinationId });
          moved += 1;
        } catch {
          failed += 1;
        }
      }

      if (page % 20 === 0) {
        console.log(JSON.stringify({ page, scanned, candidates, moved, failed }, null, 2));
      }

      next = data['@odata.nextLink'] || null;
    }

    console.log(JSON.stringify({ done: true, folderName, scanned, candidates, moved, failed }, null, 2));
  } catch (e) {
    console.error('ERROR:', e.message);
    process.exit(1);
  }
})();