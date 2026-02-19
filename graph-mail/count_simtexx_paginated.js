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

async function getToken(env, cache){
  const tr=await fetch(`https://login.microsoftonline.com/${env.TENANT_ID||'consumers'}/oauth2/v2.0/token`,{
    method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'},
    body:new URLSearchParams({client_id:env.CLIENT_ID,grant_type:'refresh_token',refresh_token:cache.refresh_token,scope:env.SCOPES||'offline_access User.Read Mail.ReadWrite Mail.Send'})
  });
  const td=await tr.json();
  if(!tr.ok) throw new Error(JSON.stringify(td));
  return td.access_token;
}

async function countSearch(term, token){
  const headers={Authorization:`Bearer ${token}`, ConsistencyLevel:'eventual'};
  let url=`https://graph.microsoft.com/v1.0/me/messages?$search=${encodeURIComponent('"'+term+'"')}&$top=50&$select=id`;
  let count=0;
  let pages=0;
  while(url){
    const r=await fetch(url,{headers});
    const d=await r.json();
    if(!r.ok) throw new Error(`search ${term}: ${JSON.stringify(d)}`);
    count += (d.value||[]).length;
    pages += 1;
    url = d['@odata.nextLink'] || null;
    if(pages>5000) throw new Error('too many pages');
  }
  return {term,count,pages};
}

(async()=>{
  const p='C:/Users/josej/.openclaw/workspace/graph-mail';
  const env=loadEnv(p);
  const cache=JSON.parse(fs.readFileSync(path.join(p,'token_cache.json'),'utf8'));
  const token=await getToken(env,cache);
  const terms=['simtexx','simtexx.cl','from:simtexx.cl','subject:simtexx'];
  for(const t of terms){
    const res=await countSearch(t,token);
    console.log(JSON.stringify(res));
  }
})();