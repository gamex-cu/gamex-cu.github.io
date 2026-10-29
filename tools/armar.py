"""Arma el catálogo GameX: index.html (web), app/catalogo.html (app) y tools/salida/catalogo-claude.html (copia en Claude).
Uso: python3 tools/armar.py   (desde cualquier carpeta). Sube en 1 la versión del catálogo en app/version.json."""
import json,os
T=os.path.dirname(os.path.abspath(__file__))+'/'
R=os.path.dirname(T.rstrip('/'))+'/'
D=T+'datos/'
os.makedirs(T+'salida',exist_ok=True)
VJ=R+'app/version.json';VV=json.load(open(VJ));VER=VV['catalogo']+1;VV['catalogo']=VER;json.dump(VV,open(VJ,'w'),ensure_ascii=False,indent=2)
head=open(T+'plantilla/cabecera.html').read(); js=open(T+'plantilla/script.html').read()
# ---- datos de la tienda (los cambia el panel: tools/datos/tienda.json) ----
import html as _h, re as _re
try: TI=json.load(open(D+'tienda.json'))
except FileNotFoundError: TI={}
try: CE=json.load(open(D+'catalogos_extra.json'))
except FileNotFoundError: CE=[]
def _slug(t): return _re.sub(r'[^a-z0-9]+','-',__import__('unicodedata').normalize('NFKD',t).encode('ascii','ignore').decode().lower()).strip('-')
def _luz(h):
    h=h.lstrip('#');r,g,b=(int(h[i:i+2],16) for i in (0,2,4));return '#%02x%02x%02x'%tuple(int(x+(255-x)*.55) for x in (r,g,b))
CE_JS=[[c['n'],'x-'+_slug(c['n']),c.get('color','#3d7bff'),c.get('texto','#fff'),_luz(c.get('color','#3d7bff'))] for c in CE if c.get('n')]
def _md(t):
    out=[];lis=[]
    def inl(x): return _re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',_h.escape(x))
    for ln in (t or '').split('\n'):
        ln=ln.strip()
        if ln.startswith('- '): lis.append('<li>'+inl(ln[2:])+'</li>');continue
        if lis: out.append('<ul>'+''.join(lis)+'</ul>');lis=[]
        if not ln: continue
        if ln.startswith('## '): out.append('<p class="cu-rt">'+inl(ln[3:])+'</p>')
        elif ln.startswith('# '): out.append('<h4>'+inl(ln[2:])+'</h4>')
        elif ln.startswith('!! '): out.append('<p class="cu-rf">'+inl(ln[3:])+'</p>')
        else: out.append('<p>'+inl(ln)+'</p>')
    if lis: out.append('<ul>'+''.join(lis)+'</ul>')
    return ''.join(out)
def _rgba(h,a):
    h=h.lstrip('#');return 'rgba(%d,%d,%d,%s)'%(int(h[0:2],16),int(h[2:4],16),int(h[4:6],16),a)
def _tienda(head,js):
    nums=[n for n in TI.get('numeros') or [] if _re.sub(r'\D','',n)]
    if not nums: return head,js
    w=lambda n:'53'+_re.sub(r'\D','',n)[-8:]
    D_N=['domingo','lunes','martes','miércoles','jueves','viernes','sábado']
    def h12(t):
        hh,mm=map(int,t.split(':'));s='a. m.' if hh<12 else 'p. m.';return f'{(hh%12) or 12}:{mm:02d} {s}'
    dias=sorted(set(TI.get('dias',[1,2,3,4,5,6])));abre,cierra=TI.get('abre','10:00'),TI.get('cierra','18:00')
    def rangos(ds):
        ds=[d if d else 7 for d in ds];ds.sort();out=[];i=0
        while i<len(ds):
            j=i
            while j+1<len(ds) and ds[j+1]==ds[j]+1: j+=1
            a,b=D_N[ds[i]%7],D_N[ds[j]%7];out.append(a.capitalize() if i==j else (f'{a.capitalize()} y {b}' if j==i+1 else f'{a.capitalize()} a {b}'));i=j+1
        return out
    hrs=''.join(f'<p class="hrs"><span>{_h.escape(r)}</span><b>{h12(abre)} – {h12(cierra)}</b></p>' for r in rangos(dias))
    cer=[d for d in range(7) if d not in dias]
    hrs+=''.join(f'<p class="hrs"><span>{_h.escape(r)}</span><b>Cerrado</b></p>' for r in rangos(cer))
    dirc=_h.escape(TI.get('direccion',''));mapa=_h.escape(TI.get('mapa',''))
    R1=lambda f:''.join(f(n) for n in nums)
    rep=[(r'<div class="wa">.*?</div>','<div class="wa">'+R1(lambda n:f'<a href="https://wa.me/{w(n)}" target="_blank" rel="noopener">{_h.escape(n)} <small>WhatsApp</small></a>')+'</div>'),
         (r'<h4>Horario</h4>.*?<p class="open" id="open-now"></p>','<h4>Horario</h4>'+hrs+'<p class="open" id="open-now"></p>'),
         (r'<p class="addr"><span class="addr-t">Dirección</span>.*?</p>','<p class="addr"><span class="addr-t">Dirección</span>'+(f'<a href="{mapa}" target="_blank" rel="noopener">{dirc}</a>' if mapa else dirc)+'</p>'),
         (r'<p class="nums">.*?</p>','<p class="nums">'+R1(lambda n:f'<a href="https://wa.me/{w(n)}" target="_blank" rel="noopener">{_h.escape(n)}</a>')+'</p>'),
         (r'<div class="wpl">.*?</div>','<div class="wpl">'+R1(lambda n:f'<a class="btn wa2" data-n="{w(n)}" target="_blank" rel="noopener" href="#">{_h.escape(n)}</a>')+'</div>'),
         (r'<div class="row choose">.*?</div>','<div class="row choose">'+''.join(f'<button class="btn" type="button" data-n="{w(n)}" aria-pressed="{"true" if i==0 else "false"}">{_h.escape(n)}</button>' for i,n in enumerate(nums))+'</div>'),
         (r'<p class="lede">.*?</p>','<p class="lede">'+_h.escape(TI.get('inicio',''))+'</p>')]
    for pat,new in rep:
        head,k=_re.subn(pat,lambda m:new,head,count=1,flags=_re.S)
        if not k: print('aviso: no encontré',pat[:30])
    _botoff=set((TI.get('ocultar') or {}).get('secciones',[]))
    BOT=[b for b in (TI.get('botones') or []) if _re.fullmatch(r'[a-z0-9-]{1,30}',b.get('id','')) and _re.fullmatch(r'#[0-9a-fA-F]{6}',b.get('color','')) and not b.get('oculto')]
    _ids={b['id'] for b in BOT}
    def _padre(b): p=b.get('padre') or '';return p if p in _ids and p!=b['id'] else ''
    def _wa(b): return _h.escape(b.get('wa') or ('Hola GameX, quiero información sobre: '+b.get('titulo','')))
    def _tile(b):
        bid=b['id'];col=b['color'];tit=_h.escape(b.get('titulo',''));sub=_h.escape(b.get('sub',''));ico=_h.escape(b.get('icono','') or '⭐')
        st=f'style="background:linear-gradient(135deg,{_rgba(col,.22)},{_rgba(col,.06)})"';tipo=b.get('tipo','pagina')
        if tipo=='seccion' and _re.fullmatch(r'[a-z0-9=-]{1,60}',str(b.get('destino',''))): at=f'href="#{b["destino"]}" class="sbtn"'
        elif tipo=='enlace' and str(b.get('enlace','')).startswith('https://'): at=f'href="{_h.escape(b["enlace"])}" target="_blank" rel="noopener" class="sbtn"'
        elif tipo=='whatsapp': at=f'href="#" class="sbtn wa-pick" data-t="{_wa(b)}"'
        else: at=f'href="#p-{bid}" class="sbtn"'
        return f'\n  <a {at} id="b-x-{bid}" {st}>\n    <span class="sbi" aria-hidden="true" style="background:{col};font-size:1.7rem">{ico}</span>\n    <span class="sbt"><b>{tit}</b><small>{sub}</small></span>\n    <span class="sgo" aria-hidden="true">→</span>\n  </a>'
    tiles=''.join(_tile(b) for b in BOT if not _padre(b) and 'x-'+b['id'] not in _botoff)
    pags=''
    for b in BOT:
        if b.get('tipo','pagina') not in ('pagina',''): continue
        hijos=''.join(_tile(x) for x in BOT if _padre(x)==b['id'])
        cuerpo=_md(b.get('texto',''))+(f'<a class="op wa-pick" href="#" data-t="{_wa(b)}">Escribir por WhatsApp</a>' if b.get('conwa') else '')
        vuelta='#p-'+_padre(b) if _padre(b) else '#'
        pags+=(f'<div id="pg-{b["id"]}" class="pgx" hidden>\n<div class="bar"><div class="wrap"><div class="vtitle"><a class="back" href="{vuelta}">← Volver</a><span class="vtx"><span class="vn" style="--ct:var(--fg)">{_h.escape(b.get("titulo",""))}</span><span class="vc">{_h.escape(b.get("sub",""))}</span></span></div></div></div>\n<div class="wrap">'
               +(f'<article class="scard cu-rw" style="margin-top:16px;border-color:var(--line)">{cuerpo}</article>' if cuerpo else '')
               +hijos+('' if cuerpo or hijos else '<p class="empty">Pronto habrá contenido aquí.</p>')+'</div>\n</div>\n')
    if tiles:
        head,k=_re.subn(r'(<a class="sbtn sb-gx" href="#cuenta" id="b-cuenta">.*?</a>)',lambda m:m.group(1)+tiles,head,count=1,flags=_re.S)
        if not k: print('aviso: no encontré dónde poner los botones')
    if pags: head=head.replace('<div id="serv" hidden>',pags+'<div id="serv" hidden>',1)
    _mt=TI.get('mantenimiento') or {}
    if _mt.get('activo'):
        _wa=''.join(f'<a class="mtw" href="https://wa.me/{w(n)}" target="_blank" rel="noopener">{_h.escape(n)}</a>' for n in nums)
        _msg=_h.escape(_mt.get('mensaje') or 'Estamos haciendo unos arreglos para mejorar la tienda. Vuelve en un rato.').replace('\n','<br>')
        _mh=open(T+'plantilla/mantenimiento.html').read().replace('__MSG__',_msg).replace('__WA__',_wa)
        head=head.replace('<div class="cartbar" id="cartbar">',_mh+'<div class="cartbar" id="cartbar">',1)
    js=js.replace("  const h=location.hash.slice(1);\n","  const h=location.hash.slice(1);\n  document.querySelectorAll('.pgx').forEach(p=>p.hidden=true);{const pg=h.startsWith('p-')&&document.getElementById('pg-'+h.slice(2));if(pg){current=null;['view','home','cats','ofer','iphone','serv','cuenta'].forEach(x=>$(x).hidden=true);pg.hidden=false;window.scrollTo(0,0);sync();return}}\n",1)
    a1,c1=[int(x.split(':')[0])+int(x.split(':')[1])/60 for x in (abre,cierra)]
    WD=['Sun','Mon','Tue','Wed','Thu','Fri','Sat']
    js=js.replace("const on=p.weekday!=='Sun'&&h>=10&&h<18;",f"const on={json.dumps([WD[d] for d in dias])}.includes(p.weekday)&&h+(+p.minute||0)/60>={a1}&&h+(+p.minute||0)/60<{c1};")
    js=js.replace("{timeZone:'America/Havana',weekday:'short',hour:'numeric',hour12:false}","{timeZone:'America/Havana',weekday:'short',hour:'numeric',minute:'numeric',hour12:false}")
    js=js.replace("let dest='5353441089';",f"let dest='{w(nums[0])}';")
    _oc=TI.get('ocultar') or {}
    _sec=[x for x in _oc.get('secciones',[]) if x in ('catalogos','ofertas','servicios','cuenta')]  # los botones propios ocultos ni se ponen
    if CE_JS:
        js=js.replace("const CI=Object.fromEntries(CONS","CONS.splice(CONS.length-1,0,..."+json.dumps(CE_JS,ensure_ascii=False)+");"+''.join("CAND.add("+json.dumps(c['n'],ensure_ascii=False)+");" for c in CE if c.get('desbloqueo'))+"\nconst CI=Object.fromEntries(CONS",1)
    _or=TI.get('orden') or {}
    if _or.get('catalogos'):
        js=js.replace("const CI=Object.fromEntries(CONS","{const _O="+json.dumps(_or['catalogos'],ensure_ascii=False)+",_i=n=>{const k=_O.indexOf(n);return k<0?999:k};const _b=CONS.map((c,i)=>[c,i]);_b.sort((x,y)=>_i(x[0][0])-_i(y[0][0])||x[1]-y[1]);CONS.splice(0,CONS.length,..._b.map(x=>x[0]))}\nconst CI=Object.fromEntries(CONS",1)
    if _or.get('secciones'):
        js=js.replace("function route(){","{const _t="+json.dumps([x for x in _or['secciones'] if x in ('catalogos','ofertas','servicios','cuenta') or _re.fullmatch(r'x-[a-z0-9-]{1,30}',x)])+".map(s=>document.getElementById('b-'+s)).filter(Boolean),_f=document.querySelector('.sbtn');if(_f&&_t.length){const m=document.createComment('');_f.before(m);_t.forEach(t=>m.before(t));m.remove()}}\nfunction route(){",1)
    _cat=[x for x in _oc.get('catalogos',[])]
    if _cat: js=js.replace("const CI=Object.fromEntries(CONS","CONS.splice(0,CONS.length,...CONS.filter(c=>!"+json.dumps(_cat,ensure_ascii=False)+".includes(c[0])));\nconst CI=Object.fromEntries(CONS",1)
    js=js.replace("function route(){","const SECOFF="+json.dumps(_sec)+";\nfunction gxOff(h){return SECOFF.some(s=>s==='ofertas'?(h==='ofertas'||h.startsWith('oferta=')):s==='servicios'?(h==='servicios'||h.startsWith('sv-')):s==='cuenta'?h==='cuenta':(h==='catalogos'||!!BYSLUG[h]))}\nSECOFF.forEach(s=>{const b=document.getElementById('b-'+s);if(b)b.style.setProperty('display','none','important')});\nfunction route(){\n  if(gxOff(location.hash.slice(1))&&location.hash)history.replaceState(null,'',location.pathname+location.search);",1)
    if TI.get('reglas'):
        out=[];lis=[]
        def inl(t): return _re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',_h.escape(t))
        for ln in TI['reglas'].split('\n'):
            ln=ln.strip()
            if ln.startswith('- '): lis.append('<li>'+inl(ln[2:])+'</li>');continue
            if lis: out.append('<ul>'+''.join(lis)+'</ul>');lis=[]
            if not ln: continue
            if ln.startswith('## '): out.append('<p class="cu-rt">'+inl(ln[3:])+'</p>')
            elif ln.startswith('# '): out.append('<h4>'+inl(ln[2:])+'</h4>')
            elif ln.startswith('!! '): out.append('<p class="cu-rf">'+inl(ln[3:])+'</p>')
            else: out.append('<p>'+inl(ln)+'</p>')
        if lis: out.append('<ul>'+''.join(lis)+'</ul>')
        body=''.join(out).replace('`','&#96;').replace('${','$&#123;')
        js,k=_re.subn(r"\$\('cu-reglas'\)\.innerHTML=`<div class=\"cu-rw\">.*?</div>`;",lambda m:"$('cu-reglas').innerHTML=`<div class=\"cu-rw\">"+body+"</div>`;",js,count=1,flags=_re.S)
        if not k: print('aviso: no encontré las reglas')
    return head,js
head,js=_tienda(head,js)
VV['mantenimiento']=bool((TI.get('mantenimiento') or {}).get('activo'));json.dump(VV,open(VJ,'w'),ensure_ascii=False,indent=2)
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
try: EXC=json.load(open(D+'exclusivos.json'))
except Exception: EXC={}
try: XP=json.load(open(D+'etiquetas_xbox_pago.json'))
except FileNotFoundError: XP={}
series+=['Xbox pago|'+n for n in XP.get('series',[])]
online+=['Xbox pago|'+n for n in XP.get('online',[])]
for _x in CE_JS: data.setdefault(_x[0],[])
# ---- juegos agregados, quitados o editados a mano desde el panel (tools/datos/panel_juegos.json) ----
try: PJ=json.load(open(D+'panel_juegos.json'))
except FileNotFoundError: PJ={}
for _x in ('agregar','quitar','editar'): PJ.setdefault(_x,[])
_PORTS={'Switch':SWE,'PC':PCE,'Meta Quest':MQE}
def _pj_et(_c,_n,_et):  # pone exactamente estas etiquetas al juego
    global online,series
    _k=_c+'|'+_n
    online=[x for x in online if x!=_k];series=[x for x in series if x!=_k]
    for _l in ('vr','vr_opcional'): ET[_l]=[x for x in ET[_l] if x!=_k]
    for _d,_l in [(_PORTS.get(_c,{}),'port'),(SWE if _c=='Switch' else {},'emulador')]:
        if _l in _d: _d[_l]=[x for x in _d[_l] if x!=_n]
    if _c in EXC: EXC[_c]=[x for x in EXC[_c] if x!=_n]
    if 'online' in _et: online.append(_k)
    if 'series' in _et: series.append(_k)
    if 'vr' in _et: ET['vr'].append(_k)
    if 'vro' in _et: ET['vr_opcional'].append(_k)
    if 'port' in _et and _c in _PORTS: _PORTS[_c].setdefault('port',[]).append(_n)
    if 'emu' in _et and _c=='Switch': SWE.setdefault('emulador',[]).append(_n)
    if 'excl' in _et: EXC.setdefault(_c,[]).append(_n)
for _q in PJ['quitar']:
    if _q.get('c') in data: data[_q['c']]=[n for n in data[_q['c']] if n!=_q.get('n')]
for _a in PJ['agregar']:
    _c,_n=_a.get('c'),(_a.get('n') or '').strip()
    if _c not in data or not _n: continue
    if _n.lower() not in {x.lower() for x in data[_c]}: data[_c].append(_n)
    _pj_et(_c,_n,set(_a.get('et') or []))
RENOMBRA={}
for _e in PJ['editar']:
    _c,_n=_e.get('c'),_e.get('n')
    if _c not in data or _n not in data[_c]: continue
    _nn=(_e.get('nuevo') or _n).strip()
    if _nn!=_n:
        data[_c]=[_nn if x==_n else x for x in data[_c]];RENOMBRA[_c+'|'+_n]=_c+'|'+_nn
        _o,_k=_c+'|'+_n,_c+'|'+_nn
        online=[_k if x==_o else x for x in online];series=[_k if x==_o else x for x in series]
        for _l in ('vr','vr_opcional'): ET[_l]=[_k if x==_o else x for x in ET[_l]]
        for _d in [_PORTS.get(_c,{}),SWE if _c=='Switch' else {}]+([{'x':EXC[_c]}] if _c in EXC else []):
            for _l in list(_d): _d[_l]=[_nn if x==_n else x for x in _d[_l]] if isinstance(_d[_l],list) else _d[_l]
        if _c in EXC: EXC[_c]=[_nn if x==_n else x for x in EXC[_c]]
        if _c=='Xbox Game Pass':
            for _l in ('x360','xog','saliendo'):
                if _l in GP: GP[_l]=[_nn if x==_n else x for x in GP[_l]]
        if _c=='Xbox pago':
            for _l in ('x360','xog'):
                if _l in XP: XP[_l]=[_nn if x==_n else x for x in XP[_l]]
    if 'et' in _e: _pj_et(_c,_nn,set(_e['et'] or []))
# ---- catálogos ocultos desde el panel (tienda.json → ocultar.catalogos) ----
OCULTOS_DATA={}
for _c in (TI.get('ocultar') or {}).get('catalogos',[]):
    if _c in data: OCULTOS_DATA[_c]=data.pop(_c)
CARD='''<a class="dlapp" id="dlapp" href="https://gamex-avisos.gamex-cu.workers.dev/descargar" rel="noopener"><span class="dli">⬇</span><span class="dlt"><b>Descarga la app para Android</b><small id="dlv">Última versión · funciona sin internet</small></span></a>
<details class="dlayuda"><summary>¿Te sale un aviso de Google al instalar?</summary><p>Es normal en las apps que no vienen de la Play Store. Toca <b>Más detalles</b> y luego <b>Instalar de todas formas</b>. Si te pregunta si quieres enviarla para que la analicen, puedes poner <b>Enviar</b>.</p></details>
'''
DCSS='''.dlayuda{max-width:560px;margin:6px 0 0;font-size:.82rem;color:var(--muted)}
.dlayuda summary{cursor:pointer;padding:4px 2px;list-style:none;text-decoration:underline;text-underline-offset:3px;width:max-content;max-width:100%}
.dlayuda summary::-webkit-details-marker{display:none}
.dlayuda p{margin:6px 2px 0;line-height:1.45}
.dlayuda b{color:var(--fg)}
.dlapp{display:flex;align-items:center;gap:14px;margin-top:12px;padding:14px;border-radius:10px;border:1px solid var(--accent);background:rgba(61,123,255,.12);color:var(--fg);text-decoration:none;max-width:560px}
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
for _o,_k in RENOMBRA.items():
    if _o in LINKS: LINKS[_k]=LINKS.pop(_o)
for _a in PJ['agregar']+[dict(_e,n=(_e.get('nuevo') or _e['n'])) for _e in PJ['editar'] if _e.get('link')]:  # enlaces de los juegos del panel
    _l=(_a.get('link') or '').strip()
    if not _l or _a.get('c') not in data: continue
    if not _l.startswith('http'):
        if _a['c'] in ('PS4','PS5') and '-' in _l and '_' in _l: _l='https://store.playstation.com/es-mx/product/'+_l
        elif _a['c'] not in ('Xbox pago','Xbox Game Pass'): continue
    LINKS[_a['c']+'|'+_a['n'].strip()]=_l
import subprocess as _sp
def _fecha(*fs):
    r=''
    for f in fs:
        try: o=_sp.run(['git','log','-1','--date=format-local:%Y-%m-%d','--format=%ad','--',f],cwd=R,capture_output=True,text=True,env=dict(os.environ,TZ='America/Havana')).stdout.strip()
        except Exception: o=''
        try:  # cambios todavía sin subir: cuentan como de hoy
            if _sp.run(['git','status','--porcelain','--',f],cwd=R,capture_output=True,text=True).stdout.strip():
                import datetime as _d0
                try:
                    from zoneinfo import ZoneInfo as _Z0; o=_d0.datetime.now(_Z0('America/Havana')).date().isoformat()
                except Exception: o=_d0.date.today().isoformat()
        except Exception: pass
        r=max(r,o)
    return r
for _c,_b in [('PS4','ps4'),('PS5','ps5'),('PC','pc'),('Meta Quest','meta_quest'),('Switch','switch')]:
    if _c in NOTES or _c not in data: continue
    _f=_fecha(*['tools/datos/'+x+_b+'.json' for x in ('','enlaces_','etiquetas_')])
    _f=max([_f]+[x.get('f','') for x in PJ.get('agregar',[])+PJ.get('quitar',[]) if x.get('c')==_c])
    if _f:
        _y,_m,_d=_f.split('-');NOTES[_c]=f'Catálogo actualizado el <b>{int(_d)} de {MESES[int(_m)-1]} de {_y}</b>'
try: SERV=json.load(open(D+'servicios.json'))
except FileNotFoundError: SERV=[]
_SO=set((TI.get('ocultar') or {}).get('servicios',[]))
SERV=[dict(x,items=[it for it in x.get('items',[]) if not it.get('oculto')]) for x in SERV if x.get('s') not in _SO]
SERV=[x for x in SERV if x['items']]
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
_todas={c+'|'+n for c,l in list(data.items())+list(OCULTOS_DATA.items()) for n in l}
if AGR is None: AGR={k:'2000-01-01' for k in _todas}   # primera vez: nada es nuevo
for _o,_k in RENOMBRA.items():
    if _o in AGR and _k not in AGR: AGR[_k]=AGR[_o]
for k in _todas: AGR.setdefault(k,HOY.isoformat())
AGR={k:v for k,v in sorted(AGR.items()) if k in _todas}
json.dump(AGR,open(_AF,'w'),ensure_ascii=False,indent=0)
NUEVO={k:v for k,v in AGR.items() if (HOY-_dt.date.fromisoformat(v)).days<7}
page=head+js.replace('__DATA__',json.dumps(data,ensure_ascii=False).replace('</','<\\/')).replace('__EXCL__',json.dumps([c+'|'+n for c,l in EXC.items() for n in l],ensure_ascii=False).replace('</','<\\/')).replace('__PORT__',json.dumps(['Switch|'+n for n in SWE.get('port',[])]+['Meta Quest|'+n for n in MQE.get('port',[])]+['PC|'+n for n in PCE.get('port',[])],ensure_ascii=False)).replace('__EMU__',json.dumps(['Switch|'+n for n in SWE.get('emulador',[])],ensure_ascii=False)).replace('__VR__',json.dumps(ET['vr'],ensure_ascii=False)).replace('__VRO__',json.dumps(ET['vr_opcional'],ensure_ascii=False)).replace('__X360__',json.dumps(['Xbox Game Pass|'+n for n in GP['x360']]+['Xbox pago|'+n for n in XP.get('x360',[])],ensure_ascii=False)).replace('__XOG__',json.dumps(['Xbox Game Pass|'+n for n in GP['xog']]+['Xbox pago|'+n for n in XP.get('xog',[])],ensure_ascii=False)).replace('__SALIENDO__',json.dumps(['Xbox Game Pass|'+n for n in GP.get('saliendo',[])],ensure_ascii=False).replace('</','<\\/')).replace('__NUEVO__',json.dumps(NUEVO,ensure_ascii=False).replace('</','<\\/')).replace('__ONLINE__',json.dumps(online,ensure_ascii=False)).replace('__SERIES__',json.dumps(series,ensure_ascii=False).replace('</','<\\/'))
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
try{const h=location.hash;if(h==='#no-contar'||h==='#contar'){h==='#no-contar'?localStorage.setItem('gx-nocontar','1'):localStorage.removeItem('gx-nocontar');
  try{const yo=localStorage.getItem('gx-uid');if(yo)fetch(URL_EV+'/no-contar',{method:'POST',body:JSON.stringify({u:yo,si:h==='#no-contar'}),headers:{'Content-Type':'text/plain'},keepalive:true}).catch(()=>{})}catch(e){}
  const d=document.createElement('div');d.textContent=h==='#no-contar'?'✓ Este equipo ya no cuenta en las estadísticas':'✓ Este equipo vuelve a contar en las estadísticas';
  d.style.cssText='position:fixed;left:50%%;top:16px;transform:translateX(-50%%);background:#1fa855;color:#fff;padding:12px 18px;border-radius:12px;font:600 15px system-ui;z-index:9999';
  document.body.appendChild(d);setTimeout(()=>d.remove(),5000);history.replaceState(null,'',location.pathname)}
  if(localStorage.getItem('gx-nocontar')==='1')return}catch(e){}
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
(function(){try{const m=(navigator.userAgent.match(/Android[^;)]*;\\s*([^;)]+?)(?:\\s+Build\\/|\\))/)||[])[1];
  const fin=x=>{x=(x||'').trim();if(x&&x!=='K'&&!/^wv$/i.test(x))ev('equipo',x.slice(0,60))};
  if(navigator.userAgentData&&navigator.userAgentData.getHighEntropyValues)navigator.userAgentData.getHighEntropyValues(['model']).then(h=>fin(h.model||m)).catch(()=>fin(m));
  else if(/iphone/i.test(navigator.userAgent))fin('iPhone');else if(/ipad/i.test(navigator.userAgent))fin('iPad');else fin(m)}catch(e){}})();
let t0=document.visibilityState==='visible'?Date.now():0;
function tiempo(){if(t0){const sg=Math.round((Date.now()-t0)/1000);t0=0;if(sg>=3)ev('tiempo','',Math.min(sg,10800))}}
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='hidden'){tiempo();enviar(true)}else t0=Date.now()});
addEventListener('pagehide',()=>{tiempo();enviar(true)});
setInterval(()=>{if(t0&&Date.now()-t0>120000){tiempo();t0=Date.now();enviar()}},30000);
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
open(R+'app/catalogo.html','w').write(alone.replace('<title>','<meta name="robots" content="noindex">\n<title>',1))
pwa='''<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="icon-180.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="GameX">
<meta name="theme-color" content="#0d1124">
<meta name="description" content="Tienda de Videojuegos GameX. Escoge tus juegos y pídelos por WhatsApp.">
'''
import sys as _sys; _sys.path.insert(0, T); import seo as _seo
if TI.get('numeros'):
    _seo.LD['telephone']=['+53'+_re.sub(r'\D','',n)[-8:] for n in TI['numeros']]
    _seo.LD['address']['streetAddress']=TI.get('direccion','').replace(', La Habana','')
    _seo.LD['openingHoursSpecification'][0].update(dayOfWeek=[['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'][d] for d in sorted(TI.get('dias',[]))],opens=TI.get('abre','10:00'),closes=TI.get('cierra','18:00'))
    if TI.get('mapa'): _seo.LD['hasMap']=TI['mapa']
_gv = ''
try: _gv = open(D+'google_verificacion.txt').read().strip()
except FileNotFoundError: pass
w=alone.replace('<title>',pwa+_seo.etiquetas(_gv)+'<title>',1)
w=w.replace('<meta name="description" content="Tienda de Videojuegos GameX. Escoge tus juegos y pídelos por WhatsApp.">','<meta name="description" content="'+_seo.DESC+'">',1).replace("ORIGEN='app'","ORIGEN='web'",1)
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
w=w.replace('<div id="home">','<div class="upd" id="upd" hidden><span>Hay una versión nueva de GameX.</span><button type="button" id="upd-b">Actualizar</button></div>\n<div class="aviso" id="aviso" hidden role="status"><div><b id="aviso-t"></b><span id="aviso-x"></span></div><button type="button" id="aviso-c" aria-label="Cerrar aviso">×</button></div>\n<div id="home">',1)
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
function gxCheck(){fetch('app/version.json?t='+Date.now(),{cache:'no-store'}).then(r=>r.json()).then(j=>{if(j.catalogo>GXV){let byp=false,n=0;try{byp=localStorage.getItem('gx-ver-igual')==='1';n=+(sessionStorage.getItem('gx-mrf')||0)}catch(e){}
  if(!byp&&!!j.mantenimiento!==document.body.classList.contains('mant-on')&&n<2){try{sessionStorage.setItem('gx-mrf',n+1)}catch(e){}gxRefresh()}else document.getElementById('upd').hidden=false}}).catch(()=>{})}
fetch('app/version.json?t='+Date.now(),{cache:'no-store'}).then(r=>r.json()).then(j=>{if(j.apkNombre)document.getElementById('dlv').textContent='Versión '+j.apkNombre+' · funciona sin internet'}).catch(()=>{});
gxCheck();document.addEventListener('visibilitychange',()=>{if(!document.hidden)gxCheck()});
(function(){const K='gamex-avisos-cerrados';let c=[];try{c=JSON.parse(localStorage.getItem(K)||'[]')}catch(e){}
 const hoy=new Date().toISOString().slice(0,10),lim=new Date(Date.now()-14*864e5).toISOString().slice(0,10);
 fetch('app/avisos.json?t='+Date.now(),{cache:'no-store'}).then(r=>r.json()).then(j=>{
  const a=(j.avisos||[]).filter(x=>x.id&&!x.silenciosa&&!c.includes(x.id)&&(x.vence?x.vence>=hoy:(x.fecha||'')>=lim)).pop();if(!a||(typeof SECOFF!=='undefined'&&SECOFF.includes('ofertas')))return;
  const el=document.getElementById('aviso');document.getElementById('aviso-t').textContent=a.titulo||'';document.getElementById('aviso-x').textContent='Toca para ver la oferta completa';el.hidden=false;
  const cerrar=()=>{el.hidden=true;c.push(a.id);try{localStorage.setItem(K,JSON.stringify(c.slice(-50)))}catch(e){}};
  document.getElementById('aviso-c').onclick=ev=>{ev.stopPropagation();cerrar()};
  el.onclick=()=>{window.gxAbrir=a.id;if(location.hash==='#ofertas')cargarOfertas();else location.hash='ofertas'};
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
import consola; consola.generar(R+'index.html', VER)  # catálogo para las apps de consola
print('ok',{k:len(v) for k,v in data.items()})
