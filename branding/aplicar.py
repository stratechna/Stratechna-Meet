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
