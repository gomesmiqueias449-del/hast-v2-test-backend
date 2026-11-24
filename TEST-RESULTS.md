# Resultado dos testes

Os testes locais em Python 3.12 concluíram com **6 aprovados**. Foram verificados login guest aleatório, saldos zero, autorização JWT do próprio perfil, bloqueio de acesso a outro perfil, renomeação persistida após reiniciar a aplicação, ausência de `device_id` na tabela e resposta HTTP 501 para a integração Photon desativada. `compileall` terminou sem erros.

A API foi publicada no Render e verificada remotamente em 2026-11-24. `GET /health` respondeu `ok=true` e `photonIntegration=false`. Um login guest sintético retornou HTTP 200; a consulta autenticada do próprio perfil retornou HTTP 200 com `coins=0` e `gems=0`. `POST /v2/photon/session` permaneceu desativado e retornou HTTP 501.

O pytest exibiu um aviso de depreciação vindo de `starlette.testclient` sobre o uso de `httpx`; não houve falhas. Nenhum token, identificador guest ou segredo JWT foi incluído neste relatório. A API não foi conectada ao jogo nem a um lobby.
