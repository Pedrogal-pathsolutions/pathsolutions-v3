# Kit PathSolutions v3

## Conteúdo

- `PROMPT_V3.md` — a missão. Cada sessão executa a fase indicada e para.
- `CLAUDE.md` — regras permanentes. O Claude Code carrega sozinho em toda sessão aberta nesta pasta.
- `.claude/skills/` — 4 skills do projeto, carregadas sob demanda:
  - `pathsol-desligamento-legado` — desligar e limpar o sistema atual, preservando as WSIs do Blob.
  - `pathsol-infra` — Terraform para recursos novos, VMs reaproveitadas, custo e disco.
  - `pathsol-contrato-h5` — o arquivo `.h5`, a fila e os testes de aceite do worker.
  - `pathsol-isolamento-tenant` — JWT, RLS, SAS e LGPD.
- `.claude/settings.json` — bloqueios (exclusão de recursos Azure, de blobs e de snapshots; destroy; import; leitura de segredos) e confirmações (sudo, rm -rf, docker, crontab, apply, ligar/desligar VM, psql, ssh, push).
- `docs/arquitetura/` — a arquitetura de referência.
- `docs/v3/` — relatórios das fases. `docs/operacao/` — registro das ações no legado.

## Instalação na VM1 (uma vez)

1. Baixe o `pathsolutions-v3.zip` no seu computador.
2. No VS Code conectado à VM1, arraste o zip para a pasta `/home/azureps` no Explorer. Isso envia o arquivo para a VM.
3. No terminal do VS Code:

```
cd ~
python3 -m zipfile -e pathsolutions-v3.zip .
cd pathsolutions-v3
git init && git add -A && git commit -m "Kit inicial da v3"
```

4. Preencha D1 a D4 em `PROMPT_V3.md`.
5. File → Open Folder → `/home/azureps/pathsolutions-v3`. O Claude Code precisa ser aberto com esta pasta como raiz.
6. Plugins: no chat do Claude Code, clique em `/` → Customize → Plugins e instale `azure`, `microsoft-docs` e `security-guidance` (marketplace oficial). Para o Terraform, adicione o marketplace `hashicorp/agent-skills` e instale `terraform`.
7. Ctrl+Shift+P → "Reload Window".
8. Teste: pergunte "Quais skills do projeto você tem e quais são as regras do CLAUDE.md?". A resposta precisa citar as 4 skills `pathsol-*`. Se não citar, a pasta aberta não é a raiz do kit.

As pastas e kits anteriores (`Pathsolutions_V2`, o kit dentro do repositório legado e o primeiro zip da v3) ficam obsoletos. Não abra sessões neles.

## Execução

Abra uma sessão nova e escreva:

```
Execute as instruções de @PROMPT_V3.md
```

Mantenha o modo de permissão padrão, que pede confirmação. As confirmações são as travas.

Cada fase termina em `PARADO — aguardando APROVADO FASE N`. Leia o relatório em `docs/v3/`, responda `APROVADO FASE N` e abra uma sessão nova para a fase seguinte, com:

```
Fase N aprovada. Execute a Fase N+1 de @PROMPT_V3.md, a partir dos relatórios em docs/v3/.
```

Uma sessão por fase: o estado fica nos relatórios, não na memória da conversa.
