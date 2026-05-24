# Update Guide

## Objetivo

Esta atualizacao adiciona:

- `dni` obrigatorio para novos usuarios
- `dni_hash` para unicidade
- `email_hash` e `nickname_hash` para lookup/indexacao
- placeholder `00000000` para usuarios antigos sem DNI
- remocao das colunas antigas de `cbu` e `cbu_hash`

## Importante

Esta mudanca exige uma pequena janela de manutencao.

Motivo:

- a aplicacao antiga nao grava `dni`
- a aplicacao nova espera as novas colunas no banco

Entao o processo seguro e:

1. Colocar a API em manutencao ou parar a instancia antiga.
2. Aplicar a migration do banco.
3. Subir a nova versao da API.
4. Validar login, criacao de usuario e checkout.

## Migration

Arquivo:

- [users_dni.sql](/C:/Users/Pedro/programacao/software/uba_questionary_api/src/databases/scripts/migrations/users_dni.sql)

O que a migration faz:

1. Remove a estrutura antiga de `cbu` (`cbu`, `cbu_hash` e indice/constraint associado), caso ela exista.
2. Adiciona as colunas `dni` e `dni_hash`.
3. Preenche `dni` com `00000000` para usuarios antigos sem DNI.
4. Define `dni` como `NOT NULL`.
5. Cria o indice unico parcial de `dni_hash`.

## Passo A Passo

1. Fazer backup do banco de producao.
2. Parar a versao antiga da API ou ativar manutencao.
3. Confirmar que a etapa antiga de `CBU` ja foi aplicada ou que as colunas `cbu`/`cbu_hash` nao sao mais necessarias.
4. Executar a migration `src/databases/scripts/migrations/users_dni.sql`.
5. Publicar a nova versao da API.
6. Testar:
   - `POST /users` com novo usuario e `dni` valido
   - `POST /login` com usuario antigo
   - `POST /forgot-password` com usuario antigo
   - `POST /stripe/generate`
7. Liberar a API novamente.

## Cenario De Quem Ja Aplicou A Migration De CBU

Se o ambiente de producao ja recebeu a migration de `CBU`, esta nova migration ja faz a reversao necessaria:

- remove `cbu`
- remove `cbu_hash`
- remove o indice/constraint `users_cbu_hash_key`
- adiciona `dni` e `dni_hash`
- reaproveita `email_hash` e `nickname_hash` ja criados em `users_cbu.sql`

Ou seja, para esse caso voce deve rodar apenas:

- [users_dni.sql](/C:/Users/Pedro/programacao/software/uba_questionary_api/src/databases/scripts/migrations/users_dni.sql)

Nao e necessario editar manualmente o banco antes, desde que a API antiga esteja parada durante a mudanca.

## Comportamento Dos Usuarios Antigos

Usuarios ja existentes receberao no banco:

`00000000`

Esse valor deve ser tratado pelo frontend como:

- cadastro incompleto
- usuario precisa atualizar o DNI

## Hashes De Email E Nickname

Os hashes de `email` e `nickname` nao sao preenchidos por SQL puro, porque os valores atuais estao criptografados com Fernet.

Na nova versao:

- novos usuarios ja nascem com `email_hash` e `nickname_hash`
- usuarios antigos recebem esses hashes automaticamente quando passam por login ou forgot-password

## Observacao Operacional

Se voce quiser que toda a base fique otimizada imediatamente, o ideal e rodar depois um backfill em Python usando a mesma chave Fernet da aplicacao para preencher `email_hash`, `nickname_hash` e, quando aplicavel, `dni_hash`.
