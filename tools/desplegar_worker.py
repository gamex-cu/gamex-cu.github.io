"""Sube (o actualiza) el Worker de avisos a Cloudflare y guarda su dirección en tools/datos/push.json.
Necesita ~/secretos/cloudflare.json (o /home/claude/secretos/cloudflare.json) con {"cuenta": "...", "token": "..."}
y acceso a api.cloudflare.com. La clave del Worker se crea sola la primera vez.
Para el panel (/panel) también lee de la misma carpeta: panel.json {"clave": "contraseña inicial del panel (luego se cambia desde el panel)", "github": "github_pat_...", "herramientas": "llave larga que se crea sola"},
vapid.json y firebase-admin.json. Si falta alguno, el panel no se activa pero los avisos siguen funcionando."""
import base64, json, os, secrets, ssl, urllib.request, uuid
T = os.path.dirname(os.path.abspath(__file__)) + '/'
SEC = next((p for p in [os.path.expanduser('~/secretos'), '/home/claude/secretos'] if os.path.exists(p + '/cloudflare.json')), '/home/claude/secretos')
CF = json.load(open(SEC + '/cloudflare.json'))
if 'clave_worker' not in CF:
    CF['clave_worker'] = secrets.token_urlsafe(32); json.dump(CF, open(SEC + '/cloudflare.json', 'w'), indent=1)
pr = os.environ.get('HTTPS_PROXY'); ca = '/root/.ccr/ca-bundle.crt'
OP = urllib.request.build_opener(*([urllib.request.ProxyHandler({'https': pr})] if pr else []),
                                 urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=ca) if os.path.exists(ca) else ssl.create_default_context()))
API = f"https://api.cloudflare.com/client/v4/accounts/{CF['cuenta']}"
def cf(path, method='GET', data=None, ctype='application/json', base=API):
    h = {'Authorization': 'Bearer ' + CF['token']}
    if data is not None and ctype: h['Content-Type'] = ctype
    req = urllib.request.Request(base + path, data=data, method=method, headers=h)
    try: return json.load(OP.open(req, timeout=60))
    except urllib.error.HTTPError as e: raise SystemExit(f'Cloudflare {e.code}: {e.read().decode()[:500]}')
NOMBRE = 'gamex-avisos'
ns = [n for n in cf('/storage/kv/namespaces?per_page=100')['result'] if n['title'] == NOMBRE]
ns_id = ns[0]['id'] if ns else cf('/storage/kv/namespaces', 'POST', json.dumps({'title': NOMBRE}).encode())['result']['id']
meta = {'main_module': 'worker.js', 'compatibility_date': '2025-01-01',
        'bindings': [{'type': 'kv_namespace', 'name': 'SUBS', 'namespace_id': ns_id}, {'type': 'durable_object_namespace', 'name': 'STATS', 'class_name': 'Stats'}, {'type': 'secret_text', 'name': 'CLAVE', 'text': CF['clave_worker']}]}
_pj = json.load(open(SEC + '/panel.json')) if os.path.exists(SEC + '/panel.json') else None
if _pj is not None and not _pj.get('herramientas'):  # llave larga para las herramientas y tareas programadas (no cambia con la contraseña del panel)
    _pj['herramientas'] = secrets.token_urlsafe(32); json.dump(_pj, open(SEC + '/panel.json', 'w'), indent=1)
for nombre, archivo, campo in [('HERRAMIENTAS', 'panel.json', 'herramientas'), ('PANEL', 'panel.json', 'clave'), ('GITHUB', 'panel.json', 'github'), ('VAPID', 'vapid.json', None), ('FIREBASE', 'firebase-admin.json', None)]:
    try:
        d = json.load(open(SEC + '/' + archivo)); v = d[campo] if campo else json.dumps(d)
        if v: meta['bindings'].append({'type': 'secret_text', 'name': nombre, 'text': v})
    except (FileNotFoundError, KeyError): print('Aviso: falta', nombre, '(el panel no funcionará completo)')
codigo = open(T + 'push-worker.js').read().replace('// __CLIENTES__', open(T + 'clientes-worker.js').read(), 1).replace('__PANEL_HTML__', json.dumps(open(T + 'panel.html').read().replace('__FUENTES_COMP__', open(T + 'datos/fuentes-comprobante.json').read()).replace('__LOGO_GAMEX__', 'data:image/png;base64,' + base64.b64encode(open(T + 'datos/logo-gamex.png', 'rb').read()).decode())), 1).replace('__MODELOS__', open(T + 'datos/modelos.json').read(), 1)
def subir(m):
    b = uuid.uuid4().hex
    body = (f'--{b}\r\nContent-Disposition: form-data; name="metadata"\r\nContent-Type: application/json\r\n\r\n{json.dumps(m)}\r\n'
            f'--{b}\r\nContent-Disposition: form-data; name="worker.js"; filename="worker.js"\r\nContent-Type: application/javascript+module\r\n\r\n'
            + codigo + f'\r\n--{b}--\r\n').encode()
    return cf(f'/workers/scripts/{NOMBRE}', 'PUT', body, f'multipart/form-data; boundary={b}')
# La primera vez crea la base de estadísticas (migración v1); las siguientes ya existe.
try: subir({**meta, 'migrations': {'new_tag': 'v1', 'new_sqlite_classes': ['Stats']}})
except SystemExit as e:
    if 'migration' not in str(e).lower() and 'tag' not in str(e).lower(): raise
    subir(meta)
cf(f'/workers/scripts/{NOMBRE}/subdomain', 'POST', json.dumps({'enabled': True}).encode())
sub = cf('/workers/subdomain')['result']['subdomain']
url = f'https://{NOMBRE}.{sub}.workers.dev'
p = json.load(open(T + 'datos/push.json')); p['url'] = url; json.dump(p, open(T + 'datos/push.json', 'w'), indent=1)
print('Worker listo:', url)
