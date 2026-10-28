// Catálogo GameX: guarda la página para usarla sin internet.
// Con internet siempre busca la versión nueva primero; sin internet usa la última guardada.
// v3: el guardado en caché ya no depende de waitUntil dentro de la respuesta (Safari lo rechazaba).
const C='gamex-offline';
const BASE=['./','icon-180.png','icon-192.png','icon-512.png','manifest.webmanifest'];
function guardar(c,u,r){return r&&r.ok&&r.type!=='opaque'?c.put(u,r):null}
self.addEventListener('install',e=>{e.waitUntil(caches.open(C).then(c=>Promise.all(BASE.map(u=>fetch(u,{cache:'reload'}).then(r=>guardar(c,u,r)).catch(()=>{})))).then(()=>self.skipWaiting()))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==C).map(x=>caches.delete(x)))).then(()=>self.clients.claim()))});
self.addEventListener('message',e=>{if(e.data==='guardar')e.waitUntil(caches.open(C).then(c=>fetch('./',{cache:'reload'}).then(r=>guardar(c,'./',r))).catch(()=>{}))});
self.addEventListener('fetch',e=>{
  const r=e.request;const u=new URL(r.url);
  if(r.method!=='GET'||u.origin!==location.origin||u.pathname.endsWith('version.json')||u.pathname.endsWith('.apk'))return;
  const nav=r.mode==='navigate'||(r.headers.get('accept')||'').includes('text/html');
  const key=nav?'./':(u.pathname.replace(/^.*\//,'')||'./');
  const red=fetch(nav?u.pathname+u.search:r,{cache:'no-store'}).then(res=>({res,cp:(res&&res.ok&&!res.redirected)?res.clone():null}));
  const desdeCache=()=>caches.open(C).then(c=>c.match(key,{ignoreSearch:true}).then(m=>m||c.match('./',{ignoreSearch:true})));
  e.respondWith(red.then(x=>x.res).catch(desdeCache));
  e.waitUntil(red.then(x=>x.cp&&caches.open(C).then(c=>c.put(key,x.cp))).catch(()=>{}));
});

// Avisos y ofertas (iPhone con GameX en la pantalla de inicio y navegadores compatibles)
self.addEventListener('push',e=>{let d={};try{d=e.data?e.data.json():{}}catch(x){d={titulo:'GameX',texto:e.data?e.data.text():''}}
  e.waitUntil(self.registration.showNotification(d.titulo||'GameX',{body:d.texto||'',icon:'icon-192.png',badge:'icon-192.png',tag:d.id||'gamex',data:{url:d.url||'',dest:d.dest||''}}))});
self.addEventListener('notificationclick',e=>{e.notification.close();const dd=e.notification.data||{},u=dd.url||(dd.dest==='ofertas'?'./#ofertas':'./');
  e.waitUntil(self.clients.matchAll({type:'window',includeUncontrolled:true}).then(cs=>{if(!dd.url&&cs.length){const c=cs[0];if(dd.dest==='ofertas'&&c.navigate)c.navigate(u).catch(()=>{});return c.focus()}return self.clients.openWindow(u)}))});
