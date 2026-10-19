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

## Retomada em 16/10/2026

- 16/10, 09:01 UTC: a VM1 religou pelo runbook. A sessão de 15/10 caiu durante uma leitura (inspeção dos volumes Docker da VM1), sem nenhuma ação em andamento.
- 16/10, 19:58 UTC: conferência do passo 7. O job `TurnOn-VMs` das 09:00:54 UTC terminou `Completed` e, no activity log das últimas 12 h, só aparece o start da VM1. A VM2 segue `VM deallocated`. Passo 7 concluído.
- 16/10, 20:03:38 UTC: autorização do Pedro no chat para as 7 ações do passo 4 na VM1, em sequência, sem pedido a cada uma. Se algo divergir, parar e perguntar: container, volume ou unit fora da lista, volume bind fora do `/data` ou qualquer erro. No passo 5, avaliar formatar o disco de dados em vez de apagar arquivo por arquivo. Se a raiz do Docker estiver no `/data`, as ações 2 (volumes) e 3 (imagens) podem ser puladas. O plano do passo 5 espera um "pode formatar" do Pedro. O Pedro está apagando a `stpathsolutionsblob001` (passo 3).
- 16/10, 20:09:45 UTC: VM1, leitura dos volumes (só leitura).
  - Resultado: 5 containers, todos do compose `pathsolutions_v2`; 8 volumes `local` sem opções de driver (6 `pathsolutions_v2_*` e 2 anônimos), todos em `/data/docker/volumes`, nenhum bind fora do `/data`. Binds dos containers: `/data/pathsolutions/*`, `/var/run/docker.sock` e dois caminhos de código em `/home/azureps/Pathsolutions_V2`. Raiz do Docker em `/data/docker` e do containerd em `/data/containerd` (link `/var/lib/containerd`): as ações 2 (volumes) e 3 (imagens) ficam para a formatação, como o Pedro autorizou.
- 16/10, 20:09:45 UTC: VM1, ação 4.1: `docker compose -p pathsolutions_v2 -f docker-compose.yml down --remove-orphans`.
  - Resultado: **erro, nada mudou.** O compose não recebeu as variáveis do legado (`ENTRADA_DIR`, `SAIDA_DIR`, `DATA_DIR`, `LOGS_DIR` e outras; o arquivo de variáveis não foi lido) e parou na validação: `invalid spec: :/path_solutions/entrada: empty section between colons` (rc=1). Continuam 5 containers, 1 rede do projeto, 8 volumes e 17 imagens. Parado para perguntar ao Pedro, pela regra de parar em qualquer erro.
- 16/10, 20:13:39 UTC: VM1, ação 4.1, segunda forma (escolha do Pedro): `docker compose -p pathsolutions_v2 down --remove-orphans`, sem o arquivo do compose.
  - Resultado: 5 containers e a rede do projeto removidos (rc=0), com 0 containers no fim. Volumes (8) e imagens (17) ficam para a formatação. Montagens sob `/data`: 1. Portas 3000/6379/8000 em escuta: 0.
- 16/10, 20:14:01 UTC: VM1, ação 4.4: `systemctl disable --now pathsolutions-backup.timer`, `stop` e `reset-failed` da service, remoção dos dois arquivos de `/etc/systemd/system` e `systemctl daemon-reload`.
  - Resultado: 0 unit files `pathsolutions-backup`, 0 arquivos ou links em `/etc/systemd/system` e nenhuma das duas em falha.
- 16/10, 20:14:02 UTC: VM1, ação 4.5: remoção da linha `@reboot` do backup no crontab do `azureps`.
  - Resultado: **erro.** o crontab não aceitou o arquivo novo. Parado para perguntar ao Pedro.
  - Observações: na ação 4.4, o `reset-failed` respondeu "Unit ... not loaded" para as duas units, que o systemd já tinha descarregado depois do `stop`; nenhuma estava em falha. Na ação 4.5, o `crontab <arquivo>` truncou o caminho longo do arquivo temporário (mais de 100 caracteres) e não aplicou nada: o crontab continua idêntico ao de antes, com a linha `@reboot`. Parado para perguntar ao Pedro.
- 16/10, 20:15:17 UTC: VM1, ação 4.5, retomada com autorização do Pedro: `crontab -` lendo da entrada padrão o crontab sem a linha `@reboot` do backup.
  - Resultado: 0 linhas ativas no crontab do `azureps` (ficam 0 linhas de comentário).
- 16/10, 20:15:17 UTC: VM1, ação 4.6: `systemctl disable --now nginx.service certbot.timer`, sem desinstalar.
  - Resultado: nginx disabled/inactive; certbot.timer disabled/inactive. Portas 80/443 sem escuta. Pacotes, configuração, certificado e os logs em `/var/log/nginx` ficam.
- 16/10, 20:15:18 UTC: VM1, ação 4.7: simulação e `apt-get remove -y aznfs` (sem autoremove).
  - Resultado: `aznfs` removido (status `deinstall ok config-files`, sem purge). 0 units `aznfs`. `/etc/fstab` com 0 entradas NFS e 0 montagens NFS ativas: nenhuma entrada de montagem a remover. Passo 4 na VM1 concluído; as ações 2 e 3 ficam cobertas pela formatação do passo 5.

## Passo 5 na VM1: levantamento (só leitura)

- 16/10, 20:03 UTC: disco de dados. O `/data` é o `/dev/sda` (LUN 0, `/dev/disk/azure/scsi1/lun0`), com 512G, ext4 no disco inteiro, rótulo `data` e UUID `3afbd359-2c66-4644-ba14-cbdf5cd8ebb9`. O disco de SO hoje é o `sdb`; em 14/10 os nomes estavam trocados. Linha do fstab: `UUID=3afbd359-… /data ext4 defaults,nofail,discard 0 2`. O `daemon.json` tem `data-root` em `/data/docker`; `/var/lib/docker` não existe; `/var/lib/containerd` é link para `/data/containerd` (root:root 700), o único link do disco de SO para o `/data`. Donos nos 2 primeiros níveis do `/data`: uid 999, `azureps` e root.
- 16/10, 20:17:39 UTC: disco de SO. Em uso: `/` com 22G de 29G (77%) e `/data` com 477G de 503G (100%).
  - `~/.git-credentials`: 1 linha, `https://github.com`, com usuário de 22 caracteres. Credential helper global: `store`.
  - `~/.gemini/projects.json` liga `/home/azureps/Pathsolutions_V2` a `pathsolutions-v2`. Histórico: `tmp/pathsolutions-v2` com 760K e `history/pathsolutions-v2` com 184K. Fora do pedido: `antigravity` (468K), `antigravity-ide` (23M), `oauth_creds.json` (1.732 B), `google_accounts.json` (68 B), `config` e `installation_id`.
  - `~/Pathsolutions_V2`: 238M.
  - `/mount/stpathsolutionsdata001`: não montado, mas com 6,7G gravados no disco de SO: 158 arquivos de maio de 2026 (17 `.svs`, 62 `.npy` e 79 `.json`), em 3 pastas.
  - Fora da lista:
    - `~/pathsolutions.bundle` (6,5M): o único head, `1316dec4`, está em 13 branches do remoto.
    - `~/deploy_pendente`: os 2 scripts estão em `origin/legado-final/sobras`, conferidos por hash git.
    - `~/micra` e `/mnt/pathsolutions`: 2 pastas vazias cada, sem arquivos.
- 16/10, 20:39 UTC: revisão independente do plano do passo 5 (3 revisores, só leitura): nenhum bloqueador. Entraram no plano:
  - travas por lun0, by-lun/0, tamanho, disco do `/` e data de criação do fs;
  - porta dura depois do `mount -a`;
  - `sudo` nas conferências;
  - corte às 22:15 UTC;
  - `sudo rm` no `Pathsolutions_V2`, que tem entradas de root.
  Achados da revisão:
  - uma janela do Antigravity tem 4 processos com cwd em `~/Pathsolutions_V2`, desde as 19:57, entre eles um segundo Claude Code;
  - o socket do Docker estava com o grupo `systemd-journal`, e não `docker`, e um container do legado montava `/var/run/docker.sock`;
  - o `docker info` mostra que as imagens ficam no containerd (snapshotter), cuja raiz também está no `/data`.
- 16/10, 20:49:53 UTC: decisões do Pedro no chat:
  - "Pode formatar, mesmo UUID": `mkfs.ext4 -U` com o UUID atual, sem editar o fstab.
  - Sobras a apagar no mesmo passo: bundle e `deploy_pendente`; rastros no disco de SO (`~/.azcopy`, o cache do claude-cli e o `/tmp` do `Pathsolutions_V2`, `~/.docker/buildx`, `/root/.docker`, o alias `dcv` do `~/.bashrc` e a entrada `pathsolutions-v2` do `projects.json` do Gemini); o conteúdo de `/var/log/nginx`, mantendo a pasta.
  - Sensíveis a apagar: `/root/.azure`, as transcrições do legado em `~/.claude/projects` (`-home-azureps-Pathsolutions-V2` e `-home-paths-Pathsolutions-V2`) e o resto do `~/.gemini` (`antigravity`, `antigravity-ide`, `oauth_creds.json` e `google_accounts.json`).
  - Ficam: `~/micra` e `/mnt/pathsolutions`.
- 16/10, 20:49:53 UTC: VM1, passo 5.1: registro antes de parar (só leitura).
  - Resultado: `docker info` = `/data/docker|overlayfs|[["driver-type","io.containerd.snapshotter.v1"]]|io.containerd.runc.v2,runc,|runc`; 17 imagens, 8 volumes, 0 containers. `daemon.json` = `{"data-root": "/data/docker"}`. containerd: `17:#root = "/var/lib/containerd"`. Link: '/var/lib/containerd' -> '/data/containerd' (destino root:root 700). Dono do `/data`: azureps:azureps 755. df:/ 29G 22G 6.7G 77%;/data 503G 477G 750M 100%;
- 16/10, 20:49:53 UTC: VM1, passo 5.2: `systemctl stop docker.socket docker.service containerd.service` e `systemctl mask --runtime` das três.
  - Resultado: as três units estão paradas e mascaradas em runtime. Nenhum processo usa o `/data` (`fuser`), e não há submontagens.
- 16/10, 20:49:54 UTC: VM1, passo 5.3: travas do disco-alvo (só leitura).
  - Resultado: alvo `/dev/sda`, que é lun0, by-lun/0 e a origem do `/data`. O disco do `/` é `/dev/sdb`. São 549.755.813.888 bytes, sem partições; UUID e data de criação (Tue May 5 00:28:20 2026) conferem.
- 16/10, 20:49:54 UTC: VM1, passo 5.4: `umount /data`.
  - Resultado: `/data` desmontado, sem nenhuma montagem de 8:0 em namespace algum. O ponto de montagem no disco de SO está vazio, e as três units continuam paradas.
- 16/10, 20:50:13 UTC: VM1, passo 5.5: `mkfs.ext4 -F -L data -U 3afbd359-2c66-4644-ba14-cbdf5cd8ebb9 -E root_owner=1000:1000 /dev/sda`, com o mesmo UUID (decisão do Pedro) e TRIM do disco inteiro, padrão do mkfs.
  - Resultado: mkfs concluído em 7 s (rc=0): Discarding device blocks: 0/134217728 done  Creating journal (262144 blocks): done Writing superblocks and filesystem accounting information: 0/4096 4/4096 done 
- 16/10, 20:50:20 UTC: VM1, passo 5.6: `udevadm settle`, `findmnt --verify --verbose`, `mount -a` e porta dura. O fstab não muda, porque o UUID é o mesmo.
  - Resultado: **parado.** findmnt --verify acusou erros:    [ ] FS type is ext4. Aguardando o Pedro.
  - Diagnóstico (21:02:19 UTC, só leitura): falso positivo da conferência do script. O resumo do `findmnt --verify` ("0 parse errors, 0 errors, 1 warning", rc=0) sai pelo stderr e apareceu no começo da saída, e o script esperava encontrá-lo na última linha. O único aviso é do `/swapfile` ("non-bind mount source /swapfile is a directory or regular file"), sem relação com o `/data`. A seção do `/data` não tem [E] nem [W]. Estado: `/dev/sda` formatado (UUID `3afbd359-…`, rótulo `data`, criado em 16/10/2026 às 20:50:13), mas **não montado**. Docker e containerd estão parados e mascarados em runtime. Pergunta ao Pedro: retomar do `mount -a`.
- 16/10, 21:05:08 UTC: decisão do Pedro: parar aqui. O passo 5 da VM1 fica parcial.

## Situação ao fim da sessão de 16/10

- Concluídos: passos 0, 1 e 2; passo 4 nas duas VMs; passo 5 na VM2; passo 7.
- Passo 3: pendente com o Pedro. A conferência das 21:05:08 UTC deu: `Succeeded`.
- Passo 5 na VM1: parcial.
  - Feito: 5.1 a 5.5 (registro, parada, travas, `umount` e `mkfs` com o mesmo UUID). O `/dev/sda` está formatado (criado em 16/10/2026 às 20:50:13 UTC) e **desmontado**. `docker.socket`, `docker.service` e `containerd.service` estão parados e mascarados em runtime; a máscara some no próximo boot.
  - Falta:
    - 5.6: `findmnt --verify`, conferindo o resumo do stderr ("0 errors") e nenhum [E] ou [W] no `/data`; depois `mount -a` e a porta dura.
    - 5.7: `/data/containerd` com modo 700 e `/data/docker` com 710.
    - 5.8: unmask, religar e comparar o `docker info` com o registro do 5.1.
    - Item 9: disco de SO e as sobras decididas pelo Pedro às 20:4x.
    - `git config --global --unset credential.helper`.
    - `df -h` final.
- Passo 6 (órfãos no Azure): não iniciado.
- Próximo boot: o auto-shutdown desaloca a VM1 hoje às 23:00 UTC, e o runbook a liga na segunda, 19/10, às 09:00 UTC.
  - O fstab, com o mesmo UUID e `nofail`, deve montar o `/data` novo e vazio.
  - O containerd deve falhar ao subir, porque `/var/lib/containerd` aponta para `/data/containerd`, que não existe no fs novo. O Docker depende dele.
  - As duas coisas são inferência, não testada. Nada que rode na VM1 depende do Docker.
- Primeira ação da próxima sessão, só leitura:
  - `findmnt /data`;
  - `sudo tune2fs -l /dev/disk/azure/scsi1/lun0 | grep created`, que deve dar 16/10/2026 às 20:50:13;
  - `systemctl is-active containerd docker`.
  Depois, retomar do 5.6 com autorização do Pedro. Se o `/data` estiver montado, o `mount -a` não muda nada, e a porta dura vale do mesmo jeito.

## Retomada em 19/10/2026

- 19/10, 09:02:11 UTC: a VM1 religou pelo runbook (job `TurnOn-VMs` das 09:01:31 às 09:01:51 UTC, `Completed`). A VM2 continua `VM deallocated`. O auto-shutdown da VM1 continua `Enabled`, às 20:00 de Brasília (23:00 UTC).
- 19/10, 18:52 UTC, sessão à parte, a pedido do Pedro: as 4 skills externas foram extraídas do `skills-externas.zip` para `.claude/skills/`, o zip foi apagado, e a seção "Skills externas" entrou no `CLAUDE.md`. Commit `9585e59`, no remoto. Não faz parte do desligamento.
- 19/10, 19:09:25 UTC: item 1, só leitura: `findmnt /data`, estado de `docker` e `containerd`, `sudo docker info`.
  - Resultado:
    - O `/data` montou às 09:02:19 (`data.mount` ativa), antes do `docker.socket` (09:02:27) e das primeiras partidas do containerd (09:02:29) e do docker (09:02:30). Origem: a lun0, que hoje é o `/dev/sdb`; o disco do `/` hoje é o `/dev/sda`, o contrário de 16/10. UUID `3afbd359-…`, rótulo `data`, fs criado em 16/10/2026 às 20:50:13, estado `clean`, 1 montagem.
    - O containerd está em laço de falha desde o boot, com `containerd: mkdir /var/lib/containerd: file exists`: o link aponta para `/data/containerd`, que não existe no fs novo. Foram 6.936 reinícios até 19:09. O docker também está em laço: espera 1 min pelo containerd e cai com `failed to start daemon: failed to get containerd plugins`. Foram 578 reinícios até 19:09. A previsão de 16/10 era inferência; agora está confirmada.
    - `sudo docker info`: sem resposta em 20 s (rc=124).
    - O `/data` não está vazio. Além do `lost+found`, tem o esqueleto que o dockerd cria a cada tentativa, em `/data/docker` (root:root 710): 11 entradas, 2 arquivos (`engine-id` e `volumes/metadata.db`, 32.804 bytes) e 1 nó de bloco (`volumes/backingFsBlockDev`); 0 containers, 0 volumes e 0 imagens. `df`: `/data` com 84K de 503G; `/` com 22G de 29G (78%).
    - Socket do Docker hoje: `root:docker 660` (`SocketGroup=docker`). Em 16/10, estava com o grupo `systemd-journal`.
    - Journal: 560,3M.
  - Divergência do registrado: a previsão de 16/10 era um `/data` "novo e vazio", e a porta dura do 5.6 exigia só `lost+found`. O que há a mais é o esqueleto do dockerd. Pergunta ao Pedro.
- 19/10, 19:16:55 UTC: processos, só leitura. Há 0 processos com cwd em `~/Pathsolutions_V2` e 0 arquivos abertos nele. Esta sessão roda no servidor do Antigravity, na janela aberta em `~/pathsolutions-v3` às 18:50. São 14 processos, entre eles 1 `codex` da extensão ChatGPT, iniciado às 18:51, com cwd `/home/azureps`.
- 19/10, 19:18 UTC: inventário do item 9, só leitura (tamanho, dono, data mais nova e arquivos abertos):
  - base:
    - `~/Pathsolutions_V2`: 238M, 15.960 entradas, mais nova de 16/10 20:17;
    - `/mount`: só tem `stpathsolutionsdata001`, com 6,7G e 162 entradas, de 02/06 ou antes, no disco de SO;
    - `~/.git-credentials`: 1 linha, host `https://github.com`;
    - Gemini `pathsolutions-v2`: `tmp` com 760K e `history` com 184K, de 16/09. O `projects.json` liga `/home/azureps/Pathsolutions_V2` a `pathsolutions-v2`, e é a única entrada;
    - `credential.helper` global: `store`.
  - sobras:
    - `~/pathsolutions.bundle`: 6,5M;
    - `~/deploy_pendente`: 12K;
    - `~/.azcopy`: 20K;
    - `~/.cache/claude-cli-nodejs/-home-azureps-Pathsolutions-V2`: 3,5M;
    - `~/.docker/buildx`: 364K;
    - `/root/.docker`: 576K;
    - `/var/log/nginx`: 30 arquivos, 832K, rotacionados pelo logrotate no boot das 09:02; o nginx continua inactive/disabled;
    - o alias `dcv` na linha 120 do `~/.bashrc`;
    - o `/tmp/claude-1000/-home-azureps-Pathsolutions-V2` não existe mais, porque o `/tmp` foi limpo no reinício.
  - sensíveis:
    - `/root/.azure`: 152K;
    - `~/.claude/projects/-home-azureps-Pathsolutions-V2`: 88M, mais nova de 16/10 20:45;
    - `~/.claude/projects/-home-paths-Pathsolutions-V2`: vazia;
    - `~/.gemini/antigravity`: 468K, de maio;
    - `~/.gemini/antigravity-ide`: 23M;
    - `oauth_creds.json` e `google_accounts.json`: de 15/09.
  - Divergência do registrado: em 16/10, o `antigravity-ide` constava como de 15/09. Hoje, às 18:51 e 18:52, o language server da janela atual do Antigravity gravou nele (`crashes/` e `implicit/`), e tem 1 arquivo aberto. O resto (`conversations`, `brain`, `knowledge` e outros) é de maio a setembro. Pergunta ao Pedro.
- 19/10, 19:21 UTC: Azure, só leitura. Subscrição `bd87a1ca-…` confirmada. O grupo `rg-prod-brsouth-001` tem 27 recursos, os mesmos da Fase 0, e não há locks.
  - Órfãos:
    - `pe-stpathsolutionsdata001-file`: `Succeeded`, conexão `Disconnected` com a `stpathsolutionsdata001`, que não existe (`ResourceNotFound`). Tem 1 NIC (`…nic.9b6d5aa7…`, 10.0.0.6, sem VM) e nenhum dns-zone-group. É o único private endpoint da subscrição.
    - `privatelink.file.core.windows.net`: 2 registros, o SOA e um A `stpathsolutionsdata001` → 10.0.0.6, o IP da NIC do endpoint. Tem 1 link, `axi3rxmfnch4o`, com a `vnet-prod-brsouth-001`, sem autorregistro. É a única zona DNS privada.
    - Runbooks `AzureAutomationTutorialWithIdentity` e `…Graphical`: `Published` desde 16/06/2026, sem agenda, sem webhook e sem job (os 21 jobs da conta são do `TurnOn-VMs`).
    - `azurevm` (`Microsoft.Web/connections`): `Error` desde a criação, em 13/06/2026. É a única API connection, e a subscrição tem 0 Logic Apps.
  - Passo 3: a `stpathsolutionsblob001` ainda existe (`Succeeded`, às 19:23).
- 19/10, 20:43:48 UTC: decisões do Pedro no chat:
  - porta dura do 5.6: aceitar o `lost+found` vazio e o esqueleto exato do dockerd em `/data/docker`; qualquer outra coisa no `/data` para o script;
  - `~/.gemini/antigravity-ide`: fica hoje. Saem os outros três itens do resto do `~/.gemini` (`antigravity`, `oauth_creds.json` e `google_accounts.json`);
  - o `codex` da extensão ChatGPT da janela atual continua rodando, e o fato vai para o relatório.
- 19/10, 20:43:48 UTC: os scripts dos itens 2, 3 e 5 de hoje estão em revisão independente, só leitura, com 3 revisores. As portas de leitura dos três já foram testadas contra o estado real. O teste pegou um falso positivo no 6.2 (`False` em vez de `false`), já corrigido.
- 19/10, 20:47:01 UTC: correção do registro de 15/10: o push do passo 1 (`git push origin --all` e `--tags`) rodou às 20:36:17 UTC, depois da decisão das 20:36:10, e não às 20:33, como está na linha de 15/10. A fonte é o horário da chamada na transcrição daquela sessão.
- 19/10, 20:48:25 UTC: VM1, passo 5.2 de novo, como prevê a retomada da skill: `systemctl stop docker.socket docker.service containerd.service` e `systemctl mask --runtime` das três.
  - Resultado: docker.socket=inactive docker.service=failed containerd.service=inactive ; as três estão mascaradas em runtime. Nenhum processo usa o `/data`, e não há submontagens.
- 19/10, 20:49:05 UTC: VM1, passo 5.6: `udevadm settle`, `findmnt --verify --verbose`, `mount -a` e porta dura (modo `aceitar`). Leitura corrigida: rc=0, resumo "Success" ou "0 parse errors, 0 errors", e nenhum [E] ou [W] na seção do `/data`.
  - Resultado: `findmnt --verify`: '0 parse errors, 0 errors, 1 warning' (rc=0), sem [E] nem [W] no `/data`; avisos fora dele:  [W] non-bind mount source /swapfile is a directory or regular file;. O `mount -a` não mudou nada. Porta dura: `/dev/sdb` (lun0) no `/data`, UUID esperado, `data.mount` ativa, fs de Fri Oct 16 20:50:13 2026, 1 MB usados, só o `lost+found` vazio e o esqueleto do dockerd em `/data/docker`, sem containers, imagens nem volumes.
- 19/10, 20:49:05 UTC: VM1, passo 5.7: `install -d -o root -g root -m 700 /data/containerd` e `install -d -o root -g root -m 710 /data/docker`.
  - Resultado: /data/containerd root:root 700;/data/docker root:root 710; o link `/var/lib/containerd` → `/data/containerd` resolve para `/dev/sdb`.
- 19/10, 20:49:05 UTC: VM1, passo 5.8: `systemctl unmask --runtime`, `reset-failed` e `start` de containerd.service, docker.socket e docker.service; `sudo docker info` comparado com o registro do 5.1.
  - Resultado: as três units estão ativas, e o `docker info` saiu igual ao do 5.1 (`/data/docker|overlayfs|[["driver-type","io.containerd.snapshotter.v1"]]|io.containerd.runc.v2,runc,|runc`). 0 containers, 0 imagens e 0 volumes. `/data/containerd` com 10 entradas criadas pelo containerd. Socket `root:docker 660`. df:/ 29G 22G 6.2G 78%;/data 503G 316K 478G 1%; Passo 5 do `/data` na VM1 concluído.
- 19/10, 21:18:10 UTC: resultado da revisão independente (3 revisores, só leitura, de 20:40 a 21:11):
  - Passo 5: o 5.2 a 5.8 rodou de 20:48:25 a 20:49:07, antes do fim da revisão. Foi decisão minha, porque o modo `aceitar` não apaga nada. A conferência feita depois não achou problema. Efeitos fora do `/data`:
    - o `daemon-reload` do `mask` disparou o `apt-daily` (de 20:49:05 a 20:49:06), sem pacote alterado: o `dpkg.log` não tem linha de 19/10;
    - o dockerd criou a interface `docker0` (DOWN) e ligou o `ip_forward`, que é o padrão do Docker.
    - O "`mount -a` não mudou nada" tem esta evidência: o fstab já estava todo montado, e o journal não tem evento de montagem entre 20:49:05.717 e 20:49:05.741.
  - Item 9: sem bloqueador. A revisão achou uma divergência do registrado: `~/.claude/projects/-home-paths-Pathsolutions-V2` não está vazia, como registrei às 19:18; tem um link `memory` → `~/pathsolutions-claude-context/memory`. Achou também o comentário `# Atalho PathSolutions` na linha 119 do `~/.bashrc`, logo acima do alias. Entraram no script mais portas:
    - itens que ficam, inclusive os destinos dos links;
    - arquivos abertos em todos os alvos;
    - `nginx` disabled;
    - `sudo -n` funcionando;
    - stderr das exclusões de pastas com lâminas fora da transcrição.
  - Passo 6: sem bloqueador. Ajustes:
    - pausa de 10 s entre releituras do ARM;
    - contagem final: ficam 19 recursos, mais a storage account do passo 3 enquanto ela existir;
    - conferência da agenda do `TurnOn-VMs` e da sub-rede depois das exclusões;
    - nomes comparados sem diferença de caixa;
    - execução com limite de 10 min.
- 19/10, 21:18:10 UTC: decisões do Pedro no chat:
  - apagar a pasta `-home-paths-Pathsolutions-V2` com o link; o destino fica, conferido antes e depois;
  - tirar do `~/.bashrc` as linhas 119 (comentário) e 120 (alias `dcv`).
- 19/10, 21:19:52 UTC: VM1, item 9: pré-condições, só leitura.
  - Resultado: os 29 itens que ficam existem. 0 processos com cwd em `~/Pathsolutions_V2` e 0 arquivos abertos nos 18 alvos (o `antigravity-ide` fica de fora e fica). O head do bundle (`1316dec4f`) está em 13 branches do remoto, e os 2 scripts do `deploy_pendente` estão em `origin/legado-final/sobras` (hash git). `.git-credentials`: 1 linha, `https://github.com`. nginx inactive/disabled. O `/tmp` do `Pathsolutions_V2` não existe. df antes: / 29G 22G 6.2G 78%.
- 19/10, 21:19:56 UTC: VM1, item 9.1: `sudo rm -rf --one-file-system /home/azureps/Pathsolutions_V2` (238M).
  - Resultado: removido.
- 19/10, 21:19:56 UTC: VM1, item 9.2: `sudo rm -rf --one-file-system /mount/stpathsolutionsdata001` e `sudo rmdir /mount` (6.7G: 79 .json, 62 .npy, 17 .svs; dados do legado, de maio e junho, sem exportação).
  - Resultado: `/mount` removido.
- 19/10, 21:19:56 UTC: VM1, item 9.3: `rm ~/.git-credentials` (1 linha, `https://github.com`; o Pedro revogou o token em 15/10).
  - Resultado: removido.
- 19/10, 21:19:56 UTC: VM1, item 9.4: `rm -rf ~/.gemini/tmp/pathsolutions-v2 ~/.gemini/history/pathsolutions-v2` (760K e 184K).
  - Resultado: removidos.
- 19/10, 21:19:57 UTC: VM1, item 9.5, ação separada: `git config --global --unset credential.helper` (era `store`).
  - Resultado: sem `credential.helper` global nem de sistema; a próxima credencial por HTTPS não é gravada em texto puro.
- 19/10, 21:19:57 UTC: VM1, item 9.6 (sobras): `rm ~/pathsolutions.bundle` (6.5M) e `rm -rf ~/deploy_pendente` (12K).
  - Resultado: removidos.
- 19/10, 21:19:57 UTC: VM1, item 9.7 (rastros): `rm -rf ~/.azcopy ~/.cache/claude-cli-nodejs/-home-azureps-Pathsolutions-V2 ~/.docker/buildx`, `sudo rm -rf /root/.docker`, as linhas 119 (`# Atalho PathSolutions`) e 120 (alias `dcv`) do `~/.bashrc` e a entrada `pathsolutions-v2` do `~/.gemini/projects.json`.
  - Resultado: removidos. O `~/.bashrc` ficou com 118 linhas, sem `dcv` e com sintaxe válida (`bash -n`); o `projects.json` ficou com `{"projects": {}}`.
- 19/10, 21:19:57 UTC: VM1, item 9.8: `sudo find /var/log/nginx -xdev -mindepth 1 -delete` (30 arquivos, 832K), mantendo a pasta. O nginx continua inactive/disabled.
  - Resultado: pasta vazia, `root:adm 755`.
- 19/10, 21:19:57 UTC: VM1, item 9.9 (sensíveis): `sudo rm -rf /root/.azure` (152K); `rm -rf ~/.claude/projects/-home-azureps-Pathsolutions-V2` (88M) e `~/.claude/projects/-home-paths-Pathsolutions-V2` (só o link `memory` → `~/pathsolutions-claude-context/memory`; o destino fica); `rm -rf ~/.gemini/antigravity` (468K); `rm ~/.gemini/oauth_creds.json ~/.gemini/google_accounts.json`; o `~/.gemini/antigravity-ide` fica, por decisão do Pedro em 19/10.
  - Resultado: removidos; `antigravity-ide` mantido.
- 19/10, 21:19:58 UTC: VM1, fim do item 9: os itens que ficam continuam lá. Erros das exclusões: 0. df do `/`: antes / 29G 22G 6.2G 78%; depois / 29G 15G 14G 53%.
- 19/10, 21:22:09 UTC: VM1, item 10: df antes e depois e estado final (só leitura).
  - df: em 16/10 às 20:49 (antes do passo 5), `/` com 22G de 29G (77%) e `/data` com 477G de 503G (100%). Agora, `/` com 15G de 29G (53%) e `/data` com 332K de 503G (1%).
  - Docker: 0 containers, 0 imagens, 0 volumes e 0 de cache de build. containerd, `docker.socket` e docker estão active/enabled, com 0 reinícios desde a religação. O socket está `root:docker 660`.
  - Legado: 0 unit files com `pathsol`, `hibou`, `inference`, `aznfs` ou `legado`; 0 units em falha. O único timer que casa com `backup` é o `dpkg-db-backup.timer`, do Ubuntu. Crontabs do `azureps` e do root com 0 linhas ativas. nginx e `certbot.timer` estão inactive/disabled, com os pacotes instalados; o `aznfs` está em `deinstall ok config-files`. Nenhuma pasta do legado no disco de SO, e `credential.helper` vazio.
  - Portas TCP em escuta:
    - 22 (sshd);
    - 53 (systemd-resolved, só local);
    - 111 (`rpcbind`, em todas as interfaces; o pacote é de 05/05/2026);
    - portas altas só em 127.0.0.1, do servidor e do language server do Antigravity.
    - No NSG, a 111 não tem regra de entrada vinda da Internet.
  - O NSG tem 3 regras de entrada só do legado: 8001, 6379 e 5432, entre as VMs. Tem também 80 e 443 abertas para qualquer origem, mas nada escuta nelas.
  - Journal: 568,3M.
- 19/10, 21:22:09 UTC: passo 5 concluído na VM1. Commit e push deste registro.
- 19/10, 21:25:32 UTC: passo 6, conferência inicial (só leitura): subscrição `bd87a1ca…` ativa; `az resource list` do grupo comparado com os 27 recursos das 19:21.
  - Resultado: iguais; a `stpathsolutionsblob001`, do passo 3, fica fora da comparação (1 storage account no grupo). Sub-rede `default` com o NSG `nsg-app-prod-001` e 3 configurações de IP (as 2 VMs e o endpoint).
- 19/10, 21:25:39 UTC: passo 6.1: `az network private-endpoint delete -g rg-prod-brsouth-001 -n pe-stpathsolutionsdata001-file` (`Disconnected`; a conta-alvo não existe). A NIC `pe-stpathsolutionsdata001-file.nic.9b6d5aa7-f952-4d24-83ea-53bae3c1c8f8` sai junto.
  - Resultado: private endpoint e NIC excluídos (`show` dos dois: NotFound). A sub-rede `default` continua com o NSG e ficou com 2 configurações de IP, as das VMs. `az resource list` sem os dois e sem nenhuma outra mudança.
- 19/10, 21:26:19 UTC: passo 6.2: `az network private-dns link vnet delete -g rg-prod-brsouth-001 -z privatelink.file.core.windows.net -n axi3rxmfnch4o --yes`.
  - Resultado: link excluído; `az resource list` sem ele e sem nenhuma outra mudança.
- 19/10, 21:26:56 UTC: passo 6.3: `az network private-dns zone delete -g rg-prod-brsouth-001 -n privatelink.file.core.windows.net --yes` (registros: SOA e A `stpathsolutionsdata001` → 10.0.0.6, que saem com a zona).
  - Resultado: zona excluída; `az resource list` sem ela e sem nenhuma outra mudança.
- 19/10, 21:27:34 UTC: passo 6.4: `az automation runbook delete -g rg-prod-brsouth-001 --automation-account-name asa-prod-brsouth-001 -n <runbook> --yes` para `AzureAutomationTutorialWithIdentity` e `AzureAutomationTutorialWithIdentityGraphical` (sem agenda, sem job e sem webhook).
  - Resultado: os 2 runbooks excluídos. O `TurnOn-VMs` continua `Published`, ligado à agenda `TurnOn-VMs`, que continua ativa. `az resource list` sem os dois e sem nenhuma outra mudança.
- 19/10, 21:27:47 UTC: passo 6.5: `az resource delete -g rg-prod-brsouth-001 -n azurevm --resource-type Microsoft.Web/connections` (`Error`; 0 Logic Apps).
  - Resultado: API connection excluída. O grupo ficou com 20 recursos: os 19 que ficam e a `stpathsolutionsblob001`, do passo 3.
- 19/10, 21:28:07 UTC: conferência do passo 3: `az storage account show -n stpathsolutionsblob001 -g rg-prod-brsouth-001` e `az resource list --resource-type Microsoft.Storage/storageAccounts`.
  - Resultado: a `stpathsolutionsblob001` ainda existe (rc=0, `Succeeded`, criada em 27/05/2026). É a única storage account da subscrição. O passo 3 continua pendente com o Pedro.
  - Recursos no fim do dia: 20 no grupo `rg-prod-brsouth-001` e o `NetworkWatcher_brazilsouth` no `NetworkWatcherRG`. No grupo ficam:
    - a conta de automação com o runbook `TurnOn-VMs`;
    - as 2 VMs, os 4 discos, as 2 extensões e a chave SSH;
    - os 2 agendamentos de auto-shutdown;
    - as 2 NICs das VMs, o NSG, os 2 IPs públicos e a VNet;
    - a `stpathsolutionsblob001`.
- 19/10, 21:28 UTC: correção sobre a espera da tarde. Das 19:26 às 20:31, a sessão ficou parada esperando a aprovação de um comando só de leitura (fstab, units e a conferência do bundle). A revisão independente começou às 20:40:00, sem espera.
