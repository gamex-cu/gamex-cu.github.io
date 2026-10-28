"""Etiquetas para que Google y las redes muestren bien la web de GameX (las usa armar.py)."""
import json

DESC = ('Tienda de videojuegos GameX en La Habana (Vedado): juegos para PS4, PS5, PC, Xbox, Nintendo Switch y Meta Quest, '
        'Game Pass, PS Plus, gift cards, desbloqueos y mantenimiento. Pide por WhatsApp.')

LD = {
    "@context": "https://schema.org", "@type": "Store", "name": "GameX – Tienda de Videojuegos",
    "url": "https://gamex-cu.github.io/", "logo": "https://gamex-cu.github.io/icon-512.png", "image": "https://gamex-cu.github.io/og.jpg",
    "description": "Tienda de videojuegos en La Habana: juegos para PlayStation 4, PlayStation 5, PC, Xbox, Nintendo Switch y Meta Quest; "
                   "suscripciones, gift cards, desbloqueos y mantenimiento de consolas.",
    "telephone": ["+5353441089", "+5353827989", "+5352933943"],
    "address": {"@type": "PostalAddress", "streetAddress": "Calle 10 #211 apto 2 e/ 11 y Línea, Vedado",
                "addressLocality": "La Habana", "addressCountry": "CU"},
    "openingHoursSpecification": [{"@type": "OpeningHoursSpecification",
                                   "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
                                   "opens": "10:00", "closes": "18:00"}],
    "hasMap": "https://maps.app.goo.gl/hfsEAhNcSgx5iHi9A",
    "sameAs": ["https://www.instagram.com/gamex.cu/", "https://www.facebook.com/share/1CKYgeuN1w/", "https://x.com/GameX_CU",
               "https://whatsapp.com/channel/0029Va8LPJrAe5ViFejeDG3O"],
}

def etiquetas(verificacion_google=''):
    t = [
        '<link rel="canonical" href="https://gamex-cu.github.io/">',
        '<meta name="robots" content="index,follow">',
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="GameX">',
        '<meta property="og:title" content="GameX – Tienda de Videojuegos en La Habana">',
        f'<meta property="og:description" content="{DESC}">',
        '<meta property="og:url" content="https://gamex-cu.github.io/">',
        '<meta property="og:image" content="https://gamex-cu.github.io/og.jpg">',
        '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">',
        '<meta property="og:locale" content="es_ES">',
        '<meta name="twitter:card" content="summary_large_image">',
        '<meta name="twitter:site" content="@GameX_CU">',
        '<script type="application/ld+json">' + json.dumps(LD, ensure_ascii=False).replace('</', '<\\/') + '</script>',
    ]
    if verificacion_google:
        t.insert(0, f'<meta name="google-site-verification" content="{verificacion_google}">')
    return '\n'.join(t) + '\n'
