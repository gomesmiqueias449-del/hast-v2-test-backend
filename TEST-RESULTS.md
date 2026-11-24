# Resultado dos testes

Execução em Python 3.12 com dependências do projeto: `pytest -q` concluiu com **6 testes aprovados**. Foram verificados login guest aleatório, saldos zero, autorização JWT do próprio perfil, bloqueio de acesso a outro perfil, renomeação persistida após reiniciar a aplicação, ausência de `device_id` na tabela e resposta HTTP 501 para a integração Photon desativada. `compileall` também terminou sem erros.

O pytest exibiu um aviso de depreciação vindo de `starlette.testclient` sobre o uso de `httpx`; não houve falhas de teste. A API foi testada em cliente ASGI local, não publicada ou conectada a um jogo.