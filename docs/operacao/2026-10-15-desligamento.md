# Desligamento do legado: registro de ações (Fase 1)

A sequência segue a skill `pathsol-desligamento-legado`. O Pedro autorizou a execução da Fase 1 em 15/10/2026, com uma autorização por ação (a confirmação de cada comando no Claude Code) e a VM2 primeiro nos passos de remoção e limpeza.

Cada entrada traz o horário de início em UTC, o comando ou a ação, e a saída resumida. Nenhum dado de paciente entra aqui.

## Passo 0: repositório da v3 no GitHub

- 17:20:30 UTC: geração de chave SSH ed25519 dedicada em `~/.config/pathsolutions-v3/deploy_key` (fora do `~/.ssh`), sem senha, comentário `pathsolutions-v3 deploy key (vm1)`; coleta da chave de host ed25519 do github.com em `~/.config/pathsolutions-v3/known_hosts`.
  - Resultado: chave criada (impressão digital `SHA256:E33k2lNyKc0AhYlNswhceKU1zOvmFqUuqeHss3X/j+o`). A chave de host ed25519 do github.com tem `SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU`, igual à publicada pelo GitHub. Aguardando o Pedro cadastrar a chave pública como deploy key com escrita.
- 20:08:52 UTC: o Pedro confirmou o cadastro da deploy key com escrita. Branch local `master` renomeada para `main`; remoto `origin` = `git@github.com:Pedrogal-pathsolutions/pathsolutions-v3.git`, com `core.sshCommand` usando só a chave dedicada e o known_hosts dedicado (`StrictHostKeyChecking=yes`).
- 20:23:36 UTC: push da `main` (`git push -u origin main`, novo branch remoto). Conferência por hash: local `55f4fc8047a82fcbf25caa457e75ab4b587b02a8` = remoto `55f4fc8047a82fcbf25caa457e75ab4b587b02a8`. Passo 0 concluído.

## Antes de começar: processos Codex

- 20:23:46 UTC: listar e encerrar (SIGTERM) os processos `codex` do usuário `azureps` na VM1.
  - Resultado: 2 processos `codex` (PIDs 112274 e 112292) receberam SIGTERM; na conferência seguinte: nenhum processo codex.

## Passo 1: código

- 20:24:16 UTC: conferências só de leitura antes da tag (mudanças sem commit, stashes, bundle, deploy_pendente, ~/inference da VM2).
  - Resultado das conferências (contagens e caminhos de código):
    - `Pathsolutions_V2`: 0 stashes; 408 arquivos apagados só na árvore de trabalho (continuam nos commits); 7 itens não rastreados: `.claude/settings.json`, 4 pastas de skills em `.claude/skills/`, `.claude_legacy/` (411 arquivos, 14 MB) e `Migration/` (3 arquivos). HEAD `fix/audit-2026-09` `ec70dbf`; 12 branches locais, 1 tag.
    - `~/pathsolutions.bundle`: a única ref (`refs/heads/main`, `1316dec4f`) está contida em 13 refs locais.
    - `~/deploy_pendente`: 2 scripts fora do histórico (`01_fase0_tenant_gate.sh`, 2.336 B; `02_push_github.sh`, 194 B).
    - VM2 `~/inference`: os 24 arquivos de código estão no histórico (hash git). Dos 11 backups, 8 estão no histórico e 3 não (`docker-compose.gpu.yml.bak_rawaug`, `server.py.bak_bridge_20260628`, `docker-compose.gpu.yml.bak.20260704_malloc`). Há também 12 `.whl` (6 MiB).
    - Decisão pedida ao Pedro sobre o que guardar antes do push.
- 20:36:10 UTC: decisão do Pedro: guardar só código. Branch `legado-final/sobras` (`00c4232`, sobre `ec70dbf`) com 5 arquivos em `sobras/` (2 de `~/deploy_pendente`, 3 backups do `~/inference` da VM2), com varredura de segredos sem ocorrências. `.claude/`, `.claude_legacy/` e `Migration/` são descartados com a pasta. Tag `legado-final-2026-10-15` no HEAD e `git fetch --prune --no-tags origin`.
- 20:33 UTC: `git push origin --all` e `git push origin --tags`, sem força.
  - Resultado: 12 das 13 branches e as 2 tags (`legado-final-2026-10-15` em `ec70dbf`, `prod-snapshot-2026-09-15` em `30dcd00`) estão no remoto com hash idêntico ao local, conferido depois de `git fetch --prune --no-tags`.
  - A `fix/audit-2026-09-dev` foi recusada pelo GitHub: "refusing to allow a Personal Access Token to create or update workflow `.github/workflows/ci.yml` without `workflow` scope". Ela tem 2 commits sem cópia (`b72c65d`, `d20d347`, de 22/09/2026; 33 arquivos). Decisão pedida ao Pedro. A exclusão do `Pathsolutions_V2` e a revogação do token esperam essa decisão.
- 20:48:33 UTC: decisão do Pedro: publicar o conteúdo da `-dev` sem o arquivo de CI. Branch `legado-final/audit-dev` (`7f8efed`, um commit sobre `ec70dbf`, com as mensagens originais no corpo e o `ci.yml` em `sobras/github-workflows/`). `git push origin legado-final/audit-dev`; local = remoto (`7f8efed`). A árvore publicada é igual à da `-dev`, fora o workflow mudado de lugar. Passo 1 concluído do lado do push; o Pedro pode revogar o token.

## Passo 2: valores visuais

- 20:48:46 UTC: `docs/v3/referencia-visual.md` gravado (1.395 linhas, 12 seções), extraído só por leitura do código do legado (frontend e extensões), sem capturas e sem copiar CSS nem componentes; varredura sem CPF nem e-mail.

## Passo 3: storage account do legado

- 20:49:33 UTC: pedido ao Pedro para apagar a `stpathsolutionsblob001` pelo Portal (aguardando).

## Passo 4: parar e remover o legado (VM2 primeiro)

- 20:49:33 UTC: VM2, leitura da unit `hibou-inference.service` (só ExecStart/ExecStop/Restart/WorkingDirectory/User/Type) e da política de reinício dos containers.
  - Resultado: unit `Type=simple`, `ExecStart=docker compose -f docker-compose.gpu.yml up --no-build --remove-orphans`, `ExecStop=... down`, `Restart=on-failure`, sem drop-ins. Containers: 4 `unless-stopped` em execução e 3 `no` parados.
- 21:21:43 UTC: VM2, `sudo systemctl disable --now hibou-inference.service`.
  - Resultado: unit inactive/disabled; o `compose down` removeu os 4 containers ativos; restaram os 3 parados.
- 21:22:07 UTC: VM2, `docker rm hiesd_aug gchtid_aug pg_extract`.
  - Resultado: 0 containers na VM2.
- 21:22:28 UTC: VM2, `docker image prune -af` e `docker builder prune -af`.
  - Resultado: 0 imagens e 0 de cache de build; `/data` da VM2 de 224G (94%) para 181G (76%).
- 22:13:27 UTC: VM2, remoção de `/etc/systemd/system/hibou-inference.service`, `systemctl daemon-reload` e `systemctl reset-failed hibou-inference.service`.
  - Resultado: **não executado**. A VM2 foi desalocada pelo auto-shutdown das 19:00 de Brasília (deallocate de 22:01:26 a 22:01:38 UTC, aplicativo do Azure Lab Services) enquanto a ação aguardava confirmação; o ssh respondeu `No route to host`. Nada rodou na VM2 depois da ação anterior.
- 22:14 UTC: conferência do passo 3: a `stpathsolutionsblob001` ainda existe. A exclusão pelo Pedro está pendente.

## Interrupção em 15/10/2026

- 23:01:14 UTC: a VM1 foi desalocada pelo auto-shutdown das 20:00 de Brasília. A sessão caiu antes deste registro e do push. Nada além do registrado acima foi executado.
- 23:04:43 UTC: a VM1 foi ligada pelo Portal, por usuário.
- 23:07 UTC: retomada. A VM2 continua desalocada, e a `stpathsolutionsblob001` ainda existe.
- Situação dos passos:
  - concluídos: 0, Codex, 1 (falta o Pedro revogar o token) e 2;
  - pendente com o Pedro: passo 3;
  - passo 4 na VM2 parcial: falta remover o arquivo da unit e o `aznfs`;
  - passo 4 na VM1 e passos 5, 6 e 7: não iniciados.
- 23:09:53 UTC: `az vm start` da VM2, para terminar nela os passos 4 e 5 antes de tirá-la do runbook (passo 7); retomada prevista na skill.
  - Resultado: VM2 `VM running` às 23:11:42 UTC.
- 23:11:58 UTC: VM2, remoção de `/etc/systemd/system/hibou-inference.service`, `systemctl daemon-reload` e `systemctl reset-failed hibou-inference.service` (retomada da ação que não rodou às 22:13).
  - Resultado: arquivo da unit removido; 0 arquivos de unit `hibou-inference`; 0 units em falha. Antes da remoção, a unit estava inactive/disabled, com 0 containers e 0 imagens depois da partida.
- 23:12:17 UTC: VM2, simulação `apt-get -s remove aznfs` e busca de entradas de montagem NFS (`/etc/fstab`, units `.mount`/`.automount`).
  - Resultado: a simulação remove só o `aznfs` 3.0.15. Não há entrada NFS no `/etc/fstab`, nem unit `.mount`/`.automount`, nem montagem NFS ativa: não existe entrada de montagem para remover na VM2.
- 23:12:38 UTC: VM2, `sudo apt-get remove -y aznfs` (sem autoremove).
  - Resultado: `aznfs` removido (status `deinstall ok config-files`, sem purge); 0 units `aznfswatchdog`. Passo 4 na VM2 concluído: 0 containers, 0 imagens, 0 volumes, nenhuma unit nem crontab do legado.

## Passo 5: apagar os dados do legado (VM2 primeiro)

- 23:13:09 UTC: VM2, registro do estado do Docker e do containerd antes de apagar o `/data` (só leitura).
  - Resultado: Docker com raiz `/data/docker` (`daemon.json`), driver overlayfs, runtime padrão `nvidia`; containerd com `root = "/data/containerd"` no `config.toml` (caminho, não link); `/var/lib/docker` não existe; só `/dev/sda` montado em `/data`; 181G e 138.966 inodes usados (maiores: cyto 79G, wsi_stage 67G, hiesd 34G).
- 23:14:07 UTC: VM2, parar docker.socket/docker.service/containerd.service, `find /data -xdev -mindepth 1 -delete`, religar e conferir o `docker info`.
  - Resultado: `/data` da VM2 de 181G para 316K (0 itens antes de religar; o Docker recriou a raiz). docker e containerd ativos; `docker info`: raiz `/data/docker`, overlayfs, runtimes `io.containerd.runc.v2`, `nvidia` e `runc`, padrão `nvidia`.
- 23:14:22 UTC: VM2, `rm -rf /home/azureps/inference` (com o `.env`).
  - Resultado: `~/inference` removido (6,6 MB, 49 arquivos). Disco de SO da VM2 em 69%. Passos 4 e 5 concluídos na VM2.

## Passo 7: VM2 fora do runbook e desalocada (antecipado, porque só depende da VM2)

- 23:14:45 UTC: leitura do conteúdo publicado do runbook `TurnOn-VMs` (só leitura).
  - Resultado: a primeira tentativa não rodou, porque a pasta temporária da sessão sumiu no reinício da VM1; refeita em seguida. Runbook `PowerShell72`, `Published`, sem rascunho em edição, última edição em 16/06/2026. O script entra com a identidade gerenciada e liga com `Start-AzVM -NoWait` cada VM da lista fixa `$VMs` (linha 8), que tem a VM1 e a VM2. A agenda `TurnOn-VMs` não passa parâmetros: segunda a sexta, 06:00 `America/Sao_Paulo`, com a próxima execução em 16/10/2026 às 06:00 BRT. Arquivo em UTF-8 sem BOM, com CRLF.
- 23:23 UTC: VM2, estado final antes de desalocar (só leitura).
  - Resultado: `/` com 20G de 29G (69%); `/data` com 316K de 251G (1%). 0 containers, 0 imagens, 0 volumes, 0 de cache de build. Crontabs do `azureps` e do root sem linhas ativas; nenhuma unit com `hibou`, `inference`, `aznfs` ou `pathsol`; 0 units em falha; nenhum timer do legado. Driver NVIDIA 595.71.05 (Tesla T4) e `nvidia-container-toolkit` 1.19.0-1 instalados; docker e containerd ativos; `~/inference` ausente.
- 23:23:29 UTC: conferência do passo 3: a `stpathsolutionsblob001` ainda existe (`Succeeded`).
- 23:31:07 UTC: o modo de permissão automático está ativo nesta sessão, então os comandos podem rodar sem a confirmação que valia como autorização. A partir daqui, as autorizações são pedidas no chat. O Pedro autorizou no chat as ações 1 (runbook) e 2 (desalocar a VM2) do passo 7 e informou que revogou o token do GitHub.
- 23:31:07 UTC: runbook `TurnOn-VMs`: conferência de que o conteúdo publicado não mudou desde a leitura; envio do rascunho sem a VM2 com `curl --data-binary` (o `az rest` mandaria o corpo em Latin-1); conferência byte a byte e publicação (`POST .../publish`).
  - Resultado: rascunho aceito (HTTP 202), idêntico ao arquivo novo, e publicado às 23:31:10 UTC (`Published`). O conteúdo publicado, lido de novo, é idêntico byte a byte ao arquivo novo: a lista `$VMs` só tem a VM1. Fica pendente a conferência no job de 16/10, às 06:00 BRT.
- 16/10, 00:01:12 UTC: `az vm deallocate -g rg-prod-brsouth-001 -n vm-appfoundation-prod-001`.
  - Resultado: `VM deallocated` às 00:01:49 UTC. Passo 7 concluído na VM2, faltando conferir no job de 16/10, às 06:00 BRT, que só a VM1 foi ligada. A VM2 fica desalocada até a Fase 4. Daqui em diante, os horários são de 16/10/2026.
