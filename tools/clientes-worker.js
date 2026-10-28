// ---------- GameX Rewards: clientes, GX, nivel y prestigio ----------
// Se inserta en push-worker.js al desplegar (marcador // __CLIENTES__). Los datos viven en el mismo
// Durable Object de estadísticas (SQLite), en tablas aparte: cli, mov, sol, ses, fallos.
// Reglas copiadas del Excel "GameX Rewards v2" (hoja GX_Config).
const GXR={porDolar:10,valorGX:0.005,n1:1500,p1:9,n2:2500,p2:17.5,n3:3500,p3:28,referido:100,prestigio:2000,cumple:2};
const nivelDe=s=>s>=GXR.n3?'Nivel 3 / MAX':s>=GXR.n2?'Nivel 2':s>=GXR.n1?'Nivel 1':'Base';
const valorDe=s=>s>=GXR.n3?GXR.p3:s>=GXR.n2?GXR.p2+(s-GXR.n2)*GXR.valorGX:s>=GXR.n1?GXR.p1+(s-GXR.n1)*GXR.valorGX:s*GXR.valorGX;
const r2=x=>Math.round(x*100)/100;
const esFecha=s=>/^\d{4}-\d{2}-\d{2}$/.test(s||'');
/* Semana de cumpleaños: 3 días antes, el día y 3 días después (mira el año anterior, el actual y el siguiente, como el Excel). */
function enCumple(fecha,nac){
  if(!esFecha(fecha)||!esFecha(nac))return false;
  const [y,m,d]=fecha.split('-').map(Number),[,mn,dn]=nac.split('-').map(Number),f=Date.UTC(y,m-1,d);
  return [y-1,y,y+1].some(a=>Math.abs(f-Date.UTC(a,mn-1,dn))<=3*864e5);
}
/* Calcula los GX de un movimiento. n = GX escritos a mano (canje y ajustes). */
function calcularMov(tipo,importe,n,fecha,nac){
  const o={cumple:0,base:0,bono:0,ganados:0,usados:0,prest:0};
  if(tipo==='Compra'){o.base=Math.round(importe*GXR.porDolar);o.cumple=enCumple(fecha,nac)?1:0;o.bono=o.cumple?o.base*(GXR.cumple-1):0;o.ganados=o.base+o.bono;o.prest=o.ganados}
  else if(tipo==='Referido'){o.bono=GXR.referido;o.ganados=GXR.referido}
  else if(tipo==='Ajuste +'){o.ganados=Math.max(0,Math.round(n))}
  else if(tipo==='Canje'||tipo==='Ajuste -'){o.usados=Math.max(0,Math.round(n))}
  return o;
}
function resumenCli(movs){
  let g=0,u=0,p=0,gast=0,compras=0,refs=0;
  for(const x of movs){g+=x.ganados;u+=x.usados;p+=x.prest;if(x.tipo==='Compra'){gast+=x.importe;compras++}if(x.tipo==='Referido')refs++}
  const saldo=g-u,nivel=nivelDe(saldo),sig=saldo<GXR.n1?GXR.n1:saldo<GXR.n2?GXR.n2:saldo<GXR.n3?GXR.n3:null;
  return {saldo,nivel,valor:r2(valorDe(saldo)),historicos:g,prestigioGX:p,prestigio:Math.floor(p/GXR.prestigio),
    faltaPrestigio:GXR.prestigio-(p%GXR.prestigio),gastado:r2(gast),compras,referidos:refs,siguiente:sig,faltan:sig?sig-saldo:0};
}
const numGX=gx=>parseInt(String(gx).slice(2),10);
const fmtGX=n=>'GX'+String(n).padStart(4,'0');
const limpiaGX=s=>{const m=String(s||'').toUpperCase().replace(/\s/g,'').match(/^(?:GX?)?(\d{1,6})$/);return m?fmtGX(+m[1]):''};
const TIPOS_MOV=['Compra','Canje','Referido','Ajuste +','Ajuste -'];

const CLI={
  cliInit(){if(this._cli)return;this._cli=1;const s=this.sql;
    s.exec('CREATE TABLE IF NOT EXISTS cli(gx TEXT PRIMARY KEY,nombre TEXT,tel TEXT,nac TEXT,registro TEXT,plataforma TEXT,estado TEXT,ph TEXT,sal TEXT,creado INTEGER,nota TEXT)');
    s.exec('CREATE TABLE IF NOT EXISTS mov(id INTEGER PRIMARY KEY AUTOINCREMENT,fecha TEXT,gx TEXT,tipo TEXT,descr TEXT,importe REAL,cumple INTEGER,base INTEGER,bono INTEGER,ganados INTEGER,usados INTEGER,prest INTEGER,obs TEXT,creado INTEGER)');
    s.exec('CREATE INDEX IF NOT EXISTS mov_gx ON mov(gx)');
    s.exec('CREATE TABLE IF NOT EXISTS sol(id INTEGER PRIMARY KEY AUTOINCREMENT,fecha TEXT,nombre TEXT,apellidos TEXT,nac TEXT,tel TEXT,plataforma TEXT,ph TEXT,sal TEXT,k TEXT,estado TEXT,gx TEXT,creado INTEGER,nota TEXT)');
    s.exec('CREATE TABLE IF NOT EXISTS ses(tok TEXT PRIMARY KEY,gx TEXT,exp INTEGER)');
    s.exec('CREATE TABLE IF NOT EXISTS fallos(clave TEXT PRIMARY KEY,n INTEGER,ts INTEGER)')},
  _movs(gx){return this.sql.exec('SELECT * FROM mov WHERE gx=? ORDER BY fecha DESC,id DESC',gx).toArray()},
  _cli1(gx){return this.sql.exec('SELECT * FROM cli WHERE gx=?',gx).toArray()[0]},
  _pub(c){if(!c)return null;const {ph,sal,...x}=c;return {...x,activada:!!ph}},
  cliLista(){this.cliInit();
    const cs=this.sql.exec('SELECT * FROM cli ORDER BY gx').toArray(),ms=this.sql.exec('SELECT * FROM mov').toArray(),por={};
    for(const m of ms)(por[m.gx]=por[m.gx]||[]).push(m);
    const pend=this.sql.exec("SELECT COUNT(*) c FROM sol WHERE estado='pendiente'").one().c;
    return {clientes:cs.map(c=>({...this._pub(c),...resumenCli(por[c.gx]||[]),ultima:(por[c.gx]||[]).reduce((a,m)=>m.fecha>a?m.fecha:a,'')})),pendientes:pend,siguiente:this.cliSiguiente(),reglas:GXR}},
  cliSiguiente(){this.cliInit();const xs=[...this.sql.exec('SELECT gx FROM cli').toArray(),...this.sql.exec("SELECT gx FROM sol WHERE gx!=''").toArray()].map(x=>numGX(x.gx)).filter(n=>!isNaN(n));return fmtGX(xs.length?Math.max(...xs)+1:0)},
  cliFicha(gx){this.cliInit();const c=this._cli1(gx);if(!c)return null;const movs=this._movs(gx);return {cliente:this._pub(c),resumen:resumenCli(movs),movs,reglas:GXR}},
  cliGuardar(d){this.cliInit();const gx=limpiaGX(d.gx);if(!gx)return {error:'ID GX no válido'};const c=this._cli1(gx);
    if(d.nuevo&&c)return {error:gx+' ya existe'};if(!d.nuevo&&!c)return {error:gx+' no existe'};
    const v={nombre:String(d.nombre||'').trim().slice(0,80),tel:String(d.tel||'').replace(/\D/g,'').slice(-8),nac:esFecha(d.nac)?d.nac:'',registro:esFecha(d.registro)?d.registro:diaCuba(Date.now()),plataforma:String(d.plataforma||'').slice(0,30),estado:d.estado==='reservado'?'reservado':'activo',nota:String(d.nota||'').slice(0,200)};
    if(c)this.sql.exec('UPDATE cli SET nombre=?,tel=?,nac=?,registro=?,plataforma=?,estado=?,nota=? WHERE gx=?',v.nombre,v.tel,v.nac,c.registro&&!d.registro?c.registro:v.registro,v.plataforma,v.estado,v.nota,gx);
    else this.sql.exec('INSERT INTO cli VALUES(?,?,?,?,?,?,?,NULL,NULL,?,?)',gx,v.nombre,v.tel,v.nac,v.registro,v.plataforma,v.estado,Date.now(),v.nota);
    if(c&&c.nac!==v.nac)this._recalcCumple(gx,v.nac);
    return this.cliFicha(gx)},
  _recalcCumple(gx,nac){for(const m of this._movs(gx))if(m.tipo==='Compra'){const o=calcularMov('Compra',m.importe,0,m.fecha,nac);this.sql.exec('UPDATE mov SET cumple=?,base=?,bono=?,ganados=?,prest=? WHERE id=?',o.cumple,o.base,o.bono,o.ganados,o.prest,m.id)}},
  cliMov(d){this.cliInit();const gx=limpiaGX(d.gx),c=gx&&this._cli1(gx);if(!c)return {error:'Cliente no encontrado'};
    if(!TIPOS_MOV.includes(d.tipo))return {error:'Tipo no válido'};
    const fecha=esFecha(d.fecha)?d.fecha:diaCuba(Date.now()),importe=d.tipo==='Compra'?r2(Math.max(0,+d.importe||0)):0,n=+d.n||0;
    if(d.tipo==='Compra'&&!(importe>0))return {error:'Pon el importe de la compra'};
    if(['Canje','Ajuste +','Ajuste -'].includes(d.tipo)&&!(n>0))return {error:'Pon cuántos GX'};
    if(['Canje','Ajuste -'].includes(d.tipo)){const s=resumenCli(this._movs(gx)).saldo;if(n>s)return {error:`El cliente solo tiene ${s} GX`}}
    const o=calcularMov(d.tipo,importe,n,fecha,c.nac);
    this.sql.exec('INSERT INTO mov(fecha,gx,tipo,descr,importe,cumple,base,bono,ganados,usados,prest,obs,creado) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',fecha,gx,d.tipo,String(d.descr||'').slice(0,120),importe,o.cumple,o.base,o.bono,o.ganados,o.usados,o.prest,String(d.obs||'').slice(0,200),Date.now());
    return {...this.cliFicha(gx),nuevo:{tipo:d.tipo,...o}}},
  cliMovBorrar(id){this.cliInit();const m=this.sql.exec('SELECT gx FROM mov WHERE id=?',+id).toArray()[0];if(!m)return {error:'No existe'};this.sql.exec('DELETE FROM mov WHERE id=?',+id);return this.cliFicha(m.gx)},
  cliBorrar(gx){this.cliInit();const n=this.sql.exec('SELECT COUNT(*) c FROM mov WHERE gx=?',gx).one().c;if(n)return {error:'Tiene movimientos: bórralos primero o déjalo como reservado'};this.sql.exec('DELETE FROM cli WHERE gx=?',gx);this.sql.exec('DELETE FROM ses WHERE gx=?',gx);return {ok:true}},
  cliClaveReset(gx){this.cliInit();this.sql.exec('UPDATE cli SET ph=NULL,sal=NULL WHERE gx=?',gx);this.sql.exec('DELETE FROM ses WHERE gx=?',gx);return this.cliFicha(gx)},
  cliImportar(d){this.cliInit();const hay=this.sql.exec('SELECT COUNT(*) c FROM cli').one().c+this.sql.exec('SELECT COUNT(*) c FROM mov').one().c;
    if(hay&&!d.reemplazar)return {error:'Ya hay datos; manda reemplazar:true para borrarlos y cargar de nuevo'};
    if(d.reemplazar){this.sql.exec('DELETE FROM cli');this.sql.exec('DELETE FROM mov')}
    for(const c of d.clientes||[])this.sql.exec('INSERT INTO cli VALUES(?,?,?,?,?,?,?,NULL,NULL,?,?)',c.gx,c.nombre||'',c.tel||'',c.nac||'',c.registro||'',c.plataforma||'',c.estado||'activo',Date.now(),c.nota||'');
    let n=0;for(const m of d.movs||[]){const c=this._cli1(m.gx);const o=calcularMov(m.tipo,+m.importe||0,+m.n||0,m.fecha,c&&c.nac);
      this.sql.exec('INSERT INTO mov(fecha,gx,tipo,descr,importe,cumple,base,bono,ganados,usados,prest,obs,creado) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',m.fecha,m.gx,m.tipo,m.descr||'',+m.importe||0,o.cumple,o.base,o.bono,o.ganados,o.usados,o.prest,m.obs||'',Date.now());n++}
    return {ok:true,clientes:(d.clientes||[]).length,movs:n}},
  cliExportar(){this.cliInit();return {clientes:this.cliLista().clientes,movs:this.sql.exec('SELECT * FROM mov ORDER BY fecha,id').toArray(),solicitudes:this.sql.exec('SELECT id,fecha,nombre,apellidos,nac,tel,plataforma,estado,gx,nota FROM sol ORDER BY id').toArray(),reglas:GXR}},
  // --- solicitudes ---
  solCrear(d){this.cliInit();const hoy=diaCuba(Date.now());
    const rec=this.sql.exec("SELECT COUNT(*) c FROM sol WHERE tel=? AND estado='pendiente'",d.tel).one().c;if(rec)return {error:'Ya hay una solicitud pendiente con ese teléfono. Te escribimos pronto.'};
    this.sql.exec("INSERT INTO sol(fecha,nombre,apellidos,nac,tel,plataforma,ph,sal,k,estado,gx,creado,nota) VALUES(?,?,?,?,?,?,?,?,?,'pendiente','',?,'')",hoy,d.nombre,d.apellidos,d.nac,d.tel,d.plataforma,d.ph,d.sal,d.k,Date.now());
    return {id:this.sql.exec('SELECT last_insert_rowid() id').one().id}},
  solLista(){this.cliInit();return {solicitudes:this.sql.exec('SELECT id,fecha,nombre,apellidos,nac,tel,plataforma,estado,gx,nota FROM sol ORDER BY (estado=\'pendiente\') DESC,id DESC LIMIT 200').toArray(),siguiente:this.cliSiguiente()}},
  solBorrar(id){this.cliInit();this.sql.exec('DELETE FROM sol WHERE id=?',+id);return this.solLista()},
  solEstado(id,k){this.cliInit();const s=this.sql.exec('SELECT estado,gx,k FROM sol WHERE id=?',+id).toArray()[0];if(!s||s.k!==k)return {error:'No encontrada'};return {estado:s.estado,gx:s.estado==='aprobada'?s.gx:''}},
  solResolver(id,accion,gxPedido,nota){this.cliInit();const s=this.sql.exec('SELECT * FROM sol WHERE id=?',+id).toArray()[0];if(!s)return {error:'No existe'};
    if(s.estado!=='pendiente')return {error:'Ya estaba '+s.estado};
    if(accion==='rechazar'){this.sql.exec("UPDATE sol SET estado='rechazada',nota=? WHERE id=?",String(nota||'').slice(0,200),+id);return this.solLista()}
    const gx=limpiaGX(gxPedido)||this.cliSiguiente(),c=this._cli1(gx);
    if(c&&c.estado!=='reservado')return {error:gx+' ya es de '+(c.nombre||'otro cliente')};
    const nombre=(s.nombre+' '+s.apellidos).trim();
    if(c)this.sql.exec("UPDATE cli SET nombre=?,tel=?,nac=?,registro=?,plataforma=?,estado='activo',ph=?,sal=? WHERE gx=?",nombre,s.tel,s.nac,diaCuba(Date.now()),s.plataforma,s.ph,s.sal,gx);
    else this.sql.exec("INSERT INTO cli VALUES(?,?,?,?,?,?,'activo',?,?,?,'')",gx,nombre,s.tel,s.nac,diaCuba(Date.now()),s.plataforma,s.ph,s.sal,Date.now());
    this.sql.exec("UPDATE sol SET estado='aprobada',gx=? WHERE id=?",gx,+id);
    return {...this.solLista(),aprobado:{gx,nombre,tel:s.tel}}},
  // --- acceso del cliente ---
  cred(gx){this.cliInit();const c=this._cli1(gx);return c?{gx:c.gx,nac:c.nac,tel:c.tel,ph:c.ph,sal:c.sal,estado:c.estado}:null},
  ponerClave(gx,ph,sal){this.cliInit();this.sql.exec('UPDATE cli SET ph=?,sal=? WHERE gx=?',ph,sal,gx);return true},
  fallo(clave,sumar){this.cliInit();const ahora=Date.now(),f=this.sql.exec('SELECT * FROM fallos WHERE clave=?',clave).toArray()[0];
    const n=f&&ahora-f.ts<15*60e3?f.n:0;if(sumar)this.sql.exec('INSERT OR REPLACE INTO fallos VALUES(?,?,?)',clave,n+1,f&&ahora-f.ts<15*60e3?f.ts:ahora);return n+(sumar?1:0)},
  sesCrear(gx,tok){this.cliInit();this.sql.exec('INSERT INTO ses VALUES(?,?,?)',tok,gx,Date.now()+180*864e5);if(Math.random()<0.05)this.sql.exec('DELETE FROM ses WHERE exp<?',Date.now());return true},
  sesGX(tok){this.cliInit();const s=this.sql.exec('SELECT gx,exp FROM ses WHERE tok=?',tok).toArray()[0];return s&&s.exp>Date.now()?s.gx:null},
  sesBorrar(tok){this.cliInit();this.sql.exec('DELETE FROM ses WHERE tok=?',tok);return true},
  miCuenta(gx){const f=this.cliFicha(gx);if(!f)return null;const c=f.cliente;
    return {gx:c.gx,nombre:c.nombre,registro:c.registro,plataforma:c.plataforma,resumen:f.resumen,reglas:GXR,
      historial:f.movs.map(m=>({fecha:m.fecha,tipo:m.tipo,descr:m.descr,importe:m.importe,cumple:!!m.cumple,ganados:m.ganados,usados:m.usados}))}},
};
Object.assign(Stats.prototype,CLI);

// --- contraseñas (PBKDF2) y rutas públicas /cuenta/* ---
const hex=b=>[...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,'0')).join('');
const azar=n=>hex(crypto.getRandomValues(new Uint8Array(n)));
async function hashClave(pass,sal){const k=await crypto.subtle.importKey('raw',new TextEncoder().encode(pass),'PBKDF2',false,['deriveBits']);
  return hex(await crypto.subtle.deriveBits({name:'PBKDF2',hash:'SHA-256',salt:new TextEncoder().encode(sal),iterations:20000},k,256))}
const claveOK=p=>typeof p==='string'&&p.length>=6&&p.length<=64;
async function cuenta(req,env,u){
  const D=statsDO(env),ruta=u.pathname.slice(8);
  if(ruta==='yo'||ruta==='salir'){
    const tok=(req.headers.get('Authorization')||'').replace(/^Bearer\s+/i,'').slice(0,80);
    const gx=tok&&await D.sesGX(tok);if(!gx)return r({error:'Tu sesión terminó. Entra de nuevo.'},401);
    if(ruta==='salir'){await D.sesBorrar(tok);return r({ok:true})}
    const c=await D.miCuenta(gx);return c?r(c):r({error:'Cuenta no encontrada'},404);
  }
  if(ruta==='solicitud'&&req.method==='GET'){return r(await D.solEstado(u.searchParams.get('id'),String(u.searchParams.get('k')||'')))}
  if(req.method!=='POST')return r({error:'Usa POST'},405);
  const q=await req.json().catch(()=>({}));
  if(ruta==='solicitar'){
    const d={nombre:String(q.nombre||'').trim().slice(0,40),apellidos:String(q.apellidos||'').trim().slice(0,60),nac:esFecha(q.nac)?q.nac:'',tel:String(q.tel||'').replace(/\D/g,'').slice(-8),plataforma:String(q.plataforma||'').slice(0,30)};
    if(!d.nombre||!d.apellidos)return r({error:'Pon tu nombre y apellidos'},400);
    if(!d.nac)return r({error:'Pon tu fecha de nacimiento'},400);
    if(d.tel.length!==8)return r({error:'El teléfono debe tener 8 dígitos'},400);
    if(!claveOK(q.pass))return r({error:'La contraseña debe tener al menos 6 caracteres'},400);
    d.sal=azar(16);d.ph=await hashClave(q.pass,d.sal);d.k=azar(12);
    const res=await D.solCrear(d);return res.error?r(res,400):r({id:res.id,k:d.k});
  }
  if(ruta==='activar'||ruta==='entrar'){
    const gx=limpiaGX(q.gx);if(!gx)return r({error:'Escribe tu ID GX (ej. GX0012)'},400);
    const ip=req.headers.get('CF-Connecting-IP')||'';
    if(await D.fallo('g:'+gx,false)>=8||await D.fallo('i:'+ip,false)>=20)return r({error:'Demasiados intentos. Espera 15 minutos o escríbenos por WhatsApp.'},429);
    const c=await D.cred(gx),mal=async m=>{await D.fallo('g:'+gx,true);await D.fallo('i:'+ip,true);return r({error:m},400)};
    if(!c||c.estado!=='activo')return mal('Ese ID GX no está registrado. Revisa el número o escríbenos.');
    if(ruta==='activar'){
      if(c.ph)return r({error:'Esa cuenta ya está activada. Usa "Entrar" con tu contraseña.'},400);
      const nacOK=c.nac?q.nac===c.nac:true,telOK=c.tel?String(q.tel4||'').replace(/\D/g,'')===c.tel.slice(-4):true;
      if(!c.nac&&!c.tel)return r({error:'Te falta un dato en nuestro registro. Escríbenos por WhatsApp para activarla.'},400);
      if(!nacOK||!telOK)return mal('Los datos no coinciden con nuestro registro. Revisa la fecha de nacimiento y los 4 últimos dígitos de tu teléfono.');
      if(!claveOK(q.pass))return r({error:'La contraseña debe tener al menos 6 caracteres'},400);
      const sal=azar(16);await D.ponerClave(gx,await hashClave(q.pass,sal),sal);
    }else{
      if(!c.ph)return r({error:'Tu cuenta todavía no está activada. Toca "Ya soy cliente" para crear tu contraseña.'},400);
      if(!igual(await hashClave(String(q.pass||''),c.sal),c.ph))return mal('Contraseña incorrecta.');
    }
    const tok=azar(24);await D.sesCrear(gx,tok);return r({token:tok,gx});
  }
  return r({error:'No existe'},404);
}
async function panelClientes(p,req,env,q){
  const D=statsDO(env);
  if(p==='cli-lista')return j(await D.cliLista());
  if(p==='cli-ficha'){const f=await D.cliFicha(limpiaGX(q.gx));return f?j(f):j({error:'No existe'},404)}
  if(p==='cli-guardar')return jx(await D.cliGuardar(q));
  if(p==='cli-mov')return jx(await D.cliMov(q));
  if(p==='cli-mov-borrar')return jx(await D.cliMovBorrar(q.id));
  if(p==='cli-borrar')return jx(await D.cliBorrar(limpiaGX(q.gx)));
  if(p==='cli-clave')return jx(await D.cliClaveReset(limpiaGX(q.gx)));
  if(p==='cli-solicitudes')return j(await D.solLista());
  if(p==='cli-solicitud')return jx(await D.solResolver(q.id,q.accion,q.gx,q.nota));
  if(p==='cli-sol-borrar')return jx(await D.solBorrar(q.id));
  if(p==='cli-importar')return jx(await D.cliImportar(q));
  if(p==='cli-exportar')return j(await D.cliExportar());
  return null;
}
const jx=o=>j(o,o&&o.error?400:200);
