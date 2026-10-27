"""Actualiza la lista de Xbox Game Pass (consola) desde el catálogo oficial de Microsoft.

Uso:  python3 tools/actualizar_gamepass.py            -> actualiza tools/datos/gamepass.json y escribe el reporte
      python3 tools/actualizar_gamepass.py --probar    -> solo muestra qué cambiaría, no guarda nada

Necesita acceso a catalog.gamepass.com y displaycatalog.mp.microsoft.com.
Las correcciones hechas a mano viven en tools/datos/reglas_gamepass.json:
  nombres   clave -> nombre corregido (se respeta siempre)
  quitar    claves que no se muestran (p. ej. ediciones repetidas)
  online    nombres marcados "Solo online"
  xog       nombres de Xbox clásico (los demás retrocompatibles son Xbox 360)
  revisados claves de juegos nuevos ya revisados por el dueño
Después de actualizar hay que correr tools/armar.py para regenerar la web y la app.
"""
import json, os, re, ssl, sys, unicodedata, urllib.request, datetime

T = os.path.dirname(os.path.abspath(__file__)) + '/'
DATOS = T + 'datos/'
LISTAS = {'consola': 'f6f1f99f-9b49-4ccd-b3bf-4d9767a77f5e', 'ea_consola': 'b8900d09-a491-44cc-916e-32b5acae621b'}

def abrir():
    hs = []
    proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    if proxy: hs.append(urllib.request.ProxyHandler({'https': proxy}))
    ca = '/root/.ccr/ca-bundle.crt'
    hs.append(urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=ca) if os.path.exists(ca) else ssl.create_default_context()))
    return urllib.request.build_opener(*hs)

OP = abrir()
def get_json(u):
    with OP.open(u, timeout=40) as r: return json.load(r)

PLAT = [r'\s*[-–:]?\s*Cross-Gen (Bundle|Edition)$', r'\s*[-–]?\s*Xbox Series X\|S( Edition)?$', r'\s*[-–]?\s*Xbox One( Edition| Version)?$',
        r'\s*[-–]?\s*for Xbox One$', r'\s*[-–]?\s*Xbox Series X$', r'\s+Console Edition$', r'\s*[-–]?\s*Standard( Edition)?$',
        r'\s*\(Xbox[^)]*\)$', r'\s*[-–]\s*Standalone$', r'\s+for( Xbox)?$', r'\s*[-–]\s*Digital$']
def limpiar(t):
    t = t.replace('™', '').replace('®', '').replace('©', '').replace('’', "'")
    t = re.sub(r'\s+', ' ', t).strip()
    for _ in range(3):
        for p in PLAT: t = re.sub(p, '', t, flags=re.I).strip(' -–')
    return t
ED = r"\b(game of the year|goty|definitive|ultimate|premium|gold|deluxe|complete|enhanced|anniversary|remastered|maximum|director'?s cut|edition|the|ea play)\b"
def clave(n): return re.sub(r'[^a-z0-9]', '', re.sub(ED, '', unicodedata.normalize('NFKD', n).lower()))
ROMANOS = re.compile(r'^(?=[IVXLC]+$)M{0,3}(C[MD]|D?C{0,3})(X[CL]|L?X{0,3})(I[XV]|V?I{0,3})$', re.I)
def nombre_por_defecto(n):
    if n.isupper() and len(n) > 5 and not re.search(r'\d', n):
        n = ' '.join(w.upper() if ROMANOS.match(w.strip(':,')) else w.capitalize() for w in n.split(' '))
        n = n.replace("'S ", "'s ")
    return n

def bajar():
    ids = []
    for lid in LISTAS.values():
        ids += [x['id'] for x in get_json(f'https://catalog.gamepass.com/sigls/v2?id={lid}&language=en-us&market=US') if 'id' in x]
    ids = sorted(set(ids)); prods = {}
    for i in range(0, len(ids), 20):
        d = get_json('https://displaycatalog.mp.microsoft.com/v7.0/products?bigIds=' + ','.join(ids[i:i + 20]) + '&market=US&languages=en-us')
        for p in d.get('Products', []):
            pr = p.get('Properties', {})
            prods[p['ProductId']] = {'t': p['LocalizedProperties'][0]['ProductTitle'], 'gen': pr.get('XboxConsoleGenCompatible') or [],
                                     'attr': [a.get('Name') for a in (pr.get('Attributes') or [])], 'pfn': pr.get('PackageFamilyName') or ''}
    return prods

def agrupar(prods):
    g = {}
    for v in prods.values():
        n = limpiar(v['t']); k = clave(n)
        e = g.setdefault(k, {'n': n, 'one': False, 'attr': set(), 'bc': False})
        if len(n) < len(e['n']): e['n'] = n
        if 'ConsoleGen8' in v['gen']: e['one'] = True
        e['attr'] |= set(v['attr'])
        if 'Xbox360BackwardCompat' in v['pfn']: e['bc'] = True
    return g

ONLINE = {'XblOnlineMultiPlayer', 'XblOnlineCoop', 'XblCrossPlatformMultiPlayer', 'XblCrossPlatformCoop'}
LOCAL = {'XblLocalMultiPlayer', 'XblLocalCoop', 'SharedSplitScreen'}
def parece_online(e): return bool(e['attr'] & ONLINE) and 'SinglePlayer' not in e['attr'] and not (e['attr'] & LOCAL)

def main():
    probar = '--probar' in sys.argv
    reglas = json.load(open(DATOS + 'reglas_gamepass.json'))
    antes = json.load(open(DATOS + 'gamepass.json'))
    g = agrupar(bajar())
    nombres, quitar, online, xog = reglas['nombres'], set(reglas['quitar']), set(reglas['online']), set(reglas['xog'])
    revisados = set(reglas.get('revisados', []))
    juegos, x360, nuevos, revisar = [], [], [], []
    for k, e in g.items():
        if k in quitar: continue
        if k not in nombres:
            nombres[k] = nombre_por_defecto(e['n']); nuevos.append(nombres[k])
            if k not in revisados and parece_online(e): revisar.append(nombres[k])
        n = nombres[k]
        juegos.append([n, not e['one']])
        if e['bc'] and n not in xog: x360.append(n)
    sk = lambda s: re.sub(r'^(the|a) ', '', s.lower())
    juegos.sort(key=lambda x: sk(x[0]))
    actuales = {n for n, _ in juegos}; previos = {n for n, _ in antes['games']}
    salieron = sorted(previos - actuales, key=sk); entraron = sorted(actuales - previos, key=sk)
    nuevo = {'fecha': datetime.date.today().isoformat(), 'games': juegos, 'online': sorted(n for n in online if n in actuales),
             'x360': sorted(x360), 'xog': sorted(n for n in xog if n in actuales)}
    hoy = datetime.date.today().isoformat()
    lin = [f'# Game Pass – revisión del {hoy}', '', f'Total: {len(juegos)} juegos (antes {len(previos)}).', '']
    lin += [f'## Entraron ({len(entraron)})'] + [f'- {n}' for n in entraron] + ['']
    lin += [f'## Salieron ({len(salieron)})'] + [f'- {n}' for n in salieron] + ['']
    lin += [f'## Por revisar si son solo online ({len(revisar)})'] + [f'- {n}' for n in sorted(revisar, key=sk)] + ['']
    rep = '\n'.join(lin)
    print(rep)
    if probar: return
    json.dump(nuevo, open(DATOS + 'gamepass.json', 'w'), ensure_ascii=False)
    reglas['nombres'] = dict(sorted(nombres.items()))
    reglas['pendientes'] = sorted(set(reglas.get('pendientes', [])) | set(revisar), key=sk)
    json.dump(reglas, open(DATOS + 'reglas_gamepass.json', 'w'), ensure_ascii=False, indent=1)
    os.makedirs(T + 'salida', exist_ok=True)
    open(T + 'salida/reporte_gamepass.md', 'w').write(rep + '\n')
    print('CAMBIOS' if (entraron or salieron) else 'SIN CAMBIOS')

if __name__ == '__main__':
    main()
