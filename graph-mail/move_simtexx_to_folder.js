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

  fs.writeFileSync(cachePath, JSON.stringify({
    createdAt: new Date().toISOString(),
    expires_in: tokenData.expires_in,
    scope: tokenData.scope,
    refresh_token: tokenData.refresh_token || cache.refresh_token
  }, null, 2));

  return tokenData.access_token;
}

async function graphGet(url, token, eventual = false) {
  const headers = { Authorization: `Bearer ${token}` };
  if (eventual) headers.ConsistencyLevel = 'eventual';
  const r = await fetch(url, { headers });
  const d = await r.json();
  if (!r.ok) throw new Error(`GET ${r.status}: ${JSON.stringify(d)}`);
  return d;
}

async function graphPost(url, token, body) {
  const r = await fetch(url, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(body)
  });
  const text = await r.text();
  let d = {};
  try { d = text ? JSON.parse(text) : {}; } catch {}
  if (!r.ok) throw new Error(`POST ${r.status}: ${text}`);
  return d;
}

async function ensureFolder(token, displayName) {
  const topFolders = await graphGet('https://graph.microsoft.com/v1.0/me/mailFolders?$top=200&$select=id,displayName', token);
  const existing = (topFolders.value || []).find(f => (f.displayName || '').toLowerCase() === displayName.toLowerCase());
  if (existing) return existing.id;

  const created = await graphPost('https://graph.microsoft.com/v1.0/me/mailFolders', token, { displayName });
  return created.id;
}

async function getSimtexxMessageIds(token) {
  let url = `https://graph.microsoft.com/v1.0/me/messages?$search=${encodeURIComponent('"simtexx"')}&$top=50&$select=id`;
  const ids = [];
  while (url) {
    const data = await graphGet(url, token, true);
    for (const m of data.value || []) ids.push(m.id);
    url = data['@odata.nextLink'] || null;
  }
  return ids;
}

async function moveMessage(token, messageId, destinationId) {
  await graphPost(`https://graph.microsoft.com/v1.0/me/messages/${messageId}/move`, token, { destinationId });
}

(async () => {
  try {
    const env = loadEnv();
    if (!env.CLIENT_ID) throw new Error('Falta CLIENT_ID en .env');

    const folderName = process.argv[2] || 'SIMTEXX (Personal)';
    const token = await getToken(env);

    const folderId = await ensureFolder(token, folderName);
    const ids = await getSimtexxMessageIds(token);

    let moved = 0;
    let failed = 0;

    for (const id of ids) {
      try {
        await moveMessage(token, id, folderId);
        moved += 1;
      } catch {
        failed += 1;
      }
    }

    console.log(JSON.stringify({ folderName, totalFound: ids.length, moved, failed }, null, 2));
  } catch (e) {
    console.error('ERROR:', e.message);
    process.exit(1);
  }
})();