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

async function token(env,cache){
  const tr=await fetch(`https://login.microsoftonline.com/${env.TENANT_ID||'consumers'}/oauth2/v2.0/token`,{
    method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'},
    body:new URLSearchParams({client_id:env.CLIENT_ID,grant_type:'refresh_token',refresh_token:cache.refresh_token,scope:env.SCOPES||'offline_access User.Read Mail.ReadWrite Mail.Send'})
  });
  const td=await tr.json();
  if(!tr.ok) throw new Error(JSON.stringify(td));
  return td.access_token;
}

(async()=>{
  const p='C:/Users/josej/.openclaw/workspace/graph-mail';
  const env=loadEnv(p);
  const cache=JSON.parse(fs.readFileSync(path.join(p,'token_cache.json'),'utf8'));
  const t=await token(env,cache);
  const headers={Authorization:`Bearer ${t}`, ConsistencyLevel:'eventual'};

  let url=`https://graph.microsoft.com/v1.0/me/messages?$search=${encodeURIComponent('"simtexx"')}&$top=50&$select=id,parentFolderId`;
  const byParent={};
  while(url){
    const r=await fetch(url,{headers});
    const d=await r.json();
    if(!r.ok) throw new Error(JSON.stringify(d));
    for(const m of (d.value||[])) byParent[m.parentFolderId]=(byParent[m.parentFolderId]||0)+1;
    url=d['@odata.nextLink']||null;
  }

  const out=[];
  for(const [id,count] of Object.entries(byParent)){
    const r=await fetch(`https://graph.microsoft.com/v1.0/me/mailFolders/${id}?$select=id,displayName,parentFolderId,totalItemCount`,{headers:{Authorization:`Bearer ${t}`}});
    const d=await r.json();
    out.push({id,count,displayName:d.displayName||'?',parentFolderId:d.parentFolderId||null,totalItemCount:d.totalItemCount??null});
  }
  console.log(JSON.stringify(out,null,2));
})();