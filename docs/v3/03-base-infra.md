# Fase 3 — Base de infraestrutura (relatório parcial)

Em andamento. Começou em 27/10/2026 (UTC), depois do APROVADO FASE 2. Este relatório é atualizado a cada sessão e cresce por fatia, na ordem da seção 19.2 do plano (`docs/v3/02-plano-v3.md`). A sessão seguinte começa por aqui e pelo `git log`.

## Situação por fatia

| Fatia | Situação |
|---|---|
| 0. Exportação de teste do Motic | não chegou; nada a fazer até ela chegar |
| 1. Decisão 4 antes do primeiro apply | feita: codex desinstalado e apply do Pedro pelo SSH, com o Antigravity fechado; falta o `az logout` no fim do dia |
| 2. Terraform e estado remoto | feita: bootstrap aplicado e estado migrado para `pathsoltfstatev3` |
| 3. Orçamento e action group | plano salvo, aguardando o apply do Pedro |
| 4 a 8 | não começadas |

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

## O que não foi possível verificar

- Se o orçamento aceita ser criado nesta subscrição CSP (o plano diz que nunca foi testado) e se o e-mail dele chega.
- O `Content-MD5` gravado no blob do estado não bate com o MD5 da cópia local. A explicação provável é a gravação do serial 7, mas não foi conferida byte a byte: o `az storage blob download` para `/dev/stdout` devolveu 0 bytes.

## Riscos

- **Login do `az` ativo o tempo todo na VM1.** Hoje o login do Pedro, com Owner, fica aberto entre as sessões. A decisão 4 limita o login ao plan e ao apply, com `az logout` no fim. Depois do primeiro dia de Terraform, cada sessão que precisar do `az` depende de o Pedro entrar de novo.
- **Auto-shutdown e decisão 3.** Mudar o da VM1 para 23:00 durante uma sessão noturna derruba a sessão às 23:00 do mesmo dia: hoje a VM1 já passou das 20:00 e só desliga às 20:00 de amanhã. A mudança fica para a fatia 6, num horário de dia.

## Decisões pedidas ao Pedro

Nenhuma até aqui.
