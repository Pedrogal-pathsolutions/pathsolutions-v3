---
name: pathsol-isolamento-tenant
description: Regras e testes obrigatórios de isolamento entre laboratórios (tenants) na PathSolutions — JWT, Row-Level Security no PostgreSQL, SAS do Blob, logs e LGPD. Use sempre que criar ou alterar rota de API, modelo ou migração de banco, query, autenticação, geração de URL assinada, caminho de storage ou logging, e sempre que revisar código por vazamento de dados.
---

# Isolamento de tenant PathSolutions

Um vazamento entre laboratórios expõe dado de paciente de um cliente a outro. Cada regra abaixo fecha um caminho concreto de vazamento.

## API

- `tenant_id` sai do JWT validado (assinatura, expiração, audiência). Uma dependência única do FastAPI resolve o tenant; nenhuma rota lê tenant de outro lugar.
- Recurso de outro tenant responde 404, não 403, para não revelar que existe.

## PostgreSQL

- Toda tabela com `tenant_id`: `ENABLE ROW LEVEL SECURITY` e `FORCE ROW LEVEL SECURITY`. Sem FORCE, o dono da tabela ignora a política.
- A aplicação conecta com um papel que não é dono das tabelas, não é superusuário e não tem `BYPASSRLS`. Migrações rodam com outro papel.
- Política: `USING (tenant_id = current_setting('app.tenant_id', true)::uuid)` e `WITH CHECK` igual.
- O tenant é definido com `SET LOCAL app.tenant_id` (ou `set_config(..., true)`) dentro da transação. Nunca no nível da sessão: com pool de conexões, a próxima requisição herdaria o tenant anterior.
- Sem tenant definido, a query não retorna nada.

## Blob

- Caminhos sempre prefixados por tenant.
- SAS de delegação de usuário quando possível, escopo de um único blob, permissão mínima (só escrita para upload), expiração curta.
- A API nunca recebe o binário da WSI.

## Logs e dados

- Nada de nome de paciente, CPF, data de nascimento ou número de caso real em log, exceção, métrica, captura de tela ou relatório. Use ids internos.
- Log de auditoria clínica (quem viu, quem assinou, se viu a IA antes de assinar) fica em tabela própria, sem update nem delete pela aplicação.

## Testes obrigatórios por rota nova

1. Token do tenant A lendo recurso do tenant B → 404.
2. Token do tenant A escrevendo com `tenant_id` de B no body → ignorado ou rejeitado; o registro nunca aparece para B.
3. Query direta no banco com o papel da aplicação sem `app.tenant_id` definido → zero linhas.
4. SAS emitida para A não abre blob de B.

Rota sem esses quatro testes passando não conclui a fase.
