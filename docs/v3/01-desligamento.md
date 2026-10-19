# Fase 1 — Desligamento do legado

Relatório da Fase 1 do `PROMPT_V3.md`, executada de 15 a 19/10/2026 com a skill `pathsol-desligamento-legado`. Cada ação tem comando, horário (UTC) e saída resumida no registro `docs/operacao/2026-10-15-desligamento.md`. Este relatório resume o registro e aponta para ele. Lâminas e pastas por caso aparecem só como contagens, sem nenhum dado de paciente.

Não houve snapshots (decisão do Pedro em 15/10/2026). O que foi apagado não tem volta, exceto o código, que está no GitHub com tag (seção 3).

## 1. Resumo

| Passo | Situação |
|---|---|
| 0. Repositório da v3 no GitHub | concluído em 15/10 |
| Processos Codex | os 2 da época foram encerrados em 15/10. Em 19/10 apareceu 1 novo, da extensão ChatGPT, que ficou por decisão do Pedro |
| 1. Código: tag e push | concluído em 15/10; o Pedro informou que revogou o token (não verificado, seção 8) |
| 2. Valores visuais | concluído em 15/10, em `docs/v3/referencia-visual.md` |
| 3. `stpathsolutionsblob001` | concluído em 19/10: o Pedro apagou a conta pelo terminal às 22:02, e a conferência das 22:05 deu `ResourceNotFound` (seção 11). A exclusão informada em 16/10 não tinha chegado ao Azure |
| 4. Parar e remover o legado | concluído: VM2 em 15/10, VM1 em 16/10 |
| 5. Dados do legado | concluído: VM2 em 15/10; VM1 com o `mkfs` em 16/10 e o resto em 19/10. Por decisão do Pedro, ficou o `~/.gemini/antigravity-ide`, usado pela janela atual do Antigravity |
| 6. Órfãos no Azure | concluído em 19/10, com 7 recursos excluídos |
| 7. VM2 fora do runbook e desalocada | concluído em 15 e 16/10, conferido nos jobs de 16 e 19/10 |

- **VM1:**
  - o `/data` foi de 477G para 332K;
  - o disco de SO foi de 22G (78%) para 15G (53%);
  - o Docker está de pé e vazio, com a mesma configuração de antes.
- **VM2:** está desalocada desde 16/10. Na última leitura, em 15/10 às 23:23, o `/data` tinha 316K, sem dados do legado; não foi relido depois (seção 8).
- **Economia estimada:** ~R$ 1,44 mil a ~R$ 1,63 mil por mês, já com a storage account apagada (seção 6).
- **Passo 3:** concluído em 19/10 às 22:02, depois da entrega deste relatório (seção 11).
- **Fato novo:** em 16/10, das 14:00 às 15:59 de Brasília, com o legado ainda no ar, a conta recebeu envios por SAS: 9 uploads em blocos e 9 diretos, com +6,6 GiB (achado 12).
- **Decisões pedidas:** seção 10. As respostas do Pedro e a aprovação estão na seção 11.

## 2. Passo a passo

Os horários são UTC. Cada linha remete ao registro, onde estão o comando exato e a saída. Algumas leituras de 19/10 entraram no registro depois, numa entrada de registro tardio (21:49:29).

### Passo 0: repositório da v3 no GitHub (15/10)

- 17:20:30: chave SSH ed25519 só para este repositório, em `~/.config/pathsolutions-v3/deploy_key`, sem senha. Impressão digital: `SHA256:E33k2lNyKc0AhYlNswhceKU1zOvmFqUuqeHss3X/j+o`. A chave de host do github.com conferiu com a publicada pelo GitHub (`SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU`).
- 20:08:52: o Pedro cadastrou a deploy key com escrita. A `master` virou `main`. O remoto é `git@github.com:Pedrogal-pathsolutions/pathsolutions-v3.git`, com `core.sshCommand` limitado à chave e ao known_hosts dedicados (`StrictHostKeyChecking=yes`).
- 20:23:36: push da `main`, com local igual ao remoto (`55f4fc8`). Desde então, cada sessão termina com push e conferência por hash.

### Antes de começar: processos Codex (15/10)

- 20:23:46: SIGTERM nos 2 processos `codex` do `azureps` na VM1. Na conferência seguinte, não havia nenhum. Em 19/10, a janela do Antigravity aberta às 18:50 iniciou outro `codex`, da extensão ChatGPT, e ele ficou rodando por decisão do Pedro (seção 7).

### Passo 1: código (15/10)

- 20:24:16: conferências só de leitura, com contagens e caminhos de código: mudanças sem commit, stashes, o bundle, o `~/deploy_pendente` e o `~/inference` da VM2.
- 20:36:10: decisão do Pedro: guardar só código.
  - A branch `legado-final/sobras` leva 5 arquivos fora do histórico: os 2 scripts do `~/deploy_pendente` e 3 backups do `~/inference` da VM2. A varredura de segredos não achou nada.
  - A tag `legado-final-2026-10-15` foi criada no HEAD (`ec70dbf`).
- 20:36:17: `git push origin --all` e `git push origin --tags`, sem força. (O registro de 15/10 diz 20:33, por engano; o horário certo vem da transcrição da sessão e consta de uma correção no registro de 19/10.) 12 das 13 branches e as 2 tags ficaram no remoto com hash igual ao local, conferido depois de `git fetch --prune --no-tags`.
- A `fix/audit-2026-09-dev` foi recusada pelo GitHub: o token não tinha o escopo `workflow`. Às 20:48:33, por decisão do Pedro, o conteúdo dela foi publicado como `legado-final/audit-dev` (`7f8efed`), com o `ci.yml` em `sobras/github-workflows/`. A árvore é a mesma da `-dev`, fora esse arquivo mudado de lugar.
- 23:31:07: o Pedro informou que revogou o token do GitHub.

### Passo 2: valores visuais (15/10)

- 20:48:46: `docs/v3/referencia-visual.md`, com 1.395 linhas e 12 seções (cores, tipografia, espaçamento, ícones, temas, heatmap, telas e rotas, fluxos, atalhos, viewer, extensões e o que não foi encontrado). Os valores foram extraídos só por leitura do código, sem capturas de tela e sem copiar CSS nem componentes. A varredura não achou CPF nem e-mail.

### Passo 3: storage account do legado

- 15/10, 20:49:33: pedido ao Pedro para apagar a conta inteira pelo Portal.
- Conferências: 15/10 às 22:14, às 23:07 e às 23:23:29, 16/10 às 21:05:08 e 19/10 às 19:23 e às 21:28:07. Em todas, a conta existia; nas que leram o estado, ele era `Succeeded`.
- Em 16/10 às 20:03, o Pedro informou que estava apagando a conta. O activity log dela, de 15/10 até 19/10 às 21:48, não tem nenhuma operação de exclusão, nem com falha: só os 9 `listKeys` da coleta da Fase 0. A exclusão não chegou ao Azure, e o motivo não foi verificado. O grupo não tem locks.
- Em 16/10 a conta recebeu envios novos (achado 12).
- Na última, `az storage account show -n stpathsolutionsblob001 -g rg-prod-brsouth-001` deu rc=0, e ela é a única storage account da subscrição.
- 19/10, 22:02:13 a 22:02:16: o Pedro apagou a conta pelo terminal. No activity log, `Microsoft.Storage/storageAccounts/delete` terminou `Succeeded`, pelo aplicativo da Azure CLI, e uma segunda chamada às 22:02:30 também terminou `Succeeded`.
- 19/10, 22:05:22: conferência. O `show` deu `ResourceNotFound` (rc=3), a subscrição tem 0 storage accounts e o grupo tem 19 recursos. **Passo 3 concluído.**

### Passo 4: parar e remover o legado

**VM2 (15/10)**
- 20:49:33: leitura da unit `hibou-inference.service` e da política de reinício: 4 containers `unless-stopped` em execução e 3 parados.
- 21:21:43: `systemctl disable --now hibou-inference.service`. O `compose down` da unit removeu os 4 containers ativos.
- 21:22:07: `docker rm` dos 3 parados, e não sobrou nenhum container.
- 21:22:28: `docker image prune -af` e `docker builder prune -af`: 0 imagens. O `/data` foi de 224G (94%) para 181G (76%).
- 22:01: o auto-shutdown das 19:00 de Brasília desalocou a VM2 antes da ação seguinte, que não rodou. Às 23:09:53, `az vm start` (VM ligada às 23:11:42).
- 23:11:58: o arquivo da unit foi removido, seguido de `daemon-reload` e `reset-failed`.
- 23:12:17 e 23:12:38: simulação e `apt-get remove -y aznfs`, sem autoremove nem purge. Não havia entrada NFS no fstab, nem unit de montagem NFS.

**VM1 (16/10)**
- 20:09:45: leitura dos volumes: 8, todos em `/data/docker/volumes`. A raiz do Docker e a do containerd estavam no `/data`, então os volumes e as imagens ficaram para a formatação do passo 5, como o Pedro autorizou.
- 20:09:45: o `compose down` com o arquivo do compose falhou (rc=1) sem mudar nada, porque faltavam as variáveis do legado. A regra de parar em erro foi aplicada.
- 20:13:39: por escolha do Pedro, `docker compose -p pathsolutions_v2 down --remove-orphans`, sem o arquivo: saíram os 5 containers e a rede.
- 20:14:01: as units `pathsolutions-backup.timer` e `.service` foram paradas, desabilitadas e removidas, seguidas de `daemon-reload`.
- 20:14:02: a remoção da linha `@reboot` do crontab falhou sem aplicar nada, porque o `crontab` truncou o caminho longo do arquivo temporário. A regra de parar foi aplicada. Às 20:15:17, com autorização, `crontab -` pela entrada padrão deixou 0 linhas ativas.
- 20:15:17: `systemctl disable --now nginx.service certbot.timer`, sem desinstalar. As portas 80 e 443 ficaram sem escuta.
- 20:15:18: `apt-get remove -y aznfs`, sem autoremove nem purge, e sem nenhuma entrada NFS para remover.

### Passo 5: dados do legado

**VM2 (15/10)**
- 23:13:09: registro do Docker e do containerd antes de apagar: raiz `/data/docker`, containerd com `root = "/data/containerd"`. Havia 181G e 138.966 inodes em uso.
- 23:14:07: parada de `docker.socket`, `docker.service` e `containerd.service`, `find /data -xdev -mindepth 1 -delete`, religação e `docker info`. O `/data` foi de 181G para 316K, com a mesma raiz e os mesmos runtimes (padrão `nvidia`).
- 23:14:22: `rm -rf /home/azureps/inference`, com o `.env` (6,6 MB, 49 arquivos). O disco de SO ficou em 69%.

**VM1: formatação (16/10)**
- 20:49:53: registro (5.1). `docker info` = `/data/docker|overlayfs|[["driver-type","io.containerd.snapshotter.v1"]]|io.containerd.runc.v2,runc,|runc`, com 17 imagens e 8 volumes. O `/data` tinha 477G de 503G (100%).
- 20:49:53 e 20:49:54: parada e `mask --runtime` das três units (5.2); travas do disco por lun0, by-lun/0, tamanho, disco do `/` e data de criação do fs (5.3); `umount /data` (5.4).
- 20:50:13: `mkfs.ext4 -F -L data -U 3afbd359-2c66-4644-ba14-cbdf5cd8ebb9 -E root_owner=1000:1000`, com o mesmo UUID por decisão do Pedro, em 7 s (5.5). Os ~477G do legado saíram de uma vez: banco, cache de tiles, volumes e imagens.
- 20:50:20: o script parou no 5.6 por um falso positivo da conferência. O resumo do `findmnt --verify` sai pelo stderr, e o script o procurava na última linha. Às 21:05:08, o Pedro decidiu parar ali, com o disco formatado e desmontado.

**VM1: retomada (19/10)**
- 09:02:11: a VM1 religou pelo runbook. O fstab, que tem o mesmo UUID e `nofail`, montou o `/data` novo às 09:02:19, antes do `docker.socket` (09:02:27). Como previsto em 16/10, o containerd entrou em laço com `mkdir /var/lib/containerd: file exists`, porque o link aponta para `/data/containerd`, que não existia no fs novo. O docker entrou em laço atrás dele. Até 19:09 foram 6.936 reinícios do containerd e 578 do docker.
- 19:09:25: leituras do item 1: `findmnt /data`, estado das units e `sudo docker info`, que não respondeu em 20 s. O disco de dados, que em 16/10 era o `/dev/sda`, hoje é o `/dev/sdb`; as travas usam a lun0 e o UUID, não o nome. O `/data` tinha, além do `lost+found`, o esqueleto que o dockerd cria a cada tentativa (`/data/docker`, 11 entradas, 32.804 bytes, sem containers, imagens nem volumes). Isso divergia do "novo e vazio" previsto, e a decisão foi do Pedro: a porta dura aceita esse esqueleto exato e nada mais.
- 20:48:25: as três units foram paradas e mascaradas de novo (5.2).
- 20:49:05: `findmnt --verify --verbose` com a leitura corrigida deu `0 parse errors, 0 errors, 1 warning`, rc=0, sem [E] nem [W] no `/data`; o único aviso é do `/swapfile`. Depois, o `mount -a` (sem efeito, porque o `/data` já estava montado) e a porta dura: lun0 (`/dev/sdb`) no `/data`, UUID esperado, `data.mount` ativa, fs de 16/10 20:50:13, 1 MB usado, só o `lost+found` vazio e o esqueleto (5.6).
- 20:49:05: `install -d -o root -g root -m 700 /data/containerd` e `-m 710 /data/docker` (5.7).
- 20:49:05 a 20:49:07: unmask, `reset-failed` e start de containerd, `docker.socket` e docker (5.8). O `sudo docker info` saiu idêntico ao de 16/10: `/data/docker|overlayfs|[["driver-type","io.containerd.snapshotter.v1"]]|io.containerd.runc.v2,runc,|runc`. Ficaram 0 containers, 0 imagens e 0 volumes; o containerd criou 10 entradas em `/data/containerd`, e o socket está `root:docker 660`. O `/data` ficou com 316K de 503G.

**VM1: disco de SO (item 9, 19/10)**
- 21:19:32: ensaio só das pré-condições, numa cópia do script que gravava num registro de rascunho e saía antes de apagar. Todas as portas passaram.
- 21:19:52: pré-condições do item 9, só leitura:
  - existem os 29 itens que ficam: a lista "Nunca tocar" da skill, os destinos dos links e o que o Pedro mandou manter;
  - 0 processos com cwd em `~/Pathsolutions_V2` e 0 arquivos abertos nos 18 alvos;
  - o head do bundle (`1316dec4f`) está em 13 branches do remoto, e os 2 scripts do `deploy_pendente` estão em `origin/legado-final/sobras`;
  - o nginx está inactive/disabled.
- 21:19:56 a 21:19:58: exclusões, em ordem:
  1. `sudo rm -rf --one-file-system ~/Pathsolutions_V2` (238M);
  2. `/mount/stpathsolutionsdata001` e `/mount`: 6,7G no disco de SO, com 17 `.svs`, 62 `.npy` e 79 `.json` do legado, sem exportação;
  3. `~/.git-credentials`, com 1 linha de `https://github.com`;
  4. o histórico do Gemini do projeto `pathsolutions-v2` (760K e 184K);
  5. `git config --global --unset credential.helper`, em ação separada;
  6. `~/pathsolutions.bundle` e `~/deploy_pendente`;
  7. `~/.azcopy`, o cache do claude-cli do legado, `~/.docker/buildx` e `/root/.docker`, as linhas 119–120 do `~/.bashrc` (comentário e alias `dcv`) e a entrada `pathsolutions-v2` do `~/.gemini/projects.json`;
  8. o conteúdo de `/var/log/nginx` (30 arquivos, 832K), mantendo a pasta;
  9. `/root/.azure`; as transcrições do legado em `~/.claude/projects` do `azureps`: `-home-azureps-Pathsolutions-V2` (88M) e `-home-paths-Pathsolutions-V2`, que só tinha um link para `~/pathsolutions-claude-context/memory` (o destino ficou). Essas duas pastas são exceção à lista "Nunca tocar" da skill (`~/.claude`), por decisão do Pedro em 16/10 e 19/10; a conta `paths` (`/home/paths`) não foi tocada. Saíram também `~/.gemini/antigravity`, `oauth_creds.json` e `google_accounts.json`.
- Resultado: 0 erros. Os 29 itens que ficam continuam lá. O `/` foi de 22G (78%) para 15G (53%).
- 21:20 a 21:22: estado final, registro, commit `aa35801` e push, com o hash local igual ao remoto (item 10).

### Passo 6: órfãos no Azure (19/10)

- 19:21 a 19:23: inventário, só leitura. Os 27 recursos do grupo eram os mesmos da Fase 0, sem locks. O endpoint apontava para a `stpathsolutionsdata001`, que não existe (`ResourceNotFound`). A zona tinha só o SOA e o registro A do endpoint. Os runbooks não tinham agenda, job nem webhook, e a conexão `azurevm` estava em `Error`, sem nenhum Logic App na subscrição.
- Antes de rodar, as portas foram testadas contra o estado real. O teste pegou um falso positivo, `False` em vez de `false` no link, que foi corrigido. A revisão independente acrescentou pausas de 10 s entre releituras, a conferência da agenda do `TurnOn-VMs` e a da sub-rede.
- 21:25:32: conferência inicial: o grupo bate com a lista das 19:21, e a sub-rede `default` tem o NSG e 3 configurações de IP.
- 21:25:39: `az network private-endpoint delete -g rg-prod-brsouth-001 -n pe-stpathsolutionsdata001-file`. O endpoint e a NIC dele (`…nic.9b6d5aa7…`, 10.0.0.6) responderam NotFound. A sub-rede continuou com o NSG e ficou com 2 configurações de IP, as das VMs.
- 21:26:19: `az network private-dns link vnet delete … -n axi3rxmfnch4o --yes`.
- 21:26:56: `az network private-dns zone delete … -n privatelink.file.core.windows.net --yes`, levando os registros SOA e A.
- 21:27:34: `az automation runbook delete … --yes` para `AzureAutomationTutorialWithIdentity` e `AzureAutomationTutorialWithIdentityGraphical`. O `TurnOn-VMs` continua `Published`, ligado à agenda `TurnOn-VMs`, que continua ativa.
- 21:27:47: `az resource delete -g rg-prod-brsouth-001 -n azurevm --resource-type Microsoft.Web/connections`.
- Depois de cada exclusão, o `az resource list` mostrou só a saída esperada. O grupo terminou com 20 recursos: os 19 que ficam e a `stpathsolutionsblob001`.

### Passo 7: VM2 fora do runbook e desalocada

- 15/10, 23:14:45: leitura do runbook `TurnOn-VMs` publicado: PowerShell 7.2, liga com `Start-AzVM -NoWait` cada VM de uma lista fixa (VM1 e VM2), seg–sex às 06:00 de Brasília.
- 15/10, 23:31:07: com autorização do Pedro, o rascunho sem a VM2 foi enviado com `curl --data-binary`, conferido byte a byte e publicado às 23:31:10. O conteúdo publicado, lido de novo, é idêntico ao arquivo novo.
- 16/10, 00:01:12: `az vm deallocate` da VM2. A operação terminou às 00:01:28 (activity log), e o estado `VM deallocated` foi lido às 00:01:49.
- 16/10, 19:58: o job das 09:00:54 terminou `Completed`, e o activity log só tem o start da VM1. Em 19/10, o job das 09:01:31 também terminou `Completed`; a VM2 seguia `VM deallocated` (seção 4).

### Interrupções

- 15/10, 22:01: o auto-shutdown desalocou a VM2 no meio do passo 4 (seção acima).
- 15/10, 23:01:14: o auto-shutdown desalocou a VM1, e a sessão caiu antes do registro e do push. Nada além do registrado tinha rodado. A VM1 foi ligada pelo Portal às 23:04:43.
- 16/10, 02:58:34: o Portal do Azure desalocou a VM1 (concluído às 02:59:24) e mandou desalocar a VM2, que já estava desalocada. Isso derrubou a sessão de 15/10, que estava numa leitura, sem nenhuma ação em andamento. As duas ações não são desta sessão: a desalocação da VM1 foi do Pedro, como ele informou em 19/10, e a da VM2 saiu no mesmo segundo, também pelo Portal. A VM1 voltou pelo runbook às 09:02.
- 16/10, 21:05: parada por decisão do Pedro, depois do falso positivo do 5.6.
- 19/10, das 19:26 às 20:31: a sessão ficou parada, esperando na tela a aprovação de um comando só de leitura (fstab, units e a conferência do bundle).

## 3. Código no GitHub: tags e hashes

Remoto do legado: `github.com/Pedrogal-pathsolutions/Pathsolutions_V2`. Os hashes abaixo vêm do clone local do legado, lido em 19/10 às 20:44:29, antes de apagar a pasta: as tags e as referências `origin/*` gravadas pelo fetch de 15/10, depois do push. A leitura está no registro de 19/10, na entrada de registro tardio. Os hashes curtos do registro do passo 1 batem com ela.

| Referência | Commit |
|---|---|
| tag `legado-final-2026-10-15` | `ec70dbf89b69895525fb7db50f455ac1af834b7e` |
| tag `prod-snapshot-2026-09-15` | `30dcd00e7e10efd2b1a0c998932cbf786238d787` |
| `fix/audit-2026-09` (HEAD do legado) | `ec70dbf89b69895525fb7db50f455ac1af834b7e` |
| `legado-final/sobras` | `00c4232484edec15a93b0a082397c05b9365a89f` |
| `legado-final/audit-dev` | `7f8efed5cbaa79252875c50b1411dfbafeb6c18b` |
| `main` | `4d955212761ab9e69e5ec884129cccdce1028808` |
| `feat/poc-semana1` | `4d955212761ab9e69e5ec884129cccdce1028808` |
| `docs/gpu2-plan` | `34a5d1b67fb3e8def26e6cea3e1032608a28a6bf` |
| `fix/archive-cache-eviction` | `971311a66d54b722c56d7776a9812238cf63506b` |
| `fix/case-slide-id-cluster` | `9850c16e1e4411b8123ad62bb129d386be938c39` |
| `fix/dashboard-cases` | `4375cd48b5d7a70d557902aec8c9bd3dab27c89a` |
| `fix/iiif-auth` | `58219b0a113c3f0ec44a30b53762f5ab3fcc735f` |
| `fix/macenko-inference` | `08acc6d8c68453ba4de37f91b4f54dbff2501a15` |
| `fix/poller-txleak` | `ec05c442f8b51d2782dbd5ac0377c37eb0559321` |
| `fix/viewer-precisao` | `d2345b5aaf94d323507280f148baf837e5052908` |

- As 2 tags são leves; o hash é o do commit.
- Os 2 commits da `fix/audit-2026-09-dev` (`b72c65d` e `d20d347`, de 22/09/2026) não estão no remoto com esses hashes. O conteúdo deles está na `legado-final/audit-dev`.
- O registro de 19/10 foi para o GitHub em mais de um commit da v3: até o item 10 no `aa35801`; o passo 6, a conferência do passo 3 e a primeira versão deste relatório no `a07de95`; esta revisão no commit seguinte. Em todos, o hash local da `main` ficou igual ao remoto.

## 4. Estado final das duas VMs

### VM1 (`vm-appviewer-prod-001`), 19/10 às 21:20

- `df -h`: `/` com 15G de 29G (53%); `/data` com 332K de 503G (1%); `/boot` com 159M de 881M (20%); `/boot/efi` com 6,2M de 105M (6%).
- `docker ps -a`: 0 containers. Há 0 imagens, 0 volumes e 0 de cache de build (`docker system df`). containerd, `docker.socket` e docker estão active/enabled, com 0 reinícios desde a religação. O `docker info` é o mesmo de antes da formatação, e o socket está `root:docker 660`.
- Units:
  - nenhum unit file com `pathsol`, `hibou`, `inference`, `aznfs` ou `legado`, e 0 units em falha;
  - nginx e `certbot.timer` estão inactive/disabled, com os pacotes instalados;
  - o único timer com "backup" no nome é o `dpkg-db-backup.timer`, do Ubuntu.
- Crontabs: 0 linhas ativas no do `azureps` e no do root. Em `/etc/cron.d` estão `e2scrub_all` e `sysstat`, do sistema, e `certbot`, do pacote que ficou (risco 4). A linha do `certbot` só roda sem systemd, então não dispara nesta VM.
- Portas TCP em escuta:
  - 22 (sshd);
  - 53 (systemd-resolved, só local);
  - 111 (`rpcbind`, achado 8);
  - portas altas só em 127.0.0.1, do servidor do Antigravity.
- Disco de SO: os alvos do item 9 não existem mais. Ficaram os itens do risco 4 e, por decisão do Pedro, o `~/.gemini/antigravity-ide` (risco 3). `credential.helper` vazio; `aznfs` em `deinstall ok config-files`, com o `nfs-common` ainda instalado (achado 8).
- Journal: 568,3M.

### VM2 (`vm-appfoundation-prod-001`)

- Está `VM deallocated` desde 16/10 (a operação da CLI terminou às 00:01:28). Às 02:58:34, o Portal mandou outro `deallocate`, sem efeito (seção 2, interrupções). Conferido em 19/10 às 19:24:03 e às 21:32.
- Estado final lido em 15/10 às 23:23, antes de desalocar:
  - `/` com 20G de 29G (69%) e `/data` com 316K de 251G (1%);
  - 0 containers, 0 imagens, 0 volumes e 0 de cache de build;
  - crontabs do `azureps` e do root sem linhas ativas;
  - nenhuma unit com `hibou`, `inference`, `aznfs` ou `pathsol`, e 0 units em falha;
  - driver NVIDIA 595.71.05 (Tesla T4) e `nvidia-container-toolkit` 1.19.0-1 instalados;
  - docker e containerd ativos; `~/inference` ausente.
- Não foi relida hoje (seção 8).

## 5. Recursos do Azure

### Excluídos

| Recurso | Tipo | Quando (UTC) |
|---|---|---|
| `pe-stpathsolutionsdata001-file` | private endpoint | 19/10 21:25:39 |
| `pe-stpathsolutionsdata001-file.nic.9b6d5aa7-f952-4d24-83ea-53bae3c1c8f8` | NIC, saiu com o endpoint | 19/10 21:25:39 |
| `privatelink.file.core.windows.net/axi3rxmfnch4o` | link da zona DNS com a VNet | 19/10 21:26:19 |
| `privatelink.file.core.windows.net` | zona DNS privada, com o SOA e o registro A | 19/10 21:26:56 |
| `asa-prod-brsouth-001/AzureAutomationTutorialWithIdentity` | runbook | 19/10 21:27:34 |
| `asa-prod-brsouth-001/AzureAutomationTutorialWithIdentityGraphical` | runbook | 19/10 21:27:34 |
| `azurevm` | API connection | 19/10 21:27:47 |
| `stpathsolutionsblob001` | storage account do legado, apagada pelo Pedro pelo terminal (passo 3) | 19/10 22:02:16 |

Mudanças sem exclusão:
- o runbook `TurnOn-VMs` ficou só com a VM1 (15/10, 23:31:10);
- a VM2 foi desalocada (16/10, 00:01:28).

### Ficaram

São 19 recursos no `rg-prod-brsouth-001` e 1 no `NetworkWatcherRG` (conferido em 19/10 às 22:05):

| Recurso | O que é |
|---|---|
| `vm-appviewer-prod-001` e `vm-appfoundation-prod-001` | VM1 e VM2 |
| os 4 discos das VMs (SO e dados de cada uma) | discos gerenciados |
| `VM-APPVIEWER-PROD-001/AADSSHLoginForLinux` e `vm-appfoundation-prod-001/NvidiaGpuDriverLinux` | extensões das VMs |
| `key-vm-azureps-prod` | chave pública SSH |
| `shutdown-computevm-vm-appviewer-prod-001` e `shutdown-computevm-vm-appfoundation-prod-001` | auto-shutdown das VMs |
| `vm-appviewer-prod-00141` e `vm-appfoundation-prod-001661` | NICs das VMs |
| `nsg-app-prod-001` | NSG |
| `pip-appfoundation-brsouth-001` e `pip-appfoundation-brsouth-002` | IPs públicos (o 001 está na VM1) |
| `vnet-prod-brsouth-001` | VNet |
| `asa-prod-brsouth-001` e `asa-prod-brsouth-001/TurnOn-VMs` | conta de automação e o runbook que liga a VM1 |
| `NetworkWatcher_brazilsouth` (`NetworkWatcherRG`) | Network Watcher |

O grupo `rg-pathsol-v3` ainda não existe.

## 6. Economia mensal (estimativa)

Os valores são preço de tabela em reais, da API de Cost Management lida na Fase 0 (`docs/v3/00-ambiente.md`, seção 11). A fatura do parceiro CSP pode ser diferente. Ainda não fechou nenhum mês depois das mudanças, então nada aqui é medido: tudo é estimativa.

| Item | Custo antes | Agora | Economia por mês |
|---|---|---|---|
| Private endpoint `pe-stpathsolutionsdata001-file` | R$ 37,22 em set/26 | excluído | ~R$ 37 |
| Zona `privatelink.file.core.windows.net` | R$ 2,50 em set/26 | excluída | ~R$ 2,50 |
| 2 runbooks de tutorial e a API connection `azurevm` | sem custo próprio na Fase 0 | excluídos | R$ 0 |
| Computação da VM2 (com saída de dados) | R$ 1.456,12 em set/26 (315,0 h). Só no horário do runbook, ~13 h por dia útil, daria ~R$ 1,3 mil/mês | desalocada até a Fase 4 | ~R$ 1,3 mil a ~R$ 1,46 mil |
| `stpathsolutionsblob001` | R$ 101,59 em set/26; ~R$ 136,72/mês pela capacidade de 14/10 (803,31 GiB) | apagada em 19/10 | ~R$ 100 a ~R$ 137 |

- **Total:** ~R$ 1,44 mil a ~R$ 1,63 mil por mês, quase tudo da VM2 desalocada e da storage account apagada.
- **O que continua custando com o legado apagado:**
  - discos e IP da VM2 desalocada: P15 (R$ 339,54), P4 (R$ 47,16) e o IP público (R$ 18,61), ~R$ 405/mês;
  - o disco de dados da VM1 (P20, R$ 653,86 em set/26), agora com 332K usados de 503G. O tamanho é decisão da Fase 2.
- A computação da VM1 não muda: ela segue no horário do runbook e do auto-shutdown.

## 7. Achados para registro

1. **Socket do Docker na VM1.** A Fase 0 (risco 9) já tinha registrado o `/var/run/docker.sock` como `root:systemd-journal 660` (gid 999), e não com o grupo `docker` (gid 988, `getent group` em 19/10). Registrou também que o container da API do legado montava o `docker.sock`, o que lhe dava acesso de root à VM1. A revisão independente de 16/10 viu o mesmo. Os containers do legado não existem mais. Em 19/10, depois do reboot e da religação, o socket está `root:docker 660` (`SocketGroup=docker`). A causa do grupo errado em 16/10 não foi verificada. Para a v3: nenhum container monta o `docker.sock`, e a Fase 3 confere o dono e o modo do socket.
2. **Laço do containerd e do docker por quase 12 h.** Foi de 09:02 a 20:48 de 19/10: 6.936 reinícios do containerd e 578 do docker até 19:09. A causa era o link `/var/lib/containerd` → `/data/containerd` sem destino no fs novo, resolvido no 5.7. O journal estava com 560,3M na leitura do item 1 e com 568,3M às 21:20.
3. **Ordem de montagem do `/data`.** Com `nofail`, a montagem do `/data` não fica ordenada antes do `local-fs.target` (`systemctl show data.mount`: só `WantedBy=local-fs.target`). Em 19/10 ela veio 8 s antes do `docker.socket`, mas nada garante isso. Se o disco de dados não montar, o `/data` vira a pasta vazia do disco de SO. Pelo que se viu em 19/10, o containerd não acha `/data/containerd` e entra em laço, o docker cai atrás dele, e no disco de SO ficam o esqueleto do dockerd e as mensagens dos reinícios no journal (inferência, não testada com o disco desmontado). Se alguém recriar `/data/containerd` nesse estado, o Docker passa a gravar no disco de SO, o padrão dos dois incidentes de disco cheio. Proposta para a Fase 3, já feita no plano de 16/10 (transcrição daquela sessão): `RequiresMountsFor=/data` no containerd e no docker.
4. **Os nomes dos discos trocam entre partidas.** O disco de dados da VM1 era `/dev/sda` em 16/10 e é `/dev/sdb` em 19/10 (em 14/10, segundo o registro de 16/10, também era o `/dev/sdb`). Qualquer script de disco tem que usar a lun0 (`/dev/disk/azure/scsi1/lun0`) ou o UUID.
5. **Ambiente desta sessão.** O Claude Code roda dentro do servidor do Antigravity na VM1, na janela aberta em `~/pathsolutions-v3`. Junto com ele rodam o language server do Antigravity, que grava em `~/.gemini/antigravity-ide`, e um `codex` da extensão ChatGPT. Os dois ficaram, por decisão do Pedro em 19/10.
6. **Falso positivo de 16/10.** O `findmnt --verify` escreve as linhas `[ ]`, `[W]` e `[E]` no stdout, e o resumo no stderr quando há erro ou aviso (no stdout, "Success", quando não há). A porta corrigida exige rc=0, "0 parse errors, 0 errors" ou "Success", e nenhum `[E]` ou `[W]` na seção do `/data`. Antes de rodar, ela foi testada contra o estado real.
7. **Correção no registro.** O push do passo 1 rodou às 20:36:17 de 15/10, e não às 20:33. A correção está no registro de 19/10, na entrada das 20:47:01.
8. **`rpcbind` na porta 111.** Ele escuta em todas as interfaces da VM1. O pacote é de 05/05/2026 e é dependência do `nfs-common`, que continua instalado porque o `aznfs` saiu sem autoremove. Que tenha vindo com o NFS do legado é inferência. Remover o `rpcbind` remove também o `nfs-common` (simulação `apt-get -s remove rpcbind`). O NSG não tem regra de entrada para a 111 vinda da Internet; dentro da VNet, a regra padrão do Azure deixa passar (inferência pela regra, sem teste de conexão). O achado existia antes da Fase 1.
9. **Regras do NSG do legado.** O `nsg-app-prod-001` tem 4 regras de entrada entre as VMs: `Allow-VM1-VM2-Hibou` (8001), `Allow-VM2-VM1-Redis` (6379) e `Allow-VM2-VM1-Postgres` (5432), do legado, e `Allow-VM1-VM2-SSH` (22, da VM1 para a VM2). Tem também 80 e 443 abertas para qualquer origem, sem nada escutando. A regra padrão `AllowVnetInBound` já deixa passar o tráfego dentro da VNet, então tirar as regras entre as VMs não muda o que passa entre elas (inferência pelas regras, sem teste de conexão). Nenhuma delas estava na lista de exclusão.
10. **Passo 5 antes do fim da revisão.** Em 19/10, o 5.2 a 5.8 rodou de 20:48:25 a 20:49:07, antes do fim da revisão independente (20:40 a 21:11). Rodar antes do fim foi decisão minha, porque o modo `aceitar`, escolhido pelo Pedro, não apagava nada, e o 5.6 a 5.8 já estava autorizado na ordem do dia. Os revisores conferiram depois e não acharam problema. Efeitos fora do `/data`:
    - o `daemon-reload` disparou o `apt-daily`, sem pacote alterado;
    - o dockerd criou a interface `docker0` e ligou o `ip_forward`, o padrão do Docker.
11. **Divergência no item 9.** A pasta `~/.claude/projects/-home-paths-Pathsolutions-V2`, registrada como vazia, tinha um link para `~/pathsolutions-claude-context/memory`. O Pedro decidiu apagar a pasta com o link, e o destino ficou intacto.
12. **Envios novos para o legado durante a Fase 1.** A `stpathsolutionsblob001` recebeu envios por SAS em 16/10, só nas horas das 17:00 e das 18:00 UTC (14:00 a 15:59 de Brasília), antes de o legado sair do ar na VM1 (20:13). Foram 566 `PutBlock`, 9 `PutBlockList`, 9 `PutBlob` e 18 `GetBlobProperties`, e a capacidade usada foi de 803,31 GiB para 809,92 GiB. De 17/10 em diante, 0 transações. Que sejam lâminas novas enviadas pela extensão do legado é inferência, pelo padrão de envio por SAS da Fase 0. Esses dados saíram junto com a conta, em 19/10 às 22:02, sem exportação (D1).

## 8. O que não foi possível verificar

- **Estado da VM2 hoje.** Ela está desalocada desde 16/10 às 00:01:49. Ligá-la só para ler pediria autorização e custaria computação. O estado final da seção 4 é o da leitura de 15/10 às 23:23.
- **Se os blocos apagados ainda guardam dados no disco gerenciado.**
  - Na VM1, o `mkfs` fez TRIM do disco de dados inteiro, e o `/` monta com `discard`.
  - Na VM2, o `/data` não monta com `discard` (Fase 0), e o `find -delete` não fez TRIM. Os blocos antigos continuam no disco, fora do alcance do sistema de arquivos, até serem sobrescritos ou passarem por um `fstrim`.
  - Que o Azure devolva zeros nos blocos com TRIM também não foi verificado.
- **Revogação do token do GitHub do legado.** O Pedro informou em 15/10; não conferi.
- **Por que o socket do Docker estava com o grupo `systemd-journal` em 16/10.**
- **Fatura do parceiro CSP**, que pode diferir do preço de tabela da seção 6.
- **Se a Diagnose desativou a extensão Chrome do legado** (item 0 das respostas do Pedro à Fase 0). Há um sinal de uso em 16/10, os envios do achado 12. Com a API do legado fora do ar desde 16/10 às 20:13, um envio novo pela extensão falharia antes do Blob (inferência).

## 9. Riscos

1. **`stpathsolutionsblob001`: resolvido em 19/10 às 22:02.** A conta saiu com as 1.033 `.svs` (588,16 GiB, Fase 0), os prováveis dumps do legado com dado de paciente (179,84 GiB, Fase 0), os envios de 16/10 (achado 12) e as duas chaves, que nunca tinham sido rotacionadas (seção 11).
2. **Disco de dados da VM2 sem TRIM.** Os blocos do legado (WSIs locais, caches) podem continuar no disco gerenciado da VM2 até serem sobrescritos (seção 8). Um `fstrim -v /data`, na próxima vez que a VM2 ligar, resolve do lado do sistema de arquivos.
3. **`~/.gemini/antigravity-ide` continua na VM1**, com conversas, `brain` e `knowledge` de maio a setembro, que podem citar o legado. Ficou porque a janela atual do Antigravity usa a pasta.
4. **Itens que ficaram e ainda referenciam o legado:**
   - por decisão do Pedro em 15/10 (skill, passo 4): a configuração do nginx e do certbot, os pacotes e o certificado com chave de `app.pathsolutions.com.br` em `/etc/letsencrypt`;
   - por decisão de 16/10: `~/micra` e `/mnt/pathsolutions`, que só têm pastas vazias;
   - sem decisão registrada, porque não entraram na lista de exclusão: `/root/nginx-backups`, `/usr/local/bin/azcopy`, os arquivos de configuração do `aznfs` nas duas VMs (removido sem purge), o `nfs-common` com o `rpcbind` (achado 8) e a entrada do projeto do legado no `~/.claude.json`. Em 19/10 foram conferidos `/root/nginx-backups` e `/usr/local/bin/azcopy`, pelas portas do item 9, e o estado dos pacotes, pelo `dpkg-query`. A entrada no `~/.claude.json` vem da revisão de 16/10 e não foi relida.
5. **Montagem do `/data` sem trava** (achado 3). Até a Fase 3, um boot em que o disco de dados não monte deixa o containerd e o docker em laço, gravando no journal do disco de SO. Se alguém recriar `/data/containerd` nesse estado, o Docker grava no disco de SO.
6. **Portas 80 e 443 abertas no NSG** (Fase 0), sem nada escutando na VM1 desde que o nginx foi parado. O que vier a escutar nelas fica exposto à Internet.
7. **Outro agente na VM1:** o `codex` da extensão ChatGPT roda junto com a janela do Antigravity (achado 5).

## 10. Decisões pedidas ao Pedro

As respostas do Pedro, de 19/10, estão na seção 11.

1. **Passo 3:** apagar a `stpathsolutionsblob001` pelo Portal, porque a exclusão de 16/10 não chegou ao Azure. Os envios de 16/10 (achado 12) saem junto: decidir se a Diagnose precisa saber disso, já que nada é exportado (D1). A conferência fica para a sessão seguinte. Se o Pedro preferir, ele aprova a Fase 1 com o passo 3 registrado como pendente.
2. **`~/.gemini/antigravity-ide`:** apagar numa sessão aberta fora do Antigravity, ou manter.
3. **Itens que ficaram (risco 4):** manter até a Fase 2 ou a 3, ou apagar já, um por um. A configuração do nginx, o certificado e os pacotes já estavam marcados para a Fase 2 decidir (skill, passo 4).
4. **Regras do NSG só do legado e `rpcbind` (achados 8 e 9):** remover agora, com autorização por ação, ou deixar para a Fase 2 ou a 3. A rede fica fora do Terraform.
5. **`fstrim` no `/data` da VM2** na próxima vez que ela ligar (Fase 4), com autorização, ou numa ação própria antes disso.
6. **Para o plano da Fase 3:** `RequiresMountsFor=/data` no containerd e no docker; conferência do dono do `docker.sock`; teto para o journal e para os logs do Docker (regra do `CLAUDE.md` sobre diretórios que crescem).
7. **`codex` da extensão ChatGPT:** deixar rodando durante as fases, ou fechar a extensão no Antigravity.
8. **Aprovação da Fase 1:** "APROVADO FASE 1".

PARADO — aguardando APROVADO FASE 1

## 11. Depois da entrega: passo 3, respostas e aprovação (19/10)

- **Passo 3 concluído.**
  - O Pedro apagou a `stpathsolutionsblob001` pelo terminal. No activity log, o `delete` terminou `Succeeded` às 22:02:16, pela Azure CLI, com uma segunda chamada às 22:02:30.
  - Na conferência das 22:05:22, `az storage account show` deu `ResourceNotFound` (rc=3), `az resource list --resource-type Microsoft.Storage/storageAccounts` não listou nenhuma conta, e o grupo ficou com 19 recursos.
- **Respostas do Pedro à seção 10:**
  1. Diagnose: o Pedro avisa em 19/10 sobre os envios de 16/10 e pede de novo que desativem a extensão.
  2. `~/.gemini/antigravity-ide`: fica. O Pedro decide quando deixar de usar o Antigravity na VM1.
  3. Itens do risco 4: ficam para a Fase 3, que prepara a VM1 para a v3. Sobre o nginx, o certificado e os pacotes, a Fase 2 decide.
  4. Regras do NSG do legado, `rpcbind` e as portas 80 e 443: Fase 3, no plano de rede. A Fase 2 define o que vai escutar na 80 e na 443.
  5. `fstrim` no `/data` da VM2: primeira ação da Fase 4, quando ela ligar.
  6. Plano da Fase 3: entram `RequiresMountsFor=/data` no containerd e no docker, o dono do `docker.sock` e o teto para o journal e para os logs do Docker.
  7. `codex`: fica, e o Pedro não usa o ChatGPT nesta VM durante as fases.
  8. A desalocação da VM1 pelo Portal em 16/10 às 02:58 UTC foi do Pedro.
- **APROVADO FASE 1**, escrito pelo Pedro em 19/10/2026. A Fase 2 começa numa sessão nova.
