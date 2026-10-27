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
for extra in ['PS5','PC','Meta Quest','Switch']:
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
GP=json.load(open(D+'gamepass.json'));gp=GP['games']
online=['Xbox Game Pass|'+n for n in GP['online']]
data['Xbox Game Pass']=[n for n,_ in gp]
series=['Xbox Game Pass|'+n for n,s in gp if s]
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
LINKS={'Xbox Game Pass|'+n:i for n,i in GP.get('ids',{}).items()}
for _c in ['PS4','PS5']:
    try:
        for n,pid in json.load(open(D+'enlaces_'+_c.lower()+'.json')).items(): LINKS[_c+'|'+n]='https://store.playstation.com/es-mx/product/'+pid
    except FileNotFoundError: pass
try:
    for n,u in json.load(open(D+'enlaces_switch.json')).items(): LINKS['Switch|'+n]=u
except FileNotFoundError: pass
js=js.replace('__LINKS__',json.dumps(LINKS,ensure_ascii=False)).replace('__NOTES__',json.dumps(NOTES,ensure_ascii=False))
page=head+js.replace('__DATA__',json.dumps(data,ensure_ascii=False).replace('</','<\\/')).replace('__PORT__',json.dumps(['Switch|'+n for n in SWE.get('port',[])],ensure_ascii=False)).replace('__EMU__',json.dumps(['Switch|'+n for n in SWE.get('emulador',[])],ensure_ascii=False)).replace('__VR__',json.dumps(ET['vr'],ensure_ascii=False)).replace('__VRO__',json.dumps(ET['vr_opcional'],ensure_ascii=False)).replace('__X360__',json.dumps(['Xbox Game Pass|'+n for n in GP['x360']],ensure_ascii=False)).replace('__XOG__',json.dumps(['Xbox Game Pass|'+n for n in GP['xog']],ensure_ascii=False)).replace('__ONLINE__',json.dumps(online,ensure_ascii=False)).replace('__SERIES__',json.dumps(series,ensure_ascii=False).replace('</','<\\/'))
art=page.replace('mark{',DCSS+'mark{',1)
k_=art.index('<a class="chan"');k2=art.index('</a>',k_)+4
art=art[:k2]+'\n'+CARD+art[k2:]
open(T+'salida/catalogo-claude.html','w').write(art)
H='<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
i=page.index('<div id="home">')
alone=H+'<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}</style>\n'+page[:i]+'</head>\n<body>\n'+page[i:]+'\n</body>\n</html>\n'
open(R+'app/catalogo.html','w').write(alone)
pwa='''<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="icon-180.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="GameX">
<meta name="theme-color" content="#0d1124">
<meta name="description" content="Catálogo de Juegos GameX. Escoge tus juegos y pídelos por WhatsApp.">
'''
w=alone.replace('<title>',pwa+'<title>',1)
css='''.ios-tip{position:fixed;left:max(12px,env(safe-area-inset-left,0px));right:max(12px,env(safe-area-inset-right,0px));bottom:calc(84px + env(safe-area-inset-bottom,0px));z-index:15;background:var(--panel);border:1px solid var(--hot);border-radius:12px;padding:14px 44px 14px 14px;color:var(--fg);font-size:.95rem;line-height:1.45;max-width:520px;margin:0 auto}
.ios-tip b{color:var(--hot)}
.ios-tip button{position:absolute;top:6px;right:8px;background:none;border:0;color:var(--muted);font-size:1.5rem;cursor:pointer;padding:4px}
.ios-tip svg{vertical-align:-3px}
.upd{position:sticky;top:env(safe-area-inset-top,0px);z-index:12;background:var(--accent);color:#fff;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px max(16px,env(safe-area-inset-right,0px)) 10px max(16px,env(safe-area-inset-left,0px));font-weight:600}
.upd button,.refresh{font:600 .95rem var(--display);border-radius:8px;cursor:pointer;padding:8px 14px}
.upd button{background:#fff;color:#0d1124;border:0}
.refresh{margin-top:14px;background:var(--panel);color:var(--fg);border:1px solid var(--line)}
.refresh:hover{border-color:var(--hot)}
'''
w=w.replace('mark{',css+DCSS+'mark{',1)
k_=w.index('<a class="chan"');k2=w.index('</a>',k_)+4
w=w[:k2]+'\n'+CARD+w[k2:]
tip='''<div class="ios-tip" id="ios-tip" hidden role="note"><button type="button" id="ios-x" aria-label="Cerrar">×</button><b>Instala GameX en tu iPhone:</b> toca <svg width="16" height="18" viewBox="0 0 16 18" fill="none" stroke="currentColor" stroke-width="1.6" aria-label="Compartir"><path d="M8 11V1M4.5 4.5 8 1l3.5 3.5"/><path d="M5 7H2.5v9.5h11V7H11"/></svg> <b>Compartir</b> abajo y luego <b>Agregar a inicio</b>. Funciona sin internet.</div>
'''
w=w.replace('<div class="cartbar"',tip+'<div class="cartbar"',1)
w=w.replace('<div id="home">','<div class="upd" id="upd" hidden><span>Hay una versión nueva del catálogo.</span><button type="button" id="upd-b">Actualizar</button></div>\n<div id="home">',1)
w=w.replace('© GameX · Catálogo de Juegos GameX</div>','© GameX · Catálogo de Juegos GameX<br><button type="button" class="refresh" id="refresh">Actualizar catálogo</button> <span id="verlbl" style="margin-left:8px"></span></div>',1)
pj='''
if('serviceWorker' in navigator){navigator.serviceWorker.register('sw.js',{updateViaCache:'none'}).catch(()=>{})}
(function(){try{const ios=/iphone|ipad|ipod/i.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);const standalone=navigator.standalone||matchMedia('(display-mode: standalone)').matches;let seen=false;try{seen=localStorage.getItem('gamex-ios-tip')==='1'}catch(e){}
if(ios&&!standalone&&!seen){const t=document.getElementById('ios-tip');t.hidden=false;document.getElementById('ios-x').onclick=()=>{t.hidden=true;try{localStorage.setItem('gamex-ios-tip','1')}catch(e){}}}}catch(e){}})();
'''
pj+='''
const GXV=__VER__;
document.getElementById('verlbl').textContent='Versión '+GXV;
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
'''.replace('__VER__',str(VER))
k=w.rindex('</script>'); w=w[:k]+pj+w[k:]
open(R+'index.html','w').write(w)
print('ok',{k:len(v) for k,v in data.items()})
