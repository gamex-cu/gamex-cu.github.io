"""Compara la lista de Switch con el catálogo oficial de Nintendo (Europa).
Uso: python3 tools/buscar_nintendo.py [--probar]
Guarda tools/datos/enlaces_switch.json {nombre: url} y tools/salida/switch_no_oficiales.txt
Necesita acceso a searching.nintendo-europe.com."""
import json, os, re, ssl, sys, unicodedata, urllib.parse, urllib.request, difflib
T = os.path.dirname(os.path.abspath(__file__)) + '/'
def abrir():
    hs = []
    pr = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    if pr: hs.append(urllib.request.ProxyHandler({'https': pr}))
    ca = '/root/.ccr/ca-bundle.crt'
    hs.append(urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=ca) if os.path.exists(ca) else ssl.create_default_context()))
    return urllib.request.build_opener(*hs)
OP = abrir()
def catalogo():
    out, start = [], 0
    while True:
        q = urllib.parse.urlencode({'q': '*', 'fq': 'type:GAME AND system_type:nintendoswitch*', 'rows': 2000, 'start': start, 'wt': 'json', 'fl': 'title,url,fs_id'})
        d = json.load(OP.open('https://searching.nintendo-europe.com/en/select?' + q, timeout=120))['response']
        out += d['docs']; start += len(d['docs'])
        if not d['docs'] or start >= d['numFound']: return out
ROM = {'ii': '2', 'iii': '3', 'iv': '4', 'vi': '6', 'vii': '7', 'viii': '8', 'ix': '9', 'xi': '11', 'xii': '12', 'xiii': '13', 'xiv': '14', 'xv': '15', 'xvi': '16'}
QUITAR = (r"[™®©]|\bnintendo switch( 2)?( edition)?\b|\bfor\b|\bswitch\b|\b(standard|digital|deluxe|complete|ultimate|definitive|gold|premium|collector'?s?|game of the year|goty|"
          r"director'?s cut|enhanced|bundle|edition|version|the|a|an|of|and|plus)\b")
def norm(s):
    s = re.sub(r'[™®©]', '', s)
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower().replace('&', ' and ').replace('+', ' plus ')
    s = re.sub(QUITAR, ' ', s)
    s = re.sub(r'\b([a-z])\.(?=[a-z]\b)', r'\1', s)
    toks = [ROM.get(t, t) for t in re.findall(r'[a-z0-9]+', s)]
    out = []
    for t in toks:
        if out and len(t) == 1 and len(out[-1]) <= 2 and out[-1].isalpha() and t.isalpha(): out[-1] += t
        else: out.append(t)
    return ' '.join(out)
def numeros(s): return {t for t in norm(s).split() if t.isdigit()}
def main():
    juegos = json.load(open(T + 'datos/switch.json'))
    et = json.load(open(T + 'datos/etiquetas_switch.json'))
    excl = set(et.get('port', [])) | set(et.get('emulador', []))
    cat = catalogo()
    for x in cat:
        x['nn'], x['nums'] = norm(x['title']), numeros(x['title'])
        x['nn2'] = norm(re.sub(r'\(.*?\)|:.*$', '', x['title']))
    por = {}
    for x in cat: por.setdefault(x['nn'], x)
    for x in cat: por.setdefault(x['nn2'], x)
    man = json.load(open(T + 'datos/enlaces_manuales.json')) if os.path.exists(T + 'datos/enlaces_manuales.json') else {}
    ok, dudas, no = {}, [], []
    for n in juegos:
        if n in excl: continue
        if 'Switch|' + n in man:
            if man['Switch|' + n]: ok[n] = man['Switch|' + n]
            else: no.append(n)
            continue
        nn = norm(n)
        if nn in por: ok[n] = 'https://www.nintendo.com' + por[nn]['url']; continue
        nums = numeros(n); mejor, mr = None, 0
        mis = set(nn.split())
        for x in cat:
            if x['nums'] != nums: continue
            r = difflib.SequenceMatcher(None, nn, x['nn']).ratio()
            if r < 0.9 and x.get('nn2') and x['nn2'] == nn: r = 0.99
            sus = set(x['nn'].split())
            if r < 0.9 and mis and len(mis) >= 2 and (mis <= sus or sus <= mis) and min(len(mis), len(sus)) / max(len(mis), len(sus)) >= 0.6: r = max(r, 0.9)
            if r > mr: mejor, mr = x, r
        if mejor and mr >= 0.9: ok[n] = 'https://www.nintendo.com' + mejor['url']
        elif mejor and mr >= 0.72: dudas.append((n, mejor['title'], round(mr, 2)))
        else: no.append(n)
    print('catálogo Nintendo:', len(cat), '| encontrados:', len(ok), '| dudosos:', len(dudas), '| NO están en Nintendo:', len(no))
    if '--probar' in sys.argv: return
    json.dump(dict(sorted(ok.items())), open(T + 'datos/enlaces_switch.json', 'w'), ensure_ascii=False, indent=0)
    os.makedirs(T + 'salida', exist_ok=True)
    with open(T + 'salida/switch_no_oficiales.txt', 'w') as f:
        f.write(f'== NO ESTÁN EN EL CATÁLOGO DE NINTENDO ({len(no)}) – posibles ports, o con nombre distinto ==\n'); f.writelines(n + '\n' for n in no)
        f.write(f'\n== PARECIDOS ({len(dudas)}): tu lista  ->  lo más parecido en Nintendo ==\n'); f.writelines(f'{n}  ->  {t}  ({r})\n' for n, t, r in dudas)
if __name__ == '__main__' and '--solo-eeuu' not in sys.argv:
    main()
    if '--probar' not in sys.argv: segunda_pasada()

# --- Segunda pasada: tienda de Nintendo de Estados Unidos (para los que no están en Europa) ---
ALG = 'https://u3b6gr4ua3-dsn.algolia.net/1/indexes/store_game_en_us/query'
ALG_H = {'X-Algolia-Application-Id': 'U3B6GR4UA3', 'X-Algolia-API-Key': 'a29c6927638bfd8cee23993e51e721c9', 'Content-Type': 'application/json'}
def buscar_us(nombre, indice='store_game_en_us'):
    q = re.sub(r"[:–\-!?,.'’()]", ' ', nombre); q = ' '.join(q.split())[:80]
    body = json.dumps({'query': q, 'hitsPerPage': 15}).encode()
    try: hits = json.load(OP.open(urllib.request.Request(ALG.replace('store_game_en_us', indice), data=body, headers=ALG_H), timeout=40)).get('hits', [])
    except Exception: return None, 0, ''
    nn, nums, mis = norm(nombre), numeros(nombre), set(norm(nombre).split())
    mejor, mr, tit = None, 0, ''
    for h in hits:
        pl = ' '.join([h.get('platform') or ''] + (h.get('corePlatforms') or []))
        if 'Switch' not in pl or not h.get('url'): continue
        t = h.get('title', ''); tn = norm(t)
        if numeros(t) != nums: continue
        r = 1.0 if tn == nn or norm(re.sub(r'\(.*?\)|:.*$', '', t)) == nn else difflib.SequenceMatcher(None, nn, tn).ratio()
        sus = set(tn.split())
        if r < 0.9 and len(mis) >= 2 and (mis <= sus or sus <= mis) and min(len(mis), len(sus)) / max(len(mis), len(sus)) >= 0.6: r = 0.9
        u = ('https://www.nintendo.com/us/store/products/' + h['slug'] + '/') if h.get('slug') and indice != 'store_game_en_us' else 'https://www.nintendo.com' + h['url']
        if r > mr: mejor, mr, tit = u, r, t
    return mejor, mr, tit

def segunda_pasada():
    from concurrent.futures import ThreadPoolExecutor
    ruta = T + 'datos/enlaces_switch.json'; ok = json.load(open(ruta))
    juegos = json.load(open(T + 'datos/switch.json'))
    et = json.load(open(T + 'datos/etiquetas_switch.json')); excl = set(et.get('port', [])) | set(et.get('emulador', []))
    man = json.load(open(T + 'datos/enlaces_manuales.json')) if os.path.exists(T + 'datos/enlaces_manuales.json') else {}
    faltan = [n for n in juegos if n not in ok and n not in excl and ('Switch|' + n) not in man]
    def ambos(n):
        a = buscar_us(n)
        if a[1] >= 0.9: return a
        b = buscar_us(n, 'ncom_game_en_us')
        return b if b[1] > a[1] else a
    with ThreadPoolExecutor(8) as ex: res = list(ex.map(lambda n: (n, ambos(n)), faltan))
    nuevos, dudas, no = {}, [], []
    for n, (u, r, t) in res:
        if u and r >= 0.9: nuevos[n] = (u, t)
        elif u and r >= 0.72: dudas.append((n, t, round(r, 2)))
        else: no.append(n)
    if '--probar' in sys.argv:
        for n, (u, t) in sorted(nuevos.items()): print(f'{n}  ->  {t}')
        print('nuevos', len(nuevos), 'dudosos', len(dudas), 'no', len(no)); return
    ok.update({n: u for n, (u, t) in nuevos.items()})
    json.dump(dict(sorted(ok.items())), open(ruta, 'w'), ensure_ascii=False, indent=0)
    with open(T + 'salida/switch_no_oficiales.txt', 'w') as f:
        f.write(f'== NO ESTÁN NI EN LA TIENDA DE EUROPA NI EN LA DE EE. UU. ({len(no)}) ==\n'); f.writelines(n + '\n' for n in no)
        f.write(f'\n== PARECIDOS EN LA TIENDA DE EE. UU. ({len(dudas)}): tu lista  ->  lo más parecido ==\n'); f.writelines(f'{n}  ->  {t}  ({r})\n' for n, t, r in dudas)
    print('EE. UU.: nuevos', len(nuevos), '| dudosos', len(dudas), '| sin encontrar', len(no))

if __name__ == '__main__' and '--solo-eeuu' in sys.argv:
    segunda_pasada()
