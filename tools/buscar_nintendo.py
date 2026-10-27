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
    return ' '.join(ROM.get(t, t) for t in re.findall(r'[a-z0-9]+', s))
def numeros(s): return {t for t in norm(s).split() if t.isdigit()}
def main():
    juegos = json.load(open(T + 'datos/switch.json'))
    et = json.load(open(T + 'datos/etiquetas_switch.json'))
    excl = set(et.get('port', [])) | set(et.get('emulador', []))
    cat = catalogo()
    for x in cat: x['nn'], x['nums'] = norm(x['title']), numeros(x['title'])
    por = {}
    for x in cat: por.setdefault(x['nn'], x)
    ok, dudas, no = {}, [], []
    for n in juegos:
        if n in excl: continue
        nn = norm(n)
        if nn in por: ok[n] = 'https://www.nintendo.com' + por[nn]['url']; continue
        nums = numeros(n); mejor, mr = None, 0
        primera = nn.split()[0] if nn else ''
        for x in cat:
            if x['nums'] != nums or not x['nn'].startswith(primera[:3]): continue
            r = difflib.SequenceMatcher(None, nn, x['nn']).ratio()
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
if __name__ == '__main__': main()
