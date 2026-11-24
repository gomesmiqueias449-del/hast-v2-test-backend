# Contrato da API de teste

## Login guest

`POST /v2/auth/guest`

```json
{"device_id":"android-teste"}
```

O valor de `device_id` é validado e descartado. A resposta traz ID guest aleatório, JWT de acesso ao perfil e um identificador temporário de sessão. Não contém AppID, região ou token Photon.

## Perfil autenticado

`GET /v2/profile/{user_id}`

Header obrigatório: `Authorization: Bearer <accessToken>`.

O `user_id` da URL deve ser exatamente o sujeito (`sub`) do JWT. O perfil contém nome, nível, `coins=0`, `gems=0`, inventário vazio e campos de progresso/configuração vazios.

## Renomear

`POST /v2/profile/{user_id}/name`

Header obrigatório: `Authorization: Bearer <accessToken>`.

```json
{"display_name":"NovoNome"}
```

Aceita nomes entre 3 e 20 caracteres depois de remover espaços externos.

## Photon

`POST /v2/photon/session` devolve HTTP 501 e `photon_integration_disabled_for_test`. A rota está presente para comunicar claramente que a integração não faz parte deste backend de teste.
