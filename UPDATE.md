# Update Guide

## Objetivo

Esta atualização adiciona:

- `cbu` obrigatório para novos usuários
- `cbu_hash` para unicidade
- `email_hash` e `nickname_hash` para lookup/indexação
- placeholder `0000000000000000000000` para usuários antigos sem CBU

## Importante

Esta mudança exige uma pequena janela de manutenção.

Motivo:

- a aplicação antiga não grava `cbu`
- a aplicação nova espera as novas colunas no banco

Então o processo seguro é:

1. Colocar a API em manutenção ou parar a instância antiga.
2. Aplicar a migration do banco.
3. Subir a nova versão da API.
4. Validar login, criação de usuário e checkout.

## Migration

Arquivo:

- [users_cbu.sql](/C:/Users/Pedro/programacao/software/uba_questionary_api/src/databases/scripts/migrations/users_cbu.sql)

O que a migration faz:

1. Adiciona as colunas `cbu`, `cbu_hash`, `email_hash` e `nickname_hash`.
2. Preenche `cbu` com `0000000000000000000000` para usuários antigos sem CBU.
3. Define `cbu` como `NOT NULL`.
4. Cria índices únicos parciais para `cbu_hash`, `email_hash` e `nickname_hash`.

## Passo A Passo

1. Fazer backup do banco de produção.
2. Parar a versão antiga da API ou ativar manutenção.
3. Executar a migration `src/databases/scripts/migrations/users_cbu.sql`.
4. Publicar a nova versão da API.
5. Testar:
   - `POST /users` com novo usuário e `cbu` válido
   - `POST /login` com usuário antigo
   - `POST /forgot-password` com usuário antigo
   - `POST /stripe/generate`
6. Liberar a API novamente.

## Comportamento Dos Usuários Antigos

Usuários já existentes receberão no banco:

`0000000000000000000000`

Esse valor deve ser tratado pelo frontend como:

- cadastro incompleto
- usuário precisa atualizar o CBU

## Hashes De Email E Nickname

Os hashes de `email` e `nickname` não são preenchidos por SQL puro, porque os valores atuais estão criptografados com Fernet.

Na nova versão:

- novos usuários já nascem com `email_hash` e `nickname_hash`
- usuários antigos recebem esses hashes automaticamente quando passam por login ou forgot-password

## Observação Operacional

Se você quiser que toda a base fique otimizada imediatamente, o ideal é rodar depois um backfill em Python usando a mesma chave Fernet da aplicação para preencher `email_hash`, `nickname_hash` e, quando aplicável, `cbu_hash`.
