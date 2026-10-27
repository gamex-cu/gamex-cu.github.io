"""Notificaciones web (iPhone con la web en pantalla de inicio, y navegadores que las soportan).
Cifrado aes128gcm (RFC 8291) + VAPID (RFC 8292), solo con la librería cryptography.
Las claves VAPID privadas NO van en este repo: ~/secretos/vapid.json o /home/claude/secretos/vapid.json"""
import base64, json, os, time, struct, urllib.request, urllib.parse
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, hmac, serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

b64e = lambda b: base64.urlsafe_b64encode(b).rstrip(b'=').decode()
def b64d(s): s = s.replace('+', '-').replace('/', '_'); return base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))
def _hmac(k, d): h = hmac.HMAC(k, hashes.SHA256()); h.update(d); return h.finalize()
def _raw_pub(pk): return pk.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)

def nuevas_claves():
    pk = ec.generate_private_key(ec.SECP256R1())
    priv = pk.private_numbers().private_value.to_bytes(32, 'big')
    return {'publica': b64e(_raw_pub(pk)), 'privada': b64e(priv)}

def ruta_claves():
    for r in [os.environ.get('GAMEX_VAPID_KEY', ''), os.path.expanduser('~/secretos/vapid.json'), '/home/claude/secretos/vapid.json']:
        if r and os.path.exists(r): return r
    return '/home/claude/secretos/vapid.json'

def cargar_claves():
    k = json.load(open(ruta_claves()))
    pk = ec.derive_private_key(int.from_bytes(b64d(k['privada']), 'big'), ec.SECP256R1())
    return pk, k['publica']

def vapid_header(endpoint, pk, pub, contacto='mailto:gamex@users.noreply.github.com'):
    u = urllib.parse.urlparse(endpoint)
    head = b64e(json.dumps({'typ': 'JWT', 'alg': 'ES256'}).encode())
    body = b64e(json.dumps({'aud': f'{u.scheme}://{u.netloc}', 'exp': int(time.time()) + 12 * 3600, 'sub': contacto}).encode())
    r, s = decode_dss_signature(pk.sign(f'{head}.{body}'.encode(), ec.ECDSA(hashes.SHA256())))
    sig = b64e(r.to_bytes(32, 'big') + s.to_bytes(32, 'big'))
    return f'vapid t={head}.{body}.{sig}, k={pub}'

def cifrar(sub, datos):
    ua_pub = b64d(sub['keys']['p256dh']); auth = b64d(sub['keys']['auth'])
    as_pk = ec.generate_private_key(ec.SECP256R1()); as_pub = _raw_pub(as_pk)
    shared = as_pk.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), ua_pub))
    ikm = _hmac(_hmac(auth, shared), b'WebPush: info\x00' + ua_pub + as_pub + b'\x01')
    salt = os.urandom(16); prk = _hmac(salt, ikm)
    cek = _hmac(prk, b'Content-Encoding: aes128gcm\x00\x01')[:16]
    nonce = _hmac(prk, b'Content-Encoding: nonce\x00\x01')[:12]
    ct = AESGCM(cek).encrypt(nonce, datos + b'\x02', None)
    return salt + struct.pack('!I', 4096) + bytes([len(as_pub)]) + as_pub + ct

def enviar(sub, datos, opener=None):
    """Devuelve el código HTTP. 404/410 = la suscripción ya no existe (borrarla)."""
    pk, pub = cargar_claves()
    body = cifrar(sub, json.dumps(datos, ensure_ascii=False).encode())
    req = urllib.request.Request(sub['endpoint'], data=body, method='POST', headers={
        'Content-Encoding': 'aes128gcm', 'Content-Type': 'application/octet-stream', 'TTL': '604800', 'Urgency': 'high',
        'Authorization': vapid_header(sub['endpoint'], pk, pub)})
    try: return (opener or urllib.request.build_opener()).open(req, timeout=30).status
    except urllib.error.HTTPError as e: return e.code
