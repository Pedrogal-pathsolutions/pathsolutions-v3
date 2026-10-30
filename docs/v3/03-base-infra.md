# Fase 3 — Base de infraestrutura

Concluída em 30/10/2026, na sessão 10, e parada no gate. Começou em 27/10/2026 (UTC), depois do APROVADO FASE 2, e seguiu as fatias da seção 19.2 do plano (`docs/v3/02-plano-v3.md`). O resumo do fechamento vem primeiro; depois vêm o histórico das sessões, os planos aplicados, as evidências, o que não foi verificado, os riscos e as decisões. O detalhe de cada ação nas VMs e no Azure, com horário, comando e saída, está em `docs/operacao/`; o código, em `infra/terraform/` e `deploy/vm1/`.

## Resumo do fechamento

### Gate (seção 19.2 do plano)

| Critério | Resultado | Evidência |
|---|---|---|
| Restauração do banco testada | Dois testes em 29/10, cada um com o backup físico mais o WAL até uma linha gravada na hora e com o dump; o rascunho é apagado no fim. A restauração roda sozinha todo dia 1, e a verificação a cada 15 min acusa se a última tiver mais de 35 dias | `docs/operacao/2026-10-29-fatia7-banco.md`; evidências (`pathsol-banco-restaura`) |
| Alertas disparados de verdade | 18 das 20 regras dispararam com evento real ou provocado, todas chamando o action group, que entrega e-mail desde a confirmação do código (29/10, 13:53 UTC). As regras com estado também resolveram (disco, banco, dead-letter, silêncio da VM1). Não dispararam o `pathsol-vm2-ligada-v3` (4 h de VM2, ~R$ 19) e o `pathsol-lock-delete-v3` (as únicas travas do grupo protegem a conta de WSI e a do estado). O orçamento disparou, mas o e-mail dele não chegou: pendência abaixo | "Resultados da fatia 8"; `docs/operacao/2026-10-29-fatia8-testes.md` |
| Proteção das WSIs testada | Sob retenção legal, nenhuma identidade sobrescreve nem apaga blob: VM1 e VM2 recebem 403 antes da retenção, e o Pedro, como dono dos dados, 409. O container e a conta reais ficam barrados pela retenção e pela trava. A conta com retenção não se apaga (`AccountProtectedFromDeletion`). O ciclo de vida muda a camada sem regravar o blob. Uma retenção tirada dispara alerta, mas o Terraform não a vê | idem |

### Pendência do gate: e-mail do orçamento

O aviso de 50% do orçamento consta como disparado no Cost Management em 27/10, 02:10 UTC (26/10, 23:10 de Brasília), mas o e-mail direto não chegou, nem no spam (Pedro, 30/10). A correção vai no `limpeza.tfplan`, a pedido do Pedro: as 5 notificações passam a ir também para o `pathsol-alertas-v3`, cujo e-mail chega, e entra um aviso de 30% do real (R$ 1.500). O gasto passa desse valor todo mês, então esse aviso prova o caminho mensalmente. O registro do alerta de 50% no Cost Management tem 1 destinatário, igual ao do `terraform.tfvars`, e nenhum action group: o endereço estava certo. Pela documentação lida em 30/10, o orçamento de subscrição aceita action group, inclusive no Azure Plan via parceiro; ele é avaliado a cada 24 h, sobre dados com 8 a 24 h de atraso, e o aviso sai até 1 h depois da avaliação. Outubro já está em 57% do teto, mas a documentação não diz se um aviso novo, já ultrapassado no mês, dispara na avaliação seguinte. Se não disparar em outubro, a prova vem em novembro, quando o gasto passar de R$ 1.500. A pendência fecha quando o e-mail do orçamento chegar pelo action group.

### Estado no fechamento

- **Terraform:** `bootstrap/` com 5 recursos e `main/` com 64 depois do `limpeza.tfplan` (até ele, o estado gravado ainda lista os 8 objetos da conta descartável). Os recursos novos ficam em `rg-pathsol-v3`; o orçamento, os papéis, as atribuições e as associações de coleta valem nos escopos do plano (subscrição, grupos e VMs). VM1, VM2, discos de SO e rede entram só como `data`. Estado remoto na `pathsoltfstatev3`, com versionamento e trava.
- **Storage:** `pathsolwsiv3` (ZRS; `wsi-diagnose` e `wsi-publico` com retenção legal; `slide-h5`; `backup-banco`; fila `jobs`; soft delete de blobs de 14 dias, sem exclusão permanente; ciclo de vida com `wsi-cold-30d`, `h5-cool-90d` e `backup-dump-35d`; trava `nao-apagar`), `pathsoldlqv3` (dead-letter), `pathsolstatusv3` (status) e `pathsoltfstatev3` (estado). A conta descartável dos testes foi apagada em 30/10.
- **Monitoramento:** action group com o receptor verificado; 20 regras de alerta (11 de activity log, 2 de métrica, 6 de busca em log e o orçamento); Log Analytics com o `Perf` e o `local0` das duas VMs. Depois do `limpeza.tfplan`, o orçamento avisa em 30, 50, 80 e 100% do real e em 100% do previsto, por e-mail direto e pelo action group.
- **VM1** (D8s_v5): `/data` no P10 e `/srv/banco` no P6 do banco; PostgreSQL 18.6 com TLS e `pg_hba` só com a VM2; pgBackRest e `pg_dump` no Blob; verificação a cada 15 min; nginx e certificado novos; agente; unit do status; IP privado estático 10.0.0.5; auto-shutdown às 23:00 e partida às 06:00 pelo runbook `pathsol-ligar-vm1-v3`.
- **VM2** (NC4as_T4_v3): `/data` no P6, identidade `pathsol-id-vm2-v3`, agente, kernel e driver 595.71.05 em hold, IP privado estático 10.0.0.4 e auto-shutdown às 23:30. Desalocada.

### Custo

Pelas tabelas dos planos aprovados, os recursos novos da fase somam ~R$ 388/mês com o volume de hoje: R$ 269,75 dos discos de dados, R$ 92,03 do disco do banco e ~R$ 27 de alertas, coleta de logs, Key Vault, filas e contas pequenas. O que é cobrado por GiB (WSI, `.h5`, backups e o soft delete deles) cresce com o uso. A exclusão do P20 e do P15 tirou R$ 1.002,80/mês, então a conta líquida da fase fica em −R$ 614/mês. O orçamento mostra R$ 2.863,13 gastos em outubro até 30/10 e previsão de R$ 3.117,28 para o mês (preço de tabela; a fatura do parceiro CSP pode ser diferente), contra o teto de R$ 5.000.

### Pendências que não bloqueiam o gate

1. **Fatia 0, exportação de teste do Motic:** não chegou. Proposta: passar para a Fase 4, onde entram o leitor e a desidentificação (decisão 2 abaixo).
2. **Conferências que dependem do relógio**, para a primeira sessão depois do gate: a resolução do `pathsol-dlq-nao-vazia-v3` (a mensagem de teste expira em 31/10, 02:02 UTC); nenhum disparo do `pathsol-vm1-saude-v3` no auto-shutdown de 30/10 (correção aplicada às 12:02 UTC); o pgBackRest no primeiro backup com soft delete (a regravação do `backup.info` gera a primeira cópia em soft delete).
3. **Estado do Terraform e orçamento:** o `limpeza.tfplan` tira do estado o último objeto da conta descartável e grava a correção do orçamento. O Pedro o aplica como última ação da sessão 10, pelo SSH, e faz o `az logout`. A conferência (sha256, `terraform plan` sem mudanças, 64 recursos no `main/` e as 5 notificações do orçamento) abre a próxima sessão.

## Situação por fatia

| Fatia | Situação |
|---|---|
| 0. Exportação de teste do Motic | não chegou. Proposta: passa para a Fase 4 (decisão 2) |
| 1. Decisão 4 antes do primeiro apply | feita: codex desinstalado, applies do Pedro pelo SSH com o Antigravity fechado e `az logout` no fim do dia |
| 2. Terraform e estado remoto | feita: bootstrap aplicado e estado migrado para `pathsoltfstatev3` |
| 3. Orçamento e action group | feita, com uma pendência do gate. O aviso de 50% disparou em 27/10, 02:10 UTC (Cost Management), mas o e-mail direto não chegou (Pedro, 30/10); a correção, com o action group e um aviso de 30%, está no `limpeza.tfplan`. O receptor do action group só foi confirmado por código em 29/10 (sessão 9); desde então os e-mails dos alertas chegam |
| 4. Storage e alertas | feita, em dois applies, a pedido do Pedro (27/10). A: conta de WSI, containers com retenção legal, papel sem exclusão e trava. B: fila e dead-letter, conta do status, Key Vault, Log Analytics, alertas de activity log e da dead-letter, container dos `.h5` e a política de ciclo de vida da decisão 1. Os dois aplicados e conferidos; os testes de proteção e de disparo foram feitos na fatia 8 (29/10) |
| 5. Primeira partida da VM2 e discos | feita (27 e 28/10). VM1 com o `/data` no P10, conferido depois do ciclo de desalocar e ligar de 27 para 28/10; VM2 com kernel e driver congelados e o `/data` no P6. O Pedro apagou o P15 (27/10, 22:41 UTC, pelo Portal) e o P20 (28/10, 21:07 UTC). Registro em `docs/operacao/2026-10-27-discos-fatia5.md` |
| 6. VMs | feita (28 e 29/10). VM1: limpeza da seção 4.5, tetos de logs, nginx e certificado novos, agente, unit do status. VM2: identidade, agente, tetos de logs e chave de host conferida. Apply do `fatias6-7.tfplan` conferido. Runbook novo (padrão 27) no PowerShell 7.6, e a automação sem o Virtual Machine Contributor. Auto-shutdown da decisão 3 desde 29/10: VM1 às 23:00 e VM2 às 23:30. No ciclo real de 28 para 29/10, o status gravou `down` e `up`, e o runbook novo ligou a VM1 desalocada; o `TurnOn-VMs` antigo foi apagado (29/10). Registro em `docs/operacao/2026-10-28-fatia6-vms.md` |
| 7. Postgres, backup e restauração | feita (29/10). PostgreSQL 18.6 em container na VM1, TLS obrigatório, `pg_hba` só com a VM2 na rede; pgBackRest com a identidade da VM1 (full semanal, diferencial diário, WAL a cada 5 min no máximo); `pg_dump` diário; verificação a cada 15 min no syslog; restauração testada duas vezes e agendada todo mês; os 2 alertas de log do banco aplicados e disparados de verdade (sessão 9). Registro em `docs/operacao/2026-10-29-fatia7-banco.md` |
| 8. Testes | feita (29 e 30/10, sessões 9 e 10). Provados: SAS só de criação com blocos, sobrescrita e exclusão sob retenção legal com cada identidade (os passos que apagam pelo Pedro), trava, poller com o papel restrito, start em Deallocating, `% Used Space` contra `df`, PutMessage e alertas disparados de verdade (dead-letter, disco 80% e 90%, banco, activity log, silêncio da VM1, orçamento), além de restauração, `oom_score_adj` e IMDS no container (fatia 7). Em 30/10: Cold pelo ciclo de vida sob retenção legal, parada limpa do Postgres no auto-shutdown, resolução dos alertas de disco e de banco, conta com retenção que não se apaga, retenção tirada que o Terraform não vê e limpeza da conta descartável. Registro em `docs/operacao/2026-10-29-fatia8-testes.md` |

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

### Sessão 8 (29/10, a partir das 11:15 UTC)

Registro detalhado em `docs/operacao/2026-10-28-fatia6-vms.md` e `docs/operacao/2026-10-29-fatia7-banco.md`, seções "Sessão 8".
1. O Pedro entrou no `az` e desalocou a VM1 pelo Portal às 23:51 de 28/10 (02:51:14 UTC), depois da sessão 7. A partida das 06:00 de 29/10 foi o ciclo real.
2. Ciclo real conferido: a desalocação chega ao convidado como desligamento ordenado (`hv_utils`, ~3,5 s até o poweroff); o status gravou `down` (HTTP 201) antes de a rede parar e `up` às 06:01:57; o runbook novo ligou a VM1 desalocada (job `Completed`, `start/action` `Succeeded` pela identidade da automação, que só tem o papel de ligar a VM1); o `/srv/banco` montou limpo, antes do containerd e do docker.
3. Achado: no desligamento, o `/srv/banco` desmontou em paralelo com a parada do docker. A unit do Postgres leva `RequiresMountsFor=/srv/banco` e `After=docker.service`.
4. Com autorização do Pedro, o runbook `TurnOn-VMs` antigo foi apagado (11:20 UTC). Fatia 6 concluída.
5. Fatia 7, autorizada como sequência de 8 passos (~11:40 UTC), com a condição do Pedro de que o `pg_hba` tenha só `hostssl` e `scram-sha-256`, com o IP privado da VM2 como única origem de rede. Três paradas, cada uma corrigida com autorização: (a) o build parou na porta do UID 999, que na VM1 é do coletor do agente de monitoramento; (b) o `stanza-create` parou porque a imagem oficial não traz o `ca-certificates`; (c) o log mostrou o servidor reiniciando inteiro 4 vezes, porque o processo assíncrono do pgBackRest, órfão, era herdado pelo postmaster como PID 1 e saía com erro. Correção de (c): `docker run --init`.
6. Resultado: banco no ar, backup full e diferencial, dois dumps e dois testes de restauração aprovados; a verificação roda a cada 15 min, e as linhas chegam ao Log Analytics (`SeverityLevel error` para as falhas).
7. Plano `fatias7-8.tfplan`: os 2 alertas de log do banco e a conta descartável dos testes de proteção (seção 6.3 do plano). Resumo em "Plano das fatias 7 e 8".
8. Verificação automática das 12:15 UTC com os 7 itens `OK`. O Pedro aprovou o plano para aplicar em seguida, o que encerra a sessão.

### Sessão 9 (29/10, a partir das 13:02 UTC)

Registro detalhado em `docs/operacao/2026-10-29-fatia8-testes.md`.
1. O Pedro aplicou o `fatias7-8.tfplan` às 13:00 UTC. Conferência: sha256 igual, `terraform plan` sem mudanças, os 10 recursos com os atributos do plano e 41 eventos no activity log, nenhum com falha; os 6 alertas previstos dispararam.
2. Decisões do Pedro sobre os riscos novos: IPs privados estáticos, uma ação por autorização; e soft delete de blobs na `pathsolwsiv3` já, com 14 dias e sem exclusão permanente (plano em "Plano do soft delete").
3. Leitura de documentação em workflow (6 tópicos, só fontes oficiais, sem comando no Azure): IP estático, soft delete, SAS `c`, retenção legal, poller e alertas.
4. **Alertas sem e-mail.** O Pedro avisou que nenhum alerta chegava. O endereço estava certo, mas o receptor do action group estava `VerificationPending`, campo que só aparece na API `2026-03-01-preview`: faltava a confirmação por código (OTP) que o action group exige (seção 9.4 do plano). O Pedro confirmou pelo Portal; o teste de notificação saiu com `Succeeded` às 13:53. O Portal renomeou o receptor, e o código seguiu o nome novo.
5. IP estático da VM2 (autorizado): `Dynamic` para `Static`, mesmo endereço; no diff do NIC só mudaram a alocação e o etag, e a VM2 subiu com 10.0.0.4 pelo DHCP do Azure.
6. Testes da fatia 8, autorizados como sequência numa pergunta só, com tokens do IMDS das VMs só nos scripts e os passos que apagam pelo Pedro, com o comando exato. Todos com o resultado esperado; os fatos novos estão em "Resultados da fatia 8".
7. O Pedro deixou o IP estático da VM1 para a última ação da sessão, depois do commit e do push e antes do apply dele.
8. Achado nos testes: o `pathsol-vm1-saude-v3` dispara em toda desalocação da VM1. Correção no código e plano alternativo (`fim-do-dia.tfplan`).

### Sessão 10 (30/10, a partir das 12:04 UTC)

Registro detalhado em `docs/operacao/2026-10-29-fatia8-testes.md`, seção "Sessão 10".
1. O Pedro aplicou o `fim-do-dia.tfplan` às 12:02 UTC e seguiu no `az`. Conferência: sha256 igual; `terraform plan` sem mudanças; soft delete de blobs na `pathsolwsiv3` com 14 dias e `allowPermanentDelete false`; o alerta novo `pathsol-blob-service-write-v3`, que disparou às 12:09 com o próprio apply; o `pathsol-vm1-saude-v3` só com `PlatformInitiated`; nenhuma falha no activity log.
2. IP estático da VM1 conferido na partida de 30/10 (10.0.0.5 pelo DHCP), e o registro da sessão 9 commitado (`f3ccd06`).
3. Cold pelo ciclo de vida sob retenção legal: os blobs `a` e `c` passaram a Cold às 05:30:01 UTC, sem mudar o `lastModified`.
4. Parada limpa do Postgres no auto-shutdown de 29/10: `database system is shut down` às 02:02:03,667 UTC, antes do docker e do `/srv/banco`; na partida, `database system was shut down at 2026-10-30 02:02:03 UTC`, sem recuperação.
5. Alertas: disco 80% e 90% e falha do banco resolvidos em 29/10; o `pathsol-dlq-nao-vazia-v3` segue disparado até a mensagem de teste expirar; o `pathsol-vm1-saude-v3` disparou no auto-shutdown, antes do apply da correção.
6. Leitura de documentação em workflow (4 tópicos, só fontes oficiais, sem comando no Azure): exclusão de conta com retenção legal, `clearLegalHold`, atribuições de papel de recurso apagado e o comportamento do azurerm 5.10.0 e do azapi 2.13.0 quando o arquivo sai da configuração.
7. Limpeza da conta descartável, com os passos que apagam pelo Pedro, um comando por vez: a exclusão com retenção deu 409 `AccountProtectedFromDeletion`; a retenção tirada não aparece no `terraform plan`; a política de ciclo de vida e a conta foram apagadas, e as 4 atribuições com escopo nela sumiram junto. Os alertas `pathsol-storage-delete-v3`, `pathsol-clear-legal-hold-v3` e `pathsol-lifecycle-delete-v3` dispararam, os dois últimos pela primeira vez.
8. `teste-protecao.tf` fora do código e `limpeza.tfplan` salvo: 0 a criar, 0 a alterar, 1 a destruir, só no estado.
9. Achado menor: a cada 15 min, o Postgres grava duas linhas `LOG` de TLS fechado sem `close_notify` pela conferência do certificado do banco (`deploy/vm1/banco/pathsol_banco.py:296`). Ficam só no journal (decisão 4 abaixo).
10. Pedido do Pedro (~13:05 UTC): o e-mail do aviso de 50% do orçamento (26/10, horário de Brasília) não chegou, nem no spam. O orçamento passou a mandar também ao `pathsol-alertas-v3`, com um aviso novo de 30% (R$ 1.500), e o `limpeza.tfplan` foi refeito: 0 a criar, 1 a alterar, 1 a destruir. Leitura de documentação em workflow (3 tópicos, só fontes oficiais, sem comando no Azure) sobre orçamento com action group. Resumo em "Plano da limpeza da conta descartável e do orçamento"; o e-mail do orçamento ficou como pendência do gate.

## Resultados da fatia 8 (29 e 30/10)

| Teste | Resultado |
|---|---|
| SAS de delegação só de criação (`c`), envio em blocos | 1º e 2º Put Block (com o blob ainda não confirmado) 201; Put Block List com `If-None-Match: *` 201. O fluxo da seção 4.2 funciona |
| Sobrescrita com `c` | Put Block, Put Block List e Put Blob sobre o existente 403 `UnauthorizedBlobOverwrite`, com ou sem `If-None-Match` |
| Versão da SAS e da requisição | Decide o `x-ms-version` da requisição: com ele em 2026-02-06, até a criação dá 403 `AuthorizationPermissionMismatch`, com qualquer `sv`; com ele em 2026-04-06, `sv` 2026-02-06 cria. A extensão precisa mandar `x-ms-version` 2026-04-06 ou mais nova em toda requisição. Com versão velha, falha fechada |
| Sobrescrita em blocos sob retenção legal | Com o token da VM1, que grava: Put Block, Put Block List, Put Blob e metadado 409 `BlobImmutableDueToLegalHold`. Criar blob novo no container sob retenção funciona |
| Exclusão com cada identidade | VM1 e VM2: 403 em blob e container, inclusive com SAS `d` assinada pela VM1 e pela ARM; a permissão é conferida antes da retenção. Pedro, como dono dos dados: `BlobImmutableDueToLegalHold`, `ContainerHasLegalHold` e `ContainerProtectedFromDeletion` na conta descartável; `ScopeLocked` no `wsi-publico` e na `pathsolwsiv3`. sha256 e ETag dos blobs iguais no fim |
| Alertas de activity log com tentativa negada | As 3 recusas do Pedro pela ARM aparecem como `Failed` e dispararam os alertas. A tentativa negada da VM1 pela ARM (403) não aparece no activity log |
| Poller com o papel restrito | O papel `pathsol-vm2-energia-v3`, sem `locations/operations/read`, leu o `Azure-AsyncOperation` e o `Location` (200) até `Succeeded`, ao contrário da página de operações assíncronas da ARM. Start em 1 min 44 s |
| Start durante o Deallocating | O start foi aceito (202). As duas operações terminaram `Succeeded`, o start 0,16 s antes, e a VM2 ficou ligada. O `Succeeded` do deallocate não prova VM desalocada: o reconciliador e o worker leem o `PowerState` |
| `% Used Space` contra `df` | Mesma conta do `df` (usado ÷ (usado + livre)), sem arredondar, nas duas VMs; no `/mnt` cheio, 93,045 contra 94% do `df` |
| Alertas disparados de verdade | Dead-letter: mensagem nova 4 min 41 s depois do PutMessage, resolvido em 25 min; `nao-vazia` em 1 h 21 min (a doc fala em contagem diária). Disco 80% e 90% em 14 e 16 min, resolvidos às 15:48 e 15:50. Banco: silêncio às 14:39 (resolvido às 15:25) e falha 8 min depois da linha sintética (resolvido às 15:59). Activity log: 23 disparos de 27 a 29/10; em 30/10, blob service (12:09), exclusão de conta negada (12:29), retenção tirada (12:34), política de ciclo de vida apagada (12:49) e conta apagada (12:54). Silêncio da VM1 em 29/10, 01:34, antes do agente entrar na VM1 (resolvido às 02:20). Orçamento: 50% em 27/10, 02:10. Os e-mails chegam desde a confirmação do código; os 5 de 30/10 chegaram (resposta do Pedro) |
| Cold pelo ciclo de vida sob retenção legal | Os blobs `a` e `c` passaram a Cold às 05:30:01 UTC de 30/10, ~15,5 h depois da criação, com o `lastModified` igual ao da criação. Confirma a inferência da seção 6.3 do plano |
| Parada limpa do Postgres na desalocação real | No auto-shutdown de 29/10 (02:02 UTC), `database system is shut down` em 0,37 s, antes do docker e do `/srv/banco`; na partida, `database system was shut down at 2026-10-30 02:02:03 UTC`, sem recuperação |
| Conta com retenção legal | `az storage account delete` pelo Pedro: 409 `AccountProtectedFromDeletion` ("The container(s) wsi-teste have legal hold") |
| Retenção tirada | O `clearLegalHold` dispara o alerta em ~5 min. O `terraform plan` segue `No changes`, sem nem a nota de mudança fora do Terraform: o azapi não detecta a falta da retenção |
| Atribuições de papel de recurso apagado | Saíram com a conta, em segundos: nem a listagem da subscrição nem o GET as encontram. A documentação não diz isso |
| Não testados | `pathsol-vm2-ligada-v3` (4 h de VM2, ~R$ 19), `pathsol-lock-delete-v3` (só há travas de produção no grupo), o `pathsol-vm1-saude-v3` com o filtro novo (só a plataforma dispara) e o e-mail de teste do action group, que o Pedro não identificou com certeza |

## Plano da limpeza da conta descartável e do orçamento (Terraform)

`terraform plan -out=limpeza.tfplan` refeito em 30/10, 13:17–13:18 UTC, depois da exclusão da conta pelo Pedro, da saída do `teste-protecao.tf` e do pedido do Pedro sobre o e-mail do orçamento: **0 a criar, 1 a alterar, 1 a destruir.** No JSON do plano, 63 `no-op`, 1 `update` no lugar (o orçamento) e 1 `delete` (só no estado); nenhum recurso com dado, de VM, disco, rede, conta de WSI, Key Vault ou trava muda. sha256: `485598005f225370e91ece93259dc17d236226746c55ca113ca3a9c05d1f646b`. O primeiro `limpeza.tfplan` (12:48, sha256 `435a7d7a…efbda5`, só com a limpeza) foi substituído e não vale mais.

| Recurso | O quê | Custo/mês |
|---|---|---:|
| `azurerm_consumption_budget_subscription.teto` (alterar, no lugar) | As 5 notificações com `contact_groups` igual ao `pathsol-alertas-v3`, além do e-mail direto, e um aviso novo de 30% do real (R$ 1.500), que o gasto passa todo mês. Valor (R$ 5.000), período mensal, início em 01/10/2026 e os outros 4 avisos ficam iguais (`alertas.tf`) | R$ 0 (orçamento e e-mail do action group sem custo; seção 5.2) |
| `azapi_resource_action.teste_legal_hold` (destruir) | Sai do estado. Com `when = "apply"`, o destroy não chama o Azure (código da tag v2.13.0 do azapi, `internal/services/azapi_resource_action_resource.go`, linhas 413–422; doc do registry: "no action will be performed on the Azure resource unless the `when` argument is set to `destroy`"). O container a que ele se refere já não existe | R$ 0 |
| Os outros 7 objetos da conta (conta, container, política e as 4 atribuições) | Deram 404 no refresh e já não estão no estado refrescado que o apply grava; nenhuma ação (código do Read do azurerm 5.10.0: com 404, "removing from state") | R$ 0 (a conta custava < R$ 0,01) |

Fatos da documentação para o orçamento (workflow de 30/10, só fontes oficiais):
- Action group em orçamento só vale nos escopos de subscrição e de resource group, pelo ID completo; o Azure Plan via parceiro é suportado, e cada notificação precisa de ao menos um e-mail ou um action group.
- A API que o azurerm 5.10.0 usa (Microsoft.Consumption, 2019-10-01) aceita até 5 notificações. O plano usa as 5; não cabe outra.
- O azurerm grava o orçamento com um PUT inteiro, que leva o eTag lido no plano (`"1dd65b5ac099078"`, igual ao do Azure às 13:15 UTC). Se o eTag mudar antes do apply, a API pode recusar (não documentado); o apply para sem mudar o orçamento, e um plano novo resolve.
- A API pede o `start_date` dentro do mês corrente ("Past start date should be selected within the timegrain period"). Por isso o apply vai até 31/10, 21:00 de Brasília, o fim de outubro em UTC (riscos).
- O common alert schema do action group não impede o alerta de orçamento.

O apply é do Pedro, pelo SSH, com o Antigravity fechado. Se o estado mudar antes, o Terraform recusa o plano velho, e outro plano é feito.

## Plano do soft delete de blobs na `pathsolwsiv3` (Terraform)

Pedido do Pedro em 29/10 (sessão 9), antes do MVP: soft delete de blobs na `pathsolwsiv3`, com 14 dias e sem exclusão permanente. Fecha o risco "backups apagáveis de dentro da VM1".

`terraform plan -out=soft-delete.tfplan` em 29/10, ~13:20 UTC: **1 a criar, 1 a alterar, 0 a destruir.** Os outros 70 recursos aparecem como `no-op`; nenhum recurso de VM, disco ou rede muda (conferido no JSON do plano). sha256: `344897fb71a3d6e18eb6c5900f877ef37f256e211981f2cb81a4d9e9a679aa74`.

| Recurso | O quê | Custo/mês |
|---|---|---:|
| `azurerm_storage_account.wsi` (alterar) | `blob_properties.delete_retention_policy`: 14 dias, `permanent_delete_enabled = false` (`wsi.tf`). No JSON do plano, só esse bloco muda: versionamento, change feed, último acesso e soft delete de container continuam desligados | hoje ~R$ 0 (o banco tem poucos MiB); com o volume da seção 7, +R$ 5 a +R$ 12 |
| `azurerm_monitor_activity_log_alert.control_plane["blob-service-write"]` | `pathsol-blob-service-write-v3`: `blobServices/write` no grupo, com sucesso ou falha. Desligar o soft delete ou encurtar a retenção é essa operação, e nenhum alerta atual a cobre (`alertas.tf`) | R$ 0 (seção 5.2) |
| **Total** | | **hoje ~R$ 0; depois, +R$ 5 a +R$ 12** |

Conta do custo: o dado em soft delete é cobrado como dado ativo, na mesma camada (Hot ZRS, R$ 0,2127/GB, Retail Prices API, lida em 29/10; soft-delete-blob-overview, "Pricing and billing"). As WSIs não entram, porque sob a retenção legal nada se apaga nem se sobrescreve. Entram o que o pgBackRest expira e os dumps que a regra `backup-dump-35d` apaga (a exclusão do ciclo de vida também vira soft delete): cada um fica 14 dias a mais, ~40% (14/35) do armazenamento dos backups. Com os R$ 13 a R$ 31 da seção 7 em ZRS, isso dá +R$ 5 a +R$ 12 por mês. Até o primeiro expire, daqui a 35 dias, só as regravações dos arquivos de controle do pgBackRest (alguns KB) geram cópias: com o versionamento desligado, sobrescrever cria um snapshot em soft delete.

Fatos da documentação (lidos em 29/10) que valem para o plano:
- Soft delete e retenção legal convivem; um blob sob a retenção não pode ser apagado, então não vira soft delete. A Microsoft recomenda ligar o soft delete antes das políticas de imutabilidade; ligar depois não é proibido.
- Com `allowPermanentDelete` desligado (o padrão), ninguém remove um blob em soft delete antes do fim dos 14 dias. Quem tem `blobServices/write` pode desligar o soft delete e apagar de novo; daí o alerta novo.
- O soft delete de blob não protege contra a exclusão do container nem da conta. O papel de backup da VM1 não tem `containers/delete`; o soft delete de container segue para o MVP.
- O azurerm 5.10.0 manda o bloco inteiro de propriedades do serviço de blob; no JSON do plano, versionamento, change feed, último acesso (que não pode ligar com a retenção legal), CORS e soft delete de container ficam como estão.
- A listagem do `pathsol-banco` não pede `include=deleted`, então não vê blobs em soft delete. Se o pgBackRest lista blobs em soft delete não foi verificado; a verificação a cada 15 min e o próximo backup mostram.

**Plano alternativo do fim do dia.** Depois do achado do alerta de saúde da VM1 (sessão 9, item 8), `terraform plan -out=fim-do-dia.tfplan` em 29/10, ~15:35 UTC: **1 a criar, 2 a alterar, 0 a destruir.** As mesmas duas mudanças do `soft-delete.tfplan` e mais `pathsol-vm1-saude-v3` só com a causa `PlatformInitiated` (sai a `Unknown`). Custo igual: R$ 0 a mais. sha256: `10b5ea9da4febfae5c2ca99ce2c06018f1e4a75435dc9b2dd836c2d5f0775c60`. O Pedro aplica um dos dois; o outro fica velho.

## Plano das fatias 7 e 8 (Terraform)

`terraform plan -out=fatias7-8.tfplan` em 29/10, ~12:20 UTC: **10 a criar, 0 a alterar, 0 a destruir.** Os 61 recursos existentes aparecem como `no-op`; nenhum recurso de VM, disco ou rede muda (conferido no JSON do plano). sha256: `e2920e2ed54b54168817440c1c29264298539427a49c36984e0f8414642b6892`.

| Recurso | O quê | Custo/mês |
|---|---|---:|
| `azurerm_monitor_scheduled_query_rules_alert_v2.banco_falha` | `pathsol-banco-falha-v3` (sev. 1): linha `SeverityLevel == "error"` do `pathsol-banco` no `Syslog` local0 da VM1, janela de 30 min, a cada 15 min, com estado | R$ 2,61 |
| `azurerm_monitor_scheduled_query_rules_alert_v2.banco_silencio` | `pathsol-banco-silencio-v3` (sev. 2): nenhuma linha do `pathsol-banco` em 40 min, de segunda a sexta, das 06:40 às 22:50 de Brasília | R$ 2,61 |
| `azurerm_storage_account.teste` | `pathsoltestev3`: conta descartável dos testes de proteção (seção 6.3 do plano), StorageV2, Standard LRS, Hot, TLS 1.2, sem chave compartilhada, sem acesso anônimo, rede pública como a `pathsolwsiv3`; sem `prevent_destroy` e sem trava, porque o Pedro a apaga depois dos testes | < R$ 0,01 (alguns KB por alguns dias; operações em centavos) |
| `azurerm_storage_container.teste` e `azapi_resource_action.teste_legal_hold` | `wsi-teste`, privado, com retenção legal (tag `teste`) pelo mesmo caminho dos containers de WSI | R$ 0 |
| `azurerm_storage_management_policy.teste` | regra `teste-cold`: Cold 0 dias depois da criação, só em `wsi-teste`, para o teste de camada sob retenção | R$ 0 |
| `azurerm_role_assignment.teste` × 4 | VM1: papel sem exclusão no `wsi-teste` (`teste-protecao.tf:68`) e `Storage Blob Delegator` na conta (`:74`), porque a chave de delegação é pedida à conta; VM2: `Storage Blob Data Reader` no `wsi-teste` (`:80`); Pedro: `Storage Blob Data Owner` no `wsi-teste` (`:86`), para os passos que apagam | R$ 0 |
| **Total** | | **~R$ 5,22** |

Preço das regras de log da Retail Prices API (BRL, brazilsouth), lido em 28/10; o plano estimava os mesmos R$ 5,22 para os dois alertas do banco (seção 7).

Escolhas da fatia 7, fora do texto do plano:
- **Imagem derivada da oficial** (`postgres:18.6-trixie` fixada por digest) com o pgBackRest 2.60.0 (sha256 do `.deb` fixado), o `ca-certificates` (a base não traz CA, e sem ela o pgBackRest não valida o Blob) e o usuário `postgres` com UID e GID 5432: na VM1, o 999 é o `azureotelcollector` e o `systemd-journal`.
- **`docker run --init`.** O `archive-push` assíncrono deixa um processo órfão; com o postmaster como PID 1, cada saída com erro desse processo derrubava o servidor inteiro (4 vezes em 29/10). Com o `docker-init` como PID 1, o órfão fica com ele.
- **Rede do host:** o que escuta é o `listen_addresses` (127.0.0.1 e 10.0.0.5). O `pg_hba` tem só a VM2 como origem de rede, a pedido do Pedro, e o superusuário entra só por socket, sem senha.
- **Locale do provedor builtin, C.UTF-8:** ordem por código Unicode, que não muda com a glibc, então um backup físico restaura numa imagem mais nova sem reindexar. A ordenação em português, quando a Fase 5 precisar, vem por colação ICU na consulta ou na coluna (não verificado).
- **TLS autoassinado** de 730 dias (até 28/10/2028), fixado pelos clientes com `sslmode=verify-full`.
- **Limiar do certificado:** 21 dias (seção 4.5) ou 1/4 da validade, o que for menor. Com os certificados de 64 dias do Let's Encrypt em 2027, a renovação normal acontece com ~21 dias, e o limiar fixo dispararia sempre.
- **Rotina diária única** às 06:00 de Brasília, com `Persistent` (roda na partida quando a VM1 estava desligada): full quando o último full tem 6 dias ou mais, senão diferencial; depois, o `pg_dump`. A verificação tolera backup e dump de até 26 h e, nas 3 primeiras horas depois da partida, um mais antigo (noite e fim de semana).
- **Dump** (`pg_dumpall --globals-only` e `pg_dump -Fc --compress=zstd` de cada banco) em blocos de 64 MiB, com `If-None-Match: *` no Put Block List; um blob só aparece inteiro, e o marcador `completo` só depois de todos.
- **Restauração mensal automática** (dia 1, 10:00, `Persistent`), num rascunho em `/data` que o código apaga no fim, com um banco sintético `canario`. A verificação acusa restauração com mais de 35 dias.
- **WAL descartado:** passado o teto de 8 GiB, o pgBackRest dá o WAL por arquivado e o descarta (texto do `pgbackrest help`). A verificação acusa quando o PostgreSQL conta como arquivado um segmento que o repositório não tem.
- **`x-ms-date`** na unit do status (pendência do relatório), reinstalada e testada.

Escolhas da fatia 8 neste plano:
- **Conta descartável em LRS:** a redundância não muda retenção legal, ciclo de vida nem permissões. Os testes de opção C da seção 6.3 (metadado, tag e regra de exclusão) não entram: a decisão 1 ficou com a opção B.
- **Teste da proteção fora da `pathsolwsiv3`.** Um blob de teste num container de WSI ficaria lá para sempre. Na conta real, as tentativas de apagar container e conta (o Pedro) não deixam resíduo; a sobrescrita de blob vai para a conta descartável, com as mesmas identidades e papéis.

**No apply** disparam, como previsto: `pathsol-storage-write-v3` (conta nova), `pathsol-lifecycle-write-v3` (política nova) e `pathsol-role-assignment-v3` (4 vezes). O `pathsol-banco-falha-v3` só dispara se houver falha nos 30 min anteriores à primeira avaliação; a última foi às 12:05:45 UTC (restauração ainda não feita).

**Depois do apply**, numa pergunta só, com autorização do Pedro:
1. Conferência: sha256, `terraform plan` sem mudanças e os 10 recursos.
2. Na conta descartável, pela VM1: SAS de delegação só de criação (`c`) com Put Block e Put Block List e `If-None-Match: *`; segundo Put Block com `c`; versão da SAS e da requisição (seção 4.2). Sobrescrita em blocos de um blob existente sob retenção legal, pela VM1 e pela VM2. Exclusão de blob e de container: VM1 e VM2 recebem 403; o Pedro, como dono dos dados, faz os passos que apagam.
3. Cold pelo ciclo de vida sob retenção legal, conferido no dia seguinte.
4. Na conta real, o Pedro tenta apagar um container de WSI e a conta: barrados pela retenção legal e pela trava.
5. No fim, o Pedro tira a retenção do `wsi-teste` (dispara o `clearLegalHold`; o `terraform plan` deve continuar sem mudanças, porque o azapi não detecta drift) e apaga a conta; o `teste-protecao.tf` sai do código.

Os testes da fatia 8 que não dependem do apply (parada limpa na desalocação, `% Used Space` contra `df`, poller e start em Deallocating, PutMessage na dead-letter, alerta de disco, orçamento e alerta do banco) também vão numa pergunta só.

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
| `journalctl -b -1` (sessão 8) | `hv_utils: Shutdown request received` 02:51:14,96; `status.json down: HTTP 201` 02:51:15,69; `srv-banco.mount` e docker parados em paralelo; `systemd-networkd` parado 02:51:18,22; `Journal stopped` 02:51:18,49 |
| activity log da VM1; jobs do Automation (sessão 8) | `deallocate/action` 02:51:14 (Portal, usuário do Pedro); job `pathsol-ligar-vm1-v3` `Completed` 09:01:24–26, `VM1 start: HTTP 202`; `start/action` `Succeeded` 09:02:15 pela identidade `75b93dbe-…`, só com o `pathsol-vm1-ligar-v3` |
| `journalctl -b 0`; `findmnt /srv/banco`; endpoint do status (sessão 8) | `Ending clean mount` do XFS 09:01:51,74; `srv-banco.mount` antes do containerd e do docker; `up: HTTP 201` 09:01:57; `{"status": "up", …09:01:57…}` |
| `az rest --method delete` do `TurnOn-VMs`; GET; activity log | rc=0; `ResourceNotFound`; agenda só com o runbook novo; `runbooks/delete` `Succeeded` 11:20:26 |
| `getent passwd 999`; `getent group 999` (VM1) | `azureotelcollector` e `systemd-journal`; 5432 livre |
| `docker buildx imagetools inspect postgres:18.6-trixie` | índice `sha256:979bccfd…e0e4`; amd64 `sha256:f4b419e3…db6f`; `STOPSIGNAL SIGINT`; volume `/var/lib/postgresql` |
| `gpg --verify InRelease`; `sha256sum -c` do `Packages.bz2` (PGDG trixie) | `Good signature`, chave `…7FCC 7D46 ACCC 4CF8`; `OK`; `pgbackrest 2.60.0-1.pgdg13+1`, sha256 `609dae5e…86ab60` |
| `az network nic list` | VM1 10.0.0.5 e VM2 10.0.0.4, alocação `Dynamic` |
| `docker build`; `id postgres`; `pgbackrest help` | imagem `sha256:7f04bd26…8f0b` com `ca-certificates 20250419+deb13u1`; UID e GID 5432; `auto` entre os tipos de chave do Azure |
| `ss -tlnp`; `pg_settings`; `pg_hba_file_rules`; `pg_database` | 5432 só em 127.0.0.1 e 10.0.0.5; `ssl=on`, TLS 1.2, checksums, `archive_mode=on`, 300 s; regras `local all postgres peer` e `hostssl all all 10.0.0.4/32 scram-sha-256`; provedor builtin C.UTF-8 |
| `psql` com `sslmode=disable` e com `verify-full` | `no pg_hba.conf entry … no encryption`; `… SSL encryption` (o TLS passou) |
| `/proc/<pid>/oom_score_adj`; `docker top` | `docker-init` e postmaster com -1000, processos do Postgres com 0; `archive-push:async` filho do `docker-init` |
| `journalctl -u pathsol-banco` | 4 reinícios com `untracked child process … exit code 103` antes do `--init`; nenhum depois |
| `pgbackrest info`; listagem do `backup-banco` | full `20261029-120528F` (22,7 MB; 2,7 MB no repositório) e um diferencial; WAL de `…0001` em diante; `dump/20261029T120530Z/` e `dump/20261029T120627Z/`, cada um com 3 arquivos e o marcador |
| `systemctl start pathsol-banco-restaura` (2 vezes) | `OK restauracao: backup com WAL até a linha nova (1 linhas) e dump 20261029T120530Z` e `(2 linhas) … 20261029T120627Z`; rascunho removido |
| consulta ao `pathsol-logs-v3` (`Syslog`, `ProcessName == "pathsol-banco"`) | `Facility local0`; `SeverityLevel info` e `error`; ingestão em até 1 min 42 s |
| `terraform fmt -check`; `validate`; `plan -out=fatias7-8.tfplan`; `show -json` | formato ok; válido; 10 a criar, 0 a alterar, 0 a destruir; 61 `no-op`; nenhum recurso de VM, disco ou rede com mudança |
| `sha256sum fatias7-8.tfplan`; `terraform plan -detailed-exitcode` (sessão 9) | `e2920e2e…6b892`; `No changes`, saída 0 |
| GET da `pathsoltestev3`, do `wsi-teste`, da política, das atribuições e dos 2 alertas do banco; activity log desde 12:50 | atributos do plano; `hasLegalHold true`, tag `teste`; regra `teste-cold`; 4 atribuições com os escopos do plano; 41 eventos sem falha e 6 disparos |
| GET do action group com a API `2026-03-01-preview` | receptor com o endereço informado pelo Pedro, `VerificationPending` às 13:40 e `Verified` às 13:53 |
| `az monitor action-group test-notifications create` | `state Complete`, e-mail `Succeeded`, enviado às 13:53:51 |
| `az network nic ip-config update` (VM2); diff do JSON do NIC; `ip -4 addr` na partida | rc=0, `Static` 10.0.0.4; só `etag` e alocação mudaram; `eth0` 10.0.0.4 pelo DHCP (168.63.129.16), mesmo MAC |
| `fatia8_vm1.py cria`, `fatia8_vm2.py teste`, `fatia8_energia.py liga` e `desliga`; log do Pedro (`fatia8-pedro-apaga.log`) | os resultados de "Resultados da fatia 8"; logs no scratchpad da sessão 9 |
| activity log do `rg-pathsol-v3` e do `rg-prod-brsouth-001` (sessão 9) | 3 exclusões negadas do Pedro (`Failed`) e 3 disparos às 14:14; start e deallocate da VM2 pela identidade da VM1, com o start `Succeeded` 0,16 s antes do deallocate |
| `Microsoft.AlertsManagement/alerts` (api 2019-05-05-preview, último dia) | disparos e resoluções da tabela "Resultados da fatia 8"; `pathsol-vm1-saude-v3` às 03:04 e 03:14 de 29/10 |
| activity log `ResourceHealth` da VM1 (29/10, 02:51) | primeiro evento `Active`, `Unavailable`, causa `Unknown`; 8 s depois, `UserInitiated` |
| `terraform plan -out=soft-delete.tfplan` e `-out=fim-do-dia.tfplan`; `show -json` | 1 a criar, 1 a alterar (`344897fb…aa74`); 1 a criar, 2 a alterar (`10b5ea9d…5c60`); 0 a destruir; na `pathsolwsiv3` só muda o `blob_properties` |
| Retail Prices API (BRL, brazilsouth, General Block Blob v2) | Hot ZRS Data Stored R$ 0,2127/GB/mês; Hot LRS R$ 0,1702 |
| `az account show` (sessão 10) | mesma subscrição, Enabled, login de usuário |
| `sha256sum fim-do-dia.tfplan`; `terraform plan -detailed-exitcode` (sessão 10) | `10b5ea9d…5c60`, igual ao do relatório; `No changes`, saída 0 |
| `az storage account blob-service-properties show` (4 contas) | `pathsolwsiv3`: soft delete de blob ligado, 14 dias, `allowPermanentDelete false`; versionamento, change feed e soft delete de container desligados. As outras 3 sem soft delete |
| `az monitor activity-log alert list`; activity log do `rg-pathsol-v3` (22 h) | `pathsol-blob-service-write-v3` e `pathsol-vm1-saude-v3` (só `PlatformInitiated`) como no plano; apply de 12:02:06 a 12:02:17, sem falha; o alerta novo disparou às 12:09:11 |
| `az network nic show`; `ip -4 addr`; `journalctl -b 0` (VM1) | `Static` 10.0.0.5; `eth0` com 10.0.0.5 pelo DHCP às 09:04:59 |
| GET do action group (api `2026-03-01-preview`) | receptor `Verified` |
| `az storage blob list` (`wsi-teste`) | `a` e `c` em `Cold` desde 30/10, 05:30:01 UTC; `lastModified` igual ao da criação |
| `journalctl --list-boots`; `journalctl -b -1` e `-b 0` (VM1) | boot −1 até 02:02:06; `database system is shut down` às 02:02:03,667, antes do `srv-banco.mount` e do docker; na partida, `was shut down at 2026-10-30 02:02:03 UTC`; backup diferencial e dump às 09:05:31 |
| `journalctl -t pathsol-banco` (desde 12:10, depois do apply do soft delete) | 7 itens `OK` às 12:15, 12:30 e 12:45, inclusive o `backup` lido pelo `pgbackrest info` |
| `Microsoft.AlertsManagement/alerts` (7 dias) | disco 80 e 90 resolvidos às 15:48 e 15:50, falha do banco às 15:59 de 29/10; `dlq-nao-vazia` disparado; `vm1-saude` às 02:19 e 02:24 de 30/10 |
| GET do orçamento e dos alertas de custo | R$ 2.863,13 gastos em outubro e previsão de R$ 3.117,28; só o aviso de 50% |
| `az role definition list --name "Storage Blob Data Owner"`; `az role assignment list --all` | `Microsoft.Storage/storageAccounts/blobServices/containers/*` nas ações de plano de controle; o papel só estava com o Pedro, no `wsi-teste` |
| activity log da limpeza (sessão 10) | `storageAccounts/delete` `Failed` 409 `AccountProtectedFromDeletion` às 12:24:04; `clearLegalHold/action` `Succeeded` às 12:29:30; `managementPolicies/delete` `Succeeded` às 12:44:49; `storageAccounts/delete` `Succeeded` às 12:47:11; disparos às 12:29:12, 12:34:10, 12:49:11 e 12:54:10 |
| `terraform plan -detailed-exitcode` depois do `clearLegalHold` | `No changes`, saída 0, sem nota de mudança fora do Terraform |
| `az storage account show`; `az role assignment list --all`; GET de uma atribuição (depois da exclusão) | `ResourceNotFound`; nenhuma atribuição com escopo na conta; 404 |
| `terraform fmt -check`; `validate`; `plan -out=limpeza.tfplan`; `show -json` (12:48) | formato ok; válido; 0 a criar, 0 a alterar, 1 a destruir; 64 `no-op` e 1 `delete` (plano substituído às 13:18) |
| `terraform providers schema -json` (azurerm 5.10.0) | `notification` do orçamento é um set, com `contact_emails`, `contact_groups` e `contact_roles` opcionais |
| GET dos alertas de custo (`Microsoft.CostManagement/alerts`, detalhes); GET do orçamento (api 2019-10-01) | aviso de 50% com 1 destinatário, igual ao do `terraform.tfvars`, e nenhum action group; eTag do orçamento `"1dd65b5ac099078"`, igual ao do plano |
| `terraform fmt -check`; `validate`; `plan -out=limpeza.tfplan`; `show -json` (13:18, refeito) | formato ok; válido; 0 a criar, 1 a alterar, 1 a destruir; 63 `no-op`, 1 `update` (orçamento: 5 notificações com o e-mail e o action group; valor, período e início iguais) e 1 `delete` |

## O que não foi possível verificar

- O e-mail do orçamento. O direto, do aviso de 50% de 27/10, não chegou (Pedro, 30/10). O caminho pelo action group só se prova no primeiro aviso depois do apply do `limpeza.tfplan`. Não foi verificado se a gravação do orçamento faz os avisos de outubro já disparados saírem de novo.
- Se o e-mail de teste do action group chegou: o Azure registra o envio com `Succeeded`, e o Pedro não o identificou com certeza.
- Se a VM2 chegou a desligar o SO no deallocate que o start interrompeu (15:01): a próxima partida dela mostra os boots (`journalctl --list-boots`).
- Se a VM1 usa o cache de host: o `az vm list-skus` não traz `CachedDiskBytes` para a D8s_v5, mas o P20 aceitou ReadWrite.
- Se um prefixo igual ao nome do container (`wsi-diagnose`) também pega um container de nome mais longo (`wsi-diagnose2`). A doc não diz. Aqui não faz diferença, porque todo container `wsi-*` é de WSI.
- Quem mudou a camada dos blobs de teste para Cold. Só há o horário (05:30:01 UTC, os dois no mesmo segundo, com a VM1 desalocada), porque o plano de dados não vai ao activity log. O conteúdo foi comparado pelo `lastModified` e pelo ETag: o sha256 da sessão 9 ficou no `/tmp`, que a partida da VM1 limpou.
- A resolução do alerta `pathsol-dlq-nao-vazia-v3`, que depende de a mensagem de teste expirar (31/10, 02:02 UTC, depois do fim da sessão 10).
- Se o `pathsol-vm1-saude-v3`, só com `PlatformInitiated`, fica quieto na desalocação. A prova é o auto-shutdown de 30/10 (31/10, 02:00 UTC), conferido na próxima sessão. O disparo real dele depende de um evento da plataforma, que não dá para provocar.
- O `pathsol-lock-delete-v3` e o `pathsol-vm2-ligada-v3` nunca dispararam (decisão 3).
- O pgBackRest diante de uma cópia em soft delete. Desde o apply, o `pgbackrest info` lê o repositório sem erro, mas a primeira regravação do `backup.info`, que cria a primeira cópia em soft delete, só acontece no próximo backup.
- Se a regra `AgentSettings` limita mesmo o cache do agente no Linux (recurso que aparece como preview).
- A renovação do certificado novo, de verdade ou por `certbot renew --dry-run`: o dry-run usa a conta de staging, que o CAA atual não permite.
- O conteúdo do `status.json` gravado no desligamento real: o journal mostra o HTTP 201, mas o `up` da partida sobrescreve o arquivo. O `back_at` fica coberto pelos testes da unit.
- O arquivamento assíncrono com `--init` diante de uma falha real de rede: a árvore de processos mostra o órfão com o `docker-init`, mas a falha não foi provocada.
- O teto de 8 GiB da fila de WAL atingido de verdade.
- A ordenação em português com o provedor builtin; fica para a Fase 5, com colação ICU onde precisar.
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
- **Backups apagáveis de dentro da VM1.** A identidade do sistema da VM1 tem o papel de backup, que apaga blobs no `backup-banco`, porque o expire do pgBackRest precisa disso. Qualquer processo da VM1 obtém o token pelo IMDS; quem tomar a VM1 apaga o banco e os backups. Desde o apply de 30/10 (decisão do Pedro de 29/10), um backup apagado ou sobrescrito volta por 14 dias; o container em si não tem soft delete, mas a VM1 não tem `containers/delete`.
- **Orçamento sem e-mail comprovado.** Até o primeiro aviso chegar pelo action group, um gasto acima do teto pode passar sem e-mail; o alerta fica só no Cost Management, no Portal. O orçamento só avisa, com 1 a 3 dias de atraso, e não para recurso nenhum.
- **Mudança futura no orçamento pelo Terraform.** O azurerm reenvia o `time_period` inteiro em todo PUT, e a API pede o `start_date` dentro do mês corrente. A documentação não diz se a regra vale para um orçamento que já existe. Se valer, qualquer mudança no orçamento a partir de novembro é recusada no apply, e o caminho é recriá-lo com o início no mês corrente (o `start_date` força recriação), com plano aprovado.
- **Retenção legal tirada não aparece no Terraform.** Provado em 30/10: depois do `clearLegalHold`, o `terraform plan` segue sem mudanças e sem nota, porque o azapi não relê a retenção. A única detecção é o `pathsol-clear-legal-hold-v3`, que dispara em ~5 min. Quem recebe o e-mail confere no activity log quem tirou; pôr a retenção de volta pede um apply com `-replace` do `azapi_resource_action` daquele container, com plano aprovado.
- **Storage Blob Data Owner também tira a retenção legal.** O papel tem `Microsoft.Storage/storageAccounts/blobServices/containers/*` nas ações de plano de controle, o que inclui o `clearLegalHold` e a exclusão de container vazio, além de Owner, Contributor e Storage Account Contributor (seção 6.4 do plano). Nenhuma identidade da v3 pode recebê-lo num container de WSI. Hoje ninguém o tem: o do Pedro no `wsi-teste` saiu com a conta.
- **Tentativa negada de quem não tem permissão não aparece no activity log.** A tentativa da VM1 de apagar um container pela ARM (403) não gerou evento nem alerta; só aparece a tentativa de quem tem a permissão e é barrado depois (trava ou retenção). No plano de dados, nada vai para o activity log. Ver tentativas negadas exigiria logs de recurso do storage, com custo; registrado no `docs/v3/roadmap.md`.
- **Alerta de saúde da VM1 só com causa da plataforma.** Com a causa `Unknown`, o `pathsol-vm1-saude-v3` disparava em toda desalocação (29 e 30/10). Desde o apply de 30/10, só `PlatformInitiated` dispara. Uma falha real que chegue primeiro com causa `Unknown`, como a desalocação de 29/10 chegou, também fica sem esse e-mail; o `pathsol-vm1-silencio-v3` (sev. 1, 10 min sem heartbeat) cobre a VM1 fora do ar no horário dela.
- **Certificado TLS do banco vence em 28/10/2028.** A verificação avisa 21 dias antes; a troca exige atualizar o certificado fixado no worker.
- **Imagem do banco congelada.** O 18.7 sai em 12/11/2026; atualizar é refazer o build com o digest novo e rodar o teste de restauração.
- **Partida da VM1 pelo runbook.** Provada em 29/10. Se um dia falhar, a VM1 fica desalocada até alguém ligá-la; o alerta `pathsol-vm1-silencio-v3` avisa a partir das 06:20, e a volta é ligar pelo Portal.

## Decisões pedidas ao Pedro

**Para o gate (sessão 10, 30/10):**
1. **Aprovação da Fase 3:** "APROVADO FASE 3", ou o que falta.
2. **Fatia 0, exportação de teste do Motic:** passa para a Fase 4, junto do leitor e da desidentificação (fatias 6 e 10 da Fase 4 na seção 19.2), ou fica como pendência da Fase 3 até a exportação chegar.
3. **`pathsol-lock-delete-v3` e `pathsol-vm2-ligada-v3`:** testar de verdade antes do go-live, com os alarmes da Fase 8 (o da VM2 custa ~R$ 19 por teste; o da trava pede uma trava criada e apagada por Terraform só para isso), ou aceitar como estão: o caminho até o e-mail é o mesmo das regras que já dispararam.
4. **Ruído do TLS no log do Postgres:** corrigir quando o `pathsol_banco.py` for mexido na Fase 4 (fechar o TLS com `unwrap()` antes de sair, com teste e autorização para reinstalar o script), ou deixar como está.

**Já respondidas:**

Respondidas em 28/10, ~23:00 UTC: o Pedro aprovou o apply do `fatias6-7.tfplan` e pediu por escrito a regra `backup-dump-35d`; o padrão 27 usa PowerShell 7.6; a extensão `log-analytics` saiu e o `az` não instala mais extensões sozinho (`extension.use_dynamic_install=no`).

Respondidas na sessão 7 (29/10): runbook novo em vez de trocar o tipo do `TurnOn-VMs`; seguir no 7.6 com o build preview; teto de 1G no journal da VM2, apagando os arquivos mais antigos; chaves de host da VM2 pelo Run Command, e a edição do alias pelo próprio Pedro.

Respondida na sessão 8 (29/10): o runbook `TurnOn-VMs` antigo foi apagado com autorização na hora, depois de o runbook novo ligar a VM1 desalocada no ciclo real.

Respondida na sessão 8 (29/10, ~12:30 UTC): o Pedro aprovou o `fatias7-8.tfplan` (sha256 `e2920e2e…6b892`) com o escopo e o papel de cada atribuição, e o aplica em seguida pelo SSH, com o Antigravity fechado. A próxima sessão começa pela conferência do apply (sha256, `terraform plan` sem mudanças, os 10 recursos e o activity log) e pede, numa pergunta só, os testes da fatia 8 listados em "Plano das fatias 7 e 8".

Respondidas na sessão 9 (29/10, ~13:50 UTC): IPs privados estáticos, uma ação por autorização (VM2 feita; VM1 como última ação da sessão, depois do commit e do push e antes do apply); soft delete de blobs na `pathsolwsiv3` com 14 dias e sem exclusão permanente, aprovado no `soft-delete.tfplan`, com a linha nova do `CLAUDE.md` e da skill `pathsol-infra`; testes da fatia 8 como sequência, com tokens do IMDS das VMs só nos scripts e os passos que apagam pelo Pedro, com o comando exato.

Respondida na sessão 9 (~15:37 UTC): o Pedro aplica o `fim-do-dia.tfplan` (sha256 `10b5ea9da4febfae5c2ca99ce2c06018f1e4a75435dc9b2dd836c2d5f0775c60`) pelo SSH, com o Antigravity fechado, depois da última ação da sessão (o IP estático da VM1), e faz o `az logout` no fim. O `soft-delete.tfplan` fica velho e não é aplicado. Antes do commit, a VM2 estava desalocada (15:39 UTC).

Respondida na sessão 10 (30/10, ~12:15 UTC): a limpeza da conta descartável seguiu com os passos que apagam pelo Pedro, um comando por vez, mais o passo opcional da política de ciclo de vida, para o alerta que nunca tinha disparado.

Respondidas na sessão 10 (~13:00 UTC): os 5 e-mails dos alertas de 30/10 chegaram (12:09, 12:29, 12:34, 12:49 e 12:54 UTC); o Pedro aplica o plano da limpeza como última ação da sessão 10, pelo SSH, com o Antigravity fechado, e faz o `az logout` no fim (decisão 4).

Pedido do Pedro na sessão 10 (~13:05 UTC): o e-mail do orçamento de 26/10 não chegou, nem no spam. Refazer o plano da limpeza com as notificações do orçamento também no `pathsol-alertas-v3` e um aviso extra em 30% (R$ 1.500), que deve disparar todo mês como prova do caminho, e registrar o e-mail do orçamento como pendência do gate. Feito: `alertas.tf` e o `limpeza.tfplan` refeito (sha256 `485598005f225370e91ece93259dc17d236226746c55ca113ca3a9c05d1f646b`), que é o que o Pedro aplica. A conferência do apply abre a próxima sessão.

PARADO — aguardando APROVADO FASE 3
