# Desligamento do legado: registro de ações (Fase 1)

A sequência segue a skill `pathsol-desligamento-legado`. O Pedro autorizou a execução da Fase 1 em 15/10/2026, com uma autorização por ação (a confirmação de cada comando no Claude Code) e a VM2 primeiro nos passos de remoção e limpeza.

Cada entrada traz o horário de início em UTC, o comando ou a ação, e a saída resumida. Nenhum dado de paciente entra aqui.

## Passo 0: repositório da v3 no GitHub

- 17:20:30 UTC: geração de chave SSH ed25519 dedicada em `~/.config/pathsolutions-v3/deploy_key` (fora do `~/.ssh`), sem senha, comentário `pathsolutions-v3 deploy key (vm1)`; coleta da chave de host ed25519 do github.com em `~/.config/pathsolutions-v3/known_hosts`.
  - Resultado: chave criada (impressão digital `SHA256:E33k2lNyKc0AhYlNswhceKU1zOvmFqUuqeHss3X/j+o`). A chave de host ed25519 do github.com tem `SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU`, igual à publicada pelo GitHub. Aguardando o Pedro cadastrar a chave pública como deploy key com escrita.
- 20:08:52 UTC: o Pedro confirmou o cadastro da deploy key com escrita. Branch local `master` renomeada para `main`; remoto `origin` = `git@github.com:Pedrogal-pathsolutions/pathsolutions-v3.git`, com `core.sshCommand` usando só a chave dedicada e o known_hosts dedicado (`StrictHostKeyChecking=yes`).
