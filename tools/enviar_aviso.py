"""Manda un aviso u oferta a la app GameX por los dos caminos:
  1) lo agrega a app/avisos.json (la app lo encuentra al abrirse o cada ~3 horas, sin depender de Google)
  2) lo envía al instante por Firebase al tema "ofertas" (llega a los teléfonos con servicios de Google)
La app muestra cada aviso una sola vez aunque llegue por los dos caminos.

Uso:  python3 tools/enviar_aviso.py "Título" "Texto del aviso" [--url https://...] [--vence 2026-11-30] [--sin-firebase]
La clave de Firebase NO va en este repo: se lee de la variable GAMEX_FIREBASE_KEY o de ~/secretos/firebase-admin.json
Después hay que subir app/avisos.json a GitHub (git add/commit/push).
Firebase necesita acceso a oauth2.googleapis.com y fcm.googleapis.com.
"""
import json, os, sys, time, datetime, base64, ssl, urllib.request, argparse
T = os.path.dirname(os.path.abspath(__file__)) + '/'
R = os.path.dirname(T.rstrip('/')) + '/'

def opener():
    hs = []
    pr = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    if pr: hs.append(urllib.request.ProxyHandler({'https': pr}))
    ca = '/root/.ccr/ca-bundle.crt'
    hs.append(urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=ca) if os.path.exists(ca) else ssl.create_default_context()))
    return urllib.request.build_opener(*hs)

def token_google(key):
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b'=')
    now = int(time.time())
    head = b64(json.dumps({'alg': 'RS256', 'typ': 'JWT'}).encode())
    body = b64(json.dumps({'iss': key['client_email'], 'scope': 'https://www.googleapis.com/auth/firebase.messaging',
                           'aud': key['token_uri'], 'iat': now, 'exp': now + 3600}).encode())
    pk = serialization.load_pem_private_key(key['private_key'].encode(), password=None)
    sig = b64(pk.sign(head + b'.' + body, padding.PKCS1v15(), hashes.SHA256()))
    jwt = (head + b'.' + body + b'.' + sig).decode()
    data = urllib.parse.urlencode({'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer', 'assertion': jwt}).encode()
    return json.load(opener().open(urllib.request.Request(key['token_uri'], data=data), timeout=30))['access_token']

def enviar_firebase(aviso):
    ruta = os.environ.get('GAMEX_FIREBASE_KEY') or os.path.expanduser('~/secretos/firebase-admin.json')
    if not os.path.exists(ruta): ruta = '/home/claude/secretos/firebase-admin.json'
    key = json.load(open(ruta))
    tok = token_google(key)
    msg = {'message': {'topic': 'ofertas', 'data': {k: str(v) for k, v in aviso.items() if k in ('id', 'titulo', 'texto', 'url')},
                       'android': {'priority': 'high', 'ttl': '604800s'}}}
    req = urllib.request.Request(f"https://fcm.googleapis.com/v1/projects/{key['project_id']}/messages:send",
                                 data=json.dumps(msg).encode(), headers={'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json'})
    return json.load(opener().open(req, timeout=30))

def enviar_web(aviso):
    """Manda el aviso a los iPhone/navegadores suscritos (lista guardada en el Worker de Cloudflare)."""
    import webpush
    cfg = json.load(open(T + 'datos/push.json'))
    clave = json.load(open(os.path.dirname(webpush.ruta_claves()) + '/cloudflare.json'))['clave_worker']
    op = opener(); h = {'X-Clave': clave, 'User-Agent': 'GameX-avisos/1.0'}
    subs = json.load(op.open(urllib.request.Request(cfg['url'] + '/lista', headers=h), timeout=30))
    ok = borradas = 0
    datos = {k: v for k, v in aviso.items() if k in ('id', 'titulo', 'texto', 'url')}
    for s in subs:
        c = webpush.enviar(s, datos, op)
        if c in (200, 201, 202): ok += 1
        elif c in (404, 410):
            op.open(urllib.request.Request(cfg['url'] + '/borrar', data=json.dumps({'endpoint': s['endpoint']}).encode(), headers={**h, 'Content-Type': 'application/json'}), timeout=30); borradas += 1
    return f'{ok} de {len(subs)} enviados' + (f', {borradas} viejos borrados' if borradas else '')

if __name__ == '__main__':
    import urllib.parse
    ap = argparse.ArgumentParser()
    ap.add_argument('titulo'); ap.add_argument('texto')
    ap.add_argument('--url', default=''); ap.add_argument('--vence', default='')
    ap.add_argument('--sin-firebase', action='store_true')
    a = ap.parse_args()
    hoy = datetime.date.today().isoformat()
    aviso = {'id': f"{hoy}-{int(time.time())}", 'fecha': hoy, 'titulo': a.titulo, 'texto': a.texto}
    if a.url: aviso['url'] = a.url
    if a.vence: aviso['vence'] = a.vence
    f = R + 'app/avisos.json'
    d = json.load(open(f)) if os.path.exists(f) else {'avisos': []}
    d['avisos'] = [x for x in d['avisos'] if not x.get('vence') or x['vence'] >= hoy][-19:] + [aviso]
    json.dump(d, open(f, 'w'), ensure_ascii=False, indent=1)
    print('Agregado a app/avisos.json:', aviso['id'])
    if not a.sin_firebase:
        try: print('Firebase:', enviar_firebase(aviso))
        except Exception as e: print('Firebase NO enviado:', e)
    try:
        if json.load(open(T + 'datos/push.json')).get('url'): print('iPhone/web:', enviar_web(aviso))
    except Exception as e: print('iPhone/web NO enviado:', e)
