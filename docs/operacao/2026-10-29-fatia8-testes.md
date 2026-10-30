# Fase 3, fatia 8: testes — registro de ações

A fatia segue a seção 19.2 do plano (`docs/v3/02-plano-v3.md`) e a lista "Depois do apply" do plano das fatias 7 e 8 (`docs/v3/03-base-infra.md`). Cada entrada traz o horário em UTC, o comando ou a ação e a saída resumida. Nenhum dado de paciente entra aqui: os blobs de teste têm nome por UUID e conteúdo aleatório.

## Conferência do apply do `fatias7-8.tfplan` (sessão 9, 29/10)

O Pedro aplicou o plano pelo SSH às 13:00 UTC (10 criados, 0 alterados, 0 destruídos, nas palavras dele).

- `sha256sum fatias7-8.tfplan`: `e2920e2ed54b54168817440c1c29264298539427a49c36984e0f8414642b6892`, igual ao do relatório.
- `terraform plan -detailed-exitcode` (13:07 UTC): `No changes`, saída 0. O estado tem os 10 recursos novos.
- `pathsoltestev3`: StorageV2, Standard_LRS, Hot, TLS1_2, `allowSharedKeyAccess false`, `defaultToOAuthAuthentication true`, `allowBlobPublicAccess false`, rede pública como a `pathsolwsiv3`, tag `componente=teste`, criada às 13:00:14; soft delete de blob desligado, soft delete de container e versionamento nulos.
- `wsi-teste` (GET, api 2025-06-01): `publicAccess None`, `hasLegalHold true`, tag `teste` gravada pelo usuário do Pedro às 13:00:56, `allowProtectedAppendWritesAll false`, sem política por tempo.
- Política de ciclo de vida da conta descartável, gravada às 13:00:55: só a regra `teste-cold`, Cold com `daysAfterCreationGreaterThan 0`, prefixo `wsi-teste`, só `blockBlob`.
- Atribuições: VM1 (`e2d9ec13-…`) com `pathsol-blob-sem-exclusao-v3` no `wsi-teste` e `Storage Blob Delegator` na conta; VM2 (`1f02fe65-…`, a `pathsol-id-vm2-v3`) com `Storage Blob Data Reader` no `wsi-teste`; o usuário do Pedro (`d59e9d98-…`) com `Storage Blob Data Owner` no `wsi-teste`. Nenhuma outra na conta.
- `pathsol-banco-falha-v3` (sev. 1, a cada 15 min, janela de 30 min, `Total` de `Falhas` > 0) e `pathsol-banco-silencio-v3` (sev. 2, a cada 15 min, janela de 45 min, contagem > 0), ligados, com estado, no workspace `pathsol-logs-v3` e no action group; consultas iguais às do código.
- Trava `nao-apagar` (CanNotDelete) ainda nas duas contas protegidas.
- Activity log do `rg-pathsol-v3` desde 12:50 UTC: 41 eventos de 13:00:13 a 13:04:11, nenhum com falha, todos do usuário do Pedro ou da plataforma. Dispararam os 6 alertas previstos às 13:04:11: `pathsol-role-assignment-v3` (4), `pathsol-storage-write-v3` (1) e `pathsol-lifecycle-write-v3` (1).

## Alertas que não chegam (sessão 9, 29/10, ~13:40 UTC)

O Pedro avisou que nenhum alerta está chegando e pediu a conferência do e-mail. Só leitura:
- Action group `pathsol-alertas-v3`: ligado, um receptor de e-mail (`pedro`), com o endereço igual, caractere a caractere, ao que o Pedro informou; `status Enabled`. Os 4 avisos do orçamento têm o mesmo endereço.
- **Causa provável:** com a API `2026-03-01-preview`, o receptor aparece com `verificationStatus: VerificationPending`; as APIs `2025-09-01-preview` e `2023-01-01` (a do `az` e a das sessões anteriores) não mostram esse campo. A página de action groups (learn.microsoft.com, atualizada em 29/07/2026) diz: "Email addresses must be verified through a one-time passcode (OTP) within 30 minutes of saving the action group. [...] If the passcode expires, open the action group and select Resend. An unverified receiver can't receive alert or test notifications after enforcement is active." O plano previa a confirmação por código (seção 9.4); ela não foi feita nem conferida na sessão 1.
- Disparos que não viraram e-mail, pelo activity log (`ActivityLogAlerts/Activated`, todos com "called on action groups : pathsol-alertas-v3"): 11 às 01:29 UTC e 6 às 13:04 UTC de 29/10. Os 3 de 27/10, 11:54 UTC, chegaram (resposta do Pedro na sessão 5); quando a exigência passou a valer não foi verificado.
- O orçamento manda e-mail direto, sem o action group. O aviso de 50% consta como disparado em 27/10, 02:10:35 UTC (Cost Management, `alerts`, gasto de R$ 2.571,56). Se esse e-mail chegou não foi verificado.
- O MX de `pathsolutions.com.br` é `smtp.google.com`. Remetentes dos action groups pela mesma página: `azure-noreply@microsoft.com`, `azureemail-noreply@microsoft.com` e `alerts-noreply@mail.windowsazure.com`.

## Respostas do Pedro (~13:50 UTC)

Numa pergunta só: confirmou o e-mail pelo código no Portal e autorizou um e-mail de teste; autorizou a sequência de testes da fatia 8, parando em qualquer divergência, com tokens do IMDS da VM1 e da VM2 só nos scripts (`fatia8_vm1.py`, `fatia8_vm2.py` e `fatia8_energia.py`, no scratchpad da sessão), e os passos que apagam pelas mãos dele, com o comando exato; autorizou o IP estático da VM2; aprovou o `soft-delete.tfplan`, para aplicar no fim do dia.

## E-mail dos alertas (13:49–13:57 UTC)

- O Pedro gravou o action group pelo Portal às 13:49:12, 13:49:13 e 13:51:56. Um teste pelo Portal às 13:50:01 falhou com `There are no valid receivers in the request`, antes da confirmação.
- 13:53:13: `verificationStatus: Verified`. O Portal trocou o nome do receptor de `pedro` para `Reynaldo_-EmailAction-`; o `alertas.tf` passou a usar esse nome, para o próximo apply não gravar de novo no action group. O `terraform plan` seguinte mostra só as 2 mudanças do `soft-delete.tfplan` (sha256 igual). As outras diferenças lidas no refresh (`custom_properties` nulo contra vazio nos 2 alertas do banco e `has_legal_hold` do `wsi-teste`) não geram mudança.
- 13:53:50: `az monitor action-group test-notifications create ... --alert-type activitylog` (autorizado): `state Complete`, e-mail `SendTime 13:53:51,99`, `Status Succeeded`.

## IP estático da VM2 (autorizado; 13:56 UTC)

- Antes: VM2 `PowerState/deallocated`; NIC `vm-appfoundation-prod-001661`, `ipconfig1`, 10.0.0.4, `Dynamic`; sem ASG, pool de balanceador ou NAT.
- 13:56:29: `az network nic ip-config update -g rg-prod-brsouth-001 --nic-name vm-appfoundation-prod-001661 -n ipconfig1 --private-ip-address 10.0.0.4`. rc=0 às 13:56:32: `Static`, 10.0.0.4, `Succeeded`.
- Diferença do JSON do NIC antes e depois: só o `etag` e o `privateIPAllocationMethod`; NSG, IP público, accelerated networking e MAC iguais.
- Partida seguinte (14:01): `eth0` com 10.0.0.4 pelo DHCP do Azure (168.63.129.16), o mesmo MAC e o SSH pelo alias.

## Testes (sessão 9)

1. 13:57:07, VM1, `fatia8_vm1.py cria` (identidade da VM1, conta descartável):
   - Chave de delegação com `x-ms-version 2026-04-06`: 200, `skv 2026-04-06`.
   - Envio do blob `a` com SAS `c` (`sv` e requisição 2026-04-06): 1º Put Block 201; 2º Put Block, com o blob ainda não confirmado, 201; Put Block List com `If-None-Match: *` 201.
   - Sobrescrita do `a` com `c`: com a requisição em 2026-04-06 (qualquer `sv`), Put Block e Put Block List dão 403 `UnauthorizedBlobOverwrite`; com a requisição em 2026-02-06, 403 `AuthorizationPermissionMismatch`. Com `If-None-Match` e por Put Blob, 403 `UnauthorizedBlobOverwrite`.
   - O mesmo envio nas outras versões: `sv` 2026-02-06 com requisição 2026-04-06 cria (blob `c`); requisição 2026-02-06 dá 403 `AuthorizationPermissionMismatch` no 1º Put Block, com qualquer `sv`. Quem decide é o `x-ms-version` da requisição, como dizem as páginas do Put Block e do Put Block List; a página de versões diz que ele é ignorado em pedidos com SAS, o que não vale aqui.
   - Token da VM1 (papel que grava) no blob existente: Put Block, Put Block List, Put Blob e Set Blob Metadata dão 409 `BlobImmutableDueToLegalHold`.
   - Leitura no fim: `a` e `c` com sha256 e ETag iguais aos da criação, camada Hot. Nenhuma sobrescrita passou.
2. 13:59:47: `systemctl stop pathsol-banco-verifica.timer`, para o alerta de silêncio; a última linha do `pathsol-banco` é das 13:45:00.
3. 14:00:02, `fatia8_energia.py liga` (identidade da VM1, papel `pathsol-vm2-energia-v3`): POST `start` 202 com `Azure-AsyncOperation`, `Location` e `Retry-After 10`; o GET no `Azure-AsyncOperation` deu 200 (`InProgress` e, às 14:01:47, `Succeeded`), e o GET final no `Location`, 200. O papel restrito leu o status, ao contrário do que diz a página de operações assíncronas da ARM. VM2 `running` às 14:01:48.
4. 14:02:46, VM2, `fatia8_vm2.py teste` (identidade da VM2): leitura 200, sha256 igual; Put Block, Put Block List e Put Blob novo 403 `AuthorizationPermissionMismatch`; PutMessage na `jobs-dead-letter` 201 às 14:02:47, com expiração em 31/10, 02:02:47 UTC (TTL de 36 h).
5. 14:03:11, VM2: `fallocate -l 152G /mnt/teste-fatia8-disco.bin` no disco temporário (ext4): `/mnt` em 93,045% (`df` 94%).
6. Passos que apagam, pelo Pedro, no terminal SSH dele (log `fatia8-pedro-apaga.log` no scratchpad), depois de conferidas a trava `nao-apagar` e a retenção legal dos três containers (13:59). Todos com o resultado esperado:
   - 14:08:57, identidade da VM1 (`fatia8_vm1.py apaga`): Delete Blob com o token 403 `AuthorizationPermissionMismatch`; Delete Blob com SAS `d` da VM1 403 `AuthorizationPermissionMismatch` (a SAS não passa do papel de quem pediu a chave); Delete Container pelos dados 403; Delete Container pela ARM 403. A permissão é conferida antes da retenção legal: 403, e não 409.
   - 14:09:09, identidade da VM2 (`fatia8_vm2.py apaga`): Delete Blob e Delete Container 403 `AuthorizationPermissionMismatch`.
   - Leituras depois de cada bloco: sha256 e ETag iguais nos blobs `a` e `c`.
   - 14:09:31, login do Pedro (Storage Blob Data Owner no `wsi-teste`), `az storage blob delete`: `BlobImmutableDueToLegalHold`. 14:09:47, `az storage container delete`: `ContainerHasLegalHold`.
   - 14:09:56, ARM, `az storage container-rm delete` do `wsi-teste`: `ContainerProtectedFromDeletion` ("protected from deletion due to LegalHold").
   - 14:10:04, ARM, `wsi-publico` da `pathsolwsiv3`: `ScopeLocked`. 14:10:25, `az storage account delete` da `pathsolwsiv3`: `ScopeLocked`.
   - Activity log: as 3 tentativas do Pedro pela ARM aparecem como `Failed`, e os alertas `pathsol-container-delete-v3` (2) e `pathsol-storage-delete-v3` (1) dispararam às 14:14:11–14:14:14; os 3 e-mails chegaram. A tentativa da VM1 pela ARM (403) não aparece no activity log e não dispara alerta: só se vê a tentativa de quem tem a permissão e é barrado depois.
7. E-mails que o Pedro recebeu (resposta das ~14:45): dead-letter, disco 80% e 90%, as 3 exclusões negadas e o silêncio do banco (`pathsol-banco-silencio-v3`). O e-mail de teste do action group ele não identificou com certeza.
8. 14:50:36: linha sintética `FALHA teste-fatia8` no syslog `local0` com a etiqueta `pathsol-banco`, prioridade `err`; em seguida `systemctl start pathsol-banco-verifica.timer`. O timer rodou a verificação na hora (7 itens `OK` às 14:50:36); a próxima é às 15:00.
9. 14:51:18, `% Used Space` contra `df` na VM2, com o `/mnt` cheio: agente às 14:52 `/` 70,737241, `/boot` 19,31507, `/data` 0,000501, `/mnt` 93,044996; `df` usado ÷ (usado + livre) 70,7372, 19,3151, 0,0005 e 93,0450 (o `df` mostra 71%, 20%, 1% e 94%). No `/mnt`, usado ÷ tamanho daria 88,28: o agente desconta os blocos reservados, como o `df`. Na VM1 (13:24 contra 13:26): `/boot` 19,314116 contra 19,3141, `/data` 0,499025 contra 0,4990, `/srv/banco` 2,134435 contra 2,1344. O alerta usa o valor sem arredondar: até 1 ponto abaixo do que o `df` mostra.
10. 14:54:47, Pedro: `ssh azure-foundation 'sudo rm -v /mnt/teste-fatia8-disco.bin && df -h /mnt'`. `/mnt` em 0,0000% no `df`; no `Perf`, 1,9e-05 desde a amostra das 14:56.
11. 15:00:51, `fatia8_energia.py desliga` (identidade da VM1): deallocate 202 às 15:00:52; `deallocating` às 15:00:54; start 202 às 15:00:55. Activity log: start `Succeeded` às 15:01:28,96 e deallocate `Succeeded` às 15:01:29,12; a VM2 ficou `running` (15:01:33). O script desalocou de novo: `Succeeded` às 15:01:51, `deallocated` às 15:01:55. O start pedido durante o Deallocating é aceito e vence; o `Succeeded` do deallocate não prova VM desalocada. Se o SO da VM2 chegou a desligar nesse meio tempo não foi verificado (próxima partida: `journalctl --list-boots`).
12. Histórico de alertas (`Microsoft.AlertsManagement/alerts`, api 2019-05-05-preview, leitura às 15:28 UTC): `pathsol-dlq-mensagem-nova-v3` disparado às 14:07:28 e resolvido às 14:32:33; `pathsol-disco-80-v3` às 14:17:01 e `pathsol-disco-90-v3` às 14:19:08; `pathsol-banco-silencio-v3` às 14:39:13, resolvido às 15:25:13; `pathsol-banco-falha-v3` às 14:58:32; `pathsol-dlq-nao-vazia-v3` às 15:24:17 (1 h 21 min depois do PutMessage); `pathsol-vm1-silencio-v3` em 29/10, 01:34:37, resolvido às 02:20:38 (antes do agente entrar na VM1); 20 disparos de activity log de 27 e 29/10, mais os 3 das 14:14.
13. Achado: `pathsol-vm1-saude-v3` disparou às 03:04:10 e 03:14:11 de 29/10, depois da desalocação da VM1 pelo Portal às 02:51:14. O activity log `ResourceHealth` mostra o primeiro evento `Active`, `Unavailable`, causa `Unknown`, e só 8 s depois `UserInitiated` ("Stopping and deallocating"). Com a causa `Unknown` no filtro, o alerta dispara em toda desalocação, inclusive no auto-shutdown. Correção no `alertas-vms.tf` (só `PlatformInitiated`) e no plano alternativo `fim-do-dia.tfplan` (sha256 `10b5ea9da4febfae5c2ca99ce2c06018f1e4a75435dc9b2dd836c2d5f0775c60`).

Ficam para as próximas sessões: a camada Cold dos blobs `a` e `c` pelo ciclo de vida (conferir em 30/10); a parada limpa do Postgres no auto-shutdown das 23:00 de 29/10 (no log da partida de 30/10); a resolução do `pathsol-dlq-nao-vazia-v3` depois da expiração da mensagem (31/10, 02:02 UTC); a resolução dos alertas de disco e de falha do banco; e a limpeza da conta descartável, pelo Pedro: tentar apagar a conta com a retenção (esperado `AccountProtectedFromDeletion`), tirar a retenção (dispara o `clearLegalHold`), apagar a conta e tirar o `teste-protecao.tf` do código.

## Fechamento da sessão 9 (~15:40 UTC)

Resposta do Pedro: aplicar o `fim-do-dia.tfplan` (sha256 `10b5ea9da4febfae5c2ca99ce2c06018f1e4a75435dc9b2dd836c2d5f0775c60`); antes do commit, confirmar a VM2 desalocada; o IP da VM1 como última ação; e os comandos do apply com o sha256 completo. 15:39:02: VM2 `PowerState/deallocated`, `ProvisioningState/succeeded`.

## IP estático da VM1 (autorizado como última ação da sessão 9; 15:40 UTC)

Feito depois do commit `37e52c5`, do push e da conferência por hash (local igual ao remoto). Este registro fica sem commit até a sessão seguinte.
- Antes: NIC `vm-appviewer-prod-00141`, `ipconfig1`, 10.0.0.5, `Dynamic`; sem ASG, pool ou NAT; VF `enP34919s1` (accelerated networking).
- 15:40:08: `az network nic ip-config update -g rg-prod-brsouth-001 --nic-name vm-appviewer-prod-00141 -n ipconfig1 --private-ip-address 10.0.0.5`. rc=0 às 15:40:16: `Static`, 10.0.0.5, `Succeeded`.
- Durante: laço de conexão TCP a `management.azure.com:443` a cada 1 s, de 15:40:03 a 15:42:03: 120 de 120 sem falha. `journalctl -k` desde 15:40:03: nenhuma linha (sem troca de VF).
- Diferença do JSON do NIC: `etag`, `privateIPAllocationMethod` (`Dynamic` para `Static`) e a caixa do nome do grupo na referência da VM; NSG, IP público, accelerated networking e MAC iguais.
- Depois (16:02): `eth0` 10.0.0.5/24, rota padrão pelo DHCP; o Postgres escuta em 127.0.0.1 e 10.0.0.5; `pathsol-banco`, `docker` e `nginx` ativos; verificação do banco com os 7 itens `OK`; `https://app.pathsolutions.com.br/` responde 503 (a resposta do nginx novo), em 0,08 s; a VM1 está ligada desde 09:01:41, sem reinício.
- Activity log: `networkInterfaces/write` do NIC da VM1 `Started` 15:40:09,61, `Accepted` 15:40:09,80 e `Succeeded` 15:40:19,10.
- Partida seguinte (sessão 10, 30/10): `eth0` com 10.0.0.5/24 pelo DHCP do Azure (168.63.129.16) às 09:04:59 UTC; o NIC continua `Static`, 10.0.0.5, com accelerated networking; o Postgres voltou a escutar em 127.0.0.1 e 10.0.0.5.

## Sessão 10 (30/10, a partir das 12:04 UTC)

O Pedro aplicou o `fim-do-dia.tfplan` (1 criado, 2 alterados, 0 destruídos, nas palavras dele) e seguiu no `az`.

### Conferência do apply do `fim-do-dia.tfplan`

- `az account show`: subscrição `bd87a1ca-…`, Enabled, login de usuário.
- `sha256sum fim-do-dia.tfplan`: `10b5ea9da4febfae5c2ca99ce2c06018f1e4a75435dc9b2dd836c2d5f0775c60`, igual ao do relatório.
- `terraform plan -detailed-exitcode` (12:06–12:08 UTC): `No changes`, saída 0.
- `pathsolwsiv3` (`blob-service-properties show`): `deleteRetentionPolicy` ligado, 14 dias, `allowPermanentDelete false`; versionamento, change feed e soft delete de container desligados, último acesso nulo, CORS vazio. As contas `pathsoldlqv3`, `pathsolstatusv3` e `pathsoltestev3` seguem sem soft delete.
- `pathsol-blob-service-write-v3`: `blobServices/write` no `rg-pathsol-v3`, `Succeeded` ou `Failed`, ligado, no `pathsol-alertas-v3`, com as 3 tags. `pathsol-vm1-saude-v3`: `ResourceHealth`, `Unavailable` ou `Degraded`, só a causa `PlatformInitiated`.
- Activity log do `rg-pathsol-v3` (22 h): o apply de 12:02:06 a 12:02:17 UTC, pelo usuário do Pedro (2 `activityLogAlerts/write`, 1 `blobServices/write` e 1 `listKeys`), nenhum com falha. As únicas falhas da janela são as 3 exclusões negadas da sessão 9.
- O alerta novo disparou às 12:09:11 UTC com o `blobServices/write` do próprio apply, 7 min depois, chamando o `pathsol-alertas-v3`. O receptor do action group segue `Verified` (API `2026-03-01-preview`).

### Camada Cold sob retenção legal

- `az storage blob list` no `wsi-teste` (login do Pedro, Storage Blob Data Owner no container), 12:12 UTC: os blobs `a` e `c` em `Cold`, com `blobTierChangeTime` de 30/10, 05:30:01 UTC, ~15,5 h depois da criação; `lastModified` igual ao da criação (29/10, 13:57:08 e 13:57:09); 8.192 bytes cada; ETags `0x8DF35C48610AB05` e `0x8DF35C4865A8041`.
- A camada mudou sob retenção legal sem nova gravação do conteúdo. Isso confirma a inferência da seção 6.3 do plano (decisão 1, opção B). O autor da mudança não aparece em log: o plano de dados não vai ao activity log, e a conta não tem logs de recurso. Às 05:30 UTC a VM1 estava desalocada, e os dois blobs mudaram no mesmo segundo: indício da execução do ciclo de vida, não prova.
- O sha256 e o ETag lidos na sessão 9 ficaram no `/tmp` dela, que a partida da VM1 limpou; a comparação é pelo `lastModified`.

### Parada limpa do Postgres no auto-shutdown de 29/10

- `journalctl --list-boots`: boot −1 de 29/10, 09:01:44, a 30/10, 02:02:06 UTC; boot 0 desde 30/10, 09:04:52 UTC.
- Boot −1: `hv_utils: Shutdown request received` 02:02:03,121; `Stopping pathsol-banco.service` ,240; `received fast shutdown request` ,298; `checkpoint starting: shutdown immediate` ,329; `database system is shut down` ,667; unit parada ,756. Só depois: `Unmounting srv-banco.mount` ,764, docker parando ,766 e `/srv/banco` desmontado ,789. A unit com `RequiresMountsFor=/srv/banco` e `After=docker.service` (achado da sessão 8) faz o Postgres parar antes do docker e do disco.
- Boot 0: `database system was shut down at 2026-10-30 02:02:03 UTC` e `ready to accept connections` às 09:05:24,614; nenhuma linha com `interrupted`, `recovery` ou `not properly shut down`. A rotina diária rodou na partida (`Persistent`): `OK backup: diff em 3 s` e `OK dump` às 09:05:31–32. A verificação tem os 7 itens `OK` desde a partida.
- Status: `down: HTTP 201` às 02:02:03,641 no desligamento e `up: HTTP 201` às 09:05:05 na partida.
- Achado menor: a cada 15 min, o Postgres grava `SSL error: unexpected eof while reading` e `could not receive data from client: Connection reset by peer` (nível `LOG`). Vem da conferência do certificado do banco (`postgres_cert`, `deploy/vm1/banco/pathsol_banco.py:296`), que fecha o TLS sem `close_notify`. Fica só no journal: o agente coleta o `local0`, e o Postgres escreve pelo docker.

### Alertas (`Microsoft.AlertsManagement/alerts`, 7 dias, leitura às ~12:10 UTC)

- Resolvidos: `pathsol-disco-80-v3` às 15:48:08 e `pathsol-disco-90-v3` às 15:50:14 de 29/10 (o `/mnt` foi esvaziado às 14:54, e a VM2, desalocada às 15:01); `pathsol-banco-falha-v3` às 15:59:33. Já registrados: `pathsol-dlq-mensagem-nova-v3` (14:32:33), `pathsol-banco-silencio-v3` (15:25:13) e `pathsol-vm1-silencio-v3` (29/10, 02:20:38).
- Ainda disparado: `pathsol-dlq-nao-vazia-v3`, desde 15:24:17 de 29/10. A mensagem de teste expira em 31/10, 02:02:47 UTC, depois do fim desta sessão; a resolução depende dessa expiração e da janela de 1 dia da regra.
- `pathsol-vm1-saude-v3` disparou às 02:19:10 e 02:24:10 UTC de 30/10, no auto-shutdown, antes do apply da correção (12:02). A prova da correção é o auto-shutdown seguinte (31/10, 02:00 UTC) sem disparo.
- Na partida de 30/10, nem o `pathsol-vm1-silencio-v3` nem o `pathsol-banco-silencio-v3` dispararam.
- Orçamento (GET, api 2023-11-01): gasto de outubro de R$ 2.863,13 e previsão de R$ 3.117,28 (preço de tabela), abaixo do aviso de 80%. Só o aviso de 50% disparou (27/10, 02:10:35 UTC).

### Limpeza da conta descartável (passos que apagam pelo Pedro, um comando por vez)

Estado de partida (12:15 UTC): `wsi-teste` com `hasLegalHold true` (tag `teste`, gravada pelo usuário do Pedro em 29/10, 13:00:56), sem política por tempo; os blobs `a` e `c` em Cold; 4 atribuições com escopo na conta (VM1 com o papel sem exclusão no container e o Storage Blob Delegator na conta; VM2 com o Storage Blob Data Reader e o Pedro com o Storage Blob Data Owner, os dois no container); nenhuma trava na conta (as 2 travas do grupo estão na `pathsolwsiv3` e na `pathsoltfstatev3`). Leitura da documentação oficial antes (workflow de 4 tópicos, sem comando no Azure): a conta com retenção legal num container com blobs não se apaga (Data protection overview, 02/10/2026), e o código listado para isso é `AccountProtectedFromDeletion` (409).

1. 12:24:04, Pedro: `az storage account delete -g rg-pathsol-v3 -n pathsoltestev3 --yes`. Activity log: `Failed`, `Conflict`, `{"code":"AccountProtectedFromDeletion","message":"pathsoltestev3 is protected from deletion.The container(s) wsi-teste have legal hold."}`. Conta e blobs intactos (mesmos ETags e `lastModified`). `pathsol-storage-delete-v3` disparou às 12:29:12.
2. 12:29:30, Pedro: `az storage container legal-hold clear -g rg-pathsol-v3 --account-name pathsoltestev3 --container-name wsi-teste --tags teste`. Activity log: `clearLegalHold/action` `Succeeded` às 12:29:30,709. GET do container: `hasLegalHold false`, tags vazia; blobs iguais. `pathsol-clear-legal-hold-v3` disparou às 12:34:10, o primeiro disparo dele.
   - `terraform plan -detailed-exitcode` às 12:30 UTC: `No changes`, saída 0, sem a nota de mudança fora do Terraform; o estado guarda `has_legal_hold = true` no container. O Terraform não vê uma retenção tirada, e só o alerta de activity log avisa (seção 6.3 do plano).
3. 12:44:49, Pedro (passo opcional, para o alerta que nunca tinha disparado): `az storage account management-policy delete -g rg-pathsol-v3 --account-name pathsoltestev3`. Activity log: `managementPolicies/delete` `Succeeded` às 12:44:49,878. Depois: `ManagementPolicyNotFound` na conta descartável; a política da `pathsolwsiv3` segue com as 3 regras e o `lastModifiedTime` de 29/10, 01:23:30. `pathsol-lifecycle-delete-v3` disparou às 12:49:11, o primeiro disparo dele.
4. 12:47:06, Pedro: `az storage account delete -g rg-pathsol-v3 -n pathsoltestev3 --yes`. Activity log: `storageAccounts/delete` `Succeeded` às 12:47:11,772; `pathsol-storage-delete-v3` disparou de novo às 12:54:10. Conferência às 12:47:24: `ResourceNotFound`; as contas `pathsoldlqv3`, `pathsolstatusv3`, `pathsoltfstatev3` e `pathsolwsiv3` em `Succeeded`, as 2 travas no lugar e 32 recursos de topo no grupo (eram 33). As 4 atribuições com escopo na conta saíram da listagem da subscrição (`az role assignment list --all`), e o GET direto de uma delas dá 404 `ResourceNotFound`: a ARM as tirou junto com a conta. A documentação não diz isso.

**Código e estado.** O `teste-protecao.tf` saiu do código (`git rm`). `terraform fmt -check` e `validate` ok; `terraform plan -out=limpeza.tfplan` às 12:48–12:50 UTC: **0 a criar, 0 a alterar, 1 a destruir.** No JSON do plano, 64 `no-op` e 1 `delete`: o `azapi_resource_action.teste_legal_hold` (`delete_because_no_resource_config`). Os outros 7 objetos (conta, container, política e as 4 atribuições) deram 404 no refresh e já não estão no estado refrescado, que tem 65 recursos gerenciados; depois do apply ficam 64. Com `when = "apply"`, o destroy do `azapi_resource_action` não chama o Azure, só tira o objeto do estado (código da tag v2.13.0 do azapi, `internal/services/azapi_resource_action_resource.go`, linhas 413–422; doc do registry: "no action will be performed on the Azure resource unless the `when` argument is set to `destroy`"). sha256: `435a7d7a7a95a9eda74e79f657ff7f1787c0683b98daea148e8ec4e583efbda5`.

### Respostas e pedido do Pedro (~13:00–13:05 UTC)

- Os 5 e-mails dos alertas de 30/10 chegaram (12:09, 12:29, 12:34, 12:49 e 12:54 UTC). O Pedro aplica o plano da limpeza hoje, como última ação da sessão, pelo SSH.
- Pedido: o e-mail do aviso de 50% do orçamento (27/10, 02:10 UTC; 26/10 no horário de Brasília) não chegou, nem no spam. Refazer o plano da limpeza com as notificações do orçamento também no `pathsol-alertas-v3` e um aviso extra em 30% (R$ 1.500), que deve disparar todo mês como prova do caminho; registrar o e-mail do orçamento como pendência do gate.
- `alertas.tf`: aviso `actual_30` e `contact_groups = [azurerm_monitor_action_group.alertas.id]` nas 5 notificações, mantido o e-mail direto. `terraform providers schema -json`: no azurerm 5.10.0, `notification` é um set, com `contact_groups` opcional.
- `terraform plan -out=limpeza.tfplan` refeito às 13:17–13:18 UTC: **0 a criar, 1 a alterar, 1 a destruir.** No JSON, 63 `no-op`, o `update` no lugar do `azurerm_consumption_budget_subscription.teto` e o `delete` do `azapi_resource_action.teste_legal_hold` (só no estado). Orçamento depois: R$ 5.000, mensal, de 01/10/2026 a 01/10/2036, com 30, 50, 80 e 100% do real e 100% do previsto, `GreaterThanOrEqualTo`, ligados, cada um com o e-mail e o action group. sha256: `485598005f225370e91ece93259dc17d236226746c55ca113ca3a9c05d1f646b`. O plano de 12:48 (`435a7d7a…efbda5`) foi substituído; uma versão intermediária, de 13:07 (`c2ea6323…0867`), também, depois de um ajuste só de comentário no `alertas.tf`, para o plano bater com o código do commit.
- Leitura de documentação em workflow (3 tópicos, só fontes oficiais, sem comando no Azure): action group em orçamento vale nos escopos de subscrição e de resource group, pelo ID completo, inclusive no Azure Plan via parceiro; a API Consumption 2019-10-01, que o azurerm 5.10.0 usa, aceita até 5 notificações; o orçamento é avaliado a cada 24 h, sobre dados com 8 a 24 h de atraso, e o aviso sai até 1 h depois; o `start_date` precisa estar no mês corrente, então o apply vai até 31/10, 21:00 de Brasília. Não documentado: se o aviso novo de 30%, já ultrapassado em outubro, dispara na avaliação seguinte, e se a gravação reenvia os avisos já disparados.
- 13:15 UTC, só leitura: o registro do aviso de 50% (`Microsoft.CostManagement/alerts`) tem 1 destinatário, igual ao do `terraform.tfvars`, e nenhum action group; o eTag do orçamento no Azure (`"1dd65b5ac099078"`) é igual ao do plano.

## Sessão 11 (30/10, a partir das ~14:09 UTC)

O Pedro aplicou o `limpeza.tfplan` (0 criados, 1 alterado, 1 destruído, nas palavras dele) e pediu a conferência. Na mesma mensagem, escreveu "APROVADO FASE 3", com a pendência do e-mail do orçamento (`docs/v3/03-base-infra.md`, "Depois da entrega"). Na abertura, o `az` estava com o login de usuário do Pedro; se ele entrou de novo depois do apply ou não chegou a sair não foi registrado.

### Conferência do apply do `limpeza.tfplan`

- `az account show`: subscrição `bd87a1ca-…`, Enabled, login de usuário.
- `sha256sum limpeza.tfplan`: `485598005f225370e91ece93259dc17d236226746c55ca113ca3a9c05d1f646b`, igual ao do relatório; o arquivo é o de 13:18:21 UTC.
- `terraform plan -detailed-exitcode` (14:10:27–14:11:14 UTC): `No changes`, saída 0, sem nota de mudança fora do Terraform.
- `terraform state list`: 64 recursos gerenciados e 11 `data`, nenhum objeto da conta descartável. O `azapi_resource_action.teste_legal_hold` saiu do estado.
- Orçamento `pathsol-orcamento-v3` (GET, api 2019-10-01, 14:13 UTC): R$ 5.000, mensal, de 01/10/2026 a 01/10/2036; eTag `"1dd6877debc32b8"` (no plano, `"1dd65b5ac099078"`). As 5 notificações (30, 50, 80 e 100% do real e 100% do previsto) estão ligadas, com `GreaterThanOrEqualTo`, cada uma com 1 e-mail, igual ao do `terraform.tfvars` (comparado sem imprimir), e o `pathsol-alertas-v3` em `contactGroups`. Gasto de outubro: R$ 2.863,13; previsão: R$ 3.086,16 (preço de tabela).
- Activity log da subscrição de 13:18 a 14:15 UTC: 22 eventos, todos do usuário do Pedro, nenhum com falha. O apply é um único `Microsoft.Consumption/budgets/write`, `Started` às 14:06:28,247 e `Succeeded` às 14:06:35,670. O destroy do `azapi_resource_action` não gerou evento, como previsto: só tirou o objeto do estado. Os outros 20 eventos são os `listKeys` e `sharedKeys` dos dois `terraform plan` (13:18 e 14:10).
- Alertas (`Microsoft.AlertsManagement/alerts`, 24 h, leitura às 14:17 UTC): nenhum disparo depois das 13:04:10. Nenhuma regra cobre o `budgets/write`: as regras por operação estão em `alertas.tf:57-101`, e o único recurso `Microsoft.Consumption` no código é o próprio orçamento (`alertas.tf:23`).
- Receptor do action group (api `2026-03-01-preview`, 14:13 UTC): `Reynaldo_-EmailAction-`, `Enabled`, `Verified`.
- Alertas de custo (`Microsoft.CostManagement/alerts`, api 2023-11-01, 14:13 UTC): só o aviso de 50% de 27/10, com 1 destinatário e nenhum action group. O de 30% ainda não disparou.

### Aviso de 30% do orçamento e fim da pendência do gate

- Mensagem do Pedro, ~14:21 UTC: "O e-mail do orçamento chegou". Pedido seguinte: conferir no Azure qual aviso disparou e por qual caminho, e fechar a pendência do gate.
- Alertas de custo (GET, api 2023-11-01, 14:21 e 14:23 UTC): um registro novo, `6bf77b2f-…`, criado às 14:17:38,087 UTC, 11 min depois da gravação do orçamento. É o aviso de 30% do real: `CostThresholdExceeded`, `GreaterThanOrEqualTo`, gasto de R$ 2.873,04 contra R$ 5.000 (no GET das 14:13, R$ 2.863,13), `Active`, `source Preset`. Destinos no registro: 1 e-mail, igual ao do `terraform.tfvars` (comparado sem imprimir), e o `pathsol-alertas-v3` em `contactGroups`. O aviso de 50% não saiu de novo: segue só o registro de 27/10.
- Não verificado: o que provocou a avaliação das 14:17 (a gravação, dados de custo novos ou a avaliação periódica, de horário desconhecido). O registro traz só um `triggeredBy` opaco (`ffb2c47d-…_7_22`). Em 27/10, o aviso de 50% também saiu ~19 min depois da criação do orçamento (~01:51 UTC): dois casos são sinal, não prova.
- Nos três registros lidos, nada mostra por qual caminho o e-mail saiu nem se o action group foi chamado: o registro do alerta não tem campo de entrega; o activity log de 14:15 a 14:23 UTC não tem nenhum evento; e o `Microsoft.AlertsManagement/alerts` não tem alerta na última hora (14:21 UTC). Nos alertas de activity log, o evento `Alert` diz "called on action groups"; para o orçamento, nenhum evento assim apareceu. Se o Azure registra o caminho em outro lugar não foi verificado. Os dois caminhos vão para o mesmo endereço (`alertas.tf:10` e `:45`).
- Pergunta ao Pedro (~14:25 UTC): qual e-mail chegou, só o do action group, só o direto ou os dois. Resposta: "Só o direto", a opção descrita como um e-mail no modelo próprio do orçamento, diferente dos alertas do Azure Monitor que chegaram no dia. Com isso, ele fechou a pendência do gate por decisão dele; a condição da aprovação, a chegada pelo action group, ficou sem prova.
- Não verificado: como é o e-mail de um aviso de orçamento enviado pelo action group (sem isso, o caminho do e-mail que chegou vem só do modelo); por que chegou um só; se o outro ainda chega (pela documentação lida na sessão 10, o aviso sai até 1 h depois da avaliação); e por que o e-mail direto de 27/10 não chegou. O receptor do action group estava `Verified` às 14:13 UTC.

### Disparo a mais do `pathsol-storage-delete-v3`

A lista de alertas mostrou um terceiro disparo do `pathsol-storage-delete-v3` em 30/10, às 13:04:10, que a sessão 10 não registrou. No activity log de 12:40 a 13:15 UTC, a exclusão da `pathsoltestev3` tem dois eventos `storageAccounts/delete` `Succeeded`, às 12:47:11,772 e às 12:57:09,237, com o mesmo `correlationId` (`6da0cd7f…`) e sem outro `Started` entre eles. Cada evento disparou a regra (12:54:10 e 13:04:11), e os dois disparos chamaram o `pathsol-alertas-v3` ("called on action groups"): foi uma exclusão só. Se o disparo de 13:04 virou e-mail não foi verificado; o Pedro confirmou os de 12:09 a 12:54. Na mesma correlação aparecem 4 `roleAssignments/delete` `Succeeded` (12:47:11,350–,366): a ARM apagou as atribuições com escopo na conta dentro da própria exclusão.

### Papéis com efeito na conta de WSI (linha nova do `CLAUDE.md`)

- `az role assignment list --scope <id da pathsolwsiv3> --include-inherited` e `az role assignment list --all` filtrado pelos escopos dentro da conta (14:14 UTC): 9 atribuições com efeito na `pathsolwsiv3`.
- Na conta e nos containers, nenhuma é de Owner, Contributor, Storage Account Contributor ou Storage Blob Data Owner. São 6: VM1 (`e2d9ec13-…`) com o `pathsol-backup-banco-v3` no `backup-banco` e o Storage Queue Data Reader na fila `jobs`; VM2 (`1f02fe65-…`) com o Storage Blob Data Reader no `wsi-diagnose` e no `wsi-publico`, o `pathsol-blob-sem-exclusao-v3` no `slide-h5` e o `pathsol-fila-worker-v3` na fila `jobs`. Nenhum desses papéis tem `clearLegalHold` nem `containers/*`: no plano de controle, o de backup tem `containers/read` e `containers/write` (`papeis.tf:85-87`); o sem exclusão, `containers/read` e `generateUserDelegationKey` (`wsi.tf:146-149`); o Storage Blob Data Reader, as mesmas duas; o Storage Queue Data Reader, só `queues/read`; o da fila, só ações de dados (`papeis.tf:68-71`). Os papéis internos foram lidos com `az role definition list`.
- Herdadas da subscrição, sem condição: 3 de Owner. A do usuário do Pedro (`d59e9d98-…`, de 29/04/2026) e duas do mesmo ForeignGroup (`4e11fbdf-…`), iguais em tudo menos o ID, criadas com 0,16 s de diferença em 28/04/2026. A Fase 0 contou "2 ForeignGroups" (`docs/v3/00-ambiente.md:65`), e o plano, "dois grupos externos" (`docs/v3/02-plano-v3.md:333`); é um principal com duas atribuições. Na mesma leitura, o `principalName` das duas é `Foreign Principal for 'Quatto' in Role 'TenantAdmins' (PATHSOLUTIONS TECNOLOGIA EM SAUDE LTDA)`. Pelo nome, deve ser o acesso de administrador do parceiro CSP, mas é inferência, sem documentação lida. Não verificado: se a Quatto é o parceiro do contrato e quem está no grupo, o que resta da pendência da Fase 0 (`docs/v3/00-ambiente.md:592`).

### Fim da sessão

- `az logout` às 14:53 UTC (decisão 4); em seguida, `az account show` pede `az login`. A próxima sessão que precisar do `az` depende de o Pedro entrar de novo.
