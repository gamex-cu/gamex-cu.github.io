// Cloudflare Worker de GameX: guarda las suscripciones de avisos (iPhone y navegadores).
// POST /suscribir   (público)  -> guarda la suscripción
// GET  /lista       (X-Clave)  -> devuelve todas las suscripciones
// POST /borrar      (X-Clave)  -> borra una suscripción {endpoint}
// Necesita: KV "SUBS" y la variable secreta CLAVE.
const CORS={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Methods':'GET,POST,OPTIONS','Access-Control-Allow-Headers':'Content-Type,X-Clave'};
const r=(b,s=200)=>new Response(typeof b==='string'?b:JSON.stringify(b),{status:s,headers:{...CORS,'Content-Type':'application/json'}});
async function id(t){const h=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(t));return [...new Uint8Array(h)].map(x=>x.toString(16).padStart(2,'0')).join('')}
export default{async fetch(req,env){
  if(req.method==='OPTIONS')return new Response(null,{headers:CORS});
  const u=new URL(req.url);
  if(u.pathname==='/suscribir'&&req.method==='POST'){
    let s;try{s=await req.json()}catch(e){return r('mal',400)}
    if(!s||typeof s.endpoint!=='string'||!s.endpoint.startsWith('https://')||s.endpoint.length>1000||!s.keys||typeof s.keys.p256dh!=='string'||typeof s.keys.auth!=='string')return r('mal',400);
    await env.SUBS.put(await id(s.endpoint),JSON.stringify({endpoint:s.endpoint,keys:{p256dh:s.keys.p256dh,auth:s.keys.auth},fecha:new Date().toISOString().slice(0,10)}));
    return r('ok');
  }
  if(!env.CLAVE||req.headers.get('X-Clave')!==env.CLAVE)return r('no',403);
  if(u.pathname==='/lista'){
    const out=[];let cur;do{const l=await env.SUBS.list({cursor:cur});for(const k of l.keys){const v=await env.SUBS.get(k.name);if(v)out.push(JSON.parse(v))}cur=l.list_complete?null:l.cursor}while(cur);
    return r(out);
  }
  if(u.pathname==='/borrar'&&req.method==='POST'){const s=await req.json();await env.SUBS.delete(await id(s.endpoint));return r('ok')}
  return r('GameX avisos',200);
}};
