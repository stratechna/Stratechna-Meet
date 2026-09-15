# Stratechna Meet

Reuniões por vídeo do Stratechna Orbit. É o [Jitsi Meet](https://github.com/jitsi/jitsi-meet)
com a marca Stratechna aplicada por cima, sem alterar o comportamento.

Imagem publicada em `ghcr.io/stratechna/stratechna-meet`.

## O que este repositório faz

Só troca a marca. Nenhuma funcionalidade é alterada, acrescentada ou removida —
o que corre é o Jitsi, na versão que está fixada no `Dockerfile`.

| Ficheiro | Papel |
|---|---|
| `Dockerfile` | fixa a versão do Jitsi e aplica a marca |
| `branding/aplicar.py` | faz as trocas, **e falha o build se alguma não encaixar** |
| `branding/verificar.sh` | arranca a imagem construída e confirma o resultado servido ao browser |
| `branding/ficheiros/` | os nossos desenhos (watermark, favicon, ícone, imagem de partilha) |

## Duas decisões que valem a pena explicar

**A marca aplica-se numa fase de build à parte.** A imagem do Jitsi não tem
`python3` — é Debian 12 enxuto, com perl e sed apenas. Em vez de instalar
python3 na imagem final, onde ficaria para sempre a aumentar a superfície, os
ficheiros saem, são tratados numa fase descartável e voltam.

**Nenhuma troca é optimista.** O `aplicar.py` conta as ocorrências e rebenta a
zero. Uma substituição que deixa de casar porque o upstream reescreveu o texto é
exactamente o caso que produz uma imagem com o nome do fornecedor à vista sem
ninguém dar por isso — e essas descobrem-se em produção, por um cliente. Por
isso o build tem de falhar, e falha.

## Actualizar a versão do Jitsi

1. Mudar `ARG JITSI_VERSION=` no `Dockerfile`.
2. Deixar correr o workflow. Se alguma troca deixou de encaixar, o build pára e
   diz qual — corrigir a âncora em `branding/aplicar.py`.
3. O `verificar.sh` corre antes da publicação: se o nome do upstream aparecer no
   que é servido ao browser, a imagem não sai.

## O que fica de fora

A autenticação, o encaminhamento e a configuração de produção não estão aqui —
vivem no `docker-compose.yml` do Orbit (`/opt/orbit/compose/meet`). Em resumo:
JWT (o inquilino vai no token e no caminho `/<cliente>/<sala>`), TLS pelo
Traefik, e o media do JVB directamente em `10000/udp` sem passar por proxy.
