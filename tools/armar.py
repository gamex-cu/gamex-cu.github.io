"""Arma el catálogo GameX: index.html (web), app/catalogo.html (app) y tools/salida/catalogo-claude.html (copia en Claude).
Uso: python3 tools/armar.py   (desde cualquier carpeta). Sube en 1 la versión del catálogo en app/version.json."""
import json,os
T=os.path.dirname(os.path.abspath(__file__))+'/'
R=os.path.dirname(T.rstrip('/'))+'/'
D=T+'datos/'
os.makedirs(T+'salida',exist_ok=True)
VJ=R+'app/version.json';VV=json.load(open(VJ));VER=VV['catalogo']+1;VV['catalogo']=VER;json.dump(VV,open(VJ,'w'),ensure_ascii=False,indent=2)
head=open(T+'plantilla/cabecera.html').read(); js=open(T+'plantilla/script.html').read()
data={'PS4':json.load(open(D+'ps4.json'))}
for extra in ['PS5','PC','Meta Quest','Switch','Xbox pago']:
    try: data[extra]=json.load(open(D+extra.lower().replace(' ','_')+'.json'))
    except FileNotFoundError: pass
ET={'vr':[],'vr_opcional':[]}
for _c,_f in [('PS4','etiquetas_ps4.json'),('PS5','etiquetas_ps5.json')]:
    try:
        _e=json.load(open(D+_f))
        ET['vr']+=[_c+'|'+n for n in _e['vr']];ET['vr_opcional']+=[_c+'|'+n for n in _e['vr_opcional']]
    except FileNotFoundError: pass
try: SWE=json.load(open(D+'etiquetas_switch.json'))
except FileNotFoundError: SWE={}
try: PCE=json.load(open(D+'etiquetas_pc.json'))
except FileNotFoundError: PCE={}
try: MQE=json.load(open(D+'etiquetas_meta_quest.json'))
except FileNotFoundError: MQE={}
GP=json.load(open(D+'gamepass.json'));gp=GP['games']
online=['Xbox Game Pass|'+n for n in GP['online']]
data['Xbox Game Pass']=[n for n,_ in gp]
series=['Xbox Game Pass|'+n for n,s in gp if s]
try: PSP=json.load(open(D+'ps_plus.json'))
except FileNotFoundError: PSP={'mes':'','juegos':[]}
data['PlayStation Plus']=[g['n'] for g in PSP['juegos']]
online+=['PlayStation Plus|'+g['n'] for g in PSP['juegos'] if g.get('online')]
try: XP=json.load(open(D+'etiquetas_xbox_pago.json'))
except FileNotFoundError: XP={}
series+=['Xbox pago|'+n for n in XP.get('series',[])]
online+=['Xbox pago|'+n for n in XP.get('online',[])]
CARD='''<a class="dlapp" id="dlapp" href="https://gamex-cu.github.io/app/GAMEX-Catalogo.apk" rel="noopener"><span class="dli">⬇</span><span class="dlt"><b>Descarga la app para Android</b><small id="dlv">Última versión · funciona sin internet</small></span></a>
'''
DCSS='''.dlapp{display:flex;align-items:center;gap:14px;margin-top:12px;padding:14px;border-radius:10px;border:1px solid var(--accent);background:rgba(61,123,255,.12);color:var(--fg);text-decoration:none;max-width:560px}
.dlapp:hover,.dlapp:focus-visible{background:rgba(61,123,255,.22);outline:none}
.dli{flex:none;width:38px;height:38px;border-radius:8px;background:var(--accent);color:#fff;display:grid;place-items:center;font-size:1.2rem}
.dlt{display:flex;flex-direction:column;gap:2px;min-width:0}
.dlt b{font-family:var(--display);font-size:1.05rem}
.dlt small{color:var(--muted);font-size:.85rem}
'''
MESES=['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
NOTES={}
if GP.get('fecha'):
    _y,_m,_d=GP['fecha'].split('-');NOTES['Xbox Game Pass']=f'Lista tomada del <b>catálogo oficial de Xbox Game Pass</b> · actualizada el {int(_d)} de {MESES[int(_m)-1]} de {_y}'
NOTES['Xbox pago']='¿No ves el juego que buscas? <b>Pregunta por él</b> por <a href="#" class="wa-pick" data-ask="1" data-t="Hola GameX, ¿tienen este juego para Xbox?">WhatsApp</a> y te lo conseguimos.'
LINKS={'Xbox Game Pass|'+n:i for n,i in GP.get('ids',{}).items()}
LINKS.update({'Xbox pago|'+n:i for n,i in XP.get('ids',{}).items()})
LINKS.update({'PlayStation Plus|'+g['n']:'https://store.playstation.com/es-mx/product/'+g['id'] for g in PSP['juegos'] if g.get('id')})
if PSP.get('hasta'):
    _y,_m,_d=PSP['hasta'].split('-');NOTES['PlayStation Plus']=f'Juegos mensuales de <b>PlayStation Plus Essential</b> · disponibles hasta el {int(_d)} de {MESES[int(_m)-1]}'
for _c in ['PS4','PS5']:
    try:
        for n,pid in json.load(open(D+'enlaces_'+_c.lower()+'.json')).items(): LINKS[_c+'|'+n]='https://store.playstation.com/es-mx/product/'+pid
    except FileNotFoundError: pass
try:
    for n,u in json.load(open(D+'enlaces_switch.json')).items(): LINKS['Switch|'+n]=u
except FileNotFoundError: pass
for _f,_c in [('enlaces_pc.json','PC')]:
    try:
        for n,u in json.load(open(D+_f)).items(): LINKS[_c+'|'+n]=u
    except FileNotFoundError: pass
try:
    for n,u in json.load(open(D+'enlaces_meta_quest.json')).items(): LINKS['Meta Quest|'+n]=u
except FileNotFoundError: pass
import subprocess as _sp
def _fecha(*fs):
    r=''
    for f in fs:
        try: o=_sp.run(['git','log','-1','--date=format-local:%Y-%m-%d','--format=%ad','--',f],cwd=R,capture_output=True,text=True,env=dict(os.environ,TZ='America/Havana')).stdout.strip()
        except Exception: o=''
        r=max(r,o)
    return r
for _c,_b in [('PS4','ps4'),('PS5','ps5'),('PC','pc'),('Meta Quest','meta_quest'),('Switch','switch')]:
    if _c in NOTES or _c not in data: continue
    _f=_fecha(*['tools/datos/'+x+_b+'.json' for x in ('','enlaces_','etiquetas_')])
    if _f:
        _y,_m,_d=_f.split('-');NOTES[_c]=f'Catálogo actualizado el <b>{int(_d)} de {MESES[int(_m)-1]} de {_y}</b>'
try: SERV=json.load(open(D+'servicios.json'))
except FileNotFoundError: SERV=[]
js=js.replace('__SERV__',json.dumps(SERV,ensure_ascii=False).replace('</','<\\/')).replace('__PSPMES__',json.dumps(PSP.get('mes',''),ensure_ascii=False)).replace('__LINKS__',json.dumps(LINKS,ensure_ascii=False)).replace('__NOTES__',json.dumps(NOTES,ensure_ascii=False))
import base64 as _b64
ICONO='data:image/png;base64,'+_b64.b64encode(open(R+'icon-180.png','rb').read()).decode()
head=head.replace('__ICONO__',ICONO)
# ---- etiqueta "Nuevo": fecha en que cada juego apareció por primera vez (dura 7 días) ----
import datetime as _dt
try:
    from zoneinfo import ZoneInfo as _Z; HOY=_dt.datetime.now(_Z('America/Havana')).date()
except Exception: HOY=_dt.date.today()
_AF=D+'agregados.json'
try: AGR=json.load(open(_AF))
except FileNotFoundError: AGR=None
_todas={c+'|'+n for c,l in data.items() for n in l}
if AGR is None: AGR={k:'2000-01-01' for k in _todas}   # primera vez: nada es nuevo
for k in _todas: AGR.setdefault(k,HOY.isoformat())
AGR={k:v for k,v in sorted(AGR.items()) if k in _todas}
json.dump(AGR,open(_AF,'w'),ensure_ascii=False,indent=0)
NUEVO={k:v for k,v in AGR.items() if (HOY-_dt.date.fromisoformat(v)).days<7}
page=head+js.replace('__DATA__',json.dumps(data,ensure_ascii=False).replace('</','<\\/')).replace('__PORT__',json.dumps(['Switch|'+n for n in SWE.get('port',[])]+['Meta Quest|'+n for n in MQE.get('port',[])]+['PC|'+n for n in PCE.get('port',[])],ensure_ascii=False)).replace('__EMU__',json.dumps(['Switch|'+n for n in SWE.get('emulador',[])],ensure_ascii=False)).replace('__VR__',json.dumps(ET['vr'],ensure_ascii=False)).replace('__VRO__',json.dumps(ET['vr_opcional'],ensure_ascii=False)).replace('__X360__',json.dumps(['Xbox Game Pass|'+n for n in GP['x360']]+['Xbox pago|'+n for n in XP.get('x360',[])],ensure_ascii=False)).replace('__XOG__',json.dumps(['Xbox Game Pass|'+n for n in GP['xog']]+['Xbox pago|'+n for n in XP.get('xog',[])],ensure_ascii=False)).replace('__SALIENDO__',json.dumps(['Xbox Game Pass|'+n for n in GP.get('saliendo',[])],ensure_ascii=False).replace('</','<\\/')).replace('__NUEVO__',json.dumps(NUEVO,ensure_ascii=False).replace('</','<\\/')).replace('__ONLINE__',json.dumps(online,ensure_ascii=False)).replace('__SERIES__',json.dumps(series,ensure_ascii=False).replace('</','<\\/'))
art=page.replace('mark{',DCSS+'mark{',1)
k_=art.index('<a class="chan"');k2=art.index('</a>',k_)+4
art=art[:k2]+'\n'+CARD+art[k2:]
open(T+'salida/catalogo-claude.html','w').write(art)
H='<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
i=page.index('<div id="home">')
alone=H+'<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}</style>\n'+page[:i]+'</head>\n<body>\n'+page[i:]+'\n</body>\n</html>\n'

# ---- estadísticas anónimas (visitas, catálogos, búsquedas, pedidos) -> Worker /evento; solo web y app, no la copia de Claude ----
_PU=json.load(open(D+'push.json')).get('url','')
EST=("""<script>(function(){const URL_EV=%s,ORIGEN='app';if(!URL_EV)return;
let uid='';try{uid=localStorage.getItem('gx-uid')||'';if(!uid){uid=Math.random().toString(36).slice(2)+Date.now().toString(36);localStorage.setItem('gx-uid',uid)}}catch(e){uid='s'+Math.random().toString(36).slice(2)}
const ua=navigator.userAgent,ios=/iphone|ipad|ipod/i.test(ua)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1),sa=navigator.standalone||matchMedia('(display-mode: standalone)').matches;
const disp=ORIGEN==='app'&&/android/i.test(ua)?'app':ios?(sa?'iphone-app':'iphone'):/android/i.test(ua)?'android':/windows|macintosh|linux|cros/i.test(ua)?'pc':'otro';
let cola=[],tm=null;
function enviar(final){if(!cola.length)return;const b=JSON.stringify({u:uid,d:disp,o:ORIGEN,e:cola.splice(0,40)});
  try{if(final&&navigator.sendBeacon){navigator.sendBeacon(URL_EV+'/evento',new Blob([b],{type:'text/plain'}));return}
    fetch(URL_EV+'/evento',{method:'POST',body:b,headers:{'Content-Type':'text/plain'},keepalive:true}).catch(()=>{})}catch(e){}}
function ev(t,v,n){cola.push(n==null?{t,v}:{t,v,n});clearTimeout(tm);tm=setTimeout(enviar,2500)}
window.gxEv=ev;
addEventListener('pagehide',()=>enviar(true));document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='hidden')enviar(true)});
ev('visita','');
let ultCat=null;function cat(){try{if(current&&current!==ultCat){ultCat=current;ev('cat',current==='todas'?'Todas':current)}if(!current)ultCat=null}catch(e){}}
addEventListener('hashchange',()=>setTimeout(cat,0));setTimeout(cat,0);
const vistas=new Set();let bt=null;const q=document.getElementById('q');
if(q)q.addEventListener('input',()=>{clearTimeout(bt);bt=setTimeout(()=>{const t=q.value.trim().toLowerCase();if(t.length<3||vistas.has(t))return;vistas.add(t);
  const m=(document.getElementById('count').textContent||'').match(/\\d[\\d.,]*/);ev('busca',t,m?+m[0].replace(/[.,]/g,''):0)},1800)});
const s=document.getElementById('send');if(s)s.addEventListener('click',()=>{try{if(!cart.length)return;ev('envio','',cart.length);cart.forEach(k=>ev('juego',k));enviar()}catch(e){}});
const c=document.getElementById('copy');if(c)c.addEventListener('click',()=>{try{if(!cart.length)return;ev('envio','copiado',cart.length);cart.forEach(k=>ev('juego',k));enviar()}catch(e){}});
document.addEventListener('click',e=>{const a=e.target.closest('#wapick [data-n]');if(a){ev('contacto',a.dataset.n);enviar()}});
})();</script>
""" % json.dumps(_PU))
_k=alone.rindex('</body>');alone=alone[:_k]+EST+alone[_k:]
open(R+'app/catalogo.html','w').write(alone)
pwa='''<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="icon-180.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="GameX">
<meta name="theme-color" content="#0d1124">
<meta name="description" content="Tienda de Videojuegos GameX. Escoge tus juegos y pídelos por WhatsApp.">
'''
w=alone.replace('<title>',pwa+'<title>',1).replace("ORIGEN='app'","ORIGEN='web'",1)
css='''.ios-tip{position:fixed;left:max(12px,env(safe-area-inset-left,0px));right:max(12px,env(safe-area-inset-right,0px));bottom:calc(84px + env(safe-area-inset-bottom,0px));z-index:15;background:var(--panel);border:1px solid var(--hot);border-radius:12px;padding:14px 44px 14px 14px;color:var(--fg);font-size:.95rem;line-height:1.45;max-width:520px;margin:0 auto}
.ios-tip b{color:var(--hot)}
.ios-tip button{position:absolute;top:6px;right:8px;background:none;border:0;color:var(--muted);font-size:1.5rem;cursor:pointer;padding:4px}
.ios-tip svg{vertical-align:-3px}
.tipb{display:inline-block;margin-top:10px;padding:7px 12px;border-radius:8px;background:var(--hot);color:#0d1124;font:600 .9rem var(--display);text-decoration:none}
.upd{position:sticky;top:env(safe-area-inset-top,0px);z-index:12;background:var(--accent);color:#fff;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px max(16px,env(safe-area-inset-right,0px)) 10px max(16px,env(safe-area-inset-left,0px));font-weight:600}
.upd button,.refresh{font:600 .95rem var(--display);border-radius:8px;cursor:pointer;padding:8px 14px}
.upd button{background:#fff;color:#0d1124;border:0}
.refresh{margin-top:14px;background:var(--panel);color:var(--fg);border:1px solid var(--line)}
.refresh:hover{border-color:var(--hot)}
.aviso{position:relative;display:flex;gap:12px;align-items:flex-start;margin:10px auto 0;max-width:640px;width:calc(100% - 32px);background:linear-gradient(135deg,rgba(242,169,0,.18),rgba(61,123,255,.14));border:1px solid var(--hot);border-radius:12px;padding:12px 40px 12px 14px;color:var(--fg);cursor:pointer;box-sizing:border-box}
.aviso b{display:block;font-family:var(--display);font-size:1.05rem;margin-bottom:2px}
.aviso span{font-size:.95rem;line-height:1.4;white-space:pre-line}
.aviso button{position:absolute;top:4px;right:6px;background:none;border:0;color:var(--muted);font-size:1.5rem;cursor:pointer;padding:4px 8px}
.pushb{margin-left:8px}
'''
w=w.replace('mark{',css+DCSS+'mark{',1)
k_=w.index('<a class="chan"');k2=w.index('</a>',k_)+4
w=w[:k2]+'\n'+CARD+w[k2:]
tip='''<div class="ios-tip" id="ios-tip" hidden role="note"><button type="button" id="ios-x" aria-label="Cerrar">×</button><b>Instala GameX en tu iPhone:</b> toca <b>•••</b> abajo, luego <b>Compartir</b> y <b>Agregar a pantalla de inicio</b>. Funciona sin internet.<br><a class="tipb" href="#iphone">📱 Ver la guía paso a paso</a></div>
'''
w=w.replace('<div class="cartbar"',tip+'<div class="cartbar"',1)
w=w.replace('<div id="home">','<div class="upd" id="upd" hidden><span>Hay una versión nueva del catálogo.</span><button type="button" id="upd-b">Actualizar</button></div>\n<div class="aviso" id="aviso" hidden role="status"><div><b id="aviso-t"></b><span id="aviso-x"></span></div><button type="button" id="aviso-c" aria-label="Cerrar aviso">×</button></div>\n<div id="home">',1)
w=w.replace('© GameX · Tienda de Videojuegos</div>','© GameX · Tienda de Videojuegos<br><button type="button" class="refresh" id="refresh">Actualizar catálogo</button><button type="button" class="refresh pushb" id="push-b" hidden>🔔 Activar avisos</button> <a class="refresh iosb" href="#iphone" id="b-iphone" hidden><svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><rect x="6" y="2.5" width="12" height="19" rx="3"/><path d="M10.5 18.5h3"/></svg> Guía para iPhone</a></div>',1)
pj='''
if('serviceWorker' in navigator){navigator.serviceWorker.register('sw.js',{updateViaCache:'none'}).catch(()=>{})}
(function(){try{const ios=/iphone|ipad|ipod/i.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);const standalone=navigator.standalone||matchMedia('(display-mode: standalone)').matches;let seen=false;try{seen=localStorage.getItem('gamex-ios-tip')==='1'}catch(e){}
if(ios&&!standalone&&!seen){const t=document.getElementById('ios-tip');t.hidden=false;document.getElementById('ios-x').onclick=()=>{t.hidden=true;try{localStorage.setItem('gamex-ios-tip','1')}catch(e){}}}}catch(e){}})();
'''
pj+='''
const GXV=__VER__;
async function gxRefresh(){const b=document.getElementById('refresh');
  try{const r=await fetch('./?v='+Date.now(),{cache:'reload'});if(!r.ok)throw 0;
    if(b)b.textContent='Actualizando…';
    try{const rg=await navigator.serviceWorker?.getRegistration();if(rg){await rg.update();rg.active&&rg.active.postMessage('guardar')}}catch(e){}
    setTimeout(()=>location.replace(location.pathname+location.hash),400);
  }catch(e){if(b)b.textContent='Necesitas internet para actualizar';setTimeout(()=>{if(b)b.textContent='Actualizar catálogo'},3000)}}
navigator.serviceWorker?.ready.then(rg=>{rg.active&&rg.active.postMessage('guardar')}).catch(()=>{});
document.getElementById('refresh').onclick=gxRefresh;document.getElementById('upd-b').onclick=gxRefresh;
function gxCheck(){fetch('app/version.json?t='+Date.now(),{cache:'no-store'}).then(r=>r.json()).then(j=>{if(j.catalogo>GXV)document.getElementById('upd').hidden=false}).catch(()=>{})}
fetch('app/version.json?t='+Date.now(),{cache:'no-store'}).then(r=>r.json()).then(j=>{if(j.apkNombre)document.getElementById('dlv').textContent='Versión '+j.apkNombre+' · funciona sin internet'}).catch(()=>{});
gxCheck();document.addEventListener('visibilitychange',()=>{if(!document.hidden)gxCheck()});
(function(){const K='gamex-avisos-cerrados';let c=[];try{c=JSON.parse(localStorage.getItem(K)||'[]')}catch(e){}
 const hoy=new Date().toISOString().slice(0,10),lim=new Date(Date.now()-14*864e5).toISOString().slice(0,10);
 fetch('app/avisos.json?t='+Date.now(),{cache:'no-store'}).then(r=>r.json()).then(j=>{
  const a=(j.avisos||[]).filter(x=>x.id&&!c.includes(x.id)&&(x.vence?x.vence>=hoy:(x.fecha||'')>=lim)).pop();if(!a)return;
  const el=document.getElementById('aviso');document.getElementById('aviso-t').textContent=a.titulo||'';document.getElementById('aviso-x').textContent=a.texto||'';el.hidden=false;
  const cerrar=()=>{el.hidden=true;c.push(a.id);try{localStorage.setItem(K,JSON.stringify(c.slice(-50)))}catch(e){}};
  document.getElementById('aviso-c').onclick=ev=>{ev.stopPropagation();cerrar()};
  el.onclick=()=>{if(a.url)window.open(a.url,'_blank','noopener')};
 }).catch(()=>{})})();
const PUSH=__PUSH__;
(function(){const bs=[...document.querySelectorAll('.pushb')];if(!PUSH.url||!('serviceWorker' in navigator)||!('PushManager' in window)||!('Notification' in window))return;
 const ios=/iphone|ipad|ipod/i.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
 const sa=navigator.standalone||matchMedia('(display-mode: standalone)').matches;if(ios&&!sa)return;
 const k=s=>{s=s.replace(/-/g,'+').replace(/_/g,'/');const r=atob(s+'='.repeat((4-s.length%4)%4));return Uint8Array.from(r,c=>c.charCodeAt(0))};
 navigator.serviceWorker.ready.then(rg=>rg.pushManager.getSubscription().then(sub=>{
  if(sub&&Notification.permission==='granted'){fetch(PUSH.url+'/suscribir',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(sub)}).catch(()=>{});return}
  if(Notification.permission==='denied')return;bs.forEach(b=>{b.hidden=false;
  b.onclick=async()=>{try{const p=await Notification.requestPermission();if(p!=='granted'){b.textContent='Avisos bloqueados';return}
   const s=await rg.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:k(PUSH.vapid)});
   const r=await fetch(PUSH.url+'/suscribir',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(s)});if(!r.ok)throw 0;
   bs.forEach(x=>{x.textContent='✓ Avisos activados';setTimeout(()=>{x.hidden=true},2500)})}catch(e){b.textContent='No se pudo activar, prueba con internet';setTimeout(()=>{b.textContent='🔔 Activar avisos'},3000)}}});
 })).catch(()=>{})})();
'''.replace('__VER__',str(VER)).replace('__PUSH__',json.dumps(json.load(open(D+'push.json'))))
k=w.rindex('</script>'); w=w[:k]+pj+w[k:]
open(R+'index.html','w').write(w)
print('ok',{k:len(v) for k,v in data.items()})
