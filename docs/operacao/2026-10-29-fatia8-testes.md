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
