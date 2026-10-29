// Cloudflare Worker de GameX: avisos (iPhone/navegadores) + panel para mandar ofertas.
// POST /suscribir        (público)   -> guarda la suscripción web push
// GET  /lista            (X-Clave)   -> devuelve todas las suscripciones (lo usa tools/enviar_aviso.py)
// POST /borrar           (X-Clave)   -> borra una suscripción {endpoint}
// GET  /panel                        -> página del panel (pide contraseña)
// GET  /panel/api/estado (X-Panel)   -> iPhones suscritos + ofertas activas
// POST /panel/api/enviar (X-Panel)   -> agrega la oferta a app/avisos.json (GitHub) y, si notificar no es false, la manda por Firebase (Android)
// POST /panel/api/web    (X-Panel)   -> manda la oferta a los iPhone, de 40 en 40
// POST /panel/api/borrar (X-Panel)   -> quita una oferta de app/avisos.json
// POST /evento          (público)   -> estadísticas anónimas de la web/app (visitas, catálogos, búsquedas, pedidos)
// GET  /panel/api/stats  (X-Panel)   -> resumen de estadísticas (?dias=1|7|30|90)
// Necesita: Durable Object STATS (clase Stats, guarda los eventos en SQLite), KV "SUBS" y los secretos CLAVE, PANEL (contraseña), VAPID, FIREBASE y GITHUB.
import {DurableObject} from 'cloudflare:workers';
const CORS={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Methods':'GET,POST,OPTIONS','Access-Control-Allow-Headers':'Content-Type,X-Clave,Authorization'};
const r=(b,s=200)=>new Response(typeof b==='string'?b:JSON.stringify(b),{status:s,headers:{...CORS,'Content-Type':'application/json'}});
const j=(b,s=200)=>new Response(JSON.stringify(b),{status:s,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'}});
const TE=new TextEncoder(),TD=new TextDecoder();
async function id(t){const h=await crypto.subtle.digest('SHA-256',TE.encode(t));return [...new Uint8Array(h)].map(x=>x.toString(16).padStart(2,'0')).join('')}
const REPO='gamex-cu/gamex-cu.github.io',ARCH='app/avisos.json',LOTE=40;
const PANEL_HTML=__PANEL_HTML__;

// ---------- utilidades ----------
function b64(bytes){let s='';const b=new Uint8Array(bytes);for(let i=0;i<b.length;i++)s+=String.fromCharCode(b[i]);return btoa(s)}
const b64u=b=>b64(b).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
function unb64(s){s=s.replace(/-/g,'+').replace(/_/g,'/').replace(/\s/g,'');s+='='.repeat((4-s.length%4)%4);const x=atob(s);const o=new Uint8Array(x.length);for(let i=0;i<x.length;i++)o[i]=x.charCodeAt(i);return o}
function cat(...a){const n=a.reduce((t,x)=>t+x.length,0),o=new Uint8Array(n);let p=0;for(const x of a){o.set(x,p);p+=x.length}return o}
async function hmac(k,d){const key=await crypto.subtle.importKey('raw',k,{name:'HMAC',hash:'SHA-256'},false,['sign']);return new Uint8Array(await crypto.subtle.sign('HMAC',key,d))}
function hoyCuba(){try{return new Date().toLocaleDateString('en-CA',{timeZone:'America/Havana'})}catch(e){return new Date().toISOString().slice(0,10)}}
const sinAst=s=>s.trim().replace(/^\*+|\*+$/g,''); // acepta la contraseña con o sin *asteriscos*
function igual(a,b){if(typeof a!=='string'||typeof b!=='string'||a.length!==b.length)return false;let x=0;for(let i=0;i<a.length;i++)x|=a.charCodeAt(i)^b.charCodeAt(i);return x===0}

// ---------- web push (RFC 8291 aes128gcm + VAPID) ----------
async function cifrar(sub,datos){
  const ua=unb64(sub.keys.p256dh),auth=unb64(sub.keys.auth);
  const eph=await crypto.subtle.generateKey({name:'ECDH',namedCurve:'P-256'},true,['deriveBits']);
  const asPub=new Uint8Array(await crypto.subtle.exportKey('raw',eph.publicKey));
  const uaKey=await crypto.subtle.importKey('raw',ua,{name:'ECDH',namedCurve:'P-256'},false,[]);
  const shared=new Uint8Array(await crypto.subtle.deriveBits({name:'ECDH',public:uaKey},eph.privateKey,256));
  const ikm=await hmac(await hmac(auth,shared),cat(TE.encode('WebPush: info\0'),ua,asPub,new Uint8Array([1])));
  const salt=crypto.getRandomValues(new Uint8Array(16)),prk=await hmac(salt,ikm);
  const cek=(await hmac(prk,TE.encode('Content-Encoding: aes128gcm\0\x01'))).slice(0,16);
  const nonce=(await hmac(prk,TE.encode('Content-Encoding: nonce\0\x01'))).slice(0,12);
  const k=await crypto.subtle.importKey('raw',cek,'AES-GCM',false,['encrypt']);
  const ct=new Uint8Array(await crypto.subtle.encrypt({name:'AES-GCM',iv:nonce},k,cat(datos,new Uint8Array([2]))));
  return cat(salt,new Uint8Array([0,0,16,0,asPub.length]),asPub,ct);
}
async function vapid(env,endpoint){
  const v=JSON.parse(env.VAPID),pub=unb64(v.publica);
  const key=await crypto.subtle.importKey('jwk',{kty:'EC',crv:'P-256',x:b64u(pub.slice(1,33)),y:b64u(pub.slice(33,65)),d:v.privada,ext:true},{name:'ECDSA',namedCurve:'P-256'},false,['sign']);
  const u=new URL(endpoint);
  const h=b64u(TE.encode(JSON.stringify({typ:'JWT',alg:'ES256'}))),b=b64u(TE.encode(JSON.stringify({aud:u.protocol+'//'+u.host,exp:Math.floor(Date.now()/1000)+12*3600,sub:'mailto:gamex@users.noreply.github.com'})));
  const sig=await crypto.subtle.sign({name:'ECDSA',hash:'SHA-256'},key,TE.encode(h+'.'+b));
  return `vapid t=${h}.${b}.${b64u(sig)}, k=${v.publica}`;
}
async function pushWeb(env,sub,datos){
  const body=await cifrar(sub,TE.encode(JSON.stringify(datos)));
  const res=await fetch(sub.endpoint,{method:'POST',body,headers:{'Content-Encoding':'aes128gcm','Content-Type':'application/octet-stream','TTL':'604800','Urgency':'high','Authorization':await vapid(env,sub.endpoint)}});
  return res.status;
}

// ---------- Firebase (Android) ----------
async function tokenGoogle(key){
  const now=Math.floor(Date.now()/1000);
  const h=b64u(TE.encode(JSON.stringify({alg:'RS256',typ:'JWT'}))),b=b64u(TE.encode(JSON.stringify({iss:key.client_email,scope:'https://www.googleapis.com/auth/firebase.messaging',aud:key.token_uri,iat:now,exp:now+3600})));
  const der=unb64(key.private_key.replace(/-----[^-]+-----/g,''));
  const pk=await crypto.subtle.importKey('pkcs8',der,{name:'RSASSA-PKCS1-v1_5',hash:'SHA-256'},false,['sign']);
  const sig=await crypto.subtle.sign('RSASSA-PKCS1-v1_5',pk,TE.encode(h+'.'+b));
  const res=await fetch(key.token_uri,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer&assertion='+h+'.'+b+'.'+b64u(sig)});
  const d=await res.json();if(!d.access_token)throw new Error('Google: '+JSON.stringify(d).slice(0,200));return d.access_token;
}
function corto(t){t=String(t||'');if(t.length<=230)return t;const c=t.slice(0,220),i=c.lastIndexOf(' ');return (i>150?c.slice(0,i):c).trim()+'… Toca para ver la oferta completa.'}
async function pushAndroid(env,aviso){
  const key=JSON.parse(env.FIREBASE),tok=await tokenGoogle(key);
  const data={};for(const k of ['id','titulo','texto','url'])if(aviso[k])data[k]=k==='texto'?corto(aviso[k]):String(aviso[k]);
  if(data.url&&/wa\.me\/|whatsapp/i.test(data.url))delete data.url; // al tocar el aviso se abre la oferta en la app, no WhatsApp
  if(!aviso.solo)data.dest='ofertas';
  const res=await fetch(`https://fcm.googleapis.com/v1/projects/${key.project_id}/messages:send`,{method:'POST',headers:{'Authorization':'Bearer '+tok,'Content-Type':'application/json'},
    body:JSON.stringify({message:{topic:'ofertas',data,android:{priority:'high',ttl:'604800s'}}})});
  if(!res.ok)throw new Error('Firebase '+res.status+': '+(await res.text()).slice(0,200));
}

// ---------- GitHub (app/avisos.json) ----------
const GH=env=>({'Authorization':'Bearer '+env.GITHUB,'User-Agent':'GameX-panel','Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'});
async function leerAvisos(env){
  const res=await fetch(`https://api.github.com/repos/${REPO}/contents/${ARCH}?ref=main`,{headers:GH(env)});
  if(!res.ok)throw new Error('GitHub '+res.status+': '+(await res.text()).slice(0,200));
  const f=await res.json();let d;try{d=JSON.parse(TD.decode(unb64(f.content)))}catch(e){d={avisos:[]}}
  if(!Array.isArray(d.avisos))d.avisos=[];if(!Array.isArray(d.silenciosas))d.silenciosas=[];return {d,sha:f.sha};
}
async function guardarAvisos(env,d,sha,msg){
  const res=await fetch(`https://api.github.com/repos/${REPO}/contents/${ARCH}`,{method:'PUT',headers:{...GH(env),'Content-Type':'application/json'},
    body:JSON.stringify({message:msg,content:b64(TE.encode(JSON.stringify(d,null,1))),sha,branch:'main'})});
  if(!res.ok)throw new Error('GitHub '+res.status+': '+(await res.text()).slice(0,200));
}
async function cambiarAvisos(env,fn,msg){ // reintenta si alguien más cambió el archivo a la vez
  for(let i=0;i<3;i++){const {d,sha}=await leerAvisos(env);fn(d);try{await guardarAvisos(env,d,sha,msg);return d}catch(e){if(i===2||!/ 409| 422/.test(e.message))throw e}}
}
// ---------- juegos agregados/quitados a mano (tools/datos/panel_juegos.json; una acción de GitHub rearma el catálogo) ----------
const PJ='tools/datos/panel_juegos.json',PJ_PLAT=['PS4','PS5','PC','Switch','Meta Quest','Xbox pago','Xbox Game Pass'];
async function pjLeer(env){
  const res=await fetch(`https://api.github.com/repos/${REPO}/contents/${PJ}?ref=main`,{headers:GH(env)});
  if(res.status===404)return {d:{agregar:[],quitar:[],editar:[]},sha:null};
  if(!res.ok)throw new Error('GitHub '+res.status+': '+(await res.text()).slice(0,200));
  const f=await res.json();let d;try{d=JSON.parse(TD.decode(unb64(f.content)))}catch(e){d={}}
  if(!Array.isArray(d.agregar))d.agregar=[];if(!Array.isArray(d.quitar))d.quitar=[];if(!Array.isArray(d.editar))d.editar=[];return {d,sha:f.sha};
}
async function pjCambiar(env,fn,msg){
  for(let i=0;i<3;i++){const {d,sha}=await pjLeer(env);const r=fn(d);
    const body={message:msg,content:b64(TE.encode(JSON.stringify(d,null,1)+'\n')),branch:'main'};if(sha)body.sha=sha;
    const res=await fetch(`https://api.github.com/repos/${REPO}/contents/${PJ}`,{method:'PUT',headers:{...GH(env),'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(res.ok)return {d,r};const t=(await res.text()).slice(0,200);if(i===2||!(res.status===409||res.status===422))throw new Error('GitHub '+res.status+': '+t)}
}
let EXTRA_CACHE=null;
async function plataformas(env){ // las de siempre + los catálogos nuevos creados en el panel
  if(!EXTRA_CACHE||Date.now()-EXTRA_CACHE.t>60000){let l=[];try{const {d}=await ghJson(env,'tools/datos/catalogos_extra.json');l=(d||[]).map(x=>x.n).filter(Boolean)}catch(e){}EXTRA_CACHE={t:Date.now(),l}}
  return PJ_PLAT.concat(EXTRA_CACHE.l);
}
let CONS_CACHE=null;
async function consolaTxt(env){ // catálogo publicado (para buscar juegos que ya están)
  if(CONS_CACHE&&Date.now()-CONS_CACHE.t<60000)return CONS_CACHE.l;
  const res=await fetch('https://raw.githubusercontent.com/'+REPO+'/main/app/consola.txt',{cf:{cacheTtl:0}});
  if(!res.ok)throw new Error('No se pudo leer el catálogo ('+res.status+')');
  const PL=await plataformas(env),l=[];let c='';for(const ln of (await res.text()).split('\n')){const f=ln.split('\t');if(f[0]==='C')c=f[2];else if(f[0]==='J'&&PL.includes(c))l.push({c,n:f[2],f:+f[1]||0})}
  CONS_CACHE={t:Date.now(),l};return l;
}
const normJ=s=>String(s||'').normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
// ---------- archivos de datos que edita el panel (tienda, servicios, PS Plus) y Game Pass ----------
const ARCHS={tienda:'tools/datos/tienda.json',servicios:'tools/datos/servicios.json',ps_plus:'tools/datos/ps_plus.json',catalogos:'tools/datos/catalogos_extra.json'};
async function ghJson(env,path,ref='main'){
  const res=await fetch(`https://api.github.com/repos/${REPO}/contents/${path}?ref=${ref}`,{headers:GH(env)});
  if(res.status===404)return {d:null,sha:null};if(!res.ok)throw new Error('GitHub '+res.status+': '+(await res.text()).slice(0,200));
  const f=await res.json();return {d:JSON.parse(TD.decode(unb64(f.content))),sha:f.sha};
}
async function ghPut(env,path,content,sha,msg){
  const body={message:msg,content:b64(typeof content==='string'?TE.encode(content):content),branch:'main'};if(sha)body.sha=sha;
  const res=await fetch(`https://api.github.com/repos/${REPO}/contents/${path}`,{method:'PUT',headers:{...GH(env),'Content-Type':'application/json'},body:JSON.stringify(body)});
  if(!res.ok)throw new Error('GitHub '+res.status+': '+(await res.text()).slice(0,200));return res.json();
}
const HHMM=/^([01]\d|2[0-3]):[0-5]\d$/,txt=(v,n)=>String(v==null?'':v).slice(0,n);
function validar(f,d){
  if(f==='tienda'){
    const nums=(Array.isArray(d.numeros)?d.numeros:[]).map(x=>txt(x,20).trim()).filter(Boolean);
    if(!nums.length||nums.some(n=>n.replace(/\D/g,'').length<8))return 'Los números de WhatsApp tienen que tener 8 cifras';
    const dias=[...new Set((Array.isArray(d.dias)?d.dias:[]).map(Number).filter(x=>x>=0&&x<=6))].sort();
    if(!HHMM.test(d.abre||'')||!HHMM.test(d.cierra||'')||d.abre>=d.cierra)return 'Revisa la hora de abrir y de cerrar';
    if(d.mapa&&!/^https:\/\//.test(d.mapa))return 'El enlace del mapa tiene que empezar con https://';
    return {inicio:txt(d.inicio,300).trim(),numeros:nums.slice(0,5),dias,abre:d.abre,cierra:d.cierra,direccion:txt(d.direccion,200).trim(),mapa:txt(d.mapa,300).trim(),reglas:txt(d.reglas,6000).replace(/\r/g,''),
      ocultar:{secciones:(d.ocultar?.secciones||[]).filter(x=>['catalogos','ofertas','servicios','cuenta'].includes(x)||/^x-[a-z0-9-]{1,30}$/.test(x)),catalogos:(d.ocultar?.catalogos||[]).map(x=>txt(x,40)).slice(0,20),servicios:(d.ocultar?.servicios||[]).map(x=>txt(x,60)).slice(0,20)},
      mantenimiento:{activo:!!d.mantenimiento?.activo,mensaje:txt(d.mantenimiento?.mensaje,500).trim()},
      botones:(Array.isArray(d.botones)?d.botones:[]).slice(0,60).map(b=>({padre:txt(b.padre,30).toLowerCase().replace(/[^a-z0-9-]/g,''),oculto:!!b.oculto,id:txt(b.id,30).toLowerCase().replace(/[^a-z0-9-]/g,'')||('b'+Math.random().toString(36).slice(2,8)),titulo:txt(b.titulo,40).trim(),sub:txt(b.sub,120).trim(),icono:txt(b.icono,8).trim(),color:/^#[0-9a-f]{6}$/i.test(b.color||'')?b.color:'#3d7bff',tipo:['pagina','enlace','whatsapp','seccion'].includes(b.tipo)?b.tipo:'pagina',destino:/^[a-z0-9=-]{1,60}$/.test(b.destino||'')?b.destino:'',enlace:/^https:\/\//.test(b.enlace||'')?txt(b.enlace,300):'',texto:txt(b.texto,4000).replace(/\r/g,''),wa:txt(b.wa,300),conwa:!!b.conwa})).filter(b=>b.titulo),
      orden:{secciones:(d.orden?.secciones||[]).filter(x=>(['catalogos','ofertas','servicios','cuenta'].includes(x)||/^x-[a-z0-9-]{1,30}$/.test(x))),catalogos:(d.orden?.catalogos||[]).map(x=>txt(x,40)).slice(0,40)}};
  }
  if(f==='servicios'){
    if(!Array.isArray(d)||d.some(s=>!s||!Array.isArray(s.items)))return 'Los servicios no están bien';
    if(JSON.stringify(d).length>150000)return 'Demasiado texto en servicios';
    for(const s of d){s.s=txt(s.s,40).replace(/[<>"]/g,'').trim();if(!s.s)return 'Hay un tipo de servicio sin nombre';s.icono=txt(s.icono,8).replace(/[<>"&]/g,'');
      if(!/^#[0-9a-f]{6}$/i.test(s.color||''))s.color='#3d7bff';if(!/^#[0-9a-f]{6}$/i.test(s.texto||''))s.texto='#b8ccff'}
    if(new Set(d.map(s=>s.s.toLowerCase())).size!==d.length)return 'Hay dos tipos de servicio con el mismo nombre';
    for(const s of d)for(const it of s.items){if(!it||!String(it.t||'').trim())return 'Hay un servicio sin nombre en '+s.s;
      if(it.grupos)for(const g of it.grupos)if(!Array.isArray(g.o)||!g.o.length||g.o.some(o=>!String(o.t||'').trim()))return 'El servicio "'+it.t+'" tiene una lista de opciones vacía';
      if(it.montos&&(!Array.isArray(it.montos)||it.montos.some(m=>!(+m>0))))return 'Montos no válidos en "'+it.t+'"'}
    return d;
  }
  if(f==='ps_plus'){
    const js=(Array.isArray(d.juegos)?d.juegos:[]).map(g=>{const o={n:txt(g.n,120).trim()};const id=txt(g.id,80).trim();if(id)o.id=/^(PPSA|CUSA)\d{5}$/i.test(id)?id.toUpperCase():id;if(g.online)o.online=true;return o}).filter(g=>g.n);
    if(!js.length)return 'Pon al menos un juego';if(!/^\d{4}-\d{2}-\d{2}$/.test(d.hasta||''))return 'Pon hasta qué día se pueden reclamar';
    if(js.some(g=>g.id&&!/^(PPSA|CUSA)\d{5}$/.test(g.id)&&!/^[A-Z]{2}\d{4}-[A-Z]{4}\d{5}_00-\w+$/.test(g.id)))return 'El código de un juego no está bien (ej. PPSA28002)';
    return {mes:txt(d.mes,40).trim(),hasta:d.hasta,fuente:'Juegos mensuales de PlayStation Plus Essential',juegos:js};
  }
  if(f==='catalogos'){
    if(!Array.isArray(d)||d.length>20)return 'Lista de catálogos no válida';const vistos=new Set(),BASE=['PS4','PS5','PC','Switch','Meta Quest','Xbox pago','Xbox Game Pass','PlayStation Plus','Nintendo Switch','PlayStation 4','PlayStation 5'].map(x=>x.toLowerCase());
    const out=[];for(const x of d){const n=txt(x&&x.n,30).replace(/[|\t\n]/g,' ').trim();if(!n)return 'Hay un catálogo sin nombre';const k=n.toLowerCase();
      if(BASE.includes(k))return '"'+n+'" ya existe';if(vistos.has(k))return '"'+n+'" está repetido';vistos.add(k);
      const col=/^#[0-9a-f]{6}$/i.test(x.color||'')?x.color:'#3d7bff',tx=/^#[0-9a-f]{6}$/i.test(x.texto||'')?x.texto:'#ffffff';
      out.push({n,color:col,texto:tx,...(x.desbloqueo?{desbloqueo:true}:{})})}
    return out;
  }
  return 'Archivo desconocido';
}
async function ultimaCorrida(env,wf){try{const r=await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${wf}/runs?per_page=1`,{headers:GH(env)});if(!r.ok)return null;const x=(await r.json()).workflow_runs?.[0];return x?{estado:x.status,res:x.conclusion,fecha:x.created_at}:null}catch(e){return null}}
async function panelDatos(p,req,env,u){
  const q=req.method==='POST'?await req.json().catch(()=>({})):Object.fromEntries(u.searchParams);
  if(p==='archivo'){const f=q.f;if(!ARCHS[f])return j({error:'Archivo desconocido'},400);const {d,sha}=await ghJson(env,ARCHS[f]);return j({d,sha,run:await ultimaCorrida(env,'panel-juegos.yml')})}
  if(p==='archivo-guardar'){const f=q.f;if(!ARCHS[f])return j({error:'Archivo desconocido'},400);const v=validar(f,q.d==null?{}:q.d);if(f==='catalogos')EXTRA_CACHE=null;if(typeof v==='string')return j({error:v},400);
    const {sha}=await ghJson(env,ARCHS[f]);if(q.sha&&sha&&q.sha!==sha)return j({error:'Alguien cambió esto mientras editabas. Recarga y vuelve a intentarlo.'},409);
    const r=await ghPut(env,ARCHS[f],JSON.stringify(v,null,1)+'\n',sha,'Panel: '+{tienda:'datos de la tienda',servicios:'servicios',ps_plus:'juegos de PS Plus',catalogos:'catálogos nuevos'}[f]);return j({ok:true,sha:r.content&&r.content.sha,d:v})}
  if(p==='gp-estado'){const {d}=await ghJson(env,'tools/salida/gamepass_cambios.json','gamepass-pendiente').catch(()=>({d:null}));return j({cambios:d,run:await ultimaCorrida(env,'gamepass.yml')})}
  if(p==='gp-revisar'||p==='gp-publicar'){
    const online=(Array.isArray(q.online)?q.online:[]).map(x=>txt(x,120)).slice(0,50);
    const res=await fetch(`https://api.github.com/repos/${REPO}/dispatches`,{method:'POST',headers:{...GH(env),'Content-Type':'application/json'},body:JSON.stringify({event_type:p,client_payload:{online}})});
    if(!res.ok)throw new Error('GitHub '+res.status+': '+(await res.text()).slice(0,200));return j({ok:true})}
  if(p==='foto'){ // foto de una oferta: llega ya achicada (JPEG) desde el panel
    const m=/^data:image\/jpeg;base64,([A-Za-z0-9+/=]+)$/.exec(String(q.img||''));if(!m)return j({error:'La foto no está bien'},400);
    const bytes=unb64(m[1]);if(bytes.length>900000)return j({error:'La foto es muy grande'},400);
    const nombre='app/fotos/'+hoyCuba()+'-'+(await id(m[1])).slice(0,12)+'.jpg';
    try{await ghPut(env,nombre,bytes,null,'Panel: foto de oferta')}catch(e){if(!/ 422/.test(e.message))throw e}
    return j({ok:true,url:'https://gamex-cu.github.io/'+nombre,raw:'https://raw.githubusercontent.com/'+REPO+'/main/'+nombre})}
  if(p==='respaldo'){
    const [av,pj,ti,sv,ps]=await Promise.all([leerAvisos(env).then(x=>x.d).catch(()=>null),pjLeer(env).then(x=>x.d).catch(()=>null),...['tienda','servicios','ps_plus'].map(f=>ghJson(env,ARCHS[f]).then(x=>x.d).catch(()=>null))]);
    return j({fecha:hoyCuba(),rewards:await statsDO(env).cliExportar(),reglas:await statsDO(env).cfgReglas(),ofertas:av,juegos_panel:pj,tienda:ti,servicios:sv,ps_plus:ps})}
  return j({error:'No existe'},404);
}
async function panelJuegos(p,req,env,u){
  const q=req.method==='POST'?await req.json().catch(()=>({})):Object.fromEntries(u.searchParams);
  const hoy=hoyCuba();
  if(p==='juegos'){const {d}=await pjLeer(env);let run=null;
    try{const r=await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/panel-juegos.yml/runs?per_page=1`,{headers:GH(env)});if(r.ok){const x=(await r.json()).workflow_runs?.[0];if(x)run={estado:x.status,res:x.conclusion,fecha:x.created_at}}}catch(e){}
    return j({...d,run,plataformas:await plataformas(env)})}
  if(p==='juegos-buscar'){const t=normJ(q.q);if(t.length<2)return j({hits:[]});const ws=t.split(' ');
    const hits=(await consolaTxt(env)).filter(g=>(!q.c||g.c===q.c)&&ws.every(w=>normJ(g.n).includes(w))).slice(0,40);return j({hits})}
  if(req.method!=='POST')return j({error:'Usa POST'},405);
  const c=String(q.c||''),n=String(q.n||'').replace(/\s+/g,' ').trim().slice(0,120);
  if(!(await plataformas(env)).includes(c))return j({error:'Escoge la consola'},400);
  if(!n)return j({error:'Falta el nombre del juego'},400);
  if(p==='juegos-agregar'){
    const link=String(q.link||'').trim().slice(0,300);
    if(link&&!/^https:\/\//.test(link)&&!/^(PPSA|CUSA)\d{5}$/i.test(link)&&!/^[A-Z]{2}\d{4}-[A-Z]{4}\d{5}_00-\w+$/.test(link)&&!((c==='Xbox pago'||c==='Xbox Game Pass')&&/^[0-9A-Z]{12}$/.test(link)))
      return j({error:'El enlace tiene que empezar con https:// (o ser un código como PPSA28002)'},400);
    const et=(Array.isArray(q.et)?q.et:[]).filter(x=>['online','vr','vro','port','emu','series','excl'].includes(x));
    const {d}=await pjCambiar(env,d=>{d.agregar=d.agregar.filter(x=>!(x.c===c&&normJ(x.n)===normJ(n)));d.quitar=d.quitar.filter(x=>!(x.c===c&&normJ(x.n)===normJ(n)));
      const e={c,n,f:hoy};if(link)e.link=/^(PPSA|CUSA)/i.test(link)?link.toUpperCase():link;if(et.length)e.et=et;d.agregar.push(e)},'Panel: agregar "'+n.slice(0,60)+'" ('+c+')');
    return j({ok:true,agregar:d.agregar,quitar:d.quitar})}
  if(p==='juegos-quitar'){
    const {d,r}=await pjCambiar(env,d=>{const antes=d.agregar.length;d.agregar=d.agregar.filter(x=>!(x.c===c&&normJ(x.n)===normJ(n)));
      if(d.agregar.length<antes)return 'deshecho';let orig=n;const ed=d.editar.find(x=>x.c===c&&(x.nuevo||x.n)===n);if(ed){orig=ed.n;d.editar=d.editar.filter(x=>x!==ed)}if(!d.quitar.some(x=>x.c===c&&x.n===orig))d.quitar.push({c,n:orig,f:hoy});return 'quitado'},'Panel: quitar "'+n.slice(0,60)+'" ('+c+')');
    return j({ok:true,r,agregar:d.agregar,quitar:d.quitar})}
  if(p==='juegos-editar'){ // cambia nombre, enlace o etiquetas de un juego que ya está
    const nuevo=String(q.nuevo||'').replace(/\s+/g,' ').trim().slice(0,120)||n,link=String(q.link||'').trim().slice(0,300);
    if(link&&!/^https:\/\//.test(link)&&!/^(PPSA|CUSA)\d{5}$/i.test(link)&&!/^[A-Z]{2}\d{4}-[A-Z]{4}\d{5}_00-\w+$/.test(link)&&!((c==='Xbox pago'||c==='Xbox Game Pass')&&/^[0-9A-Z]{12}$/.test(link)))
      return j({error:'El enlace tiene que empezar con https:// (o ser un código como PPSA28002)'},400);
    const et=(Array.isArray(q.et)?q.et:[]).filter(x=>['online','vr','vro','port','emu','series','excl'].includes(x));
    const {d}=await pjCambiar(env,d=>{
      const ag=d.agregar.find(x=>x.c===c&&normJ(x.n)===normJ(n));
      if(ag){ag.n=nuevo;if(link){ag.link=/^(PPSA|CUSA)/i.test(link)?link.toUpperCase():link;delete ag.buscado}ag.et=et;return}
      let e=d.editar.find(x=>x.c===c&&(x.nuevo||x.n)===n);if(!e){e={c,n};d.editar.push(e)}
      if(nuevo!==e.n)e.nuevo=nuevo;else delete e.nuevo;if(link)e.link=/^(PPSA|CUSA)/i.test(link)?link.toUpperCase():link;e.et=et;e.f=hoy},'Panel: editar "'+n.slice(0,60)+'" ('+c+')');
    return j({ok:true,agregar:d.agregar,quitar:d.quitar,editar:d.editar})}
  if(p==='juegos-revertir'){ // deshace una edición
    const {d}=await pjCambiar(env,d=>{d.editar=d.editar.filter(x=>!(x.c===c&&(x.nuevo||x.n)===n))},'Panel: deshacer edición de "'+n.slice(0,60)+'" ('+c+')');
    return j({ok:true,agregar:d.agregar,quitar:d.quitar,editar:d.editar})}
  if(p==='juegos-devolver'){ // deshace un "quitar"
    const {d}=await pjCambiar(env,d=>{d.quitar=d.quitar.filter(x=>!(x.c===c&&x.n===n))},'Panel: devolver "'+n.slice(0,60)+'" ('+c+')');
    return j({ok:true,agregar:d.agregar,quitar:d.quitar})}
  return j({error:'No existe'},404);
}
// Las ofertas sin notificación van aparte (silenciosas) para que las apps viejas de Android no las avisen.
const activos=d=>{const h=hoyCuba();return d.avisos.concat(d.silenciosas||[]).filter(x=>!x.vence||x.vence>=h).sort((a,b)=>a.id<b.id?-1:1)};

// ---------- suscripciones ----------
async function claves(env){const out=[];let cur;do{const l=await env.SUBS.list({cursor:cur});out.push(...l.keys.map(k=>k.name));cur=l.list_complete?null:l.cursor}while(cur);return out.sort()}


// ---------- estadísticas (Durable Object con SQLite) ----------
const TIPOS=new Set(['visita','cat','busca','envio','juego','contacto','oferta','descarga','tiempo','equipo']);
const MODELOS=__MODELOS__;
/* Nombre comercial del teléfono a partir del código de modelo (ej. SM-A165F -> Samsung Galaxy A16). */
function nombreModelo(m){if(!m)return '';const k=m.toUpperCase().trim();if(MODELOS[k])return MODELOS[k];
  let r=k.match(/^SM-S9(\d)(\d)/);if(r)return 'Samsung Galaxy S'+(22+ +r[1])+({6:'+',7:'+',8:' Ultra'}[r[2]]||'');
  r=k.match(/^SM-([AMFE])(\d)(\d)(\d)/);if(r)return 'Samsung Galaxy '+r[1]+r[2]+r[3]+(r[4]==='7'?'s':'');
  if(/^SM-/.test(k))return 'Samsung '+m;return m}
// Nombres de modelos que no están en la lista de dentro: se buscan en tools/datos/modelos/<2 letras>.json (lista de Google, la actualiza una acción semanal)
const MOD_PARTES=new Map();const esCodigo=s=>typeof s==='string'&&/^[A-Z0-9][A-Z0-9_-]{3,}$/i.test(s.trim())&&!/\s/.test(s.trim());
async function nombresGoogle(lista){
  const pedir=[...new Set(lista.filter(esCodigo).map(s=>s.trim().toUpperCase()))];if(!pedir.length)return {};
  const out={};
  await Promise.all([...new Set(pedir.map(k=>{const a=k.replace(/[^A-Z0-9]/g,'').slice(0,2);return a.length===2?a:'__'}))].map(async p=>{
    let d=MOD_PARTES.get(p);if(d===undefined){try{const r=await fetch('https://raw.githubusercontent.com/'+REPO+'/main/tools/datos/modelos/'+p+'.json',{cf:{cacheTtl:86400,cacheEverything:true}});d=r.ok?await r.json():null}catch(e){d=null}MOD_PARTES.set(p,d)}
    if(d)for(const k of pedir)if(d[k])out[k]=d[k]}));
  return out;
}
const APK='https://gamex-cu.github.io/app/GameX-1.7.apk'; // respaldo: la dirección buena se lee de app/version.json (apkUrl)
let APK_CACHE=null;
async function apkUrl(){if(APK_CACHE&&Date.now()-APK_CACHE.t<300000)return APK_CACHE.u;try{const r=await fetch('https://raw.githubusercontent.com/'+REPO+'/main/app/version.json',{cf:{cacheTtl:0}});const j=await r.json();if(/^https:\/\/gamex-cu\.github\.io\/app\/[\w.-]+\.apk$/.test(j.apkUrl||'')){APK_CACHE={t:Date.now(),u:j.apkUrl};return j.apkUrl}}catch(e){}return APK}
const diaCuba=ms=>{try{return new Date(ms).toLocaleDateString('en-CA',{timeZone:'America/Havana'})}catch(e){return new Date(ms).toISOString().slice(0,10)}};
export class Stats extends DurableObject{
  constructor(ctx,env){super(ctx,env);this.sql=ctx.storage.sql;
    this.sql.exec('CREATE TABLE IF NOT EXISTS ev(ts INTEGER,dia TEXT,tipo TEXT,v TEXT,n INTEGER,uid TEXT,disp TEXT,org TEXT)');
    this.sql.exec('CREATE INDEX IF NOT EXISTS ev_dia ON ev(dia,tipo)');
    this.sql.exec('CREATE TABLE IF NOT EXISTS ign(uid TEXT PRIMARY KEY,nota TEXT,ts INTEGER)')}
  ignorar(uid,si,nota){if(si)this.sql.exec('INSERT OR REPLACE INTO ign VALUES(?,?,?)',uid,nota||'',Date.now());else this.sql.exec('DELETE FROM ign WHERE uid=?',uid);return true}
  ignorados(){return this.sql.exec("SELECT i.uid,i.nota,i.ts,(SELECT MAX(CASE WHEN tipo='equipo' THEN v END) FROM ev WHERE ev.uid=i.uid) modelo,(SELECT MAX(disp) FROM ev WHERE ev.uid=i.uid) disp FROM ign i ORDER BY ts DESC").toArray()}
  agregar(filas){const ahora=Date.now(),dia=diaCuba(ahora);
    for(const f of filas)this.sql.exec('INSERT INTO ev VALUES(?,?,?,?,?,?,?,?)',ahora,dia,f.tipo,f.v,f.n,f.uid,f.disp,f.org);
    if(Math.random()<0.01)this.sql.exec('DELETE FROM ev WHERE ts<?',ahora-400*864e5);return filas.length}
  reiniciar(){const n=this.sql.exec('SELECT COUNT(*) c FROM ev').one().c;this.sql.exec('DELETE FROM ev');return n}
  borrarUid(uid){if(uid.startsWith('prueba:'))this.sql.exec("DELETE FROM ev WHERE v=?",uid.slice(7));else this.sql.exec('DELETE FROM ev WHERE uid=?',uid);return true}
  resumen(dias){
    const hasta=diaCuba(Date.now()),desde=diaCuba(Date.now()-(dias-1)*864e5);
    const q=(sql,...a)=>this.sql.exec(sql,desde,hasta,...a).toArray();
    const W="dia>=? AND dia<=? AND uid NOT IN (SELECT uid FROM ign)";
    const tot=q(`SELECT SUM(tipo='visita') visitas,COUNT(DISTINCT CASE WHEN tipo='visita' THEN uid END) personas,SUM(tipo='envio') pedidos,SUM(CASE WHEN tipo='envio' THEN n ELSE 0 END) juegos,SUM(tipo='contacto') contactos,SUM(tipo='busca') busquedas FROM ev WHERE ${W}`)[0]||{};
    const porDia=q(`SELECT dia,SUM(tipo='visita') visitas,COUNT(DISTINCT CASE WHEN tipo='visita' THEN uid END) personas,SUM(tipo='envio') pedidos FROM ev WHERE ${W} GROUP BY dia ORDER BY dia`);
    const top=(tipo,lim,extra='')=>q(`SELECT v,COUNT(*) c FROM ev WHERE ${W} AND tipo=? ${extra} GROUP BY v ORDER BY c DESC,v LIMIT ${lim}`,tipo);
    const ignorados=this.ignorados().map(x=>({...x,v:x.uid.slice(0,4),modelo:nombreModelo(x.modelo)}));
    return {desde,hasta,dias,ignorados,tot,porDia,catalogos:top('cat',12),juegos:top('juego',15),busquedas:top('busca',15),sinResultado:top('busca',15,'AND n=0'),
      dispositivos:q(`SELECT disp v,COUNT(DISTINCT uid) c FROM ev WHERE ${W} AND tipo='visita' GROUP BY disp ORDER BY c DESC`),
      tiempo:q(`SELECT COALESCE(SUM(CASE WHEN tipo='tiempo' THEN n ELSE 0 END),0) seg FROM ev WHERE ${W}`)[0].seg,
      modelos:q(`SELECT v,COUNT(DISTINCT uid) c FROM ev WHERE ${W} AND tipo='equipo' AND v!='' GROUP BY v ORDER BY c DESC LIMIT 20`).map(x=>({v:nombreModelo(x.v),c:x.c})),
      equipos:q(`SELECT substr(uid,1,4) v,uid,MAX(disp) disp,MAX(CASE WHEN tipo='equipo' THEN v END) modelo,SUM(tipo='visita') visitas,COALESCE(SUM(CASE WHEN tipo='tiempo' THEN n ELSE 0 END),0) seg,SUM(tipo='envio') pedidos,MAX(ts) ultimo FROM ev WHERE ${W} AND uid!='anon' GROUP BY uid HAVING visitas>0 ORDER BY seg DESC,visitas DESC LIMIT 30`).map(x=>({...x,modelo:nombreModelo(x.modelo)})),
      consolas:q(`SELECT disp v,COUNT(*) c,SUM(n) j FROM ev WHERE ${W} AND tipo='envio' AND disp IN ('ps4','ps5','switch') GROUP BY disp ORDER BY c DESC`),
      app:{descargas:q(`SELECT COUNT(*) c FROM ev WHERE ${W} AND tipo='descarga'`)[0].c||0,
           usuarios:q(`SELECT COUNT(DISTINCT uid) c FROM ev WHERE ${W} AND disp='app'`)[0].c||0,
           descargasTotal:this.sql.exec(`SELECT COUNT(*) c FROM ev WHERE tipo='descarga' AND uid NOT IN (SELECT uid FROM ign)`).one().c||0,
           usuariosTotal:this.sql.exec(`SELECT COUNT(DISTINCT uid) c FROM ev WHERE disp='app' AND uid NOT IN (SELECT uid FROM ign)`).one().c||0}};
  }
}
const statsDO=env=>env.STATS.get(env.STATS.idFromName('gamex'));
// __CLIENTES__
async function evento(req,env){
  if(!env.STATS)return r('ok');
  let b;try{b=JSON.parse(await req.text())}catch(e){return r('mal',400)}
  const lista=Array.isArray(b&&b.e)?b.e.slice(0,40):[];
  const uid=String(b&&b.u||'').replace(/[^a-z0-9]/gi,'').slice(0,24)||'anon';
  const disp=['app','android','iphone','iphone-app','pc','ps4','ps5','switch','otro'].includes(b&&b.d)?b.d:'otro';
  const org=b&&b.o==='app'?'app':'web';
  const filas=lista.filter(x=>x&&TIPOS.has(x.t)).map(x=>({tipo:x.t,v:String(x.v||'').trim().slice(0,120),n:Number.isFinite(+x.n)?Math.max(0,Math.min(x.t==='tiempo'?10800:9999,Math.round(+x.n))):null,uid,disp,org}))
    .map(f=>f.tipo==='busca'?{...f,v:f.v.toLowerCase().replace(/\s+/g,' ')}:f).filter(f=>f.tipo==='visita'||f.tipo==='contacto'||f.tipo==='envio'||(f.tipo==='tiempo'&&f.n>0)||f.v);
  if(filas.length)await statsDO(env).agregar(filas);
  return r('ok');
}

// Contraseña del panel: si se cambió desde el panel vive cifrada en el Durable Object (cfg 'panel'); si no, la del secreto PANEL.
// HERRAMIENTAS es una llave larga para las herramientas y tareas programadas; no cambia con la contraseña.
const PANEL_OK=new Map();
async function panelAuth(env,clave){
  clave=sinAst(String(clave||''));if(!clave||clave.length>200)return false;
  if(env.HERRAMIENTAS&&igual(clave,env.HERRAMIENTAS))return true;
  const k=await id('gx-panel|'+clave),t=PANEL_OK.get(k);if(t&&t>Date.now())return true;
  const ph=env.STATS?await statsDO(env).panelHash():null;
  const ok=ph?igual(await hashClave(clave,ph.sal),ph.h):(!!env.PANEL&&igual(clave,sinAst(env.PANEL)));
  if(ok)PANEL_OK.set(k,Date.now()+60000);return ok;
}
async function panel(req,env,u){
  if(u.pathname==='/panel'||u.pathname==='/panel/')return new Response(PANEL_HTML,{headers:{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store','X-Frame-Options':'DENY','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff','Strict-Transport-Security':'max-age=31536000','Permissions-Policy':'camera=(), microphone=(), geolocation=()','Content-Security-Policy':"default-src 'self'; script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https://gamex-cu.github.io; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"}});
  if(!u.pathname.startsWith('/panel/api/'))return j({error:'No existe'},404);
  const ipP=req.headers.get('CF-Connecting-IP')||'?',DOp=env.STATS?statsDO(env):null;
  if(DOp&&await DOp.fallo('p:'+ipP,false)>=10)return j({error:'Demasiados intentos con contraseña equivocada. Espera 15 minutos.'},429);
  if(!await panelAuth(env,req.headers.get('X-Panel')||'')){if(DOp)await DOp.fallo('p:'+ipP,true);await new Promise(z=>setTimeout(z,1200));return j({error:'Contraseña incorrecta'},401)}
  const p=u.pathname.slice(11);
  try{
    if(p==='juegos'||p.startsWith('juegos-'))return await panelJuegos(p,req,env,u);
    if(p==='panel-clave'&&req.method==='POST'){const q=await req.json().catch(()=>({}));const act=String(q.actual||''),nu=String(q.nueva||'');
      if(!await panelAuth(env,act)||(env.HERRAMIENTAS&&igual(sinAst(act),env.HERRAMIENTAS)))return j({error:'La contraseña actual no es correcta'},400);
      if(nu.length<10)return j({error:'La nueva tiene que tener al menos 10 caracteres'},400);if(nu.length>100)return j({error:'Demasiado larga'},400);
      if(!/[A-Za-zÁÉÍÓÚÑáéíóúñ]/.test(nu)||!/\d/.test(nu))return j({error:'Ponle letras y al menos un número'},400);
      if(sinAst(nu)!==nu)return j({error:'No empieces ni termines con espacio o *'},400);if(nu===sinAst(act))return j({error:'Es igual a la actual'},400);
      const sal=crypto.randomUUID();await statsDO(env).panelHashPoner(await hashClave(nu,sal),sal);PANEL_OK.clear();return j({ok:true})}
    if(['archivo','archivo-guardar','gp-estado','gp-revisar','gp-publicar','foto','respaldo'].includes(p))return await panelDatos(p,req,env,u);
    if(p.startsWith('cli-')){const q=req.method==='POST'?await req.json().catch(()=>({})):Object.fromEntries(u.searchParams);const res=await panelClientes(p,req,env,q);if(res)return res}
    if(p==='stats'){
      if(!env.STATS)return j({error:'Las estadísticas no están activadas'},500);
      const d=[1,7,30,90].includes(+u.searchParams.get('dias'))?+u.searchParams.get('dias'):7;
      const R=await statsDO(env).resumen(d);
      try{const raws=[...(R.modelos||[]).map(x=>x.v),...(R.equipos||[]).map(x=>x.modelo),...(R.ignorados||[]).map(x=>x.modelo)];const N=await nombresGoogle(raws);
        const nm=v=>esCodigo(v)&&N[v.trim().toUpperCase()]||v;(R.modelos||[]).forEach(x=>x.v=nm(x.v));(R.equipos||[]).forEach(x=>{if(x.modelo)x.modelo=nm(x.modelo)});(R.ignorados||[]).forEach(x=>{if(x.modelo)x.modelo=nm(x.modelo)})}catch(e){}
      return j(R);
    }
    if(p==='stats-ignorar'&&req.method==='POST'){const q=await req.json().catch(()=>({}));if(!q.uid)return j({error:'Falta el equipo'},400);await statsDO(env).ignorar(String(q.uid).slice(0,40),!!q.si,String(q.nota||'').slice(0,40));return j({ok:true})}
    if(p==='stats-reiniciar'&&req.method==='POST'){const q=await req.json().catch(()=>({}));if(q.confirmar!=='LANZAMOS')return j({error:'Falta confirmar'},400);return j({ok:true,borrados:await statsDO(env).reiniciar()})}
    if(p==='stats-limpiar'&&req.method==='POST'){const q=await req.json().catch(()=>({}));if(!q.uid)return j({error:'Falta uid'},400);await statsDO(env).borrarUid(String(q.uid));return j({ok:true})}
    if(p==='estado'){
      const [ks,{d}]=await Promise.all([claves(env),leerAvisos(env)]);
      return j({iphones:ks.length,avisos:activos(d).reverse(),hoy:hoyCuba()});
    }
    if(req.method!=='POST')return j({error:'Usa POST'},405);
    const q=await req.json().catch(()=>({}));
    if(p==='enviar'){
      let titulo=String(q.titulo||'').trim().replace(/🎮/g,'🥷').slice(0,80),texto=String(q.texto||'').trim().slice(0,1500);
      const url=String(q.url||'').trim().slice(0,500),vence=/^\d{4}-\d{2}-\d{2}$/.test(q.vence||'')?q.vence:'';
      if(!titulo)return j({error:'Falta el título'},400);
      if(!texto&&q.modo!=='aviso')return j({error:'Falta el texto'},400);
      if(url&&!/^https:\/\//.test(url))return j({error:'El enlace tiene que empezar con https://'},400);
      if(!titulo.startsWith('🥷'))titulo='🥷 '+titulo;
      const hoy=hoyCuba(),aviso={id:`${hoy}-${Math.floor(Date.now()/1000)}`,fecha:hoy,titulo,texto};
      if(url)aviso.url=url;if(vence)aviso.vence=vence;const img=String(q.img||'').trim();if(/^https:\/\/gamex-cu\.github\.io\/app\/fotos\/[\w.-]+\.jpg$/.test(img))aviso.img=img;
      const modo=['ambas','oferta','aviso'].includes(q.modo)?q.modo:(q.notificar===false?'oferta':'ambas');
      const notificar=modo!=='oferta';if(!notificar)aviso.silenciosa=true;
      if(modo==='aviso')aviso.solo=true; // no se guarda en Ofertas
      const res={aviso,notificar,modo};
      if(modo==='aviso')res.ofertas='no';else try{await cambiarAvisos(env,d=>{if(aviso.silenciosa)d.silenciosas=(d.silenciosas||[]).filter(x=>!x.vence||x.vence>=hoy).slice(-19).concat([aviso]);else d.avisos=d.avisos.filter(x=>!x.vence||x.vence>=hoy).slice(-19).concat([aviso])},'Panel: oferta "'+titulo.replace(/^🥷\s*/,'').slice(0,50)+'"');res.ofertas='ok'}catch(e){res.ofertas=e.message}
      if(notificar){try{await pushAndroid(env,aviso);res.android='ok'}catch(e){res.android=e.message}}else res.android='no';
      return j(res);
    }
    if(p==='web'){
      const a=q.aviso||{},datos={};for(const k of ['id','titulo','texto','url'])if(a[k])datos[k]=k==='texto'?corto(a[k]):String(a[k]).slice(0,500);if(datos.url&&/wa\.me\/|whatsapp/i.test(datos.url))delete datos.url;if(!a.solo&&!datos.url)datos.dest='ofertas';
      if(!datos.id||!datos.titulo)return j({error:'Falta la oferta'},400);
      const ks=await claves(env),resto=ks.filter(k=>!q.despues||k>q.despues),lote=resto.slice(0,LOTE);
      let ok=0,viejos=0,fallos=0;
      await Promise.all(lote.map(async k=>{
        const v=await env.SUBS.get(k);if(!v)return;
        try{const c=await pushWeb(env,JSON.parse(v),datos);if(c>=200&&c<300)ok++;else if(c===404||c===410){await env.SUBS.delete(k);viejos++}else fallos++}catch(e){fallos++}
      }));
      return j({total:ks.length,ok,viejos,fallos,despues:lote.length?lote[lote.length-1]:null,fin:resto.length<=LOTE});
    }
    if(p==='editar'){ /* cambia una oferta ya publicada (sin volver a notificar) */
      const idA=String(q.id||'');if(!idA)return j({error:'Falta la oferta'},400);
      let titulo=String(q.titulo||'').trim().replace(/🎮/g,'🥷').slice(0,80),texto=String(q.texto||'').trim().slice(0,1500);
      const url=String(q.url||'').trim().slice(0,500),vence=/^\d{4}-\d{2}-\d{2}$/.test(q.vence||'')?q.vence:'';
      if(!titulo||!texto)return j({error:'Falta el título o el texto'},400);
      if(url&&!/^https:\/\//.test(url))return j({error:'El enlace tiene que empezar con https://'},400);
      if(!titulo.startsWith('🥷'))titulo='🥷 '+titulo;
      let hallada=false;
      const d=await cambiarAvisos(env,d=>{for(const l of [d.avisos,d.silenciosas||[]])for(const x of l)if(x.id===idA){hallada=true;x.titulo=titulo;x.texto=texto;if(url)x.url=url;else delete x.url;if(q.img!==undefined){const im=String(q.img||'');if(/^https:\/\/gamex-cu\.github\.io\/app\/fotos\/[\w.-]+\.jpg$/.test(im))x.img=im;else delete x.img}if(vence)x.vence=vence;else delete x.vence;x.editada=hoyCuba()}},'Panel: editar oferta "'+titulo.replace(/^🥷\s*/,'').slice(0,50)+'"');
      if(!hallada)return j({error:'No encontré esa oferta (¿ya la quitaron?)'},404);
      return j({ok:true,avisos:activos(d).reverse()});
    }
    if(p==='borrar'){
      const idA=String(q.id||'');if(!idA)return j({error:'Falta la oferta'},400);
      const d=await cambiarAvisos(env,d=>{d.avisos=d.avisos.filter(x=>x.id!==idA);d.silenciosas=(d.silenciosas||[]).filter(x=>x.id!==idA)},'Panel: quitar oferta');
      return j({ok:true,avisos:activos(d).reverse()});
    }
    return j({error:'No existe'},404);
  }catch(e){return j({error:e.message||String(e)},500)}
}

export default{async fetch(req,env){
  const u=new URL(req.url);
  if(u.pathname==='/panel'||u.pathname.startsWith('/panel/'))return panel(req,env,u);
  if(req.method==='OPTIONS')return new Response(null,{headers:CORS});
  if(u.pathname.startsWith('/cuenta/'))return cuenta(req,env,u); // Mi cuenta GameX (clientes)
  if(u.pathname==='/evento'&&req.method==='POST')return evento(req,env);
  if(u.pathname==='/no-contar'&&req.method==='POST'){ /* un equipo se saca a sí mismo de las estadísticas */
    let b={};try{b=JSON.parse(await req.text())}catch(e){}
    const uid=String(b.u||'').replace(/[^a-z0-9]/gi,'').slice(0,24);
    if(uid&&env.STATS)await statsDO(env).ignorar(uid,b.si!==false,'enlace #no-contar');
    return r('ok');
  }
  if(u.pathname==='/p'){ /* pedido hecho desde la app de consola (QR): se cuenta y se abre WhatsApp */
    const NUMS=['5353441089','5353827989','5352933943'],num=NUMS[+u.searchParams.get('n')]||NUMS[0];
    const app=['ps4','ps5','switch'].includes(u.searchParams.get('a'))?u.searchParams.get('a'):'otro',t=(u.searchParams.get('t')||'').slice(0,3000);
    if(env.STATS&&t){try{
      const ua=req.headers.get('User-Agent')||'',ip=req.headers.get('CF-Connecting-IP')||'';
      const uid=(await id(ip+ua+new Date().toISOString().slice(0,10))).slice(0,24);
      const filas=[];let cat='';
      for(const l of t.split('\n')){const m1=l.match(/^\*(.+)\*$/);if(m1){cat=m1[1];continue}
        const m2=l.match(/^\d+\.\s+(.+?)(?:\s+\((?:online|Series X\|S|online, Series X\|S)\))?$/);if(m2&&cat)filas.push({tipo:'juego',v:(cat+'|'+m2[1]).slice(0,120),n:null,uid,disp:app,org:app})}
      filas.unshift({tipo:'envio',v:'consola',n:filas.length,uid,disp:app,org:app});
      await statsDO(env).agregar(filas)}catch(e){}}
    return Response.redirect('https://wa.me/'+num+'?text='+encodeURIComponent(t),302);
  }
  if(u.pathname==='/c'){ /* catálogo en texto para las apps de consola (también por http simple) */
    const g=await fetch('https://raw.githubusercontent.com/gamex-cu/gamex-cu.github.io/main/app/consola.txt',{cf:{cacheTtl:300}});
    if(!g.ok)return new Response('error',{status:502});
    return new Response(g.body,{headers:{'Content-Type':'text/plain; charset=utf-8','Cache-Control':'max-age=300'}});
  }
  if(u.pathname==='/descargar'){ /* cuenta la descarga de la app y manda al APK */
    if(env.STATS){const ua=req.headers.get('User-Agent')||'',ip=req.headers.get('CF-Connecting-IP')||'';
      const uid=(await id(ip+ua+new Date().toISOString().slice(0,10))).slice(0,24);
      const disp=/android/i.test(ua)?'android':/iphone|ipad/i.test(ua)?'iphone':/windows|macintosh|linux/i.test(ua)?'pc':'otro';
      try{await statsDO(env).agregar([{tipo:'descarga',v:u.searchParams.get('de')||'web',n:null,uid,disp,org:'web'}])}catch(e){}}
    return Response.redirect(await apkUrl(),302);
  }
  if(u.pathname==='/suscribir'&&req.method==='POST'){
    let s;try{s=await req.json()}catch(e){return r('mal',400)}
    if(!s||typeof s.endpoint!=='string'||!s.endpoint.startsWith('https://')||s.endpoint.length>1000||!s.keys||typeof s.keys.p256dh!=='string'||typeof s.keys.auth!=='string')return r('mal',400);
    await env.SUBS.put(await id(s.endpoint),JSON.stringify({endpoint:s.endpoint,keys:{p256dh:s.keys.p256dh,auth:s.keys.auth},fecha:new Date().toISOString().slice(0,10)}));
    return r('ok');
  }
  if(!env.CLAVE||req.headers.get('X-Clave')!==env.CLAVE)return r('no',403);
  if(u.pathname==='/lista'){
    const out=[];for(const k of await claves(env)){const v=await env.SUBS.get(k);if(v)out.push(JSON.parse(v))}
    return r(out);
  }
  if(u.pathname==='/borrar'&&req.method==='POST'){const s=await req.json();await env.SUBS.delete(await id(s.endpoint));return r('ok')}
  return r('GameX avisos',200);
}};
