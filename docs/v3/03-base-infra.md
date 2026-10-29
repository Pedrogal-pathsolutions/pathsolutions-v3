# Fase 3 — Base de infraestrutura (relatório parcial)

Em andamento. Começou em 27/10/2026 (UTC), depois do APROVADO FASE 2. Este relatório é atualizado a cada sessão e cresce por fatia, na ordem da seção 19.2 do plano (`docs/v3/02-plano-v3.md`). A sessão seguinte começa por aqui e pelo `git log`.

## Situação por fatia

| Fatia | Situação |
|---|---|
| 0. Exportação de teste do Motic | não chegou; nada a fazer até ela chegar |
| 1. Decisão 4 antes do primeiro apply | feita: codex desinstalado, applies do Pedro pelo SSH com o Antigravity fechado e `az logout` no fim do dia |
| 2. Terraform e estado remoto | feita: bootstrap aplicado e estado migrado para `pathsoltfstatev3` |
| 3. Orçamento e action group | feita; falta o disparo real do aviso de 50% (esperado de 1 a 3 dias depois de 27/10). O e-mail do action group chega: o Pedro recebeu os três disparos reais de 27/10, 11:54 UTC |
| 4. Storage e alertas | feita, em dois applies, a pedido do Pedro (27/10). A: conta de WSI, containers com retenção legal, papel sem exclusão e trava. B: fila e dead-letter, conta do status, Key Vault, Log Analytics, alertas de activity log e da dead-letter, container dos `.h5` e a política de ciclo de vida da decisão 1. Os dois aplicados e conferidos; os testes de proteção e de disparo ficam na fatia 8 |
| 5. Primeira partida da VM2 e discos | feita (27 e 28/10). VM1 com o `/data` no P10, conferido depois do ciclo de desalocar e ligar de 27 para 28/10; VM2 com kernel e driver congelados e o `/data` no P6. O Pedro apagou o P15 (27/10, 22:41 UTC, pelo Portal) e o P20 (28/10, 21:07 UTC). Registro em `docs/operacao/2026-10-27-discos-fatia5.md` |
| 6. VMs | quase feita (28 e 29/10). VM1: limpeza da seção 4.5, tetos de logs, nginx e certificado novos, agente, unit do status. VM2: identidade, agente, tetos de logs e chave de host conferida. Apply do `fatias6-7.tfplan` conferido. Runbook novo (padrão 27) no PowerShell 7.6, e a automação sem o Virtual Machine Contributor. Auto-shutdown da decisão 3 desde 29/10: VM1 às 23:00 e VM2 às 23:30. Faltam duas provas no ciclo real da VM1 de 29 para 30/10: o status no desligamento e o runbook novo ligando a VM1 desalocada. Registro em `docs/operacao/2026-10-28-fatia6-vms.md` |
| 7. Postgres, backup e restauração | apply feito e conferido (disco do banco, container de backup, papel do pgBackRest e regra de 35 dias dos dumps); falta todo o resto |
| 8. Testes | não começada |

## O que foi feito

### Sessão 1 (27/10, a partir das 01:04 UTC)

1. Leitura do `CLAUDE.md`, do `PROMPT_V3.md`, do plano e da skill `pathsol-infra`. Levantamento do estado, só com leitura, depois de `az account show`.
2. Terraform 1.16.7 instalado em `~/.local/bin/terraform`, com autorização do Pedro (27/10). Binário oficial, com a assinatura do `SHA256SUMS` conferida pela chave da HashiCorp (C874 011F 0AB4 0511 0D02 1055 3436 5D94 72D7 468F) e o sha256 do zip conferido. Sem sudo, sem repositório apt.
3. Versões fixadas: Terraform `~> 1.16.7` (o plano pede 1.16.x; a 1.17.0 saiu em 21/10 e não entra) e azurerm `= 5.10.0`, de 15/10 (a 5.11.0 tinha 4 dias). No azurerm 5.x, o provider não registra providers do Azure por padrão (guia de upgrade da 5.0).
4. Código do bootstrap em `infra/terraform/bootstrap/` e procedimento do apply em `infra/terraform/LEIA-ME.md`. O provider e o backend usam só o login do `az` (`use_cli = true`, `use_msi = false`), que é a decisão 4 escrita no código.
5. Plano do bootstrap salvo (`bootstrap.tfplan`, fora do git).
6. O Pedro desinstalou o codex, fechou o Antigravity e, pelo SSH, aplicou o `bootstrap.tfplan` e migrou o estado (~01:40 UTC).
7. Conferência do bootstrap: os 5 recursos existem, com os atributos do plano; o estado remoto tem a mesma linhagem e os mesmos recursos da cópia local que o `init -migrate-state` deixou (serial 7 no remoto, 6 na cópia). A cópia local guardava as chaves da conta. A pedido do Pedro, ela foi apagada depois de conferidos o `.gitignore` (`*.tfstate`, fora do git) e os 5 recursos gerenciados no estado remoto; em seguida, `terraform plan` do bootstrap respondeu `No changes`.
8. Código do orçamento e do action group em `infra/terraform/main/`, com o e-mail numa variável `sensitive` e o valor em `terraform.tfvars`, fora do git. Plano salvo (`main.tfplan`).
9. O Pedro aplicou o `main.tfplan` pelo SSH (~01:51 UTC). Conferência: `terraform plan` sem mudanças; action group e orçamento com os atributos do plano. O teste de notificação do action group não foi rodado.
10. `az logout` no fim do dia de Terraform (decisão 4). A próxima sessão que precisar do `az` depende de o Pedro entrar de novo.

### Sessão 2 (27/10, a partir das ~02:00 UTC)

1. O Pedro entrou no `az` e pediu a fatia 4 em dois applies: primeiro a conta de WSI com retenção legal, papéis e trava; depois o resto.
2. Provider azapi 2.13.0 (de 28/09/2026) fixado em `main/versions.tf`: o azurerm não tem recurso de retenção legal (plano, seções 6.4 e 21). Assinado pela chave de parceiro 6F0B91BDE98478CF, a mesma que o registro publica para essa versão. Ele também usa só o login do `az` e não registra providers.
3. Respostas do Pedro (27/10): containers só para `diagnose` e `publico` (o que a Fase 4 usa). Micra e Dr. Eugênio entram num plano próprio, antes do primeiro upload de cada um. O papel sem exclusão nasce sem atribuição: a VM1 o recebe quando o script do operador precisar (Fase 4) ou no teste de proteção (fatia 8); a VM2, na fatia 6, junto com a identidade.
4. Código do apply A em `main/wsi.tf`. Plano salvo (`wsi.tfplan`).

### Sessão 3 (27/10, a partir das ~02:30 UTC)

1. O Pedro aplicou o `wsi.tfplan` pelo SSH (02:21 UTC) e entrou de novo no `az`.
2. Conferência do apply A: `terraform plan` sem mudanças, e os 7 recursos com os atributos do plano (evidências abaixo). A retenção legal está ativa nos dois containers, com a tag `decisao1`, e a conta nasceu sem soft delete. O papel sem exclusão não tem nenhuma atribuição.
3. Pergunta do Pedro: o "sem acesso público" da `pathsolwsiv3` é `allow_nested_items_to_be_public = false` (sem acesso anônimo a containers e blobs). A rede pública segue aberta: `publicNetworkAccess Enabled`, `defaultAction Allow`, sem endpoint privado. No azurerm 5.10.0, o `public_network_access_enabled` está depreciado e deu lugar ao `public_network_access`, agora explícito no código (`Enabled`, sem mudança no plano). Qualquer rede alcança o endpoint, mas toda requisição precisa de token do Entra ID ou de SAS de delegação de usuário, porque a chave compartilhada está desligada. É o que o fluxo do plano pede: a extensão envia da rede de cada laboratório com a SAS de um blob (seção 4.2), e as VMs usam o endpoint público pelos IPs públicos delas (risco 20 do plano: a sub-rede não tem NAT). O apply B segue o mesmo modelo. Fechar a rede seria decisão nova, fora do plano: dependeria do IP fixo dos laboratórios (seção 23.3) e de um caminho para as VMs.
4. Código do apply B (`main/filas.tf`, `status.tf`, `segredos.tf`, `logs.tf`; acréscimos em `wsi.tf` e `alertas.tf`). Plano salvo (`apply-b.tfplan`).

### Sessão 4 (27/10, a partir das 11:55 UTC)

1. O Pedro registrou o `Microsoft.KeyVault` (11:44:20 UTC), aplicou o `apply-b.tfplan` pelo SSH (11:47:59 a 11:48:22 UTC) e entrou de novo no `az`. Às 11:42 UTC, o usuário dele alterou a regra `default-allow-ssh` do NSG pelo portal, fora do Terraform; pelo horário, para o SSH do apply (inferência).
2. Conferência do apply B: hash do plano igual ao do relatório, `terraform plan` sem mudanças e os 20 recursos novos com os atributos do plano (evidências abaixo). A retenção legal dos dois containers de WSI é a mesma de 02:21. Nenhuma operação falhou, e nenhuma atribuição de papel nasceu.
3. Primeiros disparos reais: às 11:54:09 e 11:54:10 UTC, ~6 min depois das operações, o `pathsol-lifecycle-write-v3` (política de ciclo de vida) e o `pathsol-storage-write-v3`, duas vezes (criação da `pathsoldlqv3` e da `pathsolstatusv3`). Se os três e-mails chegaram não foi verificado; se chegaram, também provam a entrega do action group.
4. Achados do activity log: (a) a iniciativa padrão do Defender for Cloud (`SecurityCenterBuiltIn`) auditou as contas novas (sem regra de rede virtual, sem private link) e o Key Vault (sem proteção contra purga, sem firewall, sem private endpoint). É só auditoria, e são escolhas do plano (riscos). (b) O azurerm chamou `workspaces/sharedKeys/action` duas vezes: as chaves do Log Analytics também vão para o estado.
5. Fatia 5: levantamento só de leitura da VM1 e dos discos atuais; código em `main/discos.tf`; plano salvo (`discos.tfplan`).

### Sessão 5 (27/10, a partir das ~12:50 UTC)

1. O Pedro aplicou o `discos.tfplan` (12:48 UTC), confirmou que os e-mails dos três alertas de 11:54 UTC chegaram (o action group entrega) e que a mudança no `default-allow-ssh` às 11:42 UTC foi dele. Autorizou os 9 passos da fatia 5 com duas condições: o congelamento de kernel e driver (padrão 11) é a primeira ação na primeira partida da VM2; e a exclusão do P20 e do P15 só é pedida depois de a VM reiniciar, com o `/data` no disco novo e o Docker de pé.
2. Conferência do apply: sha256 do plano igual ao do relatório, `terraform plan` sem mudanças e os dois discos com os atributos do plano.
3. VM1, passos 1 a 3 (registro em `docs/operacao/2026-10-27-discos-fatia5.md`): P10 anexado com a VM ligada (lun1, ReadOnly); `/data` no P10 (ext4 `-m 0`, rótulo `dados-vm1-v3`), com o esqueleto do Docker e do containerd copiado e conferido, o UUID trocado no fstab e `RequiresMountsFor=/data` no containerd e no docker; `docker info` igual ao de antes; P20 desanexado e `Unattached`. No detach, o kernel registrou uma falha de SYNCHRONIZE CACHE no disco já retirado (o fs estava desmontado desde 14:09:10); o Pedro mandou seguir.
4. Respostas do Pedro (~21:07 UTC): no passo 8, desalocar e ligar a VM2 de novo, em vez de reiniciar; a VM1 reinicia na partida de 28/10, pelo runbook.
5. A trava do `.claude/settings.json` nega `az disk delete` à sessão: as duas exclusões ficam com o Pedro.
6. VM2, passos 5 a 8: P6 anexado com a VM desalocada; na primeira partida (21:16 UTC), o congelamento foi a primeira ação: `apt-mark hold` em 48 pacotes do kernel e do driver 595.71.05, às 21:17:48, 33 min antes da execução marcada do `apt-daily-upgrade`. Depois, leitura, `/data` no P6 com o mesmo procedimento da VM1, P15 desanexado com a VM desalocada, partida de novo e evidência: só a lun1, `/data` montado antes do containerd e do docker, `docker info` e engine iguais, T4 com o driver 595.71.05, holds intactos. VM2 desalocada às 21:24:38; ligada por ~8 min no total.
7. Passo 9: o Pedro respondeu "Apaguei o P15", mas a conferência das 22:34 UTC achou o disco `Unattached` e `Succeeded`, sem `disks/delete` no activity log. Parado ali, já depois do corte das 22:30 UTC.
8. A sessão esperou aprovações de 12:57 a 14:03 e de 14:12 a 21:07 UTC; por isso a VM2 entrou já perto do auto-shutdown dela (22:00 UTC), com cortes de horário nos scripts.

### Sessão 6 (28/10, a partir das 20:52 UTC)

1. O Pedro entrou no `az`, apagou o P15 pelo Portal e desligou o auto-shutdown da VM1 (20:52 UTC). Pediu a conferência do P15, a do ciclo da VM1 e, depois, as fatias 6 a 8, com parada limpa até as 01:30 de Brasília.
2. P15: o activity log mostra a exclusão de 22:40:53 a 22:41:12 UTC de 27/10, seis minutos depois da conferência das 22:34. A divergência da sessão 5 era de horário.
3. VM1: desalocada pelo auto-shutdown às 23:00:35 UTC de 27/10 e ligada pelo runbook às 09:01:31 de 28/10. Na partida, só a lun1, o `/data` no P10 montado antes do containerd e do docker, e o `docker info` igual ao de 27/10. No desligamento, o journal mostra docker, containerd e `/data` parados em ordem.
4. O Pedro apagou o P20 (21:07:14 a 21:07:30 UTC, Azure CLI). Fatia 5 concluída.
5. Fatia 6, VM1, com autorização por ação (registro em `docs/operacao/2026-10-28-fatia6-vms.md`): certificado do legado revogado (conferido na CRL); 80 e 443 só para a VM1; regras 200 a 230 fora; site do legado e cópias, certbot do apt, `/etc/letsencrypt`, rpcbind, `nfs-common`, sobras vazias e 11 órfãos do apt fora; tetos de logs (journald 1G; Docker com driver `local` e cache de build de 20 GiB); nginx novo e certificado de `app.pathsolutions.com.br`, com conta ACME nova sem e-mail e CAA com `accounturi` (o Pedro criou o CAA e apagou o registro `upload`).
6. Workflow de leitura de documentação (7 tópicos, só fontes oficiais, sem comando no Azure) para o código das fatias 6 e 7. Os fatos que mudaram o código estão em "Plano das fatias 6 e 7".
7. Código e plano das fatias 6 e 7 juntos, a pedido do Pedro (`fatias6-7.tfplan`).

### Sessão 7 (29/10, a partir das 01:26 UTC)

Registro detalhado em `docs/operacao/2026-10-28-fatia6-vms.md`, seção "Sessão 7".
1. O Pedro aplicou o `fatias6-7.tfplan` (01:23:19 a 01:24:18 UTC). Conferência: sha256 igual; os 31 recursos com os atributos do plano; nenhuma falha no activity log. O primeiro `terraform plan` depois do apply queria recriar as 4 atribuições de papel interno por diferença de formato do ID (mesmo GUID). Corrigido no data source (`papeis.tf`, escopo da subscrição); depois, `No changes`, sem mudança no Azure.
2. Agente na VM1 (1.45.1, atualização automática). O `InstanceName` do `Perf` é o ponto de montagem, como as consultas dos alertas supõem; o `local0` chega à tabela `Syslog`.
3. VM2, os 8 passos autorizados: identidade nova, partida, chaves de host lidas pelo Run Command, agente com a identidade nova, tetos de logs (o journal tinha 1,1G; saíram 16 arquivos do legado, de 04 a 10/09), ciclo de desalocar e ligar com evidência, desalocada às 02:07:37. O Pedro gravou as chaves no `known_hosts` e ligou a conferência no alias: o risco da chave de host da VM2 fica corrigido.
4. Unit do status na VM1, com 8 testes do cálculo de volta e o teste de `start`, `stop` e `start` lido no endpoint público.
5. Padrão 27: ambiente PowerShell 7.6 e runbook novo `pathsol-ligar-vm1-v3` (o `TurnOn-VMs`, `PowerShell72`, recusou o ambiente novo), testado, publicado e ligado à agenda `TurnOn-VMs`; o vínculo antigo saiu e o Virtual Machine Contributor da automação também. O ambiente 7.6 roda o build `7.6.0-preview.5`; o Pedro mandou seguir.
6. Leitura de documentação em workflow (3 tópicos, só fontes oficiais, sem comando no Azure), para o runbook e para a fatia 7.
7. Fatia 7: disco do banco na lun2 da VM1, XFS em `/srv/banco` (`nofail`, ponto de montagem imutável no disco de SO), já no `Perf` e nos alertas de disco. Registro em `docs/operacao/2026-10-29-fatia7-banco.md`.
8. Auto-shutdown da decisão 3, autorizado no fim da sessão: VM1 de volta às 23:00 e VM2 às 23:30, conferidos por GET.
9. `az logout` às 02:45:29 UTC (decisão 4). A próxima sessão começa conferindo o ciclo real da VM1 (journal do boot anterior, `findmnt /srv/banco`, job das 06:00 de 30/10) e depende de o Pedro entrar no `az`.

## Plano das fatias 6 e 7 (Terraform)

`terraform plan -out=fatias6-7.tfplan` em 28/10, 22:48 UTC: **30 a criar, 1 a alterar, 0 a destruir.** A alteração é a política de ciclo de vida da `pathsolwsiv3`: ganha a regra `backup-dump-35d`, e as regras `wsi-cold-30d` e `h5-cool-90d` ficam iguais (conferido no JSON do plano). VM1, VM2, automação e grupo das VMs entram só como `data`; nenhum recurso de VM, disco atual ou rede aparece no plano. sha256: `073ee8e3a255068a5fe1ced13067ce7cdaa99124487a2679b59d6ad20bc5f48f`.

**Mudar a política de ciclo de vida exige pedido escrito do Pedro (`CLAUDE.md`, storage da v3).** A regra nova só apaga arquivos com prefixo `backup-banco/dump/` (o `pg_dump`) 35 dias depois da criação (plano, seção 7).

| Recurso | O quê | Custo/mês |
|---|---|---:|
| `azurerm_user_assigned_identity.vm2` | `pathsol-id-vm2-v3`, a identidade do worker (padrão 9); o `az` a anexa com a VM2 desalocada | R$ 0 |
| `azurerm_role_definition` × 5 | `pathsol-vm2-energia-v3` (ler, ligar e desalocar a VM2), `pathsol-vm2-autodesalocar-v3` (ler e desalocar), `pathsol-vm1-ligar-v3` (ler e ligar; padrão 27), atribuíveis no grupo das VMs; `pathsol-fila-worker-v3` (`messages/process/action` e `messages/write`) e `pathsol-backup-banco-v3` (ler, gravar e apagar blobs, mais `containers/read` e `containers/write`), atribuíveis no `rg-pathsol-v3` | R$ 0 |
| `azurerm_role_assignment` × 11 | VM1 (identidade do sistema): energia na VM2; Storage Queue Data Reader na `jobs`; papel sem exclusão no `$web` do status; backup no `backup-banco`. VM2 (identidade nova): autodesalocar nela mesma; fila do worker na `jobs`; Storage Queue Data Message Sender na `jobs-dead-letter`; Storage Blob Data Reader nos dois containers de WSI; papel sem exclusão no `slide-h5`. Automação: ligar só a VM1 | R$ 0 |
| `azurerm_monitor_data_collection_rule.vms` | `pathsol-coleta-vms-v3`: `Logical Disk(*)\% Used Space` a cada 60 s e syslog `local0` (Info para cima), só para o Log Analytics | ~R$ 2,40 de ingestão (estimativa: ≤ 0,1 GB/mês a R$ 24,0092/GB; o volume real decide o teto diário) |
| `azapi_resource.agent_settings` | `pathsol-agente-v3`, regra `AgentSettings`: cache local do agente em 4.000 MB, o mínimo (o padrão é 10.000 MB, no disco de SO) | R$ 0 |
| `azurerm_monitor_data_collection_rule_association` × 4 | as duas regras nas duas VMs | R$ 0 |
| `azurerm_monitor_scheduled_query_rules_alert_v2` × 4 | `pathsol-disco-80-v3` (sev. 2) e `pathsol-disco-90-v3` (sev. 1) na tabela `Perf`, por máquina e montagem (`/`, `/boot`, `/data`, `/srv/banco`, `/mnt`), a cada 15 min; `pathsol-vm1-silencio-v3` (sev. 1): nenhum heartbeat em 10 min, de segunda a sexta, das 06:20 às 22:50 de Brasília; `pathsol-vm2-ligada-v3` (sev. 2): 235 heartbeats ou mais em 4 h. Todos com estado: um e-mail ao disparar e um ao resolver | R$ 8,87 (disco: 2 × [R$ 2,6097 + 7 × R$ 0,2610]) + R$ 5,22 (2 × R$ 2,6097) |
| `azurerm_monitor_activity_log_alert.vm1_saude` | `pathsol-vm1-saude-v3`: Resource Health da VM1 indisponível ou degradada por causa da plataforma (seção 18) | R$ 0 |
| `azurerm_managed_disk.banco` | `pathsol-banco-v3`: P6 de 64 GiB, Premium LRS, `DenyAll`, sem rede pública, `prevent_destroy` (seção 7) | R$ 92,03 |
| `azurerm_storage_container.backup` | `backup-banco` na `pathsolwsiv3`, privado, sem retenção legal, `prevent_destroy`: `pgbackrest/` e `dump/` | R$ 0 vazio; depois, R$ 13 a R$ 31 em ZRS (seção 6.6) |
| `azurerm_storage_management_policy.wsi` (alterar) | regra `backup-dump-35d`, só no prefixo `backup-banco/dump/` | R$ 0 |
| **Total** | | **~R$ 108,52** |

Preços da Retail Prices API (BRL, brazilsouth), lidos em 28/10 (alertas) e 27/10 (P6). O plano estimava ~R$ 105,80 para os mesmos itens (P6, padrão 12 e Log Analytics).

Escolhas desta sessão, fora do texto do plano:
- **Alertas de disco por busca em log, e não por métrica.** O plano (seção 9.4) contava 12 séries de métrica de convidado. O destino de métricas do agente usa as métricas personalizadas do Azure Monitor, que a Microsoft mantém em preview e diz que "won't be made generally available" (metrics-custom-overview, lida em 28/10). O nome da métrica e a dimensão da montagem só aparecem no código do agente, não na documentação. A tabela `Perf` do Log Analytics, que a seção 9.3 já previa, é GA. A diferença de custo é de ~R$ 2,61/mês.
- **`/boot` nos alertas de disco**, além das montagens da seção 9.3: kernel novo enche o `/boot` (913M) e trava atualizações. Duas séries a mais, R$ 0,52/mês.
- **Silêncio da VM1 com o horário na consulta**, em vez de uma regra de supressão: as regras de processamento de alertas exigem registrar o `Microsoft.AlertsManagement` (NotRegistered). A consulta usa UTC−3 fixo (Brasília não tem horário de verão desde 2019). Se o horário mudar (decisão 3), a consulta muda junto.
- **Fila do worker em papel próprio**: o Update Message, que o retry usa, exige `messages/write`, e nenhum papel interno junta só isso com o `process/action` (tabela de permissões do Storage, lida em 28/10).
- **Papel de backup com `containers/write`**: a exclusão em lote do pgBackRest (Blob Batch) exige essa ação no pedido pai (mesma tabela). Ela não apaga container.
- **Alerta de job na fila há mais de 4 h e os dois alertas do banco** (seções 7 e 9.4) ficam para o próximo plano, junto do reconciliador e do script de verificação. Criados antes deles, disparariam sem motivo.

**No apply**, disparam os alertas de activity log da fatia 4: `pathsol-role-definition-v3` (5 vezes), `pathsol-role-assignment-v3` (11) e `pathsol-lifecycle-write-v3` (1). São do apply, não incidente. Depois do apply, até o agente entrar na VM1, o `pathsol-vm1-silencio-v3` dispara dentro do horário dela; por isso a instalação do agente na VM1 é o primeiro passo depois do apply.

**Depois do apply**, uma ação por autorização, registradas em `docs/operacao/`:
1. Conferência: sha256, `terraform plan` sem mudanças e os recursos com os atributos do plano.
2. VM1: agente (`AzureMonitorLinuxAgent`) com a identidade do sistema; conferir Heartbeat e `Perf` no workspace e os nomes reais das montagens (`InstanceName`) contra a consulta dos alertas.
3. VM2, desalocada: anexar a `pathsol-id-vm2-v3`. Depois, ligar; agente com a identidade nova (`mi_res_id` nas configurações), tetos de logs como os da VM1 e SSH a partir da VM1 (regras 200 a 230 já saíram); ciclo de desalocar e ligar, evidência e desalocar.
4. VM1: unit do status (seção 18), com teste.
5. Runbook (padrão 27): ambiente de execução novo e código novo; depois, retirar o Virtual Machine Contributor da automação no grupo das VMs.
6. Fatia 7: anexar o `pathsol-banco-v3` na VM1, XFS em `/srv/banco`, Postgres, pgBackRest, `pg_dump`, script de verificação e teste de restauração.

**Resto da fatia 7 (próxima sessão).** O disco já está em `/srv/banco` (XFS, `nofail`, ponto de montagem imutável). Fatos lidos em 29/10 (workflow, só fontes oficiais), que valem para o código:
- PostgreSQL 18.6 (13/08/2026); a próxima versão menor sai em 12/11/2026. Imagem `postgres:18.6-trixie`. No 18, o volume é `/var/lib/postgresql` e o PGDATA `/var/lib/postgresql/18/docker`: monta-se ali um subdiretório do disco (dono 999, modo 700), como a doc do Postgres manda. O `initdb` do 18 liga data checksums por padrão.
- Parada: a imagem declara `STOPSIGNAL SIGINT` (fast). O `docker stop` espera 10 s, e o `shutdown-timeout` do dockerd é de 15 s; os 120 s da seção 7 pedem `--stop-timeout` e `shutdown-timeout`, e como os dois interagem no desligamento não foi verificado.
- TLS: `ssl=on`, mínimo TLS 1.2 por padrão; chave do UID 999 com 0600 (ou root com 0640 e grupo 999); `hostssl` no `pg_hba.conf`, no lugar da linha `host` que a imagem grava.
- OOM: `--oom-score-adj -1000` no container, com `PG_OOM_ADJUST_FILE=/proc/self/oom_score_adj` e `PG_OOM_ADJUST_VALUE=0` para os filhos voltarem a 0 (doc do PG 18); o Docker desaconselha valor muito negativo. `/dev/shm` do container tem 64 MB por padrão (`--shm-size`).
- pgBackRest 2.60.0 numa imagem derivada da oficial (`pgbackrest=2.60.0-1.pgdg13+1`, sha256 do `.deb` `609dae5e…ab60`), porque o `archive_command` roda no container do Postgres; desde a 2.59 ele não roda como root. `repo1-type=azure`, `repo1-azure-key-type=auto` (IMDS sem client id; experimental segundo o mantenedor, issue #2741), `repo1-path=/pgbackrest`, `repo-bundle=y`, `archive-async=y` com spool local e `archive-push-queue-max` para o teto de WAL (passado o teto, o PITR quebra até um backup novo). Retenção: `repo1-retention-full-type=time`, `repo1-retention-full=35`, `repo1-retention-history=35`. O expire apaga em lote (Blob Batch), o que o `containers/write` do papel cobre. Se o IMDS responde de dentro do container não foi verificado: confere-se com `pgbackrest check`.
- `pg_dump` sem azcopy: Put Block e Put Block List com token do IMDS (o Put Blob vai até 5.000 MiB) e `If-None-Match: *`. A unit do status não manda `x-ms-date`, que a doc do Put Blob lista como obrigatório; o serviço aceitou, e a correção entra com o código do dump.
- Vigilância: idade do último backup pelo `pgbackrest info --output=json` (`timestamp.stop`) e do último WAL pela `pg_stat_archiver`, no syslog `local0`, mais os dois alertas de log do banco (plano novo).

Fatos conferidos na documentação em 28/10, que valem para os passos seguintes:
- pgBackRest 2.60.0 (18/10/2026; o PGDG de Debian trixie tem `2.60.0-1.pgdg13+1`) autentica no Blob com `repo-azure-key-type=auto` desde a 2.58.0, ainda experimental. Ele não escolhe a identidade: usa a padrão do IMDS, que na VM1 é a do sistema. A 2.60.0 faz o restore parar com erro se uma página tiver checksum inválido.
- PowerShell 7.4 no Automation: GA, mas o suporte upstream acaba em 10/11/2026. O 7.6 é GA no Automation desde julho de 2026, com suporte até 14/11/2028. Os ambientes 7.4 e 7.6 são criados à mão (não há ambiente do sistema) e ligados ao runbook pela propriedade `runtimeEnvironment` (API 2024-10-23).
- certbot 5.8.0 usa ARI na renovação por padrão. O Let's Encrypt passa o perfil padrão a 64 dias em 10/02/2027 e a 45 dias em 16/02/2028. Com 64 dias e renovação a ~2/3, sobram ~21 dias na renovação normal: o alerta de 21 dias da seção 4.5 dispararia sempre, e o script de verificação da fatia 7 precisa de um limiar relativo à validade.
- Agente: cache padrão de 10.000 MB em `/var/opt/microsoft/azuremonitoragent/events`, teto de 4.000 a 1.000.000 MB pela regra `AgentSettings` (que aparece como preview na página de gerenciamento do agente). Com só a identidade atribuída pelo usuário, as configurações da extensão levam `authentication.managedIdentity` com `identifier-name` `mi_res_id`.
- Docker 29: `builder.gc.defaultKeepStorage` é alias depreciado de `defaultReservedSpace`.

## Plano da fatia 5 (discos)

`terraform plan -out=discos.tfplan` em 27/10, 12:32 UTC: **2 a criar, 0 a alterar, 0 a destruir.** Os 29 recursos existentes aparecem sem mudança, e nenhum recurso de VM, disco atual ou rede aparece no plano. sha256 do plano: `09d553fd515469e972acab948950c18d0b77d7c69b19b6b5b96a56dfcab3bfdc`.

| Recurso | O quê | Custo/mês |
|---|---|---:|
| `azurerm_managed_disk.data["vm1"]` | `pathsol-dados-vm1-v3`: Premium SSD LRS de 128 GiB (P10), vazio, sem zona (como as VMs e os discos atuais), `prevent_destroy`. Recebe o `/data` da VM1: raízes do Docker e do containerd e os caches | R$ 177,72 |
| `azurerm_managed_disk.data["vm2"]` | `pathsol-dados-vm2-v3`: o mesmo, com 64 GiB (P6). Recebe o `/data` da VM2: raízes do Docker e do containerd; a WSI do job usa o disco temporário (seção 5.1) | R$ 92,03 |
| **Total** | Com o P20 (R$ 660,05) e o P15 (R$ 342,75) apagados, **−R$ 733,04/mês** (seção 5.4). Até as exclusões, os discos novos custam ~R$ 9 por dia (R$ 269,75 ÷ 30) | **R$ 269,75** |

Preços da Retail Prices API (BRL, brazilsouth, Premium SSD Managed Disks), lidos em 27/10: os mesmos do plano (seção 24).

Escolha desta sessão, fora do texto do plano: **`network_access_policy = "DenyAll"` e sem acesso público** nos dois discos, sem custo. Pela página "Restrict managed disks from being imported or exported" (learn.microsoft.com, lida em 27/10), o `DenyAll` impede exportar o disco, isto é, baixá-lo inteiro, e a rede pública desligada bloqueia importação e exportação pelo endpoint público. O cache de tiles da VM1 vai guardar cópias de WSI. Os 4 discos atuais estão em `AllowAll`, o padrão do Azure.

**Depois do apply**, numa sessão com o `az` do Pedro, uma ação por autorização, cada uma registrada em `docs/operacao/`:
1. VM1, ligada: `az vm disk attach` do `pathsol-dados-vm1-v3` na lun1, com cache ReadOnly. É o teste de anexar um disco de outro grupo com a VM ligada (seção 7). ReadOnly é o padrão do Azure para disco de dados, e o ReadWrite pode perder dado se a VM travar (learn.microsoft.com, "Azure premium storage: Design for high performance", lida em 27/10); o P20 de hoje está em ReadWrite.
2. VM1: `mkfs.ext4 -m 0` na lun1; com containerd e docker parados, cópia do esqueleto do `/data` (212K do Docker e 92K do containerd), troca do UUID no fstab (mesmas opções, `nofail,discard`), `RequiresMountsFor=/data` no containerd e no docker (resposta do Pedro de 19/10, item 6) e `docker info` igual ao de antes. A partida seguinte da VM1, pelo runbook, confere o boot com o disco novo.
3. VM1: `az vm disk detach` do P20.
4. `az disk delete` do P20 (decisão 2, letra a; autorização na hora; sem volta).
5. VM2, desalocada: `az vm disk attach` do `pathsol-dados-vm2-v3` na lun1, com cache ReadOnly.
6. `az vm start` da VM2, a primeira partida da v3 (R$ 4,67/h ligada; o auto-shutdown segue às 19:00 de Brasília até a fatia 6). Sem `fstrim`: o P15 vai ser apagado (resposta do Pedro à decisão 2).
7. VM2: leitura do fstab, do Docker, do `nvidia-smi` e das atualizações automáticas (riscos); depois, a mesma troca do passo 2, no P6.
8. VM2: `az vm disk detach` do P15, reinício para conferir o boot só com o P6 e `az vm deallocate`.
9. `az disk delete` do P15 (decisão 2, letra a; autorização na hora; sem volta).

Nenhum `docker pull` nem build antes do passo 9. Os tetos do Docker (logs e cache de build) entram na fatia 6, com os tetos de logs.

## Plano da fatia 4, apply B

`terraform plan -out=apply-b.tfplan` em 27/10, 02:40 UTC: **20 a criar, 0 a alterar, 0 a destruir.** Os 9 recursos existentes aparecem sem mudança, e nenhum recurso de VM, disco ou rede aparece no plano. sha256 do plano: `5b45ae4e163f9be6cc569d9687dc22070f0c16764cbd17408d6ac44412ddcba9`.

**Antes do apply, o Pedro registra o `Microsoft.KeyVault`** (`NotRegistered` em 27/10). Registrar provider é escrita na subscrição e fica fora do Terraform (comentário do provider azapi em `main/main.tf`). Comandos em `infra/terraform/LEIA-ME.md`. Registrado às 11:44:20 UTC.

| Recurso | O quê | Custo/mês |
|---|---|---:|
| `azurerm_storage_queue.jobs` | fila `jobs` na `pathsolwsiv3`. O Azure não tem TTL por fila: o produtor grava cada mensagem com TTL −1 e o visibility timeout (seção 9.1) | R$ 0,31 com a dead-letter (plano, seção 5.2) |
| `azurerm_storage_account.dead_letter` | `pathsoldlqv3`: conta só da dead-letter (seção 9.2), StorageV2, Standard LRS, Hot, TLS 1.2, sem chave compartilhada, sem acesso anônimo, `prevent_destroy` | R$ 0 vazia |
| `azurerm_storage_queue.dead_letter` | fila `jobs-dead-letter` | incluído acima |
| `azurerm_monitor_metric_alert` × 2 | `pathsol-dlq-mensagem-nova-v3`: `Transactions` com `ApiName = PutMessage` > 0 em 15 min, avaliado a cada 5 min, severidade 1. `pathsol-dlq-nao-vazia-v3`: `QueueMessageCount` médio > 0 em 1 dia, avaliado a cada hora, severidade 2. Os dois mandam ao action group | R$ 1,04 (2 × R$ 0,52194; seção 9.4) |
| `azurerm_storage_account.status` e `_static_website.status` | `pathsolstatusv3`: Standard LRS, sem chave compartilhada, sem acesso anônimo a blobs, sem logs de diagnóstico, `prevent_destroy`; site estático com índice `status.json` (padrão 26) | ~R$ 0,16 (seção 18) |
| `azurerm_key_vault.v3` | `pathsol-kv-v3`: standard, só RBAC, soft delete de 90 dias, sem proteção contra purga, `prevent_destroy` | R$ 1,57 (seção 5.2) |
| `azurerm_log_analytics_workspace.v3` | `pathsol-logs-v3`: PerGB2018, 30 dias de retenção, chaves do workspace desligadas, sem teto diário | R$ 0 até o agente (fatia 6); depois, ~R$ 1,27 (0,053 GB × R$ 24,0092/GB, Retail Prices API) |
| `azurerm_storage_container.h5` | `slide-h5` na `pathsolwsiv3`, privado, sem retenção legal (seção 6.6), `prevent_destroy`; caminhos `tenant/slide/extractor_version/` (skill `pathsol-contrato-h5`) | R$ 0 vazio; depois, por GiB (seção 6.1) |
| `azurerm_storage_management_policy.wsi` | decisão 1: `wsi-cold-30d` (Cold 30 dias depois da criação, nos containers `wsi-diagnose` e `wsi-publico`) e `h5-cool-90d` (Cool 90 dias depois da criação, no `slide-h5`), só block blobs | R$ 0; o Set Blob Tier é cobrado por operação (seção 6.3) |
| `azurerm_monitor_activity_log_alert` × 9 | categoria Administrative, status Succeeded ou Failed, no action group. No grupo: `clearLegalHold`, `managementPolicies/write` e `/delete`, exclusão de container, gravação e exclusão de storage account, exclusão de trava. Na subscrição: `roleAssignments/write` e `roleDefinitions/write` | R$ 0 (seção 5.2) |
| **Total** | | **~R$ 4,35** |

Escolhas desta sessão, dentro do plano:
- **Alertas além da lista da seção 6.4:** `managementPolicies/delete`, `containers/delete` e `roleDefinitions/write` (editar o papel sem exclusão poderia incluir a exclusão). O `storageAccounts/write` cobre a religação da chave compartilhada, o único caminho para as chaves que o Terraform lê com `listKeys` passarem a valer. Por isso o `listKeys` não tem alerta próprio: todo plan o chama.
- **Fila principal na `pathsolwsiv3` e `.h5` no `slide-h5`, na mesma conta:** o plano põe a fila e os derivados no storage da v3 (seção 5.1) e conta os `.h5` em Hot ZRS (seção 6.1).
- **Key Vault sem proteção contra purga:** depois de ligada, ela não desliga mais (doc do soft delete do Key Vault, lida em 27/10). Ligar depois continua possível. O soft delete do Key Vault é obrigatório e não é o soft delete do storage de que trata o `CLAUDE.md`.
- **Log Analytics sem teto diário:** um teto que pare a ingestão também cala os alertas de disco. Sem fonte de dados, o workspace não ingere nada. O teto é decidido na fatia 6, com o volume medido do agente.

**No apply,** os alertas de activity log nascem junto dos recursos, em paralelo. Alguns podem disparar já no apply (criação das contas e da política de ciclo de vida) e mandar e-mail ao Pedro. Isso não é incidente.

**Aplicado** pelo Pedro em 27/10, entre 11:47:59 e 11:48:22 UTC, com o mesmo sha256, e conferido na sessão 4. Três alertas dispararam, como previsto (sessão 4, item 3).

## Plano da fatia 4, apply A (WSI)

`terraform plan -out=wsi.tfplan` em 27/10, 02:12 UTC: **7 a criar, 0 a alterar, 0 a destruir.** O orçamento e o action group aparecem sem mudança, e nenhum recurso existente (VM1, VM2, discos, rede) aparece no plano. sha256 do plano: `22017a972368a6f32f5ab6e1b65319d14bc821ab7637f7498bb42ed2198b3dd3`.

| Recurso | O quê | Custo/mês |
|---|---|---:|
| `azurerm_storage_account.wsi` | `pathsolwsiv3`: StorageV2, Standard **ZRS**, Hot, TLS 1.2, chave compartilhada desligada, sem acesso anônimo a blobs (a rede pública segue aberta; sessão 3, item 3), sem soft delete (vem no MVP), `prevent_destroy` | R$ 0 vazia; depois, por GiB (Hot ZRS R$ 0,212691; plano, seção 24) |
| `azurerm_storage_container.wsi` × 2 | `wsi-diagnose` e `wsi-publico`, privados, `prevent_destroy` | R$ 0 |
| `azapi_resource_action.wsi_legal_hold` × 2 | `setLegalHold` em cada container, tag `decisao1`, `allowProtectedAppendWritesAll = false` | R$ 0 (plano, seção 6.4) |
| `azurerm_management_lock.wsi` | CanNotDelete na conta | R$ 0 |
| `azurerm_role_definition.blob_sem_exclusao` | `pathsol-blob-sem-exclusao-v3`, atribuível só em `rg-pathsol-v3`: lista containers, pede chave de delegação, lê, grava e acrescenta blobs; sem excluir, mover, apagar versão nem agir como superusuário da imutabilidade | R$ 0 |

**Entre os dois applies,** a retenção legal já vale, mas o alerta de `clearLegalHold` só nasce no apply B. Nenhum upload acontece antes da Fase 4, então essa janela não tem dado.

**Aplicado** pelo Pedro em 27/10, 02:21 UTC, com o mesmo sha256, e conferido na sessão 3.

## Plano do bootstrap

`terraform plan -out=bootstrap.tfplan` em 27/10, 01:20 UTC: **5 a criar, 0 a alterar, 0 a destruir.** Nenhum recurso existente (VM1, VM2, discos, rede) aparece no plano. sha256 do arquivo do plano: `2fbc57aff2bc6debcf5426aa3f2e9ff33807afa1e19233a64567329d825079f0`.

| Recurso | O quê | Custo/mês |
|---|---|---:|
| `azurerm_resource_group.v3` | `rg-pathsol-v3`, brazilsouth, `prevent_destroy` | R$ 0 |
| `azurerm_storage_account.tfstate` | `pathsoltfstatev3`: StorageV2, Standard LRS, Hot, TLS 1.2, chave compartilhada desligada, sem acesso público a blobs, versionamento de blobs ligado, `prevent_destroy` | ~R$ 0,50 (plano, seção 5.2: < 1 GiB em Hot LRS) |
| `azurerm_storage_container.tfstate` | container privado `tfstate` | R$ 0 |
| `azurerm_management_lock.tfstate` | CanNotDelete na conta do estado | R$ 0 |
| `azurerm_role_assignment.tfstate_operator` | Storage Blob Data Contributor do usuário do Pedro, só no container `tfstate` (o Owner não tem acesso a dados, e o backend lê e grava o estado pelo Entra ID) | R$ 0 |

## Plano do orçamento e do action group

`terraform plan -out=main.tfplan` em 27/10, ~01:50 UTC: **2 a criar, 0 a alterar, 0 a destruir.** sha256 do plano: `07ec9552d59328b58fc78a7c6f97d8bbcc98b2d2e0fd7cf959e2756bda65cc5c`.

| Recurso | O quê | Custo/mês |
|---|---|---:|
| `azurerm_monitor_action_group.alertas` | `pathsol-alertas-v3`, global, um destinatário de e-mail (o indicado pelo Pedro), esquema comum de alerta | R$ 0 (plano, seção 5.2) |
| `azurerm_consumption_budget_subscription.teto` | `pathsol-orcamento-v3`: R$ 5.000 por mês na subscrição, desde 01/10/2026; avisos em 50%, 80% e 100% do real e em 100% do previsto, por e-mail direto | R$ 0 (plano, seção 5.2) |

O orçamento manda e-mail direto, sem passar pelo action group, para não depender dele. O action group recebe os alertas de métrica e de log das fatias seguintes. Outubro já passou de R$ 2.500 até 26/10 (plano, seção 3), então o aviso de 50% deve sair na primeira avaliação do Cost Management, de 1 a 3 dias depois do apply. Esse aviso conta como disparo real do alerta de orçamento para o gate.

**Versionamento na conta do estado.** Escolha desta sessão, fora do texto do plano: permite voltar o estado depois de uma gravação ruim. Não é soft delete, e a regra do soft delete (`CLAUDE.md`, storage da v3) vale para as contas de dados. O estado tem dezenas de KB, então as versões custam centavos.

## Evidências (comando e saída resumida)

| Comando | Saída resumida |
|---|---|
| `az account show` | PATHSOLUTIONS TECNOLOGIA EM SAUDE LTDA; `bd87a1ca-e4f5-460b-9f12-c89e114293f1`; Enabled; login do usuário do Pedro no tenant |
| `az group exists -n rg-pathsol-v3` | `false` |
| `az vm list -d` | VM1 `vm-appviewer-prod-001` D8s_v5 running; VM2 `vm-appfoundation-prod-001` NC4as_T4_v3 deallocated; nenhuma das duas zonal |
| `az disk list -g rg-prod-brsouth-001` | VM1: P20 512 GiB e SO 30 GiB, Attached; VM2: P15 256 GiB e SO 30 GiB, Reserved |
| `az vm show --query identity` | VM1 SystemAssigned; VM2 sem identidade |
| `az provider list` | Registered: Storage, Compute, Network, ManagedIdentity, Authorization, OperationalInsights, Insights, Consumption, CostManagement, DevTestLab, ResourceHealth. NotRegistered: KeyVault, AlertsManagement, DBforPostgreSQL, Monitor. Automation: Registering |
| `az storage account check-name` | `pathsoltfstatev3`, `pathsolwsiv3`, `pathsoldlqv3` e `pathsolstatusv3` livres |
| `ps` na VM1 | o `codex` (extensão `openai.chatgpt` do Antigravity) rodando; o Claude Code também roda dentro do Antigravity |
| `gpg --verify`; `sha256sum -c` | `Good signature` da HashiCorp; `tf.zip: OK` |
| `terraform version` | v1.16.7 linux_amd64; sha256 do binário `54533008…d2ec` |
| `terraform init` (backend local), `fmt -check`, `validate` | azurerm v5.10.0 assinado pela HashiCorp; formato ok; `The configuration is valid` |
| `ps`; `ls ~/.antigravity-ide-server/extensions` (depois do apply) | nenhum processo nem pasta do codex |
| `az group show`; `az resource list`; `az lock list` | `rg-pathsol-v3` em brazilsouth com as 3 tags; só `pathsoltfstatev3`; trava `nao-apagar` CanNotDelete |
| `az storage account show` | Standard_LRS, StorageV2, TLS1_2, `allowSharedKeyAccess false`, `allowBlobPublicAccess false`, 3 tags |
| `az role assignment list` no container `tfstate` | Storage Blob Data Contributor |
| `az storage blob list --auth-mode login` | `bootstrap.tfstate`, 16.279 bytes, 01:40:53 UTC |
| `.terraform/terraform.tfstate` do bootstrap | backend `azurerm`, `use_cli true`, `use_msi false`, `use_azuread_auth true` |
| `terraform state pull` contra a cópia local | mesma linhagem e mesmos recursos; serial 7 contra 6 |
| `terraform show -json main.tfplan` | 4 avisos (50, 80 e 100 Actual; 100 Forecasted), `GreaterThanOrEqualTo`, 1 e-mail cada, no domínio da empresa |
| `terraform plan` do `main/` depois do apply | `No changes` |
| `az monitor action-group show` | `pathsol-alertas-v3`, enabled, `pathsolv3`, 1 receptor de e-mail com status Enabled, no domínio da empresa, 3 tags |
| GET do orçamento (`Microsoft.Consumption/budgets`, api 2023-11-01) | R$ 5.000 mensal, BRL, de 01/10/2026 a 01/10/2036; 4 avisos ativos, 1 e-mail cada, nenhum grupo; gasto 0,0 logo depois da criação |
| `az monitor activity-log list -g rg-pathsol-v3 --offset 1h` | escritas do bootstrap às 01:37–01:38 e do action group às 01:51 UTC; `listKeys` na conta do estado às 01:38:03 (apply) e 01:46:57 (plan); nenhum teste de notificação |
| `az account show` (sessão 2) | mesma subscrição, Enabled, login de usuário |
| `az storage account check-name -n pathsolwsiv3`; `az role definition list --custom-role-only` | nome livre; nenhum papel personalizado na subscrição |
| `az provider show -n Microsoft.Storage` | Brazil South com as zonas 1, 2 e 3; `blobServices` até a API 2026-09-01 |
| registro do Terraform (`Azure/azapi`) | 2.13.0 de 28/09/2026; zip linux_amd64 `bbe4a395…1b70`, igual ao hash `zh:` do lockfile; chave 6F0B91BDE98478CF |
| `terraform init`; `fmt -check`; `validate` | azapi v2.13.0 instalado; formato ok; `The configuration is valid` |
| `terraform show -json wsi.tfplan` | os atributos da tabela do apply A; o corpo do `setLegalHold`; as 3 ações de dados e as 2 de controle do papel |
| `az storage account blob-service-properties show -n pathsoltfstatev3` | soft delete de blob e de container desligados: a conta de WSI, criada pelo mesmo caminho sem `delete_retention_policy`, deve nascer igual (conferir depois do apply) |
| `az account show` (sessão 3) | mesma subscrição, Enabled, login de usuário |
| `sha256sum wsi.tfplan` | `22017a97…3dd3`, igual ao do relatório |
| `az storage account show -n pathsolwsiv3` | StorageV2, Standard_ZRS, Hot, TLS1_2, `allowSharedKeyAccess false`, `defaultToOAuthAuthentication true`, `allowBlobPublicAccess false`, `publicNetworkAccess Enabled`, `networkRuleSet.defaultAction Allow` sem regras, nenhum endpoint privado, 3 tags, criada às 02:21:01 |
| `az storage account blob-service-properties show -n pathsolwsiv3` | `deleteRetentionPolicy.enabled false`; soft delete de container, versionamento e change feed nulos |
| GET de cada container (api 2025-06-01) | `wsi-diagnose` e `wsi-publico`: `publicAccess None`, `hasLegalHold true`, tag `decisao1` gravada pelo usuário do Pedro às 02:21:40 e 02:21:38, `allowProtectedAppendWritesAll false`, sem política por tempo |
| `az lock list -g rg-pathsol-v3` | `nao-apagar` CanNotDelete na `pathsolwsiv3` e na `pathsoltfstatev3` |
| `az role definition list --custom-role-only` | `pathsol-blob-sem-exclusao-v3`, escopo `rg-pathsol-v3`, as 2 ações e as 3 ações de dados do plano, sem `notActions` |
| `az role assignment list` | nenhuma atribuição na `pathsolwsiv3` e nenhuma do papel `eb9dba69…` em toda a subscrição |
| `az monitor activity-log list -g rg-pathsol-v3 --offset 2h` | apply A entre 02:21:01 e 02:21:40, pelo usuário do Pedro (app do Azure CLI), com um `listKeys` na conta às 02:21:24. A gravação no action group às 02:01:21 tem o `correlationId` da criação das 01:51 e não traz IP: é o evento final da mesma operação |
| `terraform plan -detailed-exitcode` (depois do apply A) | `No changes`, saída 0 |
| `terraform state show azurerm_storage_account.wsi` | `public_network_access = "Enabled"`; no schema do azurerm 5.10.0, `public_network_access_enabled` está marcado como depreciado |
| `az provider show` (sessão 3) | `Microsoft.KeyVault` e `Microsoft.AlertsManagement` NotRegistered; Insights, OperationalInsights e Storage Registered |
| `az storage account check-name`; `az keyvault check-name` | `pathsoldlqv3`, `pathsolstatusv3` e `pathsol-kv-v3` livres |
| `az monitor metrics list-definitions` (queueServices da `pathsolwsiv3`) | `Transactions` (Total, dimensão `ApiName`, grão a partir de PT1M); `QueueMessageCount` (Average, sem dimensão, grão a partir de PT1H) |
| Retail Prices API, Log Analytics, brazilsouth, BRL | Analytics Logs Data Ingestion R$ 24,0092/GB; retenção R$ 1,0439/GB/mês |
| learn.microsoft.com, lidos em 27/10 | Set Blob Service Properties com Entra ID: ação `blobServices/write`. Site estático: o `allowBlobPublicAccess` não o afeta. Ciclo de vida: o prefixo começa pelo nome do container, até 10 por regra; `daysAfterCreationGreaterThan` vale para Cool e Cold. Key Vault: soft delete não desliga, retenção de 7 a 90 dias fixada na criação, proteção contra purga desligada por padrão e irreversível |
| `terraform fmt -check`; `validate`; `plan -out=apply-b.tfplan` | formato ok; `The configuration is valid`; 20 a criar, 0 a alterar, 0 a destruir |
| `terraform show -json apply-b.tfplan` | os atributos da tabela do apply B; 20 `create` e 9 `no-op` |
| `az account show` (sessão 4) | mesma subscrição, Enabled, login de usuário |
| `sha256sum apply-b.tfplan`; `terraform state list`; `terraform plan -detailed-exitcode` (depois do apply B) | `5b45ae4e…cba9`, igual ao do relatório; 29 recursos e 2 data sources; `No changes`, saída 0 |
| `az resource list -g rg-pathsol-v3`; `az provider show` | 18 recursos de topo, todos com a tag `componente`; `Microsoft.KeyVault` Registered; `AlertsManagement` e `Monitor` NotRegistered |
| `az storage account show` e `blob-service-properties show` (`pathsoldlqv3`, `pathsolstatusv3`) | StorageV2, Standard_LRS, Hot, TLS1_2, `allowSharedKeyAccess false`, `defaultToOAuthAuthentication true`, `allowBlobPublicAccess false`, criadas às 11:48:00; soft delete de blob desligado e soft delete de container, versionamento e change feed nulos, como na `pathsolwsiv3` |
| GET das filas e dos containers (ARM, api 2025-06-01) | `jobs` na `pathsolwsiv3` e `jobs-dead-letter` na `pathsoldlqv3`; `slide-h5` privado, sem retenção; `wsi-diagnose` e `wsi-publico` com `hasLegalHold true`, a tag `decisao1` de 02:21 e `allowProtectedAppendWritesAll false`; `$web` na `pathsolstatusv3` |
| `az storage account management-policy show` | `wsi-cold-30d` (Cold depois de 30 dias da criação, prefixos `wsi-diagnose` e `wsi-publico`) e `h5-cool-90d` (Cool depois de 90 dias, prefixo `slide-h5`), só `blockBlob`; gravada às 11:48:12 |
| `az storage blob service-properties show --auth-mode login`; `curl -sI` no endpoint web da `pathsolstatusv3` | site estático ligado, índice `status.json`; `404 WebContentNotFound`, sem login, porque ainda não há arquivo |
| `az keyvault show`; `az monitor log-analytics workspace show` | standard, só RBAC, soft delete de 90 dias, sem proteção contra purga, 0 políticas de acesso, sem ACL de rede; PerGB2018, 30 dias, `disableLocalAuth true`, sem teto diário (−1) |
| `az monitor metrics alert list`; `az monitor activity-log alert list` | os 2 de métrica e os 9 de activity log ligados, com critérios, escopos e action group do plano |
| `az monitor activity-log list` (`rg-pathsol-v3`, desde 11:30 UTC) | 73 eventos, nenhum com falha; escritas do usuário do Pedro (app do Azure CLI); 2 `listKeys` e 2 `workspaces/sharedKeys`; 3 `ActivityLogAlerts/Activated` às 11:54:09–10; auditorias `SecurityCenterBuiltIn` |
| `az monitor activity-log list` (subscrição, desde 11:00 UTC, fora do `rg-pathsol-v3`) | `default-allow-ssh` às 11:42:24, pelo usuário do Pedro no portal; `Microsoft.KeyVault/register` às 11:44:20, pelo Azure CLI |
| `az role assignment list --all` | 6 atribuições; a única da v3 é a do container `tfstate`; nenhuma criada no apply B |
| `lsblk`; `/etc/fstab`; `/etc/docker/daemon.json`; `docker info`; `docker system df` (VM1) | P20 na lun0 (`/dev/sdb`), ext4 `data`, `/data` com `nofail,discard`, 332K usados; `data-root` `/data/docker`; `/var/lib/containerd` → `/data/containerd`; 0 imagens, containers, volumes e cache de build; nenhum `RequiresMountsFor` |
| `az disk list -g rg-prod-brsouth-001`; `az vm show` | P20 (Attached, lun0, ReadWrite) e P4 da VM1; P15 (Reserved, lun0, ReadOnly) e P4 da VM2; os 4 sem zona, `AllowAll` e rede pública ligada |
| `az vm list-skus` | D8s_v5: 16 discos de dados, PremiumIO, sem disco temporário e sem `CachedDiskBytes`; NC4as_T4_v3: 8 discos, `CachedDiskBytes` de 144 GiB e temporário de 176 GiB |
| Retail Prices API (BRL, brazilsouth, Premium SSD Managed Disks) | P6 R$ 92,0342; P10 R$ 177,7206; P15 R$ 342,7468; P20 R$ 660,0453 por mês |
| `terraform providers schema -json` (azurerm 5.10.0) | `azurerm_managed_disk` com `network_access_policy` e `public_network_access_enabled`, sem depreciação |
| `terraform fmt -check`; `validate`; `plan -out=discos.tfplan`; `show -json` | formato ok; `The configuration is valid`; 2 a criar, 0 a alterar, 0 a destruir; 2 `create` e 29 `no-op`; nenhuma referência ao grupo das VMs |
| `systemctl cat apt-daily-upgrade.timer` (VM1) | `OnCalendar=*-*-* 6:00`, `RandomizedDelaySec=60m`, `Persistent=true` |
| `az disk show` (P15 e P20, 28/10); activity log do `rg-prod-brsouth-001` desde 27/10 14:00 | `ResourceNotFound` nos dois; `disks/delete` do P15 de 22:40:53 a 22:41:12 UTC de 27/10 (Portal) e do P20 de 21:07:14 a 21:07:30 de 28/10 (Azure CLI); VM1 desalocada às 23:00:35 de 27/10 e ligada às 09:01:31 de 28/10 |
| `lsblk`; `findmnt /data`; `journalctl -b`; `docker info` (VM1, 28/10) | só a lun1, `/data` no P10; `data.mount` 09:02:04, containerd 09:02:16, docker 09:02:33; `docker info` igual ao de 27/10 |
| GET dos agendamentos de auto-shutdown; activity log | VM1 `Disabled` (`2000`) desde 20:52:39 UTC de 28/10, pelo Portal; VM2 `Enabled` (`1900`) |
| `certbot revoke`; CRL `ye1.c.lencr.org/6.crl` de 22:07:35 | `POST /acme/revoke-cert` 200; série `05AAA4E3…F105` revogada às 21:26:08, `Cessation Of Operation` |
| `az network nsg rule list` (depois) | 100 (SSH), 1010 (80) e 1020 (443), as duas com destino `10.0.0.5` |
| `ss -tlnH`; `dpkg-query` (VM1, depois da limpeza) | nada na 111; rpcbind, `nfs-common`, aznfs, certbot do apt e 11 órfãos fora; 0 órfãos restantes |
| `journalctl -u systemd-journald`; `docker info`; `docker buildx inspect` | journal `570.3M, max 1.0G`; `LoggingDriver local`; GC com `Reserved Space 20GiB` (antes, `Max Used Space 93.13GiB`) |
| `dig CAA` nos autoritativos; `curl` e `openssl s_client` pelo DNS público | CAA com `accounturi=…/acct/3924918922` e `validationmethods=http-01`; `upload` NXDOMAIN; 503 com `verify=0`, HSTS, TLS 1.2 e 1.3, handshake recusado para outro nome |
| `az monitor log-analytics query` (as 3 consultas dos alertas) | compilam; a do silêncio devolve 1 linha às 19:47 de Brasília (quarta, VM1 sem agente) |
| Retail Prices API (BRL, brazilsouth, Azure Monitor, Alerts) | regra de log a 15 min R$ 2,6097, série extra R$ 0,2610; a 5 min, R$ 7,8291 e R$ 0,7829; série de métrica R$ 0,5219 depois de 10 grátis |
| `terraform fmt`; `validate`; `plan -out=fatias6-7.tfplan`; `show -json` | formato ok; válido; 30 a criar, 1 a alterar, 0 a destruir; regras atuais da política iguais; nenhum recurso de VM ou rede |
| `sha256sum fatias6-7.tfplan`; `terraform plan -detailed-exitcode` (sessão 7) | `073ee8e3…f48f`; saída 2 (4 atribuições a recriar por formato do ID do papel); depois da correção do data source, `No changes`, saída 0 |
| GET do papel `19e7f393…` sem escopo e no escopo da subscrição | `/providers/Microsoft.Authorization/roleDefinitions/19e7f393…` e `/subscriptions/bd87…/providers/…/19e7f393…`, os dois `Storage Queue Data Reader` |
| `az identity show`; `az role definition list --custom-role-only`; `az role assignment list --assignee` (VM1, VM2, automação) | `pathsol-id-vm2-v3` com 3 tags; 6 papéis personalizados com as ações do plano; 4 atribuições da VM1, 6 da VM2 e 2 da automação (uma delas o Virtual Machine Contributor antigo), escopos do plano |
| `az disk show`; GET do `backup-banco`; `management-policy show` | P6 64 GiB `Premium_LRS`, `DenyAll`, rede pública `Disabled`, `Unattached`; container `None`, sem retenção legal; 3 regras, `backup-dump-35d` com `delete` após 35 dias em `backup-banco/dump/` |
| GET das regras de coleta, das associações, dos 4 alertas de log e do alerta de saúde | `Logical Disk(*)\% Used Space` a 60 s e `local0` para `logs`; `MaxDiskQuotaInMB 4000`; 2 associações por VM; disco 80 (sev. 2) e 90 (sev. 1) por `Computer` e `InstanceName`, silêncio da VM1 (sev. 1) e VM2 ligada (sev. 2), a cada 15 min; Resource Health da VM1 |
| `az monitor activity-log list --max-events 2000` desde 01:15 UTC | 82 eventos, nenhum `Failed`; 5 `roleDefinitions/write`, 11 `roleAssignments/write`, 1 `managementPolicies/write`; 1 `automationAccounts/listKeys` (data source do Terraform) |
| `az vm extension set` (VM1 e VM2); `dpkg-query`; `df` | `AzureMonitorLinuxAgent` 1.45, `Succeeded`, atualização automática; `azuremonitoragent 1.45.1-1585`; `/` da VM1 de 56% para 58% e o da VM2 de 69% para 71% |
| consulta ao `pathsol-logs-v3` pelo ARM (`workspaces/query`, api 2017-10-01) | Heartbeat das duas VMs; `Perf` por ponto de montagem; `Syslog` `local0` das duas |
| `az vm run-command invoke` (VM2); `ssh -G azure-foundation` | 3 chaves de host e IP 10.0.0.4; depois da edição do Pedro, `stricthostkeychecking true` e `userknownhostsfile /home/azureps/.ssh/known_hosts` |
| VM2 depois do ciclo (02:01) | boot 01:59:58; 48 holds; `data.mount` antes do containerd e do docker; Docker `local`, `nvidia`, engine igual; T4 595.71.05; journal com teto de 1,0G |
| `systemctl enable --now`, `stop`, `start` de `pathsol-status`; `curl` no endpoint web | HTTP 201 nos três; `up`, `down` com `back_at` 06:15 de 29/10 e `up`; `application/json` e `no-cache` |
| REST do Automation (api 2024-10-23) | ambiente `pathsol-ps76-v3` (PowerShell 7.6, Az 15.1.0); PATCH do `TurnOn-VMs` recusado; runbook novo publicado igual ao repositório; teste `Completed` com `7.6.0-preview.5` e HTTP 202; agenda só com o runbook novo |

## O que não foi possível verificar

- Se o e-mail do orçamento chega. O orçamento foi criado nesta subscrição CSP, em BRL; o primeiro aviso esperado é o de 50%.
- Se uma tentativa negada aparece no activity log como Failed e dispara o alerta, e se o alerta de `QueueMessageCount` dispara com uma contagem diária (fatia 8).
- Se a VM1 usa o cache de host: o `az vm list-skus` não traz `CachedDiskBytes` para a D8s_v5, mas o P20 aceitou ReadWrite.
- Se um prefixo igual ao nome do container (`wsi-diagnose`) também pega um container de nome mais longo (`wsi-diagnose2`). A doc não diz. Aqui não faz diferença, porque todo container `wsi-*` é de WSI.
- Se o ciclo de vida muda a camada de um blob sob retenção legal (seção 6.3 do plano: inferência). Fica para os testes da fatia 8.
- O disparo real dos alertas de disco. O `InstanceName` do `Perf` é o ponto de montagem (conferido em 29/10); o disparo fica para a fatia 8.
- Se a regra `AgentSettings` limita mesmo o cache do agente no Linux (recurso que aparece como preview).
- A renovação do certificado novo, de verdade ou por `certbot renew --dry-run`: o dry-run usa a conta de staging, que o CAA atual não permite.
- O runbook novo ligando a VM1 desalocada: o teste e o job de prova rodaram com a VM1 ligada (`start` aceito, sem efeito). A prova é a partida de 30/10, às 06:00, depois do primeiro auto-shutdown religado.
- O status gravado no desligamento real (o `ExecStop` durante a desalocação): o teste foi com `systemctl stop`. Confere-se no journal do boot anterior, depois da mesma partida de 30/10.
- O `Content-MD5` gravado no blob do estado não bate com o MD5 da cópia local. A explicação provável é a gravação do serial 7, mas não foi conferida byte a byte: o `az storage blob download` para `/dev/stdout` devolveu 0 bytes.

## Riscos

- **Login do `az` só durante o Terraform.** Até 27/10, o login do Pedro, com Owner, ficava aberto entre as sessões. Desde o `az logout` desse dia, cada sessão que precisar do `az`, inclusive para leitura, depende de o Pedro entrar de novo.
- **Chaves das contas no estado do Terraform.** O azurerm chama `listKeys` em cada plan e apply, mesmo com a chave compartilhada desligada, e grava as chaves no estado. Elas só valem se alguém religar a chave compartilhada, o que exige escrita no plano de controle (Owner ou Contributor). As contas de dados da fatia 4 seguem o mesmo caminho. Os alertas de activity log da fatia 4 precisam distinguir esse `listKeys` do Terraform de um uso indevido. O mesmo vale para as chaves do Log Analytics (`workspaces/sharedKeys`), que não servem com a autenticação local desligada.
- **Kernel e driver da VM2 em hold.** Os 48 pacotes só mudam numa janela de manutenção (padrão 11), com `apt-mark unhold`, atualização e checagem da GPU. Enquanto isso, as correções de segurança do kernel não entram na VM2. A extensão `NvidiaGpuDriverLinux` (handler 1.13.0.2 no disco; 1.9 no modelo, com atualização automática de versão menor) roda `enable` a cada partida (2 s, `Ready`, nas duas de 27/10); o que o script faz sem driver não foi lido.
- **A gravação de blob inclui a troca de camada.** O Set Blob Tier exige `blobs/write` (learn.microsoft.com, página da operação Set Blob Tier, lida em 27/10), e o papel sem exclusão precisa dessa ação. Uma identidade com o papel poderia mudar a camada de uma WSI à mão; a regra (`CLAUDE.md`, storage da v3) deixa isso só para o ciclo de vida, então o código das Fases 4 e 5 não pode chamar Set Blob Tier. Mudar a camada não altera a WSI.
- **Rede pública aberta nas contas, no Key Vault e no Log Analytics.** O que protege é a identidade: sem chave compartilhada, sem acesso anônimo (exceto o site do status, por desenho) e com retenção legal nas WSIs. Uma credencial do Entra ID vazada alcança o endpoint de qualquer rede.
- **Alertas que disparam com o trabalho normal.** O `storage-write` dispara em todo apply que mude uma conta, e o `role-assignment` em toda atribuição de papel, inclusive as das próximas fatias. Cada um manda e-mail ao Pedro, que confere se o apply era dele.
- **CAA preso a uma conta ACME.** A chave da conta fica só em `/etc/letsencrypt` na VM1, sem backup. Se ela se perder, a renovação falha até o Pedro mudar o CAA na Cloudflare. O HSTS de 1 ano também obriga o nome a ficar em HTTPS.
- **Teto de cache do agente em preview e VM2 com o `/` em 71% de 29G.** O agente ocupa ~0,85 GB em cada VM. No pior caso (agente sem rede), o cache de até 4.000 MB e a fila do rsyslog, de até 1 GB, levam o `/` da VM2 para perto de 88%; os alertas de disco avisam em 80%.
- **PowerShell 7.6 do Automation em build preview.** O teste do runbook rodou com `7.6.0-preview.5`, embora a doc diga GA desde julho de 2026. O código só usa `Invoke-RestMethod` e `Invoke-WebRequest`; trocar de ambiente é um PATCH no runbook novo.
- **Chaves da conta de automação no estado.** O data source `azurerm_automation_account` chama `listKeys` em todo plan, como as contas de storage e o Log Analytics.
- **Primeira partida da VM1 pelo runbook novo.** Se ele falhar em 30/10, às 06:00, a VM1 fica desalocada até alguém ligá-la. O alerta `pathsol-vm1-silencio-v3` avisa a partir das 06:20; a volta é ligar pelo Portal e, se for o papel, recriar o Virtual Machine Contributor na automação.

## Decisões pedidas ao Pedro

Respondidas em 28/10, ~23:00 UTC: o Pedro aprovou o apply do `fatias6-7.tfplan` e pediu por escrito a regra `backup-dump-35d`; o padrão 27 usa PowerShell 7.6; a extensão `log-analytics` saiu e o `az` não instala mais extensões sozinho (`extension.use_dynamic_install=no`).

Respondidas na sessão 7 (29/10): runbook novo em vez de trocar o tipo do `TurnOn-VMs`; seguir no 7.6 com o build preview; teto de 1G no journal da VM2, apagando os arquivos mais antigos; chaves de host da VM2 pelo Run Command, e a edição do alias pelo próprio Pedro.

Pedidas:
1. **Runbook `TurnOn-VMs` antigo:** publicado, sem agenda, com código do legado (`PowerShell72`, sem suporte desde 30/09). Recomendação: apagar depois que o runbook novo ligar a VM1 desalocada em 30/10, às 06:00. Exclusão só com autorização na hora.
