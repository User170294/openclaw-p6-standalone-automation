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

async function refreshAccessToken() {
  const clientId = process.env.CLIENT_ID;
  const tenantId = process.env.TENANT_ID || 'consumers';
  const cachePath = path.join(__dirname, 'token_cache.json');
  const cache = JSON.parse(fs.readFileSync(cachePath, 'utf8'));

  const tokenUrl = `https://login.microsoftonline.com/${tenantId}/oauth2/v2.0/token`;
  const body = new URLSearchParams({
    client_id: clientId,
    grant_type: 'refresh_token',
    refresh_token: cache.refresh_token,
    scope: process.env.SCOPES || 'offline_access User.Read Mail.ReadWrite Mail.Send',
  });

  const res = await fetch(tokenUrl, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body });
  const data = await res.json();
  if (!res.ok) throw new Error(`Refresh token error: ${JSON.stringify(data)}`);

  fs.writeFileSync(cachePath, JSON.stringify({
    createdAt: new Date().toISOString(),
    expires_in: data.expires_in,
    scope: data.scope,
    refresh_token: data.refresh_token || cache.refresh_token,
  }, null, 2));

  return data.access_token;
}

async function graphDelete(messageId, token) {
  const url = `https://graph.microsoft.com/v1.0/me/messages/${messageId}`;
  const res = await fetch(url, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } });
  if (res.status !== 204) {
    const txt = await res.text();
    throw new Error(`DELETE ${messageId} failed (${res.status}): ${txt}`);
  }
}

(async () => {
  try {
    loadEnv();
    const reviewPath = path.join(__dirname, 'junk_review.json');
    const review = JSON.parse(fs.readFileSync(reviewPath, 'utf8'));

    const mode = (process.argv[2] || 'dry').toLowerCase(); // dry | apply | all
    const targets = mode === 'all'
      ? review
      : review.filter(x => x.decision === 'ELIMINAR');

    if (mode === 'dry') {
      console.log(JSON.stringify({ mode, totalReview: review.length, toDelete: targets.length }, null, 2));
      process.exit(0);
    }

    const token = await refreshAccessToken();
    let ok = 0;
    let fail = 0;

    for (const item of targets) {
      try {
        await graphDelete(item.id, token);
        ok += 1;
      } catch (e) {
        fail += 1;
        console.error(`FAIL: ${item.subject} :: ${e.message}`);
      }
    }

    console.log(JSON.stringify({ mode, attempted: targets.length, deleted: ok, failed: fail }, null, 2));
  } catch (e) {
    console.error('ERROR:', e.message);
    process.exit(1);
  }
})();