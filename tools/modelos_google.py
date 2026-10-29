"""Baja la lista oficial de teléfonos Android de Google (supported_devices.csv) y la guarda repartida en
tools/datos/modelos/<2 letras>.json  →  {"CÓDIGO DE MODELO": "Marca Nombre comercial"}.
El Worker la usa para ponerle nombre a los modelos que no conoce (pestaña Números del panel).
La corre la acción de GitHub "Modelos de teléfono" una vez por semana."""
import csv, io, json, os, re, urllib.request

T = os.path.dirname(os.path.abspath(__file__)) + '/'
OUT = T + 'datos/modelos/'
URL = 'https://storage.googleapis.com/play_public/supported_devices.csv'


def clave(m):
    return re.sub(r'\s+', ' ', m.strip().upper())


def pref(k):
    a = re.sub(r'[^A-Z0-9]', '', k)[:2]
    return a if len(a) == 2 else '__'


def main():
    raw = urllib.request.urlopen(URL, timeout=120).read()
    txt = raw.decode('utf-16') if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else raw.decode('utf-8-sig')
    filas = csv.reader(io.StringIO(txt))
    cab = [c.strip().lower() for c in next(filas)]
    iB, iN, iM = cab.index('retail branding'), cab.index('marketing name'), cab.index('model')
    mapa = {}
    for f in filas:
        if len(f) <= max(iB, iN, iM): continue
        marca, nom, mod = f[iB].strip(), f[iN].strip(), f[iM].strip()
        if not mod or not nom: continue
        n = nom if nom.lower().startswith(marca.lower()) or not marca else f'{marca} {nom}'
        mapa.setdefault(clave(mod), n)
    os.makedirs(OUT, exist_ok=True)
    partes = {}
    for k, v in mapa.items(): partes.setdefault(pref(k), {})[k] = v
    cambios = 0
    for p, d in partes.items():
        ruta = OUT + p + '.json'; nuevo = json.dumps(dict(sorted(d.items())), ensure_ascii=False, separators=(',', ':'))
        if not os.path.exists(ruta) or open(ruta).read() != nuevo:
            open(ruta, 'w').write(nuevo); cambios += 1
    print(len(mapa), 'modelos en', len(partes), 'archivos;', cambios, 'cambiados')


if __name__ == '__main__':
    main()
