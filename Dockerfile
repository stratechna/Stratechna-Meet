# Stratechna Meet — Jitsi Meet com a marca Stratechna.
#
# A versão do Jitsi está FIXA. Actualizar é mudar esta linha, de propósito: o
# aplicar.py falha o build se alguma troca deixar de encaixar, e o verificar.sh
# (no workflow) falha se o nome do upstream ficar visível.
#
# A marca aplica-se numa fase à parte porque a imagem do Jitsi NÃO tem python3
# (Debian 12 enxuto, só perl e sed). Em vez de instalar python3 na imagem final
# — que fica no produto e aumenta a superfície — os ficheiros saem, são
# tratados numa fase descartável, e voltam.
ARG JITSI_VERSION=stable-10008

FROM jitsi/web:${JITSI_VERSION} AS origem

FROM python:3.12-slim AS marca
COPY --from=origem /usr/share/jitsi-meet /trabalho/jitsi-meet
COPY --from=origem /defaults /trabalho/defaults
COPY branding/ficheiros/ /tmp/ficheiros/
COPY branding/aplicar.py /tmp/aplicar.py
RUN python3 /tmp/aplicar.py /trabalho /tmp/ficheiros

FROM jitsi/web:${JITSI_VERSION}
ARG JITSI_VERSION

LABEL org.opencontainers.image.source="https://github.com/stratechna/Stratechna-Meet" \
      org.opencontainers.image.title="Stratechna Meet" \
      org.opencontainers.image.vendor="Stratechna" \
      org.opencontainers.image.version="${JITSI_VERSION}" \
      org.opencontainers.image.base.name="jitsi/web:${JITSI_VERSION}"

COPY --from=marca /trabalho/jitsi-meet/ /usr/share/jitsi-meet/
COPY --from=marca /trabalho/defaults/ /defaults/

# A imagem do Jitsi não traz ficheiro de licença nenhum, e nós PUBLICAMOS esta
# imagem — publicar é distribuir, e a Apache 2.0 obriga a acompanhar a licença
# e a declarar as alterações feitas (cláusulas 4(a) e 4(b)). Correr como serviço
# não obrigaria; publicar obriga.
#
# Ficam em /static/ porque é uma das pastas que o nginx do Jitsi serve — assim
# estão dentro da imagem E alcançáveis em https://.../static/NOTICE.
COPY branding/LICENSE-jitsi /usr/share/jitsi-meet/static/LICENSE
COPY branding/NOTICE        /usr/share/jitsi-meet/static/NOTICE
