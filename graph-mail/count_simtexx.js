const fs = require('fs');
const path = require('path');

function loadEnv(p){
  const txt = fs.readFileSync(path.join(p,'.env'),'utf8');
  const env={};
  for(const l of txt.split(/\r?\n/)){
    if(!l||l.startsWith('#')) continue;
    const i=l.indexOf('='); if(i<0) continue;
    env[l.slice(0,i)] = l.slice(i+1);
  }
  return env;
}

(async()=>{
  const p='C:/Users/josej/.openclaw/workspace/graph-mail';
  const env=loadEnv(p);
  const cache=JSON.parse(fs.readFileSync(path.join(p,'token_cache.json'),'utf8'));
  const tr=await fetch(`https://login.microsoftonline.com/${env.TENANT_ID||'consumers'}/oauth2/v2.0/token`,{
    method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'},
    body:new URLSearchParams({client_id:env.CLIENT_ID,grant_type:'refresh_token',refresh_token:cache.refresh_token,scope:env.SCOPES||'offline_access User.Read Mail.ReadWrite Mail.Send'})
  });
  const td=await tr.json();
  const headers={Authorization:`Bearer ${td.access_token}`, ConsistencyLevel:'eventual'};
  const tests=['"simtexx"','"simtexx.cl"','"from:simtexx.cl"','"subject:simtexx"'];
  for(const q of tests){
    const url=`https://graph.microsoft.com/v1.0/me/messages?$search=${encodeURIComponent(q)}&$top=1&$count=true&$select=id`;
    const r=await fetch(url,{headers});
    const d=await r.json();
    console.log(JSON.stringify({q,status:r.status,count:d['@odata.count']??null,error:d.error?.message||null}));
  }
})();