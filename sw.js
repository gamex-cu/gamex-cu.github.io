// Catálogo GameX: guarda la página para usarla sin internet.
// Con internet siempre busca la versión nueva primero; sin internet usa la última guardada.
const C='gamex-offline';
const BASE=['./','icon-180.png','icon-192.png','icon-512.png','manifest.webmanifest'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(C).then(c=>Promise.all(BASE.map(u=>fetch(u,{cache:'reload'}).then(r=>r.ok&&c.put(u,r)).catch(()=>{})))).then(()=>self.skipWaiting()))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==C).map(x=>caches.delete(x)))).then(()=>self.clients.claim()))});
self.addEventListener('message',e=>{if(e.data==='guardar')e.waitUntil(caches.open(C).then(c=>fetch('./',{cache:'reload'}).then(r=>r.ok&&c.put('./',r))).catch(()=>{}))});
self.addEventListener('fetch',e=>{
  const r=e.request;const u=new URL(r.url);
  if(r.method!=='GET'||u.origin!==location.origin||u.pathname.endsWith('version.json')||u.pathname.endsWith('.apk'))return;
  const nav=r.mode==='navigate'||(r.headers.get('accept')||'').includes('text/html');
  const key=nav?'./':u.pathname.replace(/^.*\//,'')||'./';
  e.respondWith(fetch(nav?u.href:r,{cache:'no-store'}).then(res=>{
    if(res&&res.ok){const cp=res.clone();e.waitUntil(caches.open(C).then(c=>c.put(key,cp)))}
    return res;
  }).catch(()=>caches.open(C).then(c=>c.match(key,{ignoreSearch:true}).then(m=>m||c.match('./')))));
});
