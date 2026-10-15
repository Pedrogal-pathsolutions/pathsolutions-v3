---
name: pathsol-desligamento-legado
description: Procedimento para desligar e apagar o sistema legado da PathSolutions nas VMs 1 e 2 antes da v3 — tag e push do código, valores visuais extraídos do código, conferência da exclusão da storage account do legado (feita pelo Pedro), parada e remoção de containers, imagens, volumes, units e crontabs, limpeza do /data e das pastas do legado, exclusão dos órfãos e desalocação da VM2. Sem snapshots. Use sempre que um comando for mudar qualquer coisa no legado, para planejar ou executar o desligamento, ou num incidente antes dele.
---

# Desligamento do legado PathSolutions

Em 15/10/2026, o Pedro decidiu apagar o legado inteiro: banco, caches, dumps e lâminas. A v3 começa vazia, e as lâminas e os casos de treinamento chegam depois pelo fluxo novo.

Não há snapshots: o que esta sequência apaga não tem volta. Ficam só o código, no GitHub com tag, e a lista de valores visuais em `docs/v3/referencia-visual.md`.

Os fatos citados abaixo vêm de `docs/v3/00-ambiente.md`. As exceções são o `daemon.json`, o `/data/containerd` e o link de `/var/lib/containerd` da VM1 e as outras sobras do passo 5, que não estão no relatório. Esses itens são conferidos e registrados em `docs/operacao/<AAAA-MM-DD>-desligamento.md`, com comando e saída resumida, antes do pedido de autorização. Confira o estado atual antes de cada ação.

## Regras

- Uma ação por autorização explícita do Pedro. "Pode seguir" vale para a ação descrita, não para as próximas.
- Antes de pedir: o comando exato, o efeito esperado e se tem volta.
- Registrar em `docs/operacao/<AAAA-MM-DD>-desligamento.md` o comando e o horário (UTC) antes de executar, e a saída resumida depois. Assim, uma queda no meio deixa rastro.
- Você nunca apaga blobs, containers do Blob ou storage accounts (travas do `.claude/settings.json`). A remoção de containers Docker no passo 4 não entra nesta regra. A `stpathsolutionsblob001` é apagada pelo Pedro, pelo Portal.
- Código, comentários e arquivos de configuração do legado não são copiados para o repositório da v3. A exceção é a lista de valores visuais do passo 2.
- Nenhum dado de paciente em registro, relatório ou commit. Nomes de arquivo de lâmina e de diretório por caso podem conter número de caso: relatórios trazem só contagens.
- Nunca tocar: o repositório da v3 (`/home/azureps/pathsolutions-v3`), `~/.claude`, `~/.azure`, `~/.ssh`, `~/.codex`, a conta `paths` e o `pathsolutions-claude-context` (repositório e pasta local). Também ficam Docker e a configuração dele em `/etc/docker`, driver NVIDIA e nvidia-container-toolkit.

## Antes de começar

0. **Repositório da v3 no GitHub**, antes de qualquer outro passo (decisão do Pedro em 15/10):
   - gerar na VM1 uma chave SSH só para o repositório `Pedrogal-pathsolutions/pathsolutions-v3` (privado) e mostrar a chave pública ao Pedro, que a cadastra como deploy key com escrita;
   - configurar o remoto por SSH, fazer o push da `main` e conferir por hash;
   - daqui em diante, fazer push ao fim de cada sessão (`CLAUDE.md`).

Depois, parar os processos Codex na VM1. Eles são do Pedro, e ele autorizou parar. O Reynaldo confirmou que não tem sessões nem trabalho pendente na VM1. Durante as fases, nenhum outro agente usa a VM1.

## Sequência

1. **Código.**
   - **Antes da tag, só leitura:** conferir se o passo 5 vai apagar código que o push não leva.
     - Em `/home/azureps/Pathsolutions_V2`, contar as linhas de `git status --porcelain` e de `git stash list`, sem mostrar nomes de arquivo. Mudança sem commit não vai no push.
     - Comparar por sha256 os arquivos de `~/inference` da VM2, que não tem repositório git, com o `inference/` das branches, sem incluir o `.env`.
     - Conferir que cada ref de `~/pathsolutions.bundle` (`git bundle list-heads`) está contida em alguma branch ou tag local.
     - Conferir os arquivos de `~/deploy_pendente`.

     No registro, só contagens e caminhos de código. O que divergir vai para o Pedro decidir antes do push, enquanto ainda cabe nele (por exemplo, como uma branch a mais) e antes de ele revogar o token.
   - Criar a tag `legado-final-<AAAA-MM-DD>` em `/home/azureps/Pathsolutions_V2`.
   - Antes do push, rodar `git fetch --prune --no-tags origin`, que não muda ramos locais, tags nem a árvore de trabalho, para mostrar ao Pedro o efeito esperado.
   - Fazer push de todas as branches e tags para o `origin` (`github.com/Pedrogal-pathsolutions/Pathsolutions_V2`), inclusive a `fix/audit-2026-09`, que não tem upstream.
     - Comandos: `git push origin --all` e depois `git push origin --tags`. O push pede confirmação.
     - Nunca usar `--mirror`, `--force`, `--force-with-lease`, `--prune`, `--delete` nem refspec com `+`.
     - Se o GitHub recusar algum ramo, não forçar nem fazer `pull`.
   - Conferir por hash, depois de um novo `git fetch --prune --no-tags origin`:
     - `git rev-list --count --branches --not --remotes=origin` deve dar 0;
     - cada tag de `git show-ref --tags` deve aparecer com o mesmo hash em `git ls-remote --tags origin`.

     Se alguma das duas falhar, parar e levar ao Pedro, com a proposta de enviar com outro nome (`legado-final/<ramo>`) os ramos que têm commits sem cópia. Registrar os hashes.
   - Depois do push e da conferência, o Pedro revoga o token do GitHub; o `~/.git-credentials` sai no passo 5.
   - **`pathsolutions-claude-context`:** o Pedro não sabe de quem é a conta. Não tocar nele nem na pasta local `/home/azureps/pathsolutions-claude-context` (decisão de 15/10).

2. **Valores visuais.** Antes do passo 5, que apaga o código local, extrair do código do legado:
   - cores (com nome e uso), fontes, tamanhos, espaçamentos, raios, ícones e temas;
   - a lista de telas e rotas, e o que cada uma faz;
   - os atalhos de teclado e as interações do viewer.

   Tudo vira lista de valores em `docs/v3/referencia-visual.md`, sem copiar CSS nem componentes e sem capturas de tela.

3. **Storage account do legado.**
   - O Pedro apaga a `stpathsolutionsblob001` inteira pelo Portal, com as WSIs, os dumps e as chaves.
   - Depois, conferir que ela não existe mais: `az storage account show -n stpathsolutionsblob001 -g rg-prod-brsouth-001` deve responder `ResourceNotFound`, e `az resource list --resource-type Microsoft.Storage/storageAccounts` não deve listá-la.
   - Registrar o horário.

4. **Parar e remover o legado nas duas VMs**, uma autorização por ação.
   - **VM1:**
     - parar e remover os containers do compose `pathsolutions_v2` (`/home/azureps/Pathsolutions_V2`), as imagens, os volumes `pathsolutions_v2_*` e os anônimos, e o cache de build;
     - desabilitar, parar e remover as units `pathsolutions-backup.timer` e `pathsolutions-backup.service`, de `/etc/systemd/system`, e depois rodar `systemctl daemon-reload` e `systemctl reset-failed pathsolutions-backup.service pathsolutions-backup.timer` (a service estava em failed desde 14/10);
     - tirar do crontab do `azureps` a entrada `@reboot` do script de backup.
   - **nginx e certbot (VM1):** o site `pathsolutions` do nginx nativo e o certbot servem o legado em 80/443, abertas para a Internet. O site está em `/etc/nginx/sites-enabled`, visto em 15/10; o nome não consta do relatório da Fase 0.
     - Se o site ficar, ele segue encaminhando essas portas para 127.0.0.1:3000 e :8000. Sem os containers, deve responder com erro (provavelmente 502, não verificado), e o que vier a escutar nessas portas na VM1 ficaria exposto por ele.
     - Decisão do Pedro em 15/10: parar e desativar o `nginx.service` e o `certbot.timer`, sem desinstalar. Configuração, certificado e pacotes ficam; a Fase 2 decide.
     - Os logs em `/var/log/nginx` podem conter número de caso (seção 14 e risco 4 da Fase 0) e ficam até decisão do Pedro. Em 15/10 havia 2 atuais e 28 rotacionados.
   - **VM2**, nesta ordem:
     - antes, só leitura: `systemctl cat hibou-inference.service` (ExecStart, ExecStop, Restart, WorkingDirectory e drop-ins) e a política de reinício dos containers (`docker inspect`, `HostConfig.RestartPolicy`). A Fase 0 não registrou nenhum dos dois. No registro vão só esses campos, sem segredos;
     - `systemctl disable --now hibou-inference.service`, antes dos containers, para que a unit não os recrie;
     - parar e remover os 4 containers do compose `inference` (`/home/azureps/inference`) e os 3 parados;
     - remover as imagens (inclusive as tags de backup e de rollback) e o cache de build;
     - remover o arquivo da unit (e os drop-ins, se houver) de `/etc/systemd/system` e rodar `systemctl daemon-reload` e `systemctl reset-failed hibou-inference.service`.
   - **aznfs (VM1 e VM2):** as units `aznfswatchdog` e `aznfswatchdogv4` vêm do pacote `aznfs`, o helper de NFS do Azure. O script de setup do legado instala esse pacote para as montagens NFS da `stpathsolutionsdata001`, conta já excluída, e nenhuma das duas VMs tem montagem NFS.
     - Decisão do Pedro em 15/10: remover o `aznfs`, junto com a entrada de montagem.
     - Mostrar antes o que o `apt-get -s remove aznfs` removeria e só então rodar `apt remove aznfs`, sem `autoremove`.
     - Conferir e remover qualquer entrada de montagem NFS do legado no `/etc/fstab` e em units `.mount` ou `.automount`. Em 15/10 o `/etc/fstab` das duas VMs não tinha nenhuma; registrar se continua assim.
   - **Estado final nas duas VMs:** `docker ps -a`, `docker image ls` e `docker volume ls` vazios, nenhuma unit do legado e nenhum crontab do legado.

5. **Apagar os dados do legado.** Só depois dos passos 1 a 4 confirmados.
   - **Horário.** O auto-shutdown desaloca a VM2 às 19:00 e a VM1 às 20:00 de Brasília, todo dia. O runbook `TurnOn-VMs` só liga as duas de segunda a sexta, às 06:00. Na VM1, a sessão cai junto.
     - Só parar o Docker e começar a apagar com tempo para terminar e religar os serviços antes do corte da VM. O tempo para apagar os ~7,9 milhões de JPEG do cache de tiles da VM1 não foi medido.
     - Se a VM for desalocada no meio, retomar do ponto: conferir o que restou, parar de novo `docker.socket`, `docker.service` e `containerd.service`, terminar de apagar e religar.
     - Para retomar antes do próximo disparo do runbook, ligar a VM2 pede `az vm start`, com autorização. A VM1 só volta pelo Pedro ou pelo runbook.
   - **`/data` inteiro nas duas VMs.**
     - **Onde ficam as raízes:**
       - Na VM1, a raiz do Docker é `/data/docker` (`/etc/docker/daemon.json`). `/var/lib/containerd`, raiz padrão do containerd (o `root` do `/etc/containerd/config.toml` está comentado), é link simbólico para `/data/containerd`.
       - Na VM2, a raiz do Docker foi inferida pelas montagens overlay em `/data/docker/rootfs`, não lida do `daemon.json`, e a do containerd não foi verificada.
     - Antes de parar, registrar nas duas VMs:
       - `docker info --format '{{.DockerRootDir}} {{.Driver}} {{json .Runtimes}}'`;
       - o `/etc/docker/daemon.json` e a linha `root` do `/etc/containerd/config.toml`;
       - `ls -ld /var/lib/docker /var/lib/containerd`, e dono e modo do destino de cada link (`ls -ldL`);
       - `findmnt -R /data`.
     - Parar `docker.socket`, `docker.service` e `containerd.service`. Conferir com `findmnt -R /data` que só o disco de dados está montado ali.
     - Apagar o conteúdo de `/data`, inclusive arquivos ocultos, sem atravessar outras montagens: `sudo find /data -xdev -mindepth 1 -delete`. O ponto de montagem, o `/etc/fstab` e os links de `/var/lib` ficam.
     - Antes de religar, recriar vazio o destino de cada link, com o dono e o modo registrados; na VM1, `sudo install -d -o root -g root -m 700 /data/containerd`. O Docker recria a própria raiz, mas o containerd cria a dele com `mkdir`, que falha diante de um link sem destino. Sem esse passo, o containerd não deve subir, e o Docker depende dele (inferência, não testada).
     - Religar `containerd.service`, `docker.socket` e `docker.service`. Conferir que o `docker info` mostra a mesma raiz, o mesmo driver e os mesmos runtimes registrados antes.
     - Se o Docker não subir, parar e reportar, sem reinstalar nada e sem mexer nos links. Apagar o link levaria o containerd para o disco de SO, que na VM1 está em 79%.
   - **No disco de SO:**
     - `/mount/stpathsolutionsdata001` (VM1);
     - `/home/azureps/Pathsolutions_V2` (VM1, depois do passo 1);
     - `/home/azureps/inference`, com o `.env` (VM2);
     - `~/.git-credentials` (VM1):
       - antes de apagar, mostrar ao Pedro o número de linhas e, de cada uma, só o host e o usuário, sem a senha e com o usuário mascarado se tiver forma de token, para ele saber se há mais de uma credencial, inclusive de outra conta, como a do `pathsolutions-claude-context`;
       - apagar depois que o Pedro disser que revogou ou decidiu sobre cada uma;
       - no registro, só o número de linhas e os hosts;
       - em ação separada, propor tirar o `credential.helper=store` da configuração global do git; sem isso, a próxima credencial usada por HTTPS volta a ser gravada em texto puro;
     - o histórico do Gemini CLI do projeto legado (VM1): `~/.gemini/tmp/pathsolutions-v2/` (as conversas, em `chats/`) e `~/.gemini/history/pathsolutions-v2/` (repositório-sombra dos checkpoints). Antes, conferir no `~/.gemini/projects.json` que `pathsolutions-v2` aponta para `/home/azureps/Pathsolutions_V2`.
   - **Resto do `~/.gemini` (VM1)**, fora do pedido: os dados do Antigravity (`~/.gemini/antigravity/` e `~/.gemini/antigravity-ide/`) e as credenciais do Google (`oauth_creds.json` e `google_accounts.json`). Mostrar ao Pedro só nomes e tamanhos, sem abrir os arquivos, e perguntar sobre cada um.
   - **Fora da lista do Pedro (acréscimo, pendente de decisão):** `~/pathsolutions.bundle`, `~/deploy_pendente`, `~/micra` e `/mnt/pathsolutions` (VM1).
     - Esses caminhos não constam do relatório da Fase 0. Em 15/10 só se conferiu que existem; se são do legado não foi verificado.
     - Antes de pedir autorização para cada um, mostrar tipo, dono, tamanho, data e a evidência de que é do legado, sem nomes de arquivo.
     - O bundle só sai se o commit de cada head listado por `git bundle list-heads` já estiver no remoto (passo 1).
     - O que não for claramente do legado fica. Nada é apagado sem decisão escrita do Pedro sobre cada um.
   - Mostrar `df -h` antes e depois, nas duas VMs.

6. **Órfãos no Azure**, cada um com autorização:
   - o private endpoint `pe-stpathsolutionsdata001-file` (conferir que a NIC dele saiu junto);
   - a zona DNS privada `privatelink.file.core.windows.net` e o link de VNet dela;
   - os runbooks `AzureAutomationTutorialWithIdentity` e `AzureAutomationTutorialWithIdentityGraphical`;
   - a API connection `azurevm`.

   Conferir com `az resource list` depois de cada exclusão.

7. **VM2.**
   - Tirar a VM2 do runbook `TurnOn-VMs`. Ele continua ligando a VM1, e o auto-shutdown da VM1 (20:00) continua ativo.
   - Desalocar a VM2 (`az vm deallocate`, pede confirmação).
   - Conferir `VM deallocated` e, no job seguinte do runbook, que só a VM1 foi ligada.
   - A VM2 fica desalocada até a Fase 4.

## Relatório

O relatório vai em `docs/v3/01-desligamento.md` e traz:
- para cada passo, o comando, o horário e a saída resumida;
- o estado final das duas VMs: `df -h`, `docker ps -a`, units e crontabs;
- os recursos do Azure excluídos e os que ficaram;
- a tag e os hashes do código no GitHub;
- onde está a lista de valores visuais;
- a economia mensal, medida ou estimada.

## Incidente antes do desligamento

Diagnóstico primeiro, sem mudar nada. Depois, uma ação por autorização, com efeito colateral explícito. Nada de correção estrutural: o legado vai ser apagado.
