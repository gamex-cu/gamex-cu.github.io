// Cloudflare Worker de GameX: avisos (iPhone/navegadores) + panel para mandar ofertas.
// POST /suscribir        (público)   -> guarda la suscripción web push
// GET  /lista            (X-Clave)   -> devuelve todas las suscripciones (lo usa tools/enviar_aviso.py)
// POST /borrar           (X-Clave)   -> borra una suscripción {endpoint}
// GET  /panel                        -> página del panel (pide contraseña)
// GET  /panel/api/estado (X-Panel)   -> iPhones suscritos + ofertas activas
// POST /panel/api/enviar (X-Panel)   -> agrega la oferta a app/avisos.json (GitHub) y la manda por Firebase (Android)
// POST /panel/api/web    (X-Panel)   -> manda la oferta a los iPhone, de 40 en 40
// POST /panel/api/borrar (X-Panel)   -> quita una oferta de app/avisos.json
// POST /evento          (público)   -> estadísticas anónimas de la web/app (visitas, catálogos, búsquedas, pedidos)
// GET  /panel/api/stats  (X-Panel)   -> resumen de estadísticas (?dias=1|7|30|90)
// Necesita: Durable Object STATS (clase Stats, guarda los eventos en SQLite), KV "SUBS" y los secretos CLAVE, PANEL (contraseña), VAPID, FIREBASE y GITHUB.
import {DurableObject} from 'cloudflare:workers';
const CORS={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Methods':'GET,POST,OPTIONS','Access-Control-Allow-Headers':'Content-Type,X-Clave'};
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
async function pushAndroid(env,aviso){
  const key=JSON.parse(env.FIREBASE),tok=await tokenGoogle(key);
  const data={};for(const k of ['id','titulo','texto','url'])if(aviso[k])data[k]=String(aviso[k]);
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
  if(!Array.isArray(d.avisos))d.avisos=[];return {d,sha:f.sha};
}
async function guardarAvisos(env,d,sha,msg){
  const res=await fetch(`https://api.github.com/repos/${REPO}/contents/${ARCH}`,{method:'PUT',headers:{...GH(env),'Content-Type':'application/json'},
    body:JSON.stringify({message:msg,content:b64(TE.encode(JSON.stringify(d,null,1))),sha,branch:'main'})});
  if(!res.ok)throw new Error('GitHub '+res.status+': '+(await res.text()).slice(0,200));
}
async function cambiarAvisos(env,fn,msg){ // reintenta si alguien más cambió el archivo a la vez
  for(let i=0;i<3;i++){const {d,sha}=await leerAvisos(env);fn(d);try{await guardarAvisos(env,d,sha,msg);return d}catch(e){if(i===2||!/ 409| 422/.test(e.message))throw e}}
}
const activos=d=>{const h=hoyCuba();return d.avisos.filter(x=>!x.vence||x.vence>=h)};

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
const APK='https://gamex-cu.github.io/app/GAMEX-Catalogo.apk';
const diaCuba=ms=>{try{return new Date(ms).toLocaleDateString('en-CA',{timeZone:'America/Havana'})}catch(e){return new Date(ms).toISOString().slice(0,10)}};
export class Stats extends DurableObject{
  constructor(ctx,env){super(ctx,env);this.sql=ctx.storage.sql;
    this.sql.exec('CREATE TABLE IF NOT EXISTS ev(ts INTEGER,dia TEXT,tipo TEXT,v TEXT,n INTEGER,uid TEXT,disp TEXT,org TEXT)');
    this.sql.exec('CREATE INDEX IF NOT EXISTS ev_dia ON ev(dia,tipo)')}
  agregar(filas){const ahora=Date.now(),dia=diaCuba(ahora);
    for(const f of filas)this.sql.exec('INSERT INTO ev VALUES(?,?,?,?,?,?,?,?)',ahora,dia,f.tipo,f.v,f.n,f.uid,f.disp,f.org);
    if(Math.random()<0.01)this.sql.exec('DELETE FROM ev WHERE ts<?',ahora-400*864e5);return filas.length}
  reiniciar(){const n=this.sql.exec('SELECT COUNT(*) c FROM ev').one().c;this.sql.exec('DELETE FROM ev');return n}
  borrarUid(uid){if(uid.startsWith('prueba:'))this.sql.exec("DELETE FROM ev WHERE v=?",uid.slice(7));else this.sql.exec('DELETE FROM ev WHERE uid=?',uid);return true}
  resumen(dias){
    const hasta=diaCuba(Date.now()),desde=diaCuba(Date.now()-(dias-1)*864e5);
    const q=(sql,...a)=>this.sql.exec(sql,desde,hasta,...a).toArray();
    const W='dia>=? AND dia<=?';
    const tot=q(`SELECT SUM(tipo='visita') visitas,COUNT(DISTINCT CASE WHEN tipo='visita' THEN uid END) personas,SUM(tipo='envio') pedidos,SUM(CASE WHEN tipo='envio' THEN n ELSE 0 END) juegos,SUM(tipo='contacto') contactos,SUM(tipo='busca') busquedas FROM ev WHERE ${W}`)[0]||{};
    const porDia=q(`SELECT dia,SUM(tipo='visita') visitas,COUNT(DISTINCT CASE WHEN tipo='visita' THEN uid END) personas,SUM(tipo='envio') pedidos FROM ev WHERE ${W} GROUP BY dia ORDER BY dia`);
    const top=(tipo,lim,extra='')=>q(`SELECT v,COUNT(*) c FROM ev WHERE ${W} AND tipo=? ${extra} GROUP BY v ORDER BY c DESC,v LIMIT ${lim}`,tipo);
    return {desde,hasta,dias,tot,porDia,catalogos:top('cat',12),juegos:top('juego',15),busquedas:top('busca',15),sinResultado:top('busca',15,'AND n=0'),
      dispositivos:q(`SELECT disp v,COUNT(DISTINCT uid) c FROM ev WHERE ${W} AND tipo='visita' GROUP BY disp ORDER BY c DESC`),
      tiempo:q(`SELECT COALESCE(SUM(CASE WHEN tipo='tiempo' THEN n ELSE 0 END),0) seg FROM ev WHERE ${W}`)[0].seg,
      modelos:q(`SELECT v,COUNT(DISTINCT uid) c FROM ev WHERE ${W} AND tipo='equipo' AND v!='' GROUP BY v ORDER BY c DESC LIMIT 20`).map(x=>({v:nombreModelo(x.v),c:x.c})),
      equipos:q(`SELECT substr(uid,1,4) v,MAX(disp) disp,MAX(CASE WHEN tipo='equipo' THEN v END) modelo,SUM(tipo='visita') visitas,COALESCE(SUM(CASE WHEN tipo='tiempo' THEN n ELSE 0 END),0) seg,SUM(tipo='envio') pedidos,MAX(ts) ultimo FROM ev WHERE ${W} AND uid!='anon' GROUP BY uid HAVING visitas>0 ORDER BY seg DESC,visitas DESC LIMIT 30`).map(x=>({...x,modelo:nombreModelo(x.modelo)})),
      app:{descargas:q(`SELECT COUNT(*) c FROM ev WHERE ${W} AND tipo='descarga'`)[0].c||0,
           usuarios:q(`SELECT COUNT(DISTINCT uid) c FROM ev WHERE ${W} AND disp='app'`)[0].c||0,
           descargasTotal:this.sql.exec(`SELECT COUNT(*) c FROM ev WHERE tipo='descarga'`).one().c||0,
           usuariosTotal:this.sql.exec(`SELECT COUNT(DISTINCT uid) c FROM ev WHERE disp='app'`).one().c||0}};
  }
}
const statsDO=env=>env.STATS.get(env.STATS.idFromName('gamex'));
async function evento(req,env){
  if(!env.STATS)return r('ok');
  let b;try{b=JSON.parse(await req.text())}catch(e){return r('mal',400)}
  const lista=Array.isArray(b&&b.e)?b.e.slice(0,40):[];
  const uid=String(b&&b.u||'').replace(/[^a-z0-9]/gi,'').slice(0,24)||'anon';
  const disp=['app','android','iphone','iphone-app','pc','otro'].includes(b&&b.d)?b.d:'otro';
  const org=b&&b.o==='app'?'app':'web';
  const filas=lista.filter(x=>x&&TIPOS.has(x.t)).map(x=>({tipo:x.t,v:String(x.v||'').trim().slice(0,120),n:Number.isFinite(+x.n)?Math.max(0,Math.min(x.t==='tiempo'?10800:9999,Math.round(+x.n))):null,uid,disp,org}))
    .map(f=>f.tipo==='busca'?{...f,v:f.v.toLowerCase().replace(/\s+/g,' ')}:f).filter(f=>f.tipo==='visita'||f.tipo==='contacto'||f.tipo==='envio'||f.v);
  if(filas.length)await statsDO(env).agregar(filas);
  return r('ok');
}

async function panel(req,env,u){
  if(u.pathname==='/panel'||u.pathname==='/panel/')return new Response(PANEL_HTML,{headers:{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store','X-Frame-Options':'DENY','Referrer-Policy':'no-referrer'}});
  if(!u.pathname.startsWith('/panel/api/'))return j({error:'No existe'},404);
  if(!env.PANEL||!igual(sinAst(req.headers.get('X-Panel')||''),sinAst(env.PANEL))){await new Promise(z=>setTimeout(z,1200));return j({error:'Contraseña incorrecta'},401)}
  const p=u.pathname.slice(11);
  try{
    if(p==='stats'){
      if(!env.STATS)return j({error:'Las estadísticas no están activadas'},500);
      const d=[1,7,30,90].includes(+u.searchParams.get('dias'))?+u.searchParams.get('dias'):7;
      return j(await statsDO(env).resumen(d));
    }
    if(p==='stats-reiniciar'&&req.method==='POST'){const q=await req.json().catch(()=>({}));if(q.confirmar!=='LANZAMOS')return j({error:'Falta confirmar'},400);return j({ok:true,borrados:await statsDO(env).reiniciar()})}
    if(p==='stats-limpiar'&&req.method==='POST'){const q=await req.json().catch(()=>({}));if(!q.uid)return j({error:'Falta uid'},400);await statsDO(env).borrarUid(String(q.uid));return j({ok:true})}
    if(p==='estado'){
      const [ks,{d}]=await Promise.all([claves(env),leerAvisos(env)]);
      return j({iphones:ks.length,avisos:activos(d).reverse(),hoy:hoyCuba()});
    }
    if(req.method!=='POST')return j({error:'Usa POST'},405);
    const q=await req.json().catch(()=>({}));
    if(p==='enviar'){
      let titulo=String(q.titulo||'').trim().replace(/🎮/g,'🥷').slice(0,80),texto=String(q.texto||'').trim().slice(0,400);
      const url=String(q.url||'').trim().slice(0,500),vence=/^\d{4}-\d{2}-\d{2}$/.test(q.vence||'')?q.vence:'';
      if(!titulo||!texto)return j({error:'Falta el título o el texto'},400);
      if(url&&!/^https:\/\//.test(url))return j({error:'El enlace tiene que empezar con https://'},400);
      if(!titulo.startsWith('🥷'))titulo='🥷 '+titulo;
      const hoy=hoyCuba(),aviso={id:`${hoy}-${Math.floor(Date.now()/1000)}`,fecha:hoy,titulo,texto};
      if(url)aviso.url=url;if(vence)aviso.vence=vence;
      const res={aviso};
      try{await cambiarAvisos(env,d=>{d.avisos=d.avisos.filter(x=>!x.vence||x.vence>=hoy).slice(-19).concat([aviso])},'Panel: oferta "'+titulo.replace(/^🥷\s*/,'').slice(0,50)+'"');res.ofertas='ok'}catch(e){res.ofertas=e.message}
      try{await pushAndroid(env,aviso);res.android='ok'}catch(e){res.android=e.message}
      return j(res);
    }
    if(p==='web'){
      const a=q.aviso||{},datos={};for(const k of ['id','titulo','texto','url'])if(a[k])datos[k]=String(a[k]).slice(0,500);
      if(!datos.id||!datos.titulo)return j({error:'Falta la oferta'},400);
      const ks=await claves(env),resto=ks.filter(k=>!q.despues||k>q.despues),lote=resto.slice(0,LOTE);
      let ok=0,viejos=0,fallos=0;
      await Promise.all(lote.map(async k=>{
        const v=await env.SUBS.get(k);if(!v)return;
        try{const c=await pushWeb(env,JSON.parse(v),datos);if(c>=200&&c<300)ok++;else if(c===404||c===410){await env.SUBS.delete(k);viejos++}else fallos++}catch(e){fallos++}
      }));
      return j({total:ks.length,ok,viejos,fallos,despues:lote.length?lote[lote.length-1]:null,fin:resto.length<=LOTE});
    }
    if(p==='borrar'){
      const idA=String(q.id||'');if(!idA)return j({error:'Falta la oferta'},400);
      const d=await cambiarAvisos(env,d=>{d.avisos=d.avisos.filter(x=>x.id!==idA)},'Panel: quitar oferta');
      return j({ok:true,avisos:activos(d).reverse()});
    }
    return j({error:'No existe'},404);
  }catch(e){return j({error:e.message||String(e)},500)}
}

export default{async fetch(req,env){
  const u=new URL(req.url);
  if(u.pathname==='/panel'||u.pathname.startsWith('/panel/'))return panel(req,env,u);
  if(req.method==='OPTIONS')return new Response(null,{headers:CORS});
  if(u.pathname==='/evento'&&req.method==='POST')return evento(req,env);
  if(u.pathname==='/descargar'){ /* cuenta la descarga de la app y manda al APK */
    if(env.STATS){const ua=req.headers.get('User-Agent')||'',ip=req.headers.get('CF-Connecting-IP')||'';
      const uid=(await id(ip+ua+new Date().toISOString().slice(0,10))).slice(0,24);
      const disp=/android/i.test(ua)?'android':/iphone|ipad/i.test(ua)?'iphone':/windows|macintosh|linux/i.test(ua)?'pc':'otro';
      try{await statsDO(env).agregar([{tipo:'descarga',v:u.searchParams.get('de')||'web',n:null,uid,disp,org:'web'}])}catch(e){}}
    return Response.redirect(APK,302);
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
