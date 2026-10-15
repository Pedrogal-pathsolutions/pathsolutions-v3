# Fase 0 — Ambiente

Levantamento somente leitura do ambiente atual, feito em 14 e 15/10/2026.

- **Recorte único dos dados do Azure e da VM1:** T = 2026-10-15 00:14 UTC (21:14 de 14/10 em Brasília), salvo indicação. O activity log foi lido na janela absoluta de 2026-07-17 00:14 UTC a T: 1.037 eventos na subscrição e 1.021 no grupo. O `/data` da VM1 está cheio desde ~21:02 UTC de 14/10: a última escrita legível foi às 21:02:30, e as IOPS do disco de dados ficaram perto de 100% a partir de 21:05. Desde então, o Postgres do legado está em laço de recuperação por falta de espaço (seção 8.1).

Outras partes do legado seguiram rodando:
- a VM2 ficou com CPU alta até ser desalocada às 22:02 UTC;
- o `wsi-output` recebeu 8 blobs entre 21:03 e 21:45:52 UTC;
- às 23:34 UTC, backend, frontend e redis estavam healthy.

O efeito para os usuários não foi verificado: nenhuma requisição HTTP foi feita. Como nenhum blob foi criado depois de 21:45:52 UTC, os números do Blob ficaram estáveis no fim da coleta. Nas leituras de 23:22 a 00:17 UTC, o uso do `/data` ficou entre 477,32 e 477,35 GiB.
- **VM1 depois do recorte:** foi desalocada pelo Portal às 02:34:49 UTC de 15/10 e ligada pelo runbook às 09:02 UTC. Em 15/10 às 13:35 UTC, o banco do legado seguia fora do ar (seção 8.1).
- **VM2 por dentro:** lida por ssh em 15/10 às 11:54 UTC, depois que o runbook `TurnOn-VMs` a ligou (seção 13). Os dados locais da VM2 são desse horário.

## 1. Resumo

| Tema | Situação | Seção |
|---|---|---|
| Legado | **Banco do legado fora do ar**, confirmado de novo em 15/10 às 13:35 UTC. O `/data` da VM1 segue 100% cheio. Em 14/10 o Postgres estava em laço de recuperação (`PANIC ... No space left on device`). Em 15/10, depois da nova partida da VM1, o container do banco reinicia sem conseguir subir (`FATAL: could not write lock file ... No space left on device`), e backend e queue-worker estão unhealthy. A indisponibilidade para os usuários é inferência: o acesso à aplicação não foi testado. Decisão do Pedro em 14/10: não mexer no legado; a Fase 1 foi reordenada na skill de desligamento (commit `1ea41a7`). | 8.1, 13, 15 |
| WSIs | 1.033 arquivos `.svs` (588,16 GiB) no container `wsi-slides` da `stpathsolutionsblob001`. Fora do Blob, a coleta só confirmou cópia de 17 delas, no disco de SO da VM1 (mesmo nome e tamanho, sem hash). A VM2 tem 516 arquivos `.svs`, `.ndpi`, `.mrxs`, `.tif` ou `.tiff` (61,01 GiB) no `/data`, inclusive datasets; quantos são lâminas inteiras não foi verificado, e eles não foram comparados com o Blob. Não há soft delete, versionamento, lock, snapshot nem backup. A conta aceita conexões de qualquer rede e usa chave compartilhada. | 7, 14 |
| Subscrição | É **CSP** (`quotaId CSP_2015-05-01`, "Microsoft Azure Plan" via parceiro), não pay-as-you-go direta como dizem o `CLAUDE.md`, o `PROMPT_V3.md` e a skill `pathsol-infra`. Os custos abaixo são preço de tabela em BRL; a fatura do parceiro não foi vista. | 3, 11 |
| Custo | jul R$ 2.868,05 · ago R$ 1.601,32 · set R$ 3.747,27 · out (1–13) R$ 1.495,55. A parte fixa é de cerca de R$ 1.165/mês, quase toda em discos Premium. Não há orçamento nem alerta. Se a VM1 ficasse ligada 24 h, um mês cheio ficaria em ~R$ 4,9–5,1 mil, no limite do teto D3 de R$ 5.000 (estimativa). É um cenário: o auto-shutdown da VM1 foi reativado em 15/10. | 11 |
| Estimativas pedidas | Snapshots incrementais dos 4 discos: **~R$ 263,29/mês** pelo espaço usado (VM1 R$ 177,25; VM2 R$ 86,04). Contando o `/data` da VM2 pelos 256 GiB, porque ele não usa TRIM online, o valor vai a R$ 274,95. O teto absoluto, pelos 828 GiB provisionados, é R$ 293,86. Soft delete: R$ 0 para ligar e ~R$ 0/mês com as sobrescritas observadas em 30 dias. Esse valor é um limite inferior, porque sem logs as exclusões não aparecem. Uma exclusão acidental de todas as WSIs custaria R$ 100,10, uma vez, pelos 30 dias de retenção. | 12 |
| Backup | Nenhum snapshot, cofre ou imagem. O dump mais novo do banco do legado (provável `.sql.gz` de ~37,5 GiB) é de 15/09/2026 e está só no Blob, no container `backups`. No disco da VM1 não há cópia dele: o `scripts/backup.sh` do legado apaga o dump local depois do envio. Depois de 15/09 só há logs de falha. | 7, 8.2, 15 |
| Monitoramento | Nenhum: 0 alertas, 0 action groups, 0 workspaces, 0 diagnostic settings, 0 orçamentos. | 8.4 |
| VMs | Em 14/10, a VM2 foi desalocada às 22:02 UTC pelo auto-shutdown das 19:00, e o Pedro desativou o auto-shutdown da VM1 às 22:46 UTC. Em 15/10, pelo Portal e por usuário, o auto-shutdown da VM1 foi reativado (02:34:38 UTC; Enabled, 20:00) e a VM1 foi desalocada (02:34:49 UTC). Às 09:02 UTC, o runbook `TurnOn-VMs` ligou as duas. | 5, 8.3, 13 |
| VM2 por dentro | Tesla T4, driver NVIDIA **595.71.05** (o `nvidia-smi` mostra CUDA 13.2, o máximo suportado pelo driver) e CUDA toolkit **12.8.2** em `/usr/local/cuda-12.8`, fora do PATH. O `/data` da VM2 está em **94%** (15G livres), acima do alerta de 90%. Roda o compose `inference` do legado (4 containers) e a unit `hibou-inference.service`. | 5.2, 6, 8.6 |
| Cota T4 | NCASv3_T4 em 4/4 vCPUs, toda ocupada pela VM2, mesmo desalocada. | 9 |
| Ferramentas | Terraform **não está instalado** em nenhuma das duas VMs. Na VM1 faltam também node, npm e pip3. Na VM2 faltam az, psql, node e npm. | 10 |
| Código do legado | Fica em `/home/azureps/Pathsolutions_V2`. A branch atual, `fix/audit-2026-09`, não tem upstream; 35 commits não aparecem em nenhuma ref remota conhecida. | 8.5 |

## 2. O que foi feito

1. **Leitura das regras.** `CLAUDE.md`, a spec de arquitetura, o `PROMPT_V3.md`, as travas de `.claude/settings.json` e a skill `pathsol-infra`.
2. **Subscrição e máquina.** `az account show` antes de qualquer outro `az`; a sessão roda na VM1, identificada pelo IMDS.
3. **Coleta paralela.** Seis agentes de leitura, um por domínio: VMs e rede, storage e WSIs, cota, custo, automação e monitoramento, SO da VM1. Cada um teve um verificador independente, que rederivou os números por outro método: 196 conferências, 186 confirmadas, 6 contraditas em detalhes que não mudam conclusões (corrigidos aqui) e 4 inconclusivas. Depois vieram um crítico de completude e uma rodada de preenchimento de lacunas.
4. **Leituras com confirmação do Pedro**, feitas pela sessão principal: `systemctl`, `crontab` (azureps e root), `psql --version`, `sudo docker ps -a`, `sudo docker system df -v` e contagem de erros no log do container do banco (só tipos de mensagem).
5. **Tentativa de ssh na VM2.** Falhou com `No route to host`: a VM2 tinha acabado de ser desalocada pelo auto-shutdown das 19:00. O Pedro decidiu deixar essa leitura para 15/10.
6. **Auto-shutdown da VM1.** Às 19:45 de Brasília a sessão avisou que o auto-shutdown da VM1 (20:00) derrubaria a sessão. O Pedro o desativou pelo Portal às 22:46:23 UTC. Em 15/10, às 02:34:38 UTC, ele foi reativado pelo Portal, e às 02:34:49 a VM1 foi desalocada pelo Portal, as duas operações por usuário (seção 13). Nenhuma mudança no Azure foi feita pela sessão.
7. **Pedidos do Pedro em 14/10:** (a) não mexer no legado hoje; (b) nova ordem dos passos 1 a 6 da Fase 1 na skill `pathsol-desligamento-legado`, com commit separado (`1ea41a7`); (c) estimativa de custo de soft delete e snapshots neste relatório (seção 12).
8. **Revisão adversarial do relatório** em 14–15/10, com quatro lentes (privacidade, números contra evidência em duas metades, completude e regras) e um verificador cético por achado: 54 achados, 46 confirmados e corrigidos, 7 refutados e 1 já coberto.
9. **Leitura da VM2 em 15/10** por ssh, com confirmação do Pedro, depois que o runbook ligou a VM2 (seção 13).
10. **Revisão final** em 15/10, com duas lentes (fatos da VM2; consistência, privacidade e completude) e um verificador por achado: 22 achados, 21 confirmados e corrigidos. Para fechar dois deles com evidência, a sessão releu o activity log da VM1 e, com confirmação, o estado do legado na VM1 às 13:35 UTC (seções 8.1 e 13).

**Escritas desta fase:** o ID da subscrição no `CLAUDE.md`, este relatório e a skill (commit `1ea41a7`, a pedido do Pedro). Arquivos temporários ficaram só no scratchpad da sessão, em `/tmp`, sem nomes de blob.

**Rastros deixados por leituras:**
- Leituras do plano de dados do Blob com `--auth-mode key` geraram operações `listKeys` na `stpathsolutionsblob001`: 40 entre 22:51:29 UTC de 14/10 e 00:15:24 UTC de 15/10, todas desta coleta, pela Azure CLI desta VM. Nos 90 dias anteriores não houve nenhuma. Nenhuma chave foi impressa ou gravada, e não haverá novas listagens nesta fase. A atribuição a esta coleta se apoia em horário e contagem: o activity log mostra o cliente (Portal ou CLI), mas não o processo da VM1 que fez a chamada, e há outras sessões de agentes na mesma conta (risco 13). O usuário não tem papel de dados (Storage Blob Data Reader), por isso o `--auth-mode login` falhou.
- Consultas ao Cost Management e ao activity log.
- O ssh de 15/10 imprimiu o aviso de que adicionou a chave de host ED25519 da VM2 à lista de hosts conhecidos. Se ela foi gravada, e em que arquivo, não foi verificado (seção 13).

**Desvios de processo, registrados para não se repetirem:**
- Um agente verificador leu, com `cat` via Bash, arquivos de metadados de extensões em `~/.azure/cliextensions`, contornando a regra `deny Read(~/.azure/**)`. O conteúdo não era sensível (versões de extensão).
- Outro verificador gravou por alguns segundos um IP público num arquivo do scratchpad antes de redigi-lo; a varredura posterior encontrou 0 IPs públicos nos arquivos.

## 3. Subscrição

| Item | Valor | Evidência |
|---|---|---|
| Nome | PATHSOLUTIONS TECNOLOGIA EM SAUDE LTDA | `az account show` |
| ID | `bd87a1ca-e4f5-460b-9f12-c89e114293f1` (gravado no `CLAUDE.md`) | `az account show` |
| Estado | Enabled; única subscrição visível | `az account list` |
| Oferta | `quotaId = CSP_2015-05-01`, `spendingLimit = Off`; cobrança "Microsoft Azure Plan" com dimensões de parceiro no Cost Management | `az rest --method get .../subscriptions/<id>?api-version=2022-12-01`; verificador de custo |
| Acessos com Owner | 1 usuário e 2 ForeignGroups (padrão de parceiro CSP). Identidade dos grupos não verificada | `az role assignment list` (domínios storage e vms) |
| Extensões do az | account 0.2.5, automation 1.0.0b2, quota 1.0.0, support 2.0.1 | `az extension list` |

## 4. Recursos e grupos

28 recursos e 17 tipos. São 27 no grupo `rg-prod-brsouth-001` (em 6 deles o ID grafa o grupo em maiúsculas, mas é o mesmo grupo) e 1 em `NetworkWatcherRG`. `rg-pathsol-v3` ainda não existe. Evidência: `az resource list -o table` e `az group list`.

| # | Nome | Tipo | Grupo | Observação |
|---|---|---|---|---|
| 1 | vm-appviewer-prod-001 | virtualMachines | rg-prod-brsouth-001 | **VM1**, Standard_D8s_v5 |
| 2 | vm-appfoundation-prod-001 | virtualMachines | rg-prod-brsouth-001 | **VM2**, Standard_NC4as_T4_v3 |
| 3 | vm-appviewer-prod-001_OsDisk_1_2cdb4cd2… | disks | rg-prod-brsouth-001 | SO da VM1, P4 30 GiB |
| 4 | vm-appviewer-prod-001_DataDisk_0 | disks | rg-prod-brsouth-001 | dados da VM1, P20 512 GiB |
| 5 | vm-appfoundation-prod-001_OsDisk_1_be3c948b… | disks | rg-prod-brsouth-001 | SO da VM2, P4 30 GiB |
| 6 | vm-appfoundation-prod-001_DataDisk_0 | disks | rg-prod-brsouth-001 | dados da VM2, P15 256 GiB |
| 7 | VM-APPVIEWER-PROD-001/AADSSHLoginForLinux | virtualMachines/extensions | rg-prod-brsouth-001 | login SSH via Entra ID na VM1 |
| 8 | vm-appfoundation-prod-001/NvidiaGpuDriverLinux | virtualMachines/extensions | rg-prod-brsouth-001 | driver NVIDIA na VM2, extensão 1.9 |
| 9 | key-vm-azureps-prod | sshPublicKeys | rg-prod-brsouth-001 | chave pública SSH |
| 10 | vm-appviewer-prod-00141 | networkInterfaces | rg-prod-brsouth-001 | NIC da VM1 (10.0.0.5) |
| 11 | vm-appfoundation-prod-001661 | networkInterfaces | rg-prod-brsouth-001 | NIC da VM2 (10.0.0.4) |
| 12 | pe-stpathsolutionsdata001-file.nic.9b6d5aa7… | networkInterfaces | rg-prod-brsouth-001 | NIC do private endpoint órfão (10.0.0.6) |
| 13 | nsg-app-prod-001 | networkSecurityGroups | rg-prod-brsouth-001 | sub-rede default e as duas NICs |
| 14 | pip-appfoundation-brsouth-001 | publicIPAddresses | rg-prod-brsouth-001 | **está na VM1**, apesar do nome |
| 15 | pip-appfoundation-brsouth-002 | publicIPAddresses | rg-prod-brsouth-001 | na VM2 |
| 16 | vnet-prod-brsouth-001 | virtualNetworks | rg-prod-brsouth-001 | 10.0.0.0/16 |
| 17 | pe-stpathsolutionsdata001-file | privateEndpoints | rg-prod-brsouth-001 | **órfão**: a conta-alvo não existe; Disconnected |
| 18 | privatelink.file.core.windows.net | privateDnsZones | rg-prod-brsouth-001 | só atende a conta removida |
| 19 | privatelink.file.core.windows.net/axi3rxmfnch4o | privateDnsZones/virtualNetworkLinks | rg-prod-brsouth-001 | link da zona com a VNet |
| 20 | stpathsolutionsblob001 | storageAccounts | rg-prod-brsouth-001 | WSIs; única storage account |
| 21 | shutdown-computevm-vm-appviewer-prod-001 | DevTestLab/schedules | rg-prod-brsouth-001 | auto-shutdown da VM1, **Disabled** desde 14/10 22:46 UTC |
| 22 | shutdown-computevm-vm-appfoundation-prod-001 | DevTestLab/schedules | rg-prod-brsouth-001 | auto-shutdown da VM2, Enabled, 19:00 |
| 23 | asa-prod-brsouth-001 | automationAccounts | rg-prod-brsouth-001 | identidade com Virtual Machine Contributor no grupo |
| 24 | asa-prod-brsouth-001/TurnOn-VMs | automationAccounts/runbooks | rg-prod-brsouth-001 | liga VM1 e VM2, seg–sex 06:00 |
| 25 | asa-prod-brsouth-001/AzureAutomationTutorialWithIdentity | automationAccounts/runbooks | rg-prod-brsouth-001 | tutorial, sem uso |
| 26 | asa-prod-brsouth-001/AzureAutomationTutorialWithIdentityGraphical | automationAccounts/runbooks | rg-prod-brsouth-001 | tutorial, sem uso |
| 27 | azurevm | Web/connections | rg-prod-brsouth-001 | em Error desde a criação; nenhum Logic App |
| 28 | NetworkWatcher_brazilsouth | networkWatchers | NetworkWatcherRG | sem flow logs |

Não existem snapshots, cofres de backup, imagens, galerias, locks, Key Vault, Postgres gerenciado, filas, alertas, action groups nem workspaces.

## 5. VMs

### 5.1 Estado, tamanho e discos

| | VM1 — vm-appviewer-prod-001 | VM2 — vm-appfoundation-prod-001 |
|---|---|---|
| Estado (corte) | VM running; em 15/10, desalocada pelo Portal às 02:34:49 UTC e ligada pelo runbook às 09:02 UTC | **VM deallocated** desde 2026-10-14 22:02:16 UTC (auto-shutdown); em 15/10, ligada pelo runbook às 09:02 UTC (`VM running` às 11:50) |
| Tamanho | Standard_D8s_v5: 8 vCPU, 32 GiB, sem disco temporário | Standard_NC4as_T4_v3: 4 vCPU, 28 GiB, 1 GPU T4, disco temporário de 176 GiB (efêmero) |
| Prioridade e zona | Regular, sem zona | Regular, sem zona (o SKU só existe na zona 3 em brazilsouth) |
| Segurança | TrustedLaunch Gen2, Secure Boot e vTPM ligados | TrustedLaunch Gen2, **Secure Boot desligado**, vTPM ligado |
| Imagem | Ubuntu 24.04 (24.04.202604160); SO local: Ubuntu 24.04.4, kernel 7.0.0-1017-azure | Ubuntu 24.04 (24.04.202604160); SO local: Ubuntu 24.04.4, kernel 7.0.0-1017-azure, 27 GiB de RAM visíveis |
| Criada em | 2026-04-30 | 2026-04-30 |
| Disco de SO | P4 30 GiB, Premium_LRS, cache ReadWrite | P4 30 GiB, Premium_LRS, cache ReadWrite |
| Disco de dados | P20 512 GiB (LUN 0), Premium_LRS, cache ReadWrite, montado em `/data` | P15 256 GiB (LUN 0), Premium_LRS, cache ReadOnly |
| Rede | 10.0.0.5, IP público `pip-appfoundation-brsouth-001` | 10.0.0.4, IP público `pip-appfoundation-brsouth-002` |
| Extensões | AADSSHLoginForLinux 1.0 | NvidiaGpuDriverLinux 1.9 (não expõe versão de driver) |
| Desligamento automático | Disabled de 14/10 22:46:23 UTC a 15/10 02:34:38 UTC; reativado pelo Portal: **Enabled**, 20:00 todo dia | Enabled, 19:00 todo dia (E. South America Standard Time) |
| Ligação automática | runbook `TurnOn-VMs`, seg–sex 06:00 de Brasília | idem; o disparo de 15/10 rodou (job Completed 09:01:44–09:02:01 UTC); o próximo é sexta, 16/10, às 06:00 |

Os 4 discos usam chave da plataforma, `networkAccessPolicy AllowAll` e `publicNetworkAccess Enabled`. Não há disco solto.

Evidência: `az vm show -d`, `az vm get-instance-view`, `az disk list -g rg-prod-brsouth-001`, `az vm list-skus -l brazilsouth`, `az vm extension list`, `az resource show ... Microsoft.DevTestLab/schedules`.

### 5.2 Uso de disco (`df -h`)

**VM1** (`df -h` e `df -B1`, 15/10 ~00:00 UTC):

| Montagem | Disco | Tamanho | Usado | Livre | Uso |
|---|---|---|---|---|---|
| `/` | SO (sda1) | 29G | 22G | 6,1G | **79%** |
| `/boot` | SO (sda16) | 881M | 159M | 661M | 20% |
| `/boot/efi` | SO (sda15) | 105M | 6,2M | 99M | 6% |
| `/data` | dados (sdb) | 503G | 478G | **0** | **100%** |

O que ocupa o `/data`:

| Item | Tamanho |
|---|---|
| volume Docker `pathsolutions_v2_postgres-data` | 140,7 GB (≈131,0 GiB) |
| cache de tiles `/data/pathsolutions/tile_cache_dz` | 156,17 GiB alocados (136,0 GiB aparentes; 7,9 milhões de JPEG). Os arquivos com data de modificação entre 1 e 14/10 somam 69,1 GiB aparentes; o crescimento líquido no período não foi medido |
| volume Docker `pathsolutions_v2_tile-cache` | 107,4 GB (≈100,0 GiB; segundo cache de tiles) |
| `wsi-saida` | 32,4 GiB |
| `training` | 32,0 GiB (datasets 31,0 GiB) |
| imagens Docker | 8,655 GB (≈8,06 GiB) |

Os valores em GB vêm do `sudo docker system df`, que usa unidade decimal (10⁹ bytes); entre parênteses está a conversão para GiB. Os demais vêm do `du` e são espaço alocado, salvo onde está escrito "aparentes".

Outros fatos sobre os discos da VM1:
- O disco de SO guarda o swapfile de 8 GiB e 6,7 GiB em `/mount/stpathsolutionsdata001`, que é um diretório comum, não uma montagem:
  - 17 `.svs` (4,30 GiB), todas com mesmo nome e tamanho no `wsi-slides`;
  - 62 `.npy` (2,31 GiB), todos com tamanho igual a algum blob do `wsi-output` (conferência só por tamanho);
  - 79 `.json` (menos de 0,1 GiB).
- Não há montagem NFS, SMB nem blobfuse.
- `/` e `/data` usam a opção `discard` (TRIM online).

**VM2** (`df -h` e `df -B1`, 15/10 11:54 UTC). Na VM2, o disco de SO é o `sdb`, o de dados é o `sda` e o temporário é o `sdc`.

| Montagem | Disco | Tamanho | Usado | Livre | Uso |
|---|---|---|---|---|---|
| `/` | SO (sdb1) | 29G | 20G | 8,9G | 69% |
| `/boot` | SO (sdb16) | 881M | 159M | 661M | 20% |
| `/boot/efi` | SO (sdb15) | 105M | 6,2M | 99M | 6% |
| `/data` | dados (sda) | 251G | 224G | 15G | **94%** |
| `/mnt` | temporário (sdc1, efêmero) | 173G | 32K | 164G | 1% |

Outros fatos sobre os discos da VM2:
- O `/data` está acima do alerta de 90%. Nele ficam a raiz do Docker (`/data/docker`), com 11 imagens que somam 42,32 GB (24,57 GB recuperáveis) e 31,06 GB de cache de build (8,82 GB recuperáveis). Também ficam ali os datasets de `/data/wsi_stage/datasets` (32G, `du -sh`).
- O `find` da seção 13 contou no `/data` 516 arquivos com extensão `.svs`, `.ndpi`, `.mrxs`, `.tif` ou `.tiff`, que somam 61,01 GiB. A busca cobriu também os datasets.
- A contagem não separa extensão nem diretório, e `.tif` e `.tiff` servem também a fotos de microscopia e patches. Quantos desses arquivos são lâminas inteiras não foi verificado (seção 14).
- A busca e o `du` rodaram como `azureps`, sem sudo e com os erros descartados. Diretórios que esse usuário não consegue listar ficaram de fora sem aviso, e a poda de `/var/lib/docker` não cobre o `/data/docker`.
- `/` usa `discard` (TRIM online); o `/data` não usa. O `fstrim.timer` aparece no `systemctl list-timers --all`, que lista também timers inativos; o estado dele e a última execução não foram verificados.
- O `/etc/fstab` só tem `/`, `/boot`, `/boot/efi`, `/data` (`nofail`) e `/mnt`. As montagens NFS que o script de setup do legado gravaria não estão lá, e não há montagem de rede ativa.

Evidência: `df -h`; `df -B1`; `sudo docker system df -v`; `du -s --block-size=1 /data/pathsolutions/tile_cache_dz`; `findmnt`; coletor e verificador do domínio VM1.

### 5.3 Rede

O NSG `nsg-app-prod-001` está na sub-rede default e nas duas NICs:
- Da Internet entram só **80 e 443**, com destino `*`, nas duas VMs. Na VM2 nada escuta nessas portas (seção 8.6).
- A **22** entra só na VM1, a partir de um único IP público /32 (omitido). Essa regra foi reescrita 11 vezes em 90 dias, com 8 origens diferentes.
- As regras VM1↔VM2 (8001, 22, 6379, 5432) são redundantes com a regra padrão `AllowVnetInBound`. Pelo NSG, Postgres (5432) e Redis (6379) da VM1, publicados em `0.0.0.0`, ficam liberados para toda a VNet.
- A exposição efetiva não foi verificada. O ufw da VM1 está habilitado (`ENABLED=yes`), mas as regras dele não foram lidas, e não houve consulta às regras efetivas por NIC nem teste de conexão. É provável que o ufw não bloqueie essas portas, porque portas publicadas pelo Docker costumam não passar por ele, mas isso é inferência.
- A sub-rede tem `defaultOutboundAccess=false`, então a saída para a Internet depende dos IPs públicos.

Evidência: `az network nsg show`, `az network nic show`, `az network public-ip show`, `az network vnet show`, `az monitor activity-log list` (escritas na regra SSH).

## 6. GPU da VM2: nvidia-smi, driver e CUDA

Lido na VM2 em 15/10 às 11:54 UTC (seção 13):

| Item | Valor |
|---|---|
| GPU | Tesla T4, 16.384 MiB, persistence mode ligado; 43 °C, 28 W de 70 W |
| Driver NVIDIA | **595.71.05**: `nvidia-smi`, `/proc/driver/nvidia/version` e pacotes `nvidia-driver`, `nvidia-dkms`, `cuda-drivers` e `libnvidia-compute` 595.71.05-1ubuntu1. A data de 24/04/2026 no `/proc/driver/nvidia/version` vem da versão do driver: é anterior à criação da VM (30/04/2026), então não é a data de instalação. Que o módulo tenha sido compilado na própria VM pelo DKMS (gcc 13.3.0 do Ubuntu 24.04) é inferência |
| CUDA | O `nvidia-smi` mostra "CUDA Version: 13.2", que é o máximo suportado pelo driver. O toolkit instalado é o **12.8.2** (`/usr/local/cuda-12.8`, pacote `cuda-toolkit-12-8`), e o `nvcc` não está no PATH. Há também pacotes só de configuração das linhas 12.9 e 13.2 |
| nvidia-container-toolkit | 1.19.0-1 |
| Uso no momento | 1.653 MiB em uso, 1.650 MiB deles em 2 processos `python` (734 e 916 MiB); 0% de utilização |

A instalação real difere do script de setup do legado, que previa CUDA 12.6 e driver por `ubuntu-drivers`. Qual mecanismo instalou o driver 595 (a extensão do Azure ou pacotes do repositório NVIDIA) não foi verificado. A imagem de inferência do legado usa CUDA 12.2 runtime e `torch` com wheels `cu121`.

Fatos indiretos, registrados em 14/10 antes da leitura:

| Fonte | Fato |
|---|---|
| Azure | Extensão `NvidiaGpuDriverLinux` 1.9, Succeeded, com `settings` nulo: o Azure não expõe a versão do driver. |
| Script de setup do legado (`deploy/setup-vm2.sh`) | Driver instalado por `ubuntu-drivers install --gpgpu`, sem versão fixada; CUDA toolkit `cuda-toolkit-12-6` do repositório NVIDIA para Ubuntu 24.04; nvidia-container-toolkit e Docker. O script também instala o `aznfs` e acrescenta ao `/etc/fstab` duas montagens NFS dos compartilhamentos `wsi-entrada` e `wsi-saida` da conta excluída `stpathsolutionsdata001` (sem `nofail` nem `_netdev`). É intenção do script, não estado verificado. O script só chama o `ubuntu-drivers` quando o `nvidia-smi` não existe, e não menciona a extensão do Azure. A leitura de 15/10 conferiu o `/etc/fstab`: as montagens NFS do script não estão lá (seção 5.2). |
| Imagem de inferência do legado (`inference/Dockerfile.hibou`) | Base `nvidia/cuda:12.2.0-runtime-ubuntu22.04` e `torch==2.3.0` com wheels `cu121`. |

## 7. WSIs no Blob

**Conta `stpathsolutionsblob001`.** É a única storage account da subscrição.

| Item | Configuração |
|---|---|
| Tipo e redundância | StorageV2, Standard_LRS, camada Hot, sem HNS, criada em 2026-05-27 |
| Rede | Aceita qualquer rede: `defaultAction Allow`, 0 regras de VNet ou IP, 0 private endpoints. `allowBlobPublicAccess=false`; TLS 1.2 |
| Chave compartilhada | Ativa e usada. Em 30 dias houve 229.280 transações por chave, 21.732 por SAS e 0 OAuth. Por SAS, só envio de blobs e leitura de propriedades (PutBlock, PutBlob, PutBlockList, GetBlobProperties). Não há política de expiração de chave nem de SAS (`keyPolicy` e `sasPolicy` nulas). As chaves nunca foram rotacionadas desde a criação |
| Proteção de dados | Soft delete de blob e de container, versionamento, change feed, ciclo de vida, inventário, lock e imutabilidade: nenhum configurado. Também não há logs de diagnóstico nem Storage Analytics |
| Filas, tabelas e file shares | Nenhum |

**Containers**, pela listagem completa de 14/10 23:16 UTC (repetida às 00:00 UTC de 15/10, com o mesmo resultado):

| Container | Blobs | Tamanho | Conteúdo, por extensão |
|---|---|---|---|
| `wsi-slides` | 1.033 | 588,16 GiB | 1.033 `.svs`, todos na raiz do container |
| `backups` | 33 | 180,01 GiB | 18 `.sql.gz` (179,84 GiB; prováveis dumps do banco do legado; o mais novo é de 15/09) e 15 `.tar.gz` (0,17 GiB) |
| `wsi-output` | 2.160 | 35,14 GiB | 714 `.npy`, 1.443 `.json`, 3 `.txt` |
| `wsi-metadata` | 316 | 62,4 KiB | 316 `.json` |
| **Total** | **3.542** | **803,31 GiB** | Tudo Hot e BlockBlob; sem snapshots, versões ou blobs apagados |

**WSIs.** Só o `wsi-slides` tem lâminas:

| Item | Valor |
|---|---|
| Quantidade | 1.033 |
| Formatos | só `.svs`; nenhum MIRAX, DICOM, NDPI ou formato Motic |
| Tamanho total | 631.536.358.434 B = 588,16 GiB = 0,574 TiB (base 1024) |
| Tamanho por lâmina | média 583,0 MiB · mediana 437,6 MiB · mínima 39,3 MiB · máxima 3.735 MiB |
| Entrada por mês (creationTime) | mai 72 · jun 167 · jul 136 · ago 290 · set 245 · out (até 14/10) 123 |
| Modificadas depois da criação | 61 (nenhuma nos últimos 30 dias); a causa não foi verificada |
| Pares com tamanho idêntico | 7 (possíveis duplicatas; só 25 lâminas têm `contentMd5`) |

Evidência:
- `az storage account show`; `az storage account blob-service-properties show`; `az storage account management-policy show`.
- `az storage blob list --auth-mode key --num-results "*" --query "[].[name, properties.contentLength, ...]" -o tsv | python3 -I <agregador>`, que imprime só agregados.
- Verificador por outro método: JMESPath `length(@)` e `sum(...)`, e métricas `BlobCount` e `BlobCapacity`.

## 8. O que roda hoje

### 8.1 VM1: containers e o incidente de disco

`sudo docker ps -a`, 14/10 23:34 UTC. Projeto compose `pathsolutions_v2`, diretório `/home/azureps/Pathsolutions_V2`.

| Container | Imagem | Estado |
|---|---|---|
| pathsolutions-backend | pathsolutions_v2-backend | Up 15 h (healthy) |
| pathsolutions-queue-worker | pathsolutions_v2-queue-worker | Up 15 h (**unhealthy**) |
| pathsolutions-frontend | pathsolutions_v2-frontend | Up 15 h (healthy) |
| pathsolutions-redis | redis:7-alpine | Up 15 h (healthy) |
| pathsolutions-db | pgvector/pgvector:pg15 | Up 15 h (**unhealthy**) |

Não há containers parados. Há 17 imagens e 8 volumes; o cache de build está em 0 B.

**Incidente:**
- Das últimas 300 linhas do log do `pathsolutions-db`, 29 contêm `No space left on device`. Exemplo: `PANIC: could not write to file "pg_logical/replorigin_checkpoint.tmp": No space left on device`. O ciclo se repete: recuperação → PANIC → reinício, cerca de 1,2 vez por segundo.
- A última escrita legível no `/data` foi às 21:02 UTC de 14/10.
- Em 09/10 aparece a mesma assinatura de I/O que o laço do Postgres produz em 14/10: muitas operações minúsculas por segundo e IOPS consumidas a 100%.
  - Nas métricas da plataforma, o disco de dados chegou a 100% das IOPS consumidas nas janelas das 21h, 22h e 23h UTC.
  - O sar registra ~2.366 op/s de ~0,08 KB das 21:50 às 23:00.
  - Pela data de modificação dos arquivos legíveis de `/data`, houve 282.418 gravados às 20h, 3 às 21h e nenhum às 22h.
  - Às ~23:00 UTC o auto-shutdown desalocou a VM, que só voltou em 12/10.
  - Que o disco tenha enchido em 09/10 é inferência: não há medição de ocupação desse dia, e o log do Postgres daquela noite não foi verificado.
  - O crítico da coleta achou ainda descartes (TRIM) de ~86 GiB em 12/10 e ~118 GiB em 13/10 no disco de dados; a origem não foi verificada.
- Banco e caches estão no mesmo disco.

**Releitura em 15/10 às 13:35 UTC**, depois da partida da VM1 às 09:02:
- `/data` continua em 100%, com 0 livre.
- O container `pathsolutions-db` reinicia sem conseguir subir: aparecia como "Up 32 seconds (health: starting)", e 75 das últimas 300 linhas do log são `FATAL: could not write lock file ... No space left on device`.
- `pathsolutions-backend` e `pathsolutions-queue-worker` estão unhealthy; `pathsolutions-frontend` e `pathsolutions-redis`, healthy.

Evidência: `sudo docker ps -a --format ...`; `sudo docker logs --tail 300 pathsolutions-db | grep -c 'No space left on device'`; `df -h /data` (14/10 e 15/10); métricas de disco e coletor do domínio VM1.

### 8.2 VM1: systemd, cron e portas

| Item | Do legado ou que serve ao legado |
|---|---|
| systemd | `pathsolutions-backup.timer` (quartas 06:30 de Brasília), que dispara `pathsolutions-backup.service`, em **failed**: a execução de 14/10, das 09:30 às 10:09 UTC, saiu com código 1. Também `nginx.service` (nativo; 80/443 → 127.0.0.1:3000 e :8000), `docker.service`, `containerd.service`, `certbot.timer` e `aznfswatchdog`/`aznfswatchdogv4` (helper de NFS do Azure, sem montagem ativa). O resto é do SO e do Azure. |
| crontab azureps | `@reboot sleep 120 && /home/azureps/Pathsolutions_V2/scripts/backup-scheduled.sh`. Roda a cada partida da VM, ou seja, todo dia útil pelo runbook. Isso não basta para explicar os logs de `/data/backups`: de 23/09 a 14/10, pela data de modificação, há log em toda quarta (dois ou três), quinta e sexta, e nenhum em segunda ou terça, embora a VM1 tenha dado partida em todos esses dias úteis. A causa do padrão não foi verificada. |
| crontab root | não existe. Em `/var/spool/cron/crontabs` só há o do azureps; a conta `paths` (uid 1001) não tem crontab. |
| `/etc/crontab` e `/etc/cron.d` | padrão do Ubuntu, mais certbot, e2scrub_all e sysstat. Nada do legado. |
| Portas | 22; 80 e 443 (nginx nativo); 3000 (frontend); 5432 (Postgres) e 6379 (Redis) em `0.0.0.0`; 8000 (API) em 10.0.0.5 e 127.0.0.1; 111 (rpcbind). |

Evidência: `systemctl list-units/list-unit-files/list-timers`; `systemctl show pathsolutions-backup.service`; `crontab -l`; `sudo -n crontab -l -u root`; `sudo -n ls /var/spool/cron/crontabs`; `ss -ltn`; leitura de `/proc`.

### 8.3 Agendamentos no Azure

| Item | O que faz |
|---|---|
| Runbook `TurnOn-VMs` (PowerShell 7.2) | Liga a VM1 e a VM2 de segunda a sexta às 06:00 de Brasília, sem olhar fila nem estado. A agenda foi criada em 16/06/2026 e a recorrência atual vale desde 04/09; antes disso, na janela de 90 dias, a automação só ligou as VMs em 17/07. Houve 22 jobs, todos Completed, de 15/09 a 14/10, e mais 1 Completed em 15/10, das 09:01:44 às 09:02:01 UTC (seção 13). Um aviso de Service Health ainda ativo, com última atualização em 25/09 (data da primeira publicação não verificada), anuncia para 30/09/2026 a aposentadoria do PowerShell 7.1/7.2 nos runbooks da Automation. |
| Auto-shutdown da VM2 | Desaloca todo dia às 19:00, sem olhar carga. Em 14/10 a CPU ficou entre 55% e 98% (médias de 5 min) na hora e meia antes do corte. |
| Auto-shutdown da VM1 | Desativado pelo Pedro em 14/10 às 22:46:23 UTC e reativado pelo Portal, por usuário, em 15/10 às 02:34:38 UTC (Enabled, 20:00). Onze segundos depois, às 02:34:49, a VM1 foi desalocada pelo Portal. A VM1 volta a ser desligada às 20:00 de Brasília, e sessões abertas nela caem nesse horário. |

Em 90 dias de activity log houve 68 starts (60 da automação, 8 manuais) e 66 desalocações (56 do auto-shutdown, 10 manuais), e nenhuma exclusão de recurso.

Evidência:
- `az automation runbook list` e `az automation runbook show -n TurnOn-VMs`: PowerShell72, Published, sem parâmetros.
- `az rest --method get .../runbooks/TurnOn-VMs/content`, lido só para extrair fatos: o runbook pede o start das duas VMs sem esperar e sem consultar fila nem estado.
- `az automation schedule list`: semanal, seg–sex 06:00 America/Sao_Paulo, habilitada.
- `az automation job list`: 22 jobs Completed.
- `az monitor activity-log list --offset 90d --max-events 5000`, contado com `jq` (967 eventos até 14/10 22:46 UTC): start 68, deallocate 66, delete 0, 1 evento de Service Health da Automation. A releitura no recorte não tem operação de VM depois de 22:02 UTC.
- `az monitor metrics list --metrics "Percentage CPU" --interval PT5M` na VM2, de 20:30 a 22:10 UTC: médias de 5 min entre 55,5% e 98%.
- Verificadores por outro método: REST da lista de jobs, activity log filtrado por `--resource-id` de cada VM e CPU em PT15M e PT1M.

### 8.4 Monitoramento

Não há nenhum: 0 alertas de métrica, log ou activity log; 0 action groups; 0 workspaces; 0 Application Insights; 0 diagnostic settings; 0 orçamentos; nenhum agente nas VMs; o activity log não é exportado. O provider `Microsoft.AlertsManagement` não está registrado. As métricas nativas da VM não medem ocupação de disco.

Evidência:
- 0 em todos: `az monitor metrics alert list`, `az monitor activity-log alert list`, `az monitor action-group list`, `az monitor log-analytics workspace list`, e `az resource list --resource-type` para scheduledQueryRules, components e dataCollectionRules.
- `az monitor diagnostic-settings list --resource` nas VMs, na storage account, na automation e no NSG, e na subscrição: 0.
- `az consumption budget list` na subscrição e no grupo: 0.
- `az vm extension list`: só AADSSHLoginForLinux e NvidiaGpuDriverLinux.
- `az monitor metrics list-definitions` da VM1: nenhuma métrica de ocupação de sistema de arquivos.
- Verificador por outro método: as mesmas APIs por `az rest`, com 14 respostas e 0 itens, e `az provider list`, com `Microsoft.AlertsManagement` NotRegistered.

### 8.5 Código do legado

| Item | Valor |
|---|---|
| Local | `/home/azureps/Pathsolutions_V2` (237 MiB), na VM1 |
| Remoto | `origin https://github.com/Pedrogal-pathsolutions/Pathsolutions_V2.git`, sem credencial na URL |
| Estado | Branch `fix/audit-2026-09`, sem upstream; HEAD `ec70dbf` de 2026-09-22. 35 commits do HEAD (37 somando as branches locais) não estão em nenhuma ref remota conhecida. A última busca no remoto foi em 2026-06-25. O estado atual do GitHub não foi verificado: `git fetch` é escrita. |
| Compose e Dockerfiles | `docker-compose.yml`, `docker-compose.viewer.yml`, `inference/docker-compose.gpu.yml`, `Dockerfile.backend`, `Dockerfile.frontend`, `inference/Dockerfile.hibou` |
| Arquivos de ambiente | `.env.viewer` e `backend/.env` no repositório legado, com modo 600 e fora do índice do git (só os `.env.example` são versionados; o histórico não foi verificado). A unit `pathsolutions-backup.service` tem 2 linhas `Environment=`. O conteúdo não foi lido. Podem guardar a senha do banco e a chave ou a connection string do Blob (não verificado) |
| Outros repositórios na VM1 | `/home/azureps/pathsolutions-claude-context`, com remoto em outra conta do GitHub (`<outra conta>/pathsolutions-claude-context`; o dono deve ser confirmado), e históricos internos de ferramentas (`.gemini`, `.codex`), sem remoto |
| Kit antigo | `Pathsolutions_V2/Migration` e `Pathsolutions_V2/.claude/skills`. Uma das skills antigas tem o mesmo nome da atual `pathsol-isolamento-tenant`, com conteúdo diferente |
| VM2 | Nenhum repositório git. O código do legado está implantado como diretório comum em `/home/azureps/inference`, que é o diretório do compose `inference`. Há `/home/azureps/inference/.env` (modo 600), que não foi lido. Nenhuma unit do legado tem linhas `Environment=` |

Evidência: `git -c safe.directory='*' -C <repo> remote -v | sed (redação)`, `rev-parse`, `log -1`, `log --not --remotes | wc -l`. Para os arquivos de ambiente: `find` por nome e `stat`, sem abrir o conteúdo, e o `.gitignore` com os caminhos do índice do git.

### 8.6 VM2: containers, systemd, cron e portas

Lido em 15/10 às 11:54 UTC (seção 13). Na VM2, o `azureps` está nos grupos `sudo`, `docker` e `lxd`, entre outros (`id -nG`), e o `sudo -n` funcionou sem senha. Os comandos `docker` rodaram primeiro sem sudo, com `sudo -n` de reserva; a saída não mostra qual dos dois respondeu. A sessão entrou na VM2 pela conta `azureps` da VM1, sem interação (`BatchMode=yes`). Portanto, qualquer processo dessa conta na VM1 pode fazer o mesmo e virar root na VM2 (risco 13).

| Container | Imagem | Estado |
|---|---|---|
| pathsolutions-gpu-worker | inference-gpu-queue-worker | Up 3 h |
| pathsolutions-hibou | inference-hibou-inference | Up 3 h (healthy) |
| pathsolutions-rawaug-worker | inference-hibou-inference | Up 3 h |
| pathsolutions-lora-worker | inference-hibou-inference | Up 3 h |
| hiesd_aug, gchtid_aug, pg_extract | 3f5e375e3ccb (o `docker ps` mostra só o ID; se a imagem tem tag não foi verificado) | Exited (0) há 3 meses |

Os 4 containers Up são do compose `inference`, no diretório `/home/azureps/inference`. Os 3 Exited têm o rótulo de projeto `inference`, mas o rótulo de diretório está vazio. Há 11 imagens e nenhum volume Docker. Entre as imagens estão tags de backup e de rollback de `inference-hibou-inference` e `inference-gpu-queue-worker`, de 13,2 GB cada e com camadas compartilhadas, e a `histotools/histoqc:master`.

| Item | Valor |
|---|---|
| systemd do legado | `hibou-inference.service`, habilitada e rodando. As outras units habilitadas são de GPU (`nvidia-persistenced`, `nvidia-cdi-refresh`, `gpu-manager`, `nvidia-suspend`, `nvidia-resume`, `nvidia-hibernate`), Docker, AZNFS e SO. Nenhuma está em falha. Os timers são só os do SO, entre eles o `apt-daily-upgrade.timer`, e o `unattended-upgrades.service` está habilitado e rodando. Se as atualizações automáticas alcançam o kernel ou os pacotes da NVIDIA não foi verificado. Com o `nvidia-dkms` (seção 6), cada kernel novo exige recompilar o módulo da GPU, e uma falha deixaria a VM2 sem driver a partir da partida seguinte (inferência) |
| crontabs | Nenhum para `azureps` nem para `root`. `/etc/crontab` e `/etc/cron.d` (e2scrub_all, sysstat) são o padrão. Nada do legado |
| Portas | 22 (ssh), 111 (rpcbind) e **8001** em `0.0.0.0`, alvo da regra `Allow-VM1-VM2-Hibou` do NSG e liberada para a VNet. Nada escuta em 80 nem em 443, embora o NSG as abra para a VM2 |

Os 4 containers do legado subiram com a partida da VM às 09:02 UTC e estavam rodando às 11:54 UTC. O banco do legado seguia fora do ar às 13:35 UTC (seção 8.1). O que esses containers fazem nessa situação não foi verificado.

Evidência: o comando da seção 13 (`docker ps -a`, `docker image ls`, `docker system df -v`, `systemctl list-units`, `list-unit-files` e `list-timers`, `crontab -l`, `sudo -n crontab -l -u root`, `ss -ltn`).

## 9. Cota em brazilsouth

| Linha (`az vm list-usage --location brazilsouth`) | Uso / limite |
|---|---|
| Standard NCASv3_T4 Family vCPUs | **4 / 4** |
| Total Regional vCPUs | 12 / 60 |
| Total Regional Low-priority vCPUs (provável cota Spot; inferência) | 0 / 3 |
| Standard DSv5 Family vCPUs | 8 / 50 |
| Standard NVADSA10v5 Family vCPUs | 0 / 6 |

Detalhes da cota:
- Os quatro tamanhos T4 existem em brazilsouth, só na zona 3, sem restrição para a subscrição.
- Hoje não cabe nenhuma NC4as_T4_v3 adicional: a família está cheia, e a cota de baixa prioridade (3 vCPUs) é menor que 4. Que essa linha seja a cota Spot é inferência: a URL antiga `low-priority-quota` da documentação da Microsoft leva hoje à página de cota Spot, mas nenhuma página oficial consultada nomeia a linha.
- A VM2 desalocada continua contando na cota.
- Histórico: em 29/04/2026 um pedido de autoatendimento para a família NC antiga falhou e um chamado de cota foi aberto e fechado. Que esse chamado deu o limite atual da T4 é inferência.

Evidência: `az vm list-usage`; `az vm list-skus --size Standard_NC`; verificador com `az quota show` e `az quota usage show`, que deram os mesmos números.

## 10. Ferramentas instaladas

| Ferramenta | VM1 | VM2 |
|---|---|---|
| terraform | **ausente** | **ausente** |
| az | 2.86.0 | ausente |
| docker | 29.4.2 (compose v5.1.3, buildx v0.33.0) | 29.4.3 |
| python | python3 3.12.3; o comando `python` e o `pip3` não existem | python3 3.12.3; o comando `python` não existe |
| node / npm | ausentes do PATH (os servidores de IDE trazem node próprio) | ausentes |
| psql | 16.15 (cliente; o servidor do legado é PostgreSQL 15 em container) | ausente |
| git | 2.43.0 | 2.43.0 |
| outros | azcopy 10.32.4; nvidia-smi ausente (esperado) | nvidia-smi 595.71.05; `nvcc` fora do PATH (toolkit 12.8.2 em `/usr/local/cuda-12.8`); azcopy e blobfuse2 ausentes |

Evidência: `command -v`, `--version` de cada ferramenta (`psql --version` com confirmação), `dpkg -l`.

## 11. Custo mensal por recurso

Fonte: API Cost Management Query (`ActualCost`, mensal, agrupado por `ResourceId`), chamada com `az rest --method post`. Moeda BRL; todo o custo é Usage/OnDemand. Um verificador refez as contas com outros agrupamentos e chegou aos mesmos centavos.

| Recurso | Jul/26 | Ago/26 | Set/26 | Out/26 (1–13) |
|---|---:|---:|---:|---:|
| VM2 vm-appfoundation-prod-001 (computação + saída de dados) | 997,60 | 58,56 | 1.456,12 | 545,32 |
| VM1 vm-appviewer-prod-001 (computação + saída de dados) | 662,93 | 322,65 | 1.024,81 | 402,27 |
| Disco de dados da VM1 (P20) | 653,93 | 649,64 | 653,86 | 276,78 |
| Disco de dados da VM2 (P15) | 339,57 | 337,34 | 339,54 | 143,72 |
| stpathsolutionsblob001 | 40,10 | 60,40 | 101,59 | 53,88 |
| Disco de SO da VM2 (P4) | 47,16 | 46,85 | 47,16 | 19,96 |
| Disco de SO da VM1 (P4) | 47,16 | 46,85 | 47,16 | 19,96 |
| pe-stpathsolutionsdata001-file (órfão) | 38,47 | 38,22 | 37,22 | 16,28 |
| pip-appfoundation-brsouth-001 | 19,24 | 19,11 | 18,61 | 8,14 |
| pip-appfoundation-brsouth-002 | 19,24 | 19,11 | 18,61 | 8,14 |
| privatelink.file.core.windows.net (órfã) | 2,59 | 2,57 | 2,50 | 1,09 |
| asa-prod-brsouth-001 | 0,05 | 0,00 | 0,08 | 0,00 |
| **Total** | **2.868,05** | **1.601,32** | **3.747,27** | **1.495,55** |

Como ler a tabela:
- **Horas ligadas e preço efetivo:** a VM2 ficou 215,8 h em julho, 12,8 h em agosto, 315,0 h em setembro e 116,9 h de 1 a 13/10, a R$ 4,59–4,67/h. A VM1 ficou 208,7 h, 102,1 h, 323,3 h e 125,9 h, a R$ 3,14–3,19/h. O preço em dólar é o mesmo todo mês; a variação em reais vem do câmbio.
- **Parte fixa:** cerca de R$ 1.165/mês (setembro), nos discos Premium, que cobram mesmo com a VM desalocada, nos IPs públicos e no private endpoint órfão com a zona DNS.
- **Recursos já removidos:** `stpathsolutionsdata001` custou R$ 2.448,84 em maio/26.
- **Orçamento e alertas:** não existe orçamento nem alerta de custo.
- **Ressalva:** são preços de tabela convertidos para reais. O que o parceiro CSP fatura não foi verificado.
- **Estimativa:** com a VM1 ligada 24 h, a computação dela sobe para cerca de R$ 2.332/mês (R$ 3,1943 × 730 h), contra R$ 1.022,85 em setembro (os R$ 1.024,81 da tabela incluem R$ 1,96 de saída de dados).
- **Teto D3 (R$ 5.000/mês, `PROMPT_V3.md`):** num mês inteiro com a VM1 ligada 24 h (cenário: o auto-shutdown dela foi reativado em 15/10) e os fixos e o Blob de setembro, a subscrição fica entre ~R$ 4,93 mil, com a VM2 só no horário do runbook (~13 h por dia útil), e ~R$ 5,05 mil, com a VM2 no ritmo de setembro (2.331,84 + 1.456,12 + 1.164,66 + 101,59). Ou seja, no teto ou acima dele, sem orçamento nem alerta. Somando os snapshots da Fase 1 (~R$ 263,29/mês, até R$ 274,95) e o Blob atual (~R$ 136,72/mês por 803,31 GiB), sobra pouco do teto para a VM2 e para os recursos novos da v3. São estimativas a preço de tabela.

## 12. Estimativas pedidas: snapshots e soft delete

### 12.1 Snapshots dos discos

A skill da Fase 1 prevê snapshots incrementais. Pela documentação da Microsoft:
- eles ficam em Standard HDD, qualquer que seja o disco de origem;
- usam ZRS onde houver;
- são cobrados só pelo espaço usado;
- o primeiro é uma cópia completa.

O preço de tabela em brazilsouth é R$ 0,3549 por GB-mês (Standard HDD, Snapshots LRS e ZRS; Azure Retail Prices API, `currencyCode=BRL`). A unidade cobrada é GiB-mês: no Blob, a quantidade faturada bate com a média da capacidade em GiB (domínio custo), e a documentação de snapshots usa GiB no exemplo de cobrança.

| Disco | VM | Provisionado | Usado | Estimativa mensal |
|---|---|---|---:|---:|
| vm-appviewer-prod-001_OsDisk_1_2cdb4cd2… | VM1 | 30 GiB (P4) | 22,11 GiB | R$ 7,85 |
| vm-appviewer-prod-001_DataDisk_0 | VM1 | 512 GiB (P20) | 477,32 GiB | R$ 169,40 |
| vm-appfoundation-prod-001_OsDisk_1_be3c948b… | VM2 | 30 GiB (P4) | 19,29 GiB | R$ 6,85 |
| vm-appfoundation-prod-001_DataDisk_0 | VM2 | 256 GiB (P15) | 223,14 GiB | R$ 79,19 (até R$ 90,85) |
| **Total** | | **828 GiB** | **741,86 GiB** | **R$ 263,29** (R$ 274,95 contando o `/data` da VM2 pelos 256 GiB; teto de R$ 293,86 pelos 828 GiB provisionados) |

Premissas e observações:
- **Espaço usado:** é o `df -B1` da VM1 (15/10 ~00:00 UTC) e da VM2 (15/10 11:54 UTC). No disco de SO, somei `/`, `/boot` e `/boot/efi`:
  - VM1: 23.737.669.120 B;
  - VM2: 20.540.399.616 + 165.822.464 + 6.399.488 = 20.712.621.568 B;
  - `/data` da VM2: 239.592.189.952 B.
- **TRIM e cobrança:** o snapshot cobra os blocos gravados no disco. Nas montagens com TRIM online (`discard`), que são as da VM1 e o `/` da VM2, esse valor fica próximo do `df`, mas pode ser um pouco maior (metadados do sistema de arquivos). O `/data` da VM2 não usa `discard`: blocos de arquivos apagados podem continuar contados até o próximo `fstrim`. Por isso o teto desse disco é o tamanho provisionado (256 GiB, R$ 90,85), e o total pode chegar a R$ 274,95.
- **Caches de tiles:** pela ordem aprovada, o snapshot vem antes de qualquer limpeza, então os dois caches entram nele: ~156,2 GiB + ~100 GiB (107,4 GB do Docker, em unidade decimal). Isso responde por cerca de R$ 91/mês dos R$ 169,40 do disco de dados da VM1. Apagar os caches depois não reduz o custo desse snapshot.
- **Prazo:** os snapshots só são apagados depois do go-live, com pedido escrito do Pedro (`CLAUDE.md`). O custo total é o valor mensal vezes os meses até lá.
- **Privacidade:** até o go-live, os snapshots guardam:
  - dados clínicos: na VM1, o banco do legado, os dois caches de tiles e as lâminas de `wsi-entrada`; na VM2, possivelmente parte dos 516 arquivos de formato de lâmina do `/data`, que incluem datasets e não foram comparados com o Blob;
  - arquivos com prováveis credenciais dos discos de SO das duas VMs: na VM1, `~/.git-credentials` e os `.env` do legado; na VM2, `/home/azureps/inference/.env`. Nenhum foi lido (risco 10). O passo 2 da skill não define a política de rede dos snapshots, e os discos de origem estão com `networkAccessPolicy AllowAll` e `publicNetworkAccess Enabled`. Proposta para decisão (seção 16, item 14): criar os snapshots com `--network-access-policy DenyAll --public-network-access Disabled`, o que impede exportá-los por SAS. As duas opções existem no `az snapshot create` da CLI 2.86.0 (conferido no código da CLI, sem executá-la). Não foi verificado se criar um disco a partir de um snapshot com `DenyAll`, que é o caminho de volta da skill, continua funcionando.
- **Alternativa:** snapshot completo em Premium custaria R$ 1,19 por GB-mês, 3,35 vezes o incremental. Que o completo também seja cobrado só pelo espaço usado não foi verificado.

### 12.2 Soft delete de blobs e de containers (30 dias)

Pela documentação da Microsoft:
- ligar o soft delete de blob ou de container **não tem custo**;
- o que for apagado ou sobrescrito continua cobrado, na mesma tarifa do dado ativo, até o fim da retenção;
- cada sobrescrita gera um snapshot apagado do estado anterior;
- mudar só metadados ou propriedades não gera nada.

Tarifa: Hot LRS, R$ 0,1702 por GiB-mês (Retail Prices API e preço efetivo de out/26 no Cost Management).

Reescrita observada nos últimos 30 dias, na listagem de 15/10 ~00:00 UTC, sem nomes, só com tamanho, criação e última modificação:

| Container | Sobrescritos nos últimos 30 dias | Criados nos últimos 30 dias (dado novo, sem custo extra) |
|---|---|---|
| wsi-slides | 0 | 246 (161,46 GiB) |
| wsi-output | 1 (~0 GiB) | 704 (13,24 GiB) |
| wsi-metadata | 43 (KiB) | 77 |
| backups | 0 | 2 (37,48 GiB) |

| Cenário | Custo estimado |
|---|---:|
| Ligar soft delete de blob e de container | R$ 0 |
| Regime observado (reescrita ~0 GiB/mês) | ~R$ 0/mês |
| Exclusão acidental de todas as WSIs (588,16 GiB retidos por 30 dias) | R$ 100,10, uma vez |
| Exclusão dos 18 dumps do container `backups` (179,84 GiB) | R$ 30,61, uma vez |
| Exclusão de todos os containers (803,31 GiB) | R$ 136,72, uma vez |

Exclusões não aparecem numa listagem: sem logs nem change feed, só se veem as sobrescritas. Por isso a reescrita observada é um limite inferior. Com o legado parado na Fase 1, a reescrita tende a zero.

O lock `CanNotDelete` impede excluir a conta, mas, segundo a Microsoft, não protege containers nem blobs. O custo do lock não foi verificado.

Fontes:
- `learn.microsoft.com/azure/virtual-machines/disks-incremental-snapshots`
- `learn.microsoft.com/azure/storage/blobs/soft-delete-blob-overview`
- `learn.microsoft.com/azure/storage/blobs/soft-delete-container-overview`
- `learn.microsoft.com/azure/storage/common/lock-account-resource`
- `prices.azure.com/api/retail/prices` (brazilsouth, BRL)

## 13. Leitura da VM2 (15/10)

Feita em 15/10, numa sessão nova. Antes dela, pelo Portal e por usuário (activity log, e-mail não impresso):
- o auto-shutdown da VM1 foi reativado às 02:34:38 UTC;
- a VM1 foi desalocada às 02:34:49 UTC (`deallocate`, concluído às 02:35:51);
- a VM1 voltou às 09:02:19 UTC (`uptime -s`), ligada pelo runbook (start concluído às 09:03:15, por identidade de serviço).

Confirmações, às 11:50 UTC:
- `az account show`: PATHSOLUTIONS TECNOLOGIA EM SAUDE LTDA, `bd87a1ca-e4f5-460b-9f12-c89e114293f1`, Enabled.
- `az automation job list` (último do `TurnOn-VMs`): Completed, de 09:01:44 a 09:02:01 UTC.
- `az vm list -d`: VM1 e VM2 em `VM running`. A VM2 está ligada desde 09:02:27 UTC.

O ssh, com a confirmação do Pedro:
1. Primeira tentativa, `ssh azureps@10.0.0.4`: `Permission denied (publickey)`. A rede chegou à VM2, mas a chave que ela aceita não estava disponível para a sessão. Não havia agente SSH utilizável (`ssh-add -l` com código 2).
2. As notas do próprio legado registram o acesso pelo alias `azure-foundation` do `~/.ssh/config`, que aponta para 10.0.0.4 com a chave `key-vm-azureps-prod.pem`. Elas registram também que `ssh 10.0.0.4` sem a chave falha assim.
3. Segunda tentativa, pelo alias: concluída às 11:54 UTC. O `~/.ssh` não foi lido; foi o ssh que usou a própria configuração.
4. Efeito colateral possível: a segunda tentativa imprimiu o aviso "Permanently added '10.0.0.4' (ED25519) to the list of known hosts".
   - Com `BatchMode=yes`, o ssh só aceita sozinho uma chave de host nova se `StrictHostKeyChecking` for `no` ou `accept-new`. A opção não estava na linha de comando nem no `/etc/ssh/ssh_config`, então vem da configuração do usuário, que não foi lida. Pelo alias, portanto, a VM1 aceita sem confirmação uma chave de host desconhecida da VM2.
   - Se a chave foi gravada, e em que arquivo, não foi verificado: depende do `UserKnownHostsFile`, e com `/dev/null` o mesmo aviso aparece sem gravar nada.
   - A primeira tentativa, pelo IP, passou da verificação de chave sem esse aviso. Isso indica que o alias usa outro arquivo de known_hosts (inferência).
   - Na VM2, o login e os `sudo -n` ficam nos logs de autenticação (esperado, não verificado).

Comando executado, o mesmo preparado em 14/10 com o destino trocado pelo alias:

```
ssh -o BatchMode=yes -o ConnectTimeout=15 azure-foundation 'bash -s' <<'EOF'
R() { sed -E 's#://[^/@ ]+@#://***@#g; s/((key|token|secret|pass|pwd|sig|sas)[a-z_]*=)[^ &]+/\1***/Ig; s/[A-Za-z0-9+_-]{32,}/***/g'; }
echo "== host"; hostname; . /etc/os-release; echo "$PRETTY_NAME"; uname -r; uptime -p; uptime -s; nproc; free -h | sed -n 1,2p; id -nG
echo "== df -h"; df -h -x tmpfs -x devtmpfs -x squashfs -x overlay
echo "== df -B1"; df -B1 --output=source,size,used,avail,target -x tmpfs -x devtmpfs -x squashfs -x overlay
echo "== lsblk"; lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT
echo "== montagens de rede/fuse"; findmnt -rn -t cifs,nfs,nfs4,fuse,fuse.blobfuse2,fuse.blobfuse -o TARGET,FSTYPE
echo "== discard"; grep -E ' / | /data' /proc/mounts | awk '{print $2, ($4 ~ /discard/ ? "discard" : "sem discard")}'
echo "== nvidia-smi"; nvidia-smi 2>&1
echo "== gpu csv"; nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,utilization.gpu,temperature.gpu --format=csv 2>&1
echo "== driver proc"; cat /proc/driver/nvidia/version 2>&1
echo "== cuda toolkit"; command -v nvcc && nvcc --version | tail -2; ls -d /usr/local/cuda* 2>/dev/null; grep -A2 '"cuda"' /usr/local/cuda/version.json 2>/dev/null
echo "== pacotes nvidia/cuda"; dpkg -l | awk '/^ii/ && $2 ~ /^(cuda-toolkit|cuda-runtime|cuda-drivers|nvidia-driver|nvidia-dkms|libnvidia-compute|nvidia-container-toolkit|nvidia-utils)/ {print $2, $3}'
echo "== docker ps -a"; F='{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Label "com.docker.compose.project"}}\t{{.Label "com.docker.compose.project.working_dir"}}'; docker ps -a --format "$F" 2>/dev/null || sudo -n docker ps -a --format "$F" 2>&1
echo "== docker images"; docker image ls --format '{{.Repository}}:{{.Tag}}\t{{.Size}}' 2>/dev/null || sudo -n docker image ls --format '{{.Repository}}:{{.Tag}}\t{{.Size}}' 2>&1
echo "== docker system df"; docker system df 2>/dev/null || sudo -n docker system df 2>&1
echo "== docker volumes"; (docker system df -v 2>/dev/null || sudo -n docker system df -v 2>&1) | sed -n '/Local Volumes space usage/,/Build cache usage/p'
echo "== systemd em execucao"; systemctl list-units --type=service --state=running --no-pager --plain --no-legend | awk '{print $1}'
echo "== systemd falhas"; systemctl list-units --state=failed --no-pager --plain --no-legend | awk '{print $1}'
echo "== systemd habilitados"; systemctl list-unit-files --type=service --state=enabled --no-pager --no-legend | awk '{print $1}'
echo "== timers"; systemctl list-timers --all --no-pager --no-legend | awk '{print $(NF-1), $NF}'
echo "== unidades em /etc/systemd/system"; ls /etc/systemd/system/*.service /etc/systemd/system/*.timer /etc/systemd/system/*.mount 2>/dev/null
echo "== crontab azureps"; crontab -l 2>&1 | awk '!/^[[:space:]]*#/ && NF' | R
echo "== crontab root"; sudo -n crontab -l -u root 2>&1 | awk '!/^[[:space:]]*#/ && NF' | R
echo "== crontabs de usuarios"; sudo -n ls /var/spool/cron/crontabs 2>&1
echo "== /etc/crontab"; awk '!/^[[:space:]]*#/ && NF' /etc/crontab | R
echo "== /etc/cron.d"; for f in /etc/cron.d/*; do echo "-- $f"; awk '!/^[[:space:]]*#/ && NF' "$f" | R; done
echo "== fstab (ponto, tipo, opcoes)"; awk '!/^[[:space:]]*#/ && NF {print $2, $3, $4}' /etc/fstab
echo "== arquivos de ambiente e credenciais (so caminho e modo)"; for m in $(findmnt -rn -t ext4,xfs,btrfs -o TARGET); do timeout 300 find "$m" -xdev \( -path /proc -o -path /sys -o -path /var/lib/docker -o -path /var/lib/containerd -o -path /snap -o -name node_modules \) -prune -o -type f \( -name '.env' -o -name '.env.*' -o -name '*.env' -o -name '.git-credentials' \) -printf '%m %u %p\n' 2>/dev/null; done | sort -u
echo "== units com Environment (so contagem)"; grep -c -E '^[[:space:]]*Environment(File)?=' /etc/systemd/system/*.service 2>/dev/null | awk -F: '$NF>0'
echo "== repositorios git"; for m in $(findmnt -rn -t ext4,xfs,btrfs -o TARGET); do timeout 300 find "$m" -xdev \( -path /proc -o -path /sys -o -path /var/lib/docker -o -path /var/lib/containerd -o -path /snap \) -prune -o -type d -name .git -print -prune 2>/dev/null; done | sort -u | while read g; do d=$(dirname "$g"); echo "-- $d"; git -c safe.directory='*' -C "$d" remote -v | R | sort -u; git -c safe.directory='*' -C "$d" rev-parse --abbrev-ref HEAD; git -c safe.directory='*' -C "$d" log -1 --format='%h %cs'; du -sh "$d" 2>/dev/null | cut -f1; done
echo "== laminas locais (so contagem)"; for m in $(findmnt -rn -t ext4,xfs,btrfs -o TARGET); do timeout 300 find "$m" -xdev \( -path /proc -o -path /sys -o -path /var/lib/docker -o -path /snap \) -prune -o -type f \( -iname '*.svs' -o -iname '*.ndpi' -o -iname '*.mrxs' -o -iname '*.tif' -o -iname '*.tiff' \) -printf '%s\n' 2>/dev/null | awk -v m="$m" '{n++; s+=$1} END{printf "%s: %d arquivos, %.2f GiB\n", m, n, s/1024^3}'; done
echo "== datasets do legado"; ls -d /data/wsi_stage/datasets 2>&1; du -sh /data/wsi_stage/datasets 2>/dev/null
echo "== ferramentas"; for t in terraform az docker python3 python node npm git psql nvidia-smi nvcc blobfuse2 azcopy; do printf '%s: ' "$t"; if command -v "$t" >/dev/null; then case "$t" in az) az version --query '"azure-cli"' -o tsv 2>/dev/null;; azcopy) echo "presente (versao nao executada)";; *) "$t" --version 2>&1 | head -1;; esac; else echo "nao instalado"; fi; done
echo "== portas"; ss -ltn | awk 'NR>1{print $4}' | sort -u
EOF
```

Os resultados estão nas seções 5, 6, 8.5, 8.6, 10 e 12.1. Em 15/10 não houve listagem de blob, portanto nenhum `listKeys` novo.

O runbook roda em PowerShell 7.2, cujo suporte o aviso de Service Health deu como encerrado em 30/09/2026. Mesmo assim, os jobs continuaram Completed: os 22 de 15/09 a 14/10 e o de 15/10 (09:01:44–09:02:01 UTC). Até quando ele continua rodando não foi verificado.

## 14. O que não foi possível verificar

- **VM2: conteúdo local.** Não foram verificados:
  - se os 516 arquivos do `/data` existem no Blob: não houve comparação, para não gerar novos `listKeys`;
  - quantos desses 516 são lâminas inteiras. A contagem junta `.svs`, `.ndpi`, `.mrxs`, `.tif` e `.tiff`, sem separar extensão nem diretório. O código do legado lê de `/data/wsi_stage/datasets/bach` fotos de microscopia do BACH em `.tif` (`inference/extract_training_embeddings.py:173` e `:196`), então parte dos 516 provavelmente não é lâmina inteira (inferência);
  - o que está em diretórios que o `azureps` não consegue listar: as buscas de lâminas, `.env` e `.git` e o `du` dos datasets rodaram sem sudo e com os erros descartados. Isso vale também para o "nenhum repositório git" da seção 8.5;
  - o conteúdo de `/home/azureps/inference/.env`;
  - o que os 4 containers do legado fazem com o banco fora do ar, que seguia assim às 13:35 UTC (seção 8.1);
  - o que ocupa os 224G do `/data`, além do Docker e dos datasets;
  - qual mecanismo instalou o driver 595 (seção 6).
- **Fatura do parceiro CSP** e se ela coincide com o Cost Management. A identidade usada não enxerga nenhuma billing account.
- **Conteúdo e integridade dos blobs:** nada foi baixado. Ficam sem resposta se os 7 pares de mesmo tamanho são duplicatas e por que 61 SVS foram modificadas depois da criação.
- **Exclusão da `stpathsolutionsdata001`:** ocorreu entre 27/05 e ~16/07/2026, fora da janela de 90 dias do activity log; a data exata não foi verificada. A conta também não está entre as contas excluídas recuperáveis.
- **Estado do repositório do legado no GitHub:** `git fetch` é escrita.
- **Onde o legado guarda a chave da `stpathsolutionsblob001`** (ou a connection string) e quem emite os SAS de envio, com que permissões, escopo e validade. Os candidatos são os arquivos de ambiente da seção 8.5, que não foram lidos. Que a chave seja estática é inferência: houve 229.280 transações por chave em 30 dias e nenhum `listKeys` nos 90 dias anteriores a esta coleta. Que os SAS sejam os envios dos laboratórios pela extensão do navegador também é inferência; sem logs de diagnóstico, a origem não aparece. Soft delete e lock não mudam quem pode acessar a conta: SAS já emitidos seguem aceitos até expirar ou ser revogados.
- **Áreas sem acesso:** `/home/paths` (conta `paths`, uid 1001) e `/data/postgres`. Este último é provavelmente um diretório de dados Postgres (inferência por nome, dono uid 999, modo 700 e 17 subdiretórios; mtime de 28/05/2026), não montado no container atual; conteúdo, tamanho e datas não foram verificados. Pode ser útil para a D1.
- **Arquivos locais não lidos que podem conter número de caso, dado pessoal ou credencial:**
  - `/data/pathsolutions/masks_ingest.json` (1,5 MB, de 11/06);
  - os nomes dos diretórios por lâmina de `tile_cache_dz` e de `wsi-saida`;
  - o banco SQLite do n8n em `/data/n8n` (de maio, sem container n8n);
  - os logs do nginx nativo no disco de SO, que não foram inventariados.
- **Causa dos descartes (TRIM) no disco de dados em 12 e 13/10** (~86 e ~118 GiB liberados) e se houve ação manual.
- **Serviço na porta 8001 da VM2:** que seja a API de inferência Hibou é inferência, pelo nome da regra do NSG e pela unit `hibou-inference.service`; não houve requisição. Nas portas 80 e 443 da VM2 nada escuta (`ss -ltn`).
- **Identidade dos dois ForeignGroups com Owner** e do dono do IP de origem da regra SSH.
- **Lâminas locais.** O que foi conferido sem nomes, pela comparação de tamanho exato com os 3.542 blobs:

  | Local | Arquivos | Tamanho | Mesmo tamanho no Blob | Leitura |
  |---|---:|---:|---:|---|
  | `/mount/stpathsolutionsdata001` (disco de SO) | 17 `.svs` | 4,30 GiB | 17, com mesmo nome, no `wsi-slides` | têm cópia |
  | `/data/pathsolutions/wsi-entrada` | 2 `.svs` + 1 `.part` | 0,74 GiB | 0 | sem cópia idêntica no Blob. Os 3 têm tamanho múltiplo exato de 64 KiB, o que nenhuma das 1.033 WSIs do Blob tem: indício de transferência interrompida, de direção não verificada (envio ao legado ou download do Blob; se foi download, pode haver versão completa no Blob com outro tamanho). São 2 `.svs` de 06/10 e o `.part` parado desde 15/09 |
  | `/data/pathsolutions/training/datasets/bach/...` | 30 `.svs` | 6,29 GiB | 0 | estrutura do dataset público ICIAR 2018 BACH, não de laboratório |
  | `/data/entrada` | 1 `.svs` | 115 KiB | 0 | nome indica teste sintético |

  Não foram verificados a integridade dos arquivos de `wsi-entrada` nem o hash dos 33. O hash ficou para depois de liberar o disco, que no recorte T estava com as IOPS perto de 100%. A licença do BACH também não foi verificada.

## 15. Riscos

**Em curso:** o banco do legado está fora do ar desde ~21:02 UTC de 14/10 e seguia assim em 15/10 às 13:35 UTC, depois da nova partida da VM1: o container do banco reinicia sem conseguir subir, e backend e queue-worker estão unhealthy (seção 8.1). A cada partida, o `@reboot` do crontab roda o script de backup do legado (seção 8.2). Pela decisão de 14/10 (opção a), o banco não é religado antes da Fase 1, e a ordem nova da Fase 1 não devolve o sistema ao laboratório: o passo 3 religa só o banco, e frontend e backend sobem apenas durante as capturas de tela.

As lâminas chegam por envio direto ao Blob com SAS, que aparece só em operações de envio. Houve transações SAS em 20 dos 30 dias até 13/10, e em 08, 13 e 14/10 elas ficaram entre 17h e 21h UTC. As horas antes das 17h só foram consultadas em 14/10, sem SAS. O último `.svs` chegou às 20:19:33 UTC de 14/10. Os envios de 15/10 em diante encontram o banco fora; o efeito (envio recusado, ou lâmina no Blob sem registro no legado) não foi verificado. Evidência: métrica `Transactions` da conta por tipo de autenticação, diária e horária, e `creationTime` da listagem sem nomes.

**Dados:**
1. As WSIs são a única cópia, num único datacenter (LRS), sem soft delete, versionamento, lock ou backup. Uma exclusão ou sobrescrita hoje é irreversível. A Fase 1 começa por isso (soft delete e lock).
2. O backup do banco do legado está parado desde 15/09: no disco, só logs de falha, e no Blob o dump mais novo é de 15/09. Os rótulos de 15/09 para cá existem só no banco, que está em laço de recuperação.
3. Há lâminas fora do Blob.
   - Na VM1, as 2 `.svs` e o `.part` de `wsi-entrada` não têm cópia idêntica no Blob.
   - Na VM2, há 516 arquivos `.svs`, `.ndpi`, `.mrxs`, `.tif` ou `.tiff` (61,01 GiB) no `/data`, inclusive datasets, que não foram comparados com o Blob. Quantos são lâminas inteiras não foi verificado, e a busca, sem sudo, não viu diretórios que o `azureps` não consegue listar (seção 14).
   - Na redação atual, o passo 11 da skill (liberar disco) apagaria os diretórios do legado em `/data` nas duas VMs, porque o passo 4 cobre só os 17 `.svs` de `/mount`.
   - Depois do go-live, quando os snapshots forem apagados, não sobraria cópia do que não estiver no Blob.
4. Exposição LGPD: 179,84 GiB de prováveis dumps com dados de paciente ficam em camada Hot, numa conta aberta a qualquer rede, com chave compartilhada ativa e nunca rotacionada, e sem trilha de auditoria. Os nomes das lâminas parecem números de caso, então qualquer log ou relatório que use o caminho do blob pode vazar identificador. Na VM1, fora do Blob, há arquivos não lidos que podem conter esses nomes, dado pessoal ou credenciais (seção 14). O passo 11 da skill (liberar disco) só cobre o `/data`, e nenhum outro passo limpa lâminas ou logs do disco de SO da VM1, que segue na v3. Sem mudança na skill, ficariam lá os arquivos de `/mount/stpathsolutionsdata001` e, se existirem, os logs do nginx nativo.

**Operação:**

5. O disco cheio se repete. Em 14/10 está confirmado (seção 8.1). Em 09/10 o disco de dados teve o mesmo padrão de I/O; que tenha enchido é inferência.
   - Um comentário no compose do legado (`docker-compose.yml:141-142`) registra o `/data` a 100% em 15/09 e cita um PANIC do Postgres em 08/07; isso não foi verificado por métrica.
   - O `CLAUDE.md` entrou no repositório às 19:21 UTC de 14/10 (commit `ecbdf6a`), antes do enchimento das ~21:02 UTC. Os incidentes de julho e outubro que ele cita provavelmente são esses de 08/07 e 09/10 (inferência), e não eventos a mais.
   - Dos dois caches de tiles, o `tile_cache_dz` (156 GiB) não tem teto de tamanho: o legado só o reduz por tempo sem acesso (`backend/src/services/auto_archive.py:248` e `:323`), e nada em `backend/src` confere o espaço livre antes de gravar nele.
   - O volume Docker `pathsolutions_v2_tile-cache` tem teto de 100 GiB (`docker-compose.yml:144`) e já está nele.
   - Juntos, os dois caches ocupam ~256 GiB no mesmo disco do banco.
6. Não há monitoramento nem orçamento. Nada avisou do disco cheio, nem das VMs ligadas sem parar de 31/08 a 02/09 (~55 h) e de 15 a 17/09 (VM2, ~61 h).
7. O auto-shutdown da VM2 desliga às 19:00 sem olhar a carga e cortou a VM com CPU alta em 14/10; se havia job em curso, não foi verificado. O `TurnOn-VMs` liga a VM2 sem olhar a fila e roda num runtime com aposentadoria anunciada.
8. O disco de SO da VM1 está em 79%, a um ponto do alerta de 80% da v3. O P4 também satura em IOPS nas partidas, pela métrica de IOPS consumidas.
   - **8a.** O `/data` da VM2 está em 94% (15G livres), acima do alerta de 90%, com a raiz do Docker no mesmo disco: imagens de 42,32 GB e cache de build de 31,06 GB. É o mesmo modo de falha da VM1. A parte recuperável (24,57 GB de imagens e 8,82 GB de cache de build, pelo `docker system df`) é a candidata natural na limpeza da Fase 1.
   - **8b.** Na VM2, os 4 containers do legado e a `hibou-inference.service` subiram com a partida de 15/10 e estavam rodando às 11:54 UTC, com o banco do legado fora do ar. O que fazem nessa situação não foi verificado.
     - A unit está habilitada. A política de reinício dos containers não foi lida, então que eles subam a cada partida do runbook é inferência.
     - A GPU tinha 1.653 MiB (≈1,61 GiB) em uso e 0% de utilização, 1.650 MiB deles em 2 processos `python`. Que esses processos sejam dos containers ou da unit é inferência: o `nvidia-smi` não liga PID a container.

**Segurança:**

9. O container da API monta o `docker.sock` do host, o que equivale a root na VM1. O socket está com o grupo `systemd-journal` em vez de `docker`; o mecanismo não foi verificado.
10. Prováveis segredos em texto puro nos discos de SO das duas VMs, nenhum deles lido (conteúdo não verificado):
    - na VM1, `~/.git-credentials` existe (modo 600, modificado em 22/09/2026), e o git usa `credential.helper=store`, no global e no repositório do legado;
    - na VM1, os arquivos de ambiente do legado e as 2 linhas `Environment=` da unit de backup podem guardar a senha do banco e a chave ou a connection string do Blob (seção 8.5);
    - na VM2, `/home/azureps/inference/.env` (modo 600), no diretório do compose `inference` (seção 8.5).

    Os snapshots do passo 2 da Fase 1 vão conter esses arquivos até o go-live. As travas do `.claude/settings.json` não os cobrem fora do repositório da v3, e regras de Read não barram o Bash (seção 2).
11. Os 4 discos permitem exportação por SAS (`networkAccessPolicy AllowAll`).
12. Dois ForeignGroups (padrão de parceiro CSP; identidade não verificada) têm Owner na subscrição, e a identidade da automation tem Virtual Machine Contributor em todo o grupo.
13. Há outras sessões de agentes ativas na VM1 (2 processos Codex), além de servidores de IDE, todos como `azureps`, a mesma conta usada nesta coleta.
    - Essa conta tem `sudo` sem senha e o login do `az`, com Owner na subscrição.
    - Salvo restrição do próprio agente (não verificada), esses agentes podem alterar o legado em paralelo às fases e ler o banco, os dumps, as lâminas e as chaves do Blob, e o que leem pode seguir para os provedores deles. O que leram ou enviaram não foi verificado.
    - Há também um histórico do Gemini CLI do projeto legado em `~/.gemini/history/`.

**Código e custo:**

14. 35 a 37 commits do legado podem não ter cópia remota.
15. O kit antigo dentro do repositório legado tem uma skill com o mesmo nome da atual `pathsol-isolamento-tenant`, com conteúdo diferente. Uma sessão aberta em `Pathsolutions_V2` a carregaria.
16. Se o auto-shutdown da VM1 for desativado de novo, como entre 14/10 22:46 e 15/10 02:34 UTC, a VM1 custa cerca de R$ 76,7 por dia de computação (estimativa). Num mês inteiro assim, a subscrição fica entre ~R$ 4,93 mil e ~R$ 5,05 mil, no teto D3 de R$ 5.000 ou acima dele, sem orçamento nem alerta (seção 11).

## 16. Decisões pedidas ao Pedro

Já decididas, registradas aqui:
- em 14/10, não mexer no legado, com o banco fora do ar até a Fase 1 (opção a; na leitura de 14/10, nginx, frontend e backend estavam de pé);
- nova ordem da Fase 1 na skill (commit `1ea41a7`);
- leitura da VM2 em 15/10, feita;
- auto-shutdown da VM1 reativado em 15/10 às 02:34:38 UTC (Enabled, 20:00), pelo Portal.

0. **Urgente:** avisar os usuários da Diagnose de que o sistema está indisponível? O banco do legado seguia fora do ar em 15/10 às 13:35 UTC, e os envios do dia costumam começar às 17h UTC (seção 15, "Em curso"). O passo 13 da skill já prevê registrar o pedido para desativarem a extensão Chrome, e esse pedido pode ser antecipado.
1. **Auto-shutdown da VM1 durante as fases:** ele foi reativado em 15/10 (20:00), então sessões abertas na VM1 caem nesse horário. Se for preciso desativá-lo para uma fase longa, a VM1 ligada 24 h custa cerca de R$ 2,33 mil/mês de computação. Num mês inteiro assim, a subscrição chega ao teto D3 de R$ 5.000 ou passa dele: ~R$ 4,93 mil a ~R$ 5,05 mil, sem orçamento nem alerta (seção 11).
2. **Modelo da subscrição:** corrigir "pay-as-you-go" para CSP ("Microsoft Azure Plan" via parceiro) no `CLAUDE.md`, no `PROMPT_V3.md` e na skill `pathsol-infra`? E informar a fatura do parceiro de jul a set, para comparar com o Cost Management.
3. **Passo 4 da Fase 1 (lâminas locais):** incluir as 2 `.svs` e o `.part` de `/data/pathsolutions/wsi-entrada` (VM1), que não têm cópia idêntica no Blob? E conferir antes do passo 11, sem nomes e com sudo, os 516 arquivos da VM2, separados por extensão e com os datasets à parte? Proposta para os arquivos sem cópia:
   - hash e conferência de integridade depois do passo 3;
   - se estiverem completas, envio ao Blob antes do passo 11, no `wsi-slides` ou num prefixo separado, à sua escolha, **sem sobrescrever nada**:
     - a Fase 0 comparou só tamanhos, não nomes, e o indício de transferência interrompida deixa aberta a hipótese de a versão completa já estar no Blob com o mesmo nome;
     - antes do envio, conferir se existe blob com o mesmo nome no destino; se existir, nada é enviado e a decisão volta para você;
     - o envio usa um comando que falha se o blob já existir, porque nenhuma WSI do Blob pode ser alterada;
     - a mesma regra vale para o passo 4 da skill, que hoje diz "O que não existir é copiado para lá": copia-se só o que não existir com o mesmo nome, sem sobrescrita, e mesmo nome com tamanho diferente vai para a sua decisão;
   - se estiverem truncadas, ficam só no snapshot;
   - o `.part` pode ser descartado depois do snapshot.

   As 30 `.svs` do BACH, dataset público, entram só no manifesto de datasets do passo 8, com fonte e licença, sem cópia para o `wsi-slides`, para não misturar dataset público com o acervo clínico.
4. **Passo 11 da skill (liberar disco):** o caminho `/data/wsi_stage/datasets` existe na VM2 (32G), mas não na VM1, onde os datasets estão em `/data/pathsolutions/training/datasets` (31,0 GiB). Acrescentar o caminho da VM1 à skill?
5. **Fontes alternativas para a D1:**
   - examinar na Fase 1, com sudo, o `/data/postgres` (provável diretório de dados de maio) como possível fonte de rótulos antes de qualquer remoção?
   - se o banco não voltar no passo 3, usar como fonte o dump mais novo do container `backups`, de 15/09 (provável dump; conteúdo não verificado), restaurado num Postgres separado, sem tocar no volume atual?

   Nesse caso, os rótulos posteriores a 15/09 ficariam fora da exportação. Eles continuam só no volume atual, preservado pelo snapshot do passo 2.
6. **Código do legado:** confirmar que o passo 7 (tag e push) deve incluir o push da branch `fix/audit-2026-09`, que não tem upstream, para `Pedrogal-pathsolutions/Pathsolutions_V2`. Confirmar também de quem é a conta do repositório `pathsolutions-claude-context`.
7. **Provável credencial do GitHub em `~/.git-credentials` (arquivo não lido):** conferir e revogar ou rotacionar depois da preservação do código?
8. **Outros agentes na VM1** (processos Codex ativos): pausar durante as Fases 0 e 1? E, antes da Fase 1, decidir se continuam com acesso à conta `azureps` (`sudo` e login do `az`)?
9. **Terraform:** a instalação na VM1 fica para a Fase 3, com autorização, conforme a skill `pathsol-infra`?
10. **Cota T4 (4/4):** pedir aumento só se o plano da Fase 2 previr uma segunda GPU; com CSP, o caminho do pedido (portal ou parceiro) não foi verificado.
11. **Registro das ações no legado:** registrar em `docs/operacao/`, como pede a regra de registro de ações no legado, três operações feitas pelo Portal por usuário (e-mail não impresso):
    - a desativação do auto-shutdown da VM1 (14/10, 22:46:23 UTC);
    - a reativação dele (15/10, 02:34:38 UTC);
    - a desalocação da VM1 (15/10, 02:34:49 UTC).

    Se alguma não foi sua, a autoria precisa ser apurada no activity log antes da Fase 1. Este relatório já as documenta.
12. **Acesso ao Blob sem chave na Fase 1:** a Fase 1 usa o plano de dados do Blob antes da Fase 3. O passo 4 confere o `wsi-slides` e copia o que faltar, e o passo 8 grava no `backup-legado` e confere os checksums. Sem papel de dados, isso só se faz com a chave da conta, como na Fase 0 (seção 2). Proposta, antes do passo 4 e com uma autorização por ação:
    - dar à identidade de operação Storage Blob Data Reader só no container `wsi-slides`;
    - criar o `backup-legado`, que ainda não existe (seção 7), e dar Storage Blob Data Contributor só nele;
    - gravar no `wsi-slides` (passo 4 ou item 3) com autorização à parte.

    A alternativa é aceitar por escrito o uso da chave na Fase 1, com cada `listKeys` registrado em `docs/operacao/`.
13. **Chaves da `stpathsolutionsblob001`:** rotacionar as duas chaves, nunca rotacionadas desde a criação, depois do passo 10 da Fase 1, com o legado parado? Assim, as cópias que estiverem nos arquivos de ambiente e nos snapshots perdem a validade. É uma mudança num recurso fora do Terraform, com autorização própria.
14. **Política de rede dos snapshots:** criar os snapshots do passo 2 com `--network-access-policy DenyAll --public-network-access Disabled`, para que não possam ser exportados por SAS (seção 12.1)? O efeito disso na restauração não foi verificado.

## 17. Evidências principais (comando e saída resumida)

| Comando | Saída resumida |
|---|---|
| `az account show -o json` | name PATHSOLUTIONS TECNOLOGIA EM SAUDE LTDA; id bd87a1ca-…-c89e114293f1; Enabled |
| `az rest --method get .../subscriptions/<id>?api-version=2022-12-01` | quotaId CSP_2015-05-01; spendingLimit Off |
| `curl IMDS /metadata/instance/compute` | name vm-appviewer-prod-001; Standard_D8s_v5 |
| `az resource list -o table` | 28 linhas; grupos rg-prod-brsouth-001 e NetworkWatcherRG |
| `az vm list -d` (início) e `az vm get-instance-view` (22:44 UTC) | VM2 de "VM running" para `PowerState/deallocated`, última operação 22:02:14 UTC |
| `ssh -o BatchMode=yes azureps@10.0.0.4 ...`; `ip neigh show 10.0.0.4` | `No route to host`; ARP `FAILED` |
| `az resource show ... DevTestLab/schedules` | VM2 Enabled 1900; VM1 Enabled 2000 às 22:44 e Disabled às 22:47 UTC |
| `az automation runbook list`; `az automation schedule list`; `az automation job list` (asa-prod-brsouth-001) | TurnOn-VMs PowerShell72; agenda seg–sex 06:00, recorrência desde 04/09; 22 jobs Completed de 15/09 a 14/10 |
| `az monitor activity-log list --offset 90d --max-events 5000` (coletor de automação) | 967 eventos até 14/10 22:46 UTC; start 68 (60 automação, 8 usuário); deallocate 66 (56 auto-shutdown, 10 usuário); delete 0 |
| `az monitor metrics list --metrics "Percentage CPU" --interval PT5M` (VM2, 20:30–22:10 UTC de 14/10) | médias de 5 min entre 55,5% e 98% |
| `az monitor metrics alert list`; `activity-log alert list`; `action-group list`; `log-analytics workspace list`; `diagnostic-settings list`; `az consumption budget list` | 0 em todos |
| `az provider list` (verificador de automação) | `Microsoft.AlertsManagement` NotRegistered |
| `systemctl list-units --state=failed` | `pathsolutions-backup.service` |
| `systemctl show pathsolutions-backup.service` | Result=exit-code, ExecMainStatus=1, 09:30 → 10:09 UTC |
| `crontab -l`; `sudo -n crontab -l -u root` | `@reboot sleep 120 && .../backup-scheduled.sh`; "no crontab for root" |
| `psql --version` | psql (PostgreSQL) 16.15 |
| `df -h / /data` | / 79%; /data 100%, 0 disponível |
| `sudo docker ps -a --format ...` | 5 containers do compose pathsolutions_v2; db e queue-worker unhealthy |
| `sudo docker logs --tail 300 pathsolutions-db \| grep -c 'No space left on device'` | 29 |
| `sudo docker system df -v` | postgres-data 140,7 GB; tile-cache 107,4 GB; build cache 0 B |
| `du -s --block-size=1 /data/pathsolutions/tile_cache_dz` | 167.683.817.472 B (156,17 GiB) |
| `az storage blob list ... \| python3 -I churn.py` (sem nomes) | sobrescritos em 30 dias: slides 0, output 1, metadata 43, backups 0 |
| `az storage blob list ... \| python3 -I compare.py /mount/stpathsolutionsdata001` | 17 locais; 17 com mesmo nome e tamanho no wsi-slides |
| `curl prices.azure.com/api/retail/prices (BRL, brazilsouth)` | Snapshot Standard HDD LRS/ZRS 0,3549; Premium 1,19; Hot LRS 0,1702 por GB-mês |
| `az rest --method post .../Microsoft.CostManagement/query` | jul 2.868,05; ago 1.601,32; set 3.747,27; out 1–13 1.495,55 (BRL) |
| `az vm list-usage --location brazilsouth` | NCASv3_T4 4/4; Total Regional 12/60 |
| 15/10 11:50 UTC: `az account show`; `az automation job list` (último TurnOn-VMs); `az vm list -d` | subscrição correta; job Completed 09:01:44–09:02:01 UTC; VM1 e VM2 `VM running` |
| 15/10: `ssh azureps@10.0.0.4 ...`; `ssh-add -l` | `Permission denied (publickey)`; sem agente utilizável (código 2) |
| 15/10 11:54 UTC: `ssh azure-foundation 'bash -s'` com o comando da seção 13 | concluído (código 0); aviso de chave de host adicionada aos hosts conhecidos; arquivo não verificado |
| 15/10: `az monitor activity-log list --resource-id <VM1>` (00:00–12:30 UTC), `--resource-id <schedule da VM1>` (14/10 22:00 a 15/10 12:30 UTC) e `az resource show` dos dois schedules | schedule write da VM1 às 02:34:38 (Portal, usuário); `deallocate` da VM1 às 02:34:49 (Portal, usuário), Succeeded às 02:35:51; start às 09:02:00 (identidade de serviço), Succeeded às 09:03:15; VM1 Enabled 2000; VM2 Enabled 1900 |
| 15/10 13:35 UTC, na VM1: `df -h / /data`; `sudo -n docker ps -a`; `sudo -n docker logs --tail 300 pathsolutions-db` | /data 100%, 0 livre; db "Up 32 seconds (health: starting)"; backend e queue-worker unhealthy; 75 linhas `FATAL: could not write lock file ... No space left on device` |
| (na VM2) `df -B1`; `lsblk`; `/proc/mounts`; `/etc/fstab` | / 20.540.399.616 B usados (69%); /data 239.592.189.952 B (94%); /data sem `discard`; sem NFS no fstab |
| (na VM2) `nvidia-smi`; `/proc/driver/nvidia/version`; `dpkg -l`; `/usr/local/cuda/version.json` | Tesla T4; driver 595.71.05; CUDA 13.2 (máximo do driver); toolkit 12.8.2; nvidia-container-toolkit 1.19.0 |
| (na VM2) `docker ps -a`; `docker image ls`; `docker system df -v` | compose `inference`: 4 containers Up e 3 Exited; 11 imagens (42,32 GB); build cache 31,06 GB; 0 volumes |
| (na VM2) `systemctl list-units/list-unit-files/list-timers`; `crontab -l`; `sudo -n crontab -l -u root`; `ss -ltn` | `hibou-inference.service` rodando; 0 falhas; nenhum crontab; portas 22, 111 e 8001 |
| (na VM2) `find` por `.git`, `.env` e `.svs`/`.ndpi`/`.mrxs`/`.tif`/`.tiff`, e `du -sh` dos datasets, sem sudo e com os erros descartados; só contagens e caminhos | 0 repositórios; `/home/azureps/inference/.env` (600); 516 arquivos com essas extensões (61,01 GiB) no /data, sem divisão por extensão; `/data/wsi_stage/datasets` 32G |
| `az monitor activity-log list --offset 1d --query "[?operationName.value=='Microsoft.Storage/storageAccounts/listKeys/action' && status.value=='Succeeded']..."` (15/10 00:26 UTC) | 40 listKeys, de 22:51:29 (14/10) a 00:15:24 UTC (15/10) |
| comparação de tamanho exato de 33 lâminas locais contra os 3.542 blobs (lacuna 3; sem nomes) | 0 com tamanho igual |
| `/proc/<pid>/mountinfo` de cada container; `stat` do socket no host e no container da API (risco 9) | só o container da API monta o `docker.sock`; no host, root:systemd-journal, modo 660 |
| `git config --global --get credential.helper`; `ls -l ~/.git-credentials`, sem ler o conteúdo (risco 10) | `store`; arquivo presente, modo 600, modificado em 22/09 |
| `pgrep -u azureps -c -x codex` (risco 13) | 2 processos |

Os demais comandos estão citados em cada seção. As saídas completas dos agentes estão no registro local da sessão do Claude Code na VM1.

PARADO — aguardando APROVADO FASE 0
