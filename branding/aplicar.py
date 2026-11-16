#!/usr/bin/env python3
"""Aplica a marca Stratechna aos ficheiros do Jitsi Meet.

A regra desta casa: **cada troca tem de encaixar, ou o build falha**. Uma
substituição que deixa de casar porque o upstream mudou o texto é exactamente o
caso que produz uma imagem com o nome do fornecedor à vista sem ninguém dar por
isso — e essas descobrem-se em produção, por um cliente.

Por isso não há `str.replace` optimista em lado nenhum: `trocar()` conta as
ocorrências e rebenta a zero.

Uso: aplicar.py <raiz> <ficheiros>
  <raiz>      a árvore com jitsi-meet/ e defaults/ tirada da imagem original
  <ficheiros> a pasta com os nossos SVG/PNG/ICO
"""
import json
import pathlib
import re
import shutil
import sys

RAIZ = pathlib.Path(sys.argv[1])
NOSSOS = pathlib.Path(sys.argv[2])

WEB = RAIZ / "jitsi-meet"
DEFAULTS = RAIZ / "defaults"

NOME = "Stratechna Meet"
MARCA = "Stratechna"
SITIO = "https://stratechna.com"

falhas: list[str] = []
feitos: list[str] = []


def trocar(caminho: pathlib.Path, velho: str, novo: str, minimo: int = 1) -> None:
    """Substitui e exige que tenha havido pelo menos `minimo` ocorrências."""
    if not caminho.exists():
        falhas.append(f"{caminho}: não existe")
        return
    texto = caminho.read_text(encoding="utf-8")
    n = texto.count(velho)
    if n < minimo:
        falhas.append(f"{caminho}: «{velho[:60]}» apareceu {n}x, esperava >= {minimo}")
        return
    caminho.write_text(texto.replace(velho, novo), encoding="utf-8")
    feitos.append(f"{caminho.name}: {n}x «{velho[:40]}»")


def copiar(origem: str, destino: pathlib.Path) -> None:
    o = NOSSOS / origem
    if not o.exists():
        falhas.append(f"falta o nosso ficheiro {origem}")
        return
    if not destino.parent.exists():
        falhas.append(f"{destino.parent}: não existe")
        return
    shutil.copyfile(o, destino)
    feitos.append(f"{destino.relative_to(RAIZ)} <- {origem}")


# ── 1. o separador do browser e as partilhas ───────────────────────────────
titulo = WEB / "title.html"
trocar(titulo, "Jitsi Meet", NOME, minimo=3)
trocar(titulo,
       "Join a WebRTC video conference powered by the Jitsi Videobridge",
       "Reunião por vídeo do Stratechna Orbit", minimo=3)
trocar(titulo, "images/jitsilogo.png", "images/stratechna-meet.png", minimo=2)

# ── 2. nome da aplicação e do fornecedor ───────────────────────────────────
icfg = DEFAULTS / "interface_config.js"
trocar(icfg, "APP_NAME: 'Jitsi Meet'", f"APP_NAME: '{NOME}'")
trocar(icfg, "PROVIDER_NAME: 'Jitsi'", f"PROVIDER_NAME: '{MARCA}'")
trocar(icfg, "JITSI_WATERMARK_LINK: 'https://jitsi.org'",
       f"JITSI_WATERMARK_LINK: '{SITIO}'")

# Comentários de JavaScript. Não são visíveis a ninguém, mas vão inline no HTML
# que o browser recebe — quem abrir o código-fonte da página lê o nome do
# fornecedor. Ficam com âncora própria de propósito: se o upstream reescrever o
# comentário, o build pára e olha-se para isto em vez de publicar às cegas.
trocar(DEFAULTS / "system-config.js", "// Jitsi Meet configuration.",
       f"// Configuração do {NOME}.")
trocar(icfg, "the mobile app Jitsi Meet is to be promoted",
       f"the mobile app {NOME} is to be promoted")

# ── 3. os nossos desenhos por cima dos deles ───────────────────────────────
# O watermark é o logótipo no canto da sala; o favicon é o separador.
copiar("watermark.svg", WEB / "images" / "watermark.svg")
copiar("favicon.svg", WEB / "images" / "favicon.svg")
copiar("stratechna-meet.png", WEB / "images" / "stratechna-meet.png")
copiar("apple-touch-icon.png", WEB / "images" / "apple-touch-icon.png")

# ── 3b. o catálogo inglês EMBUTIDO no pacote da app ────────────────────────
# O inglês não vem só do lang/main.json: o app.bundle.min.js leva uma cópia
# compilada do catálogo, e é essa que se usa quando o browser está em inglês.
# Por isso a página de entrada dizia «Jitsi Meet» e «Jitsi on mobile» com os
# ficheiros de idioma todos limpos — a verificação só olhava para os JSON.
#
# Troca-se só o VALOR de cada frase, chave a chave, a partir do main.json
# original (antes do passo 4): cada par "chave":"valor" tem de aparecer
# exactamente uma vez no pacote, ou o build pára. Os identificadores de código
# não se tocam.
def _folhas(o, caminho=()):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from _folhas(v, caminho + (k,))
    elif isinstance(o, str):
        yield caminho, o


def _marca_texto(t: str) -> str:
    t = t.replace("Jitsi Meet", NOME)
    return re.sub(r"(?<![A-Za-z])Jitsi(?![A-Za-z])", NOME, t)


def _no_pacote(chave: str, valor: str) -> str:
    # O catálogo está dentro de uma string JS entre plicas: as plicas do texto
    # vão escapadas.
    return json.dumps({chave: valor}, ensure_ascii=False,
                      separators=(",", ":"))[1:-1].replace("'", "\\'")


pacote = WEB / "libs" / "app.bundle.min.js"
catalogo_en = json.loads((WEB / "lang" / "main.json").read_text(encoding="utf-8"))
if pacote.exists():
    js = pacote.read_text(encoding="utf-8")
    n_trocas = 0
    for caminho, valor in _folhas(catalogo_en):
        if not re.search(r"(?<![A-Za-z])Jitsi(?![A-Za-z])", valor):
            continue
        velho = _no_pacote(caminho[-1], valor)
        n = js.count(velho)
        if n != 1:
            falhas.append(f"app.bundle.min.js: «{'.'.join(caminho)}» apareceu {n}x, esperava 1")
            continue
        js = js.replace(velho, _no_pacote(caminho[-1], _marca_texto(valor)))
        n_trocas += 1
    if n_trocas < 5:
        falhas.append(f"app.bundle.min.js: só {n_trocas} frases do catálogo embutido, esperava >= 5")
    pacote.write_text(js, encoding="utf-8")
    feitos.append(f"libs/app.bundle.min.js: {n_trocas} frases do catálogo inglês embutido")
else:
    falhas.append(f"{pacote}: não existe")

# ── 3c. letra e paleta Stratechna ──────────────────────────────────────────
# A folha própria entra pelo plugin.head.html — o ficheiro que o index.html já
# inclui (SSI) e que o upstream deixa VAZIO precisamente para isto. Se um dia
# deixar de estar vazio ou de ser incluído, o build pára e olha-se.
cabeca = WEB / "plugin.head.html"
indice = WEB / "index.html"
if not cabeca.exists() or "plugin.head.html" not in indice.read_text(encoding="utf-8"):
    falhas.append("plugin.head.html: não existe ou o index.html já não o inclui")
elif cabeca.read_text(encoding="utf-8").strip():
    falhas.append("plugin.head.html: o upstream passou a pôr lá conteúdo — rever")
else:
    cabeca.write_text('<link rel="stylesheet" href="/css/stratechna-meet.css?v=1">\n',
                      encoding="utf-8")
    feitos.append("plugin.head.html -> css/stratechna-meet.css")
copiar("stratechna-meet.css", WEB / "css" / "stratechna-meet.css")
# A letra é servida pelo próprio Meet (pasta /fonts, já servida pelo nginx do
# Jitsi): nada vai ao Google.
for f in sorted((NOSSOS / "fonts").glob("*")):
    copiar(f"fonts/{f.name}", WEB / "fonts" / f.name)
# O tema da sala (React) só aceita cores pelo tema de marca dinâmica — o ponto
# oficial (config.dynamicBrandingUrl, que a imagem define a partir da variável
# DYNAMIC_BRANDING_URL; ver o Dockerfile).
copiar("stratechna-marca.json", WEB / "static" / "stratechna-marca.json")
if "DYNAMIC_BRANDING_URL" not in (DEFAULTS / "settings-config.js").read_text(encoding="utf-8"):
    falhas.append("settings-config.js: a variável DYNAMIC_BRANDING_URL deixou de existir")

# ── 4. as traduções ────────────────────────────────────────────────────────
# Só sete ocorrências por idioma, todas em texto que o utilizador lê. A ordem
# importa: «Jitsi Meet» primeiro, senão o «Jitsi» solto parte-o a meio.
for lang in sorted((WEB / "lang").glob("main*.json")):
    texto = lang.read_text(encoding="utf-8")
    if "Jitsi" not in texto:
        continue
    novo = texto.replace("Jitsi Meet", NOME)
    novo = re.sub(r"(?<![A-Za-z])Jitsi(?![A-Za-z])", NOME, novo)
    lang.write_text(novo, encoding="utf-8")
    feitos.append(f"lang/{lang.name}: {texto.count('Jitsi')}x")

# ── resultado ──────────────────────────────────────────────────────────────
for f in feitos:
    print("  ok:", f)
if falhas:
    print()
    for f in falhas:
        print("  FALHA:", f)
    print(f"\n{len(falhas)} troca(s) não encaixaram — o upstream mudou. "
          "Rever antes de publicar.")
    sys.exit(1)
print(f"\nmarca aplicada: {len(feitos)} alterações")
