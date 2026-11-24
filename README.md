# Backend independente de teste — Hast

Projeto FastAPI separado dos serviços Render já existentes. Implementa login guest, perfil persistido em SQLite e renomeação protegida por JWT. Cada login cria um ID guest aleatório; o `device_id` é validado, mas não é armazenado nem usado como identificador. O saldo inicial é sempre `coins=0` e `gems=0`.

**Photon está desativado.** A rota `POST /v2/photon/session` responde HTTP 501 com `photon_integration_disabled_for_test`. A API não retorna AppID, região ou credencial Photon e não cria/entra em salas. Isso respeita a separação do fluxo nativo e evita tratar o exemplo do anexo como compatível com um APK existente. Também não modifica DLL, cliente Unity, backend global ou serviço oficial.

## Rotas

- `GET /health` — verificação do serviço.
- `POST /v2/auth/guest` — recebe `{"device_id":"android-teste"}` e devolve `userId`, `displayName`, `accessToken` e `sessionId` temporário.
- `GET /v2/profile/{user_id}` — devolve o perfil do dono do token Bearer.
- `POST /v2/profile/{user_id}/name` — renomeia o próprio perfil com token Bearer; o nome é limitado a 3–20 caracteres.
- `POST /v2/photon/session` — desativada, HTTP 501.

O `sessionId` é apenas um valor aleatório de diagnóstico; o `accessToken` JWT é a credencial usada nas rotas de perfil. O segredo JWT não tem valor padrão: o serviço recusa iniciar se `JWT_SECRET` não tiver ao menos 32 bytes. O ID do usuário guest e o perfil são persistidos no SQLite; o identificador de dispositivo não é.

## Executar localmente

Requer Python 3.10 ou superior.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export JWT_SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
export DATABASE_PATH="./data/game.db"
uvicorn main:app --host 127.0.0.1 --port 8000
```

Em outra janela, teste a saúde e o login:

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/v2/auth/guest \
  -H 'Content-Type: application/json' \
  -d '{"device_id":"android-teste"}'
```

Use o `userId` e o `accessToken` retornados para consultar o próprio perfil:

```bash
curl http://127.0.0.1:8000/v2/profile/SEU_USER_ID \
  -H 'Authorization: Bearer SEU_ACCESS_TOKEN'
```

Para alterar o nome, envie `POST /v2/profile/SEU_USER_ID/name` com o mesmo header Bearer e JSON `{"display_name":"NovoNome"}`. O token só autoriza o perfil cujo ID corresponde ao campo `sub` do JWT.

## Publicação no Render

O arquivo `render.yaml` define um Web Service público no plano gratuito e na região Virginia. O Render gera `JWT_SECRET` no próprio serviço; nenhum segredo fica no repositório. A primeira sincronização do Blueprint exige aprovação no Render antes de criar o serviço.

Este plano usa SQLite no filesystem efêmero do serviço gratuito. Portanto, dados de guest e nomes podem ser perdidos em reinícios ou novos deploys. É apropriado para teste, não para dados que precisem de persistência durável; para isso, seria necessário configurar armazenamento persistente ou migrar para um banco gerenciado.

## Testes

```bash
pytest -q
```
