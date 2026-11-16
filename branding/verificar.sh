#!/bin/bash
# Teste depois do build: arranca a imagem e falha se o nome do upstream estiver
# visível ou se faltar alguma peça da marca.
# Uso: branding/verificar.sh <imagem>     (corre no workflow antes de publicar)
#
# Corre só o jitsi/web, sem prosody nem jvb: o que se verifica aqui é o que o
# browser recebe antes de haver sala nenhuma — que é exactamente onde a marca
# do fornecedor aparecia.
set -uo pipefail
IMG=${1:?uso: verificar.sh <imagem>}
DIR=$(cd "$(dirname "$0")" && pwd)
ID=verif-meet-$$
PORTA=${PORTA:-18400}
B=http://127.0.0.1:$PORTA
FALHAS=0
falha() { FALHAS=$((FALHAS + 1)); echo "  FALHA: $1"; }
ok() { echo "  ok: $1"; }
limpar() { docker rm -f $ID >/dev/null 2>&1; }
trap limpar EXIT

# «Jitsi» como palavra inteira. Os identificadores de código (JITSI_WATERMARK_LINK,
# jitsiNodeModules) não contam — trocá-los partia a aplicação.
conta_nome() { python3 -c 'import re,sys; print(len(re.findall(r"(?<![A-Za-z0-9_$])Jitsi(?![A-Za-z0-9_$])", sys.stdin.read())))'; }

docker run -d --name $ID -p 127.0.0.1:$PORTA:80 \
  -e PUBLIC_URL=$B -e DISABLE_HTTPS=1 -e ENABLE_LETSENCRYPT=0 \
  -e XMPP_DOMAIN=meet.jitsi -e XMPP_AUTH_DOMAIN=auth.meet.jitsi \
  -e XMPP_MUC_DOMAIN=muc.meet.jitsi -e XMPP_GUEST_DOMAIN=guest.meet.jitsi \
  -e XMPP_INTERNAL_MUC_DOMAIN=internal-muc.meet.jitsi -e XMPP_SERVER=xmpp.meet.jitsi \
  -e XMPP_BOSH_URL_BASE=http://xmpp.meet.jitsi:5280 \
  "$IMG" >/dev/null

echo "== à espera do arranque =="
for i in $(seq 1 60); do
  [ "$(curl -s -o /dev/null -w '%{http_code}' "$B/")" = 200 ] && break
  if [ "$i" = 60 ]; then docker logs --tail 30 $ID; echo "FALHA: não arrancou"; exit 1; fi
  sleep 2
done
ok "arrancou"

obter() { curl -fsS --retry 5 --retry-delay 2 --retry-all-errors "$@"; }

echo "== página inicial =="
H=$(obter "$B/")
T=$(printf '%s' "$H" | tr '\n' ' ' | sed -nE 's/.*<title[^>]*>[[:space:]]*([^<]*[^[:space:]<])[[:space:]]*<\/title>.*/\1/p' | head -1)
[ "$T" = "Stratechna Meet" ] && ok "título «$T»" || falha "título «$T»"
N=$(printf '%s' "$H" | conta_nome)
[ "$N" = 0 ] && ok "HTML sem «Jitsi»" || falha "HTML com $N «Jitsi»: $(printf '%s' "$H" | grep -oE '.{0,30}Jitsi.{0,20}' | head -2)"

echo "== configuração servida ao browser =="
C=$(obter "$B/interface_config.js")
printf '%s' "$C" | grep -q "APP_NAME: 'Stratechna Meet'" && ok "APP_NAME" || falha "APP_NAME não é o nosso"
printf '%s' "$C" | grep -q "PROVIDER_NAME: 'Stratechna'" && ok "PROVIDER_NAME" || falha "PROVIDER_NAME não é o nosso"
printf '%s' "$C" | grep -q "JITSI_WATERMARK_LINK: 'https://stratechna.com'" && ok "watermark aponta para nós" || falha "watermark ainda aponta para jitsi.org"

echo "== os desenhos são mesmo os nossos =="
for f in watermark.svg favicon.svg; do
  if [ "$(obter "$B/images/$f" | sha256sum | cut -c1-16)" = "$(sha256sum < "$DIR/ficheiros/$f" | cut -c1-16)" ]; then
    ok "images/$f"
  else
    falha "images/$f não é o nosso"
  fi
done

echo "== traduções =="
# O inglês é `main.json`, sem sufixo — os outros idiomas é que levam `-xx`.
for F in main.json main-pt.json main-de.json; do
  if ! C=$(obter "$B/lang/$F"); then falha "lang/$F não foi servido"; continue; fi
  n=$(printf '%s' "$C" | conta_nome)
  [ "$n" = 0 ] && ok "lang/$F sem «Jitsi»" || falha "lang/$F com $n «Jitsi»"
done

echo "== catálogo inglês embutido no pacote da app =="
# Era por aqui que a página de entrada dizia «Jitsi Meet» com os JSON limpos.
P=$(obter "$B/libs/app.bundle.min.js")
for chave in headerTitle jitsiOnMobile productLabel; do
  if printf '%s' "$P" | grep -qE "\"$chave\":\"[^\"]*Jitsi"; then falha "pacote: «$chave» ainda com «Jitsi»"; else ok "pacote: «$chave»"; fi
done
printf '%s' "$P" | grep -q '"headerTitle":"Stratechna Meet"' && ok "título da página de entrada" || falha "headerTitle não é o nosso"

echo "== letra e paleta Stratechna =="
printf '%s' "$H" | grep -q 'css/stratechna-meet.css' && ok "folha própria no HTML (plugin.head.html)" || falha "folha própria não incluída no HTML"
CSS=$(obter "$B/css/stratechna-meet.css") && ok "css/stratechna-meet.css servida" || falha "css/stratechna-meet.css não servida"
printf '%s' "$CSS" | grep -q '#b20009' && ok "vermelho de acção na folha" || falha "folha sem #b20009"
for f in dm-sans-latin-wght-normal.woff2 dm-sans-latin-ext-wght-normal.woff2 dm-sans-latin-wght-italic.woff2; do
  if [ "$(obter "$B/fonts/$f" | sha256sum | cut -c1-16)" = "$(sha256sum < "$DIR/ficheiros/fonts/$f" | cut -c1-16)" ]; then ok "fonts/$f servida pelo Meet"; else falha "fonts/$f não servida"; fi
done
if printf '%s%s' "$H" "$CSS" | grep -qi 'fonts.googleapis\|fonts.gstatic'; then falha "pedido ao Google Fonts"; else ok "nada vai ao Google Fonts"; fi
obter "$B/static/stratechna-marca.json" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["customTheme"]["palette"]["action01"]=="#b20009"' \
  && ok "tema de marca dinâmica (action01 = #b20009)" || falha "static/stratechna-marca.json inválido"
obter "$B/config.js" | grep -q "config.dynamicBrandingUrl = '/static/stratechna-marca.json'" \
  && ok "config.dynamicBrandingUrl" || falha "config.js sem dynamicBrandingUrl"

echo
if [ $FALHAS -gt 0 ]; then
  echo "VERIFICAÇÃO FALHOU ($FALHAS) — a imagem não deve ser publicada"
  exit 1
fi
echo "VERIFICAÇÃO OK — marca Stratechna Meet, sem o nome do upstream"
