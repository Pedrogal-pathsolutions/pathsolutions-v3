# Operações no legado feitas pelo Portal (14 e 15/10/2026)

O Pedro pediu este registro em 15/10, ao responder à decisão 11 do relatório da Fase 0.

A fonte é o activity log da subscrição (`az monitor activity-log list`), lido pela sessão da Fase 0. O e-mail do chamador não foi impresso; para comparar os chamadores, a sessão usou o hash SHA-256 do campo `caller`.

| UTC | Recurso | Operação | Cliente | Efeito |
|---|---|---|---|---|
| 2026-10-14 22:46:23 | `shutdown-computevm-vm-appviewer-prod-001` | `Microsoft.DevTestLab/schedules/write` | Azure Portal | auto-shutdown da VM1 desativado (era 20:00, E. South America Standard Time) |
| 2026-10-15 02:34:38 | `shutdown-computevm-vm-appviewer-prod-001` | `Microsoft.DevTestLab/schedules/write` | Azure Portal | auto-shutdown da VM1 reativado: Enabled, 20:00 |
| 2026-10-15 02:34:49 → 02:35:51 | `vm-appviewer-prod-001` | `Microsoft.Compute/virtualMachines/deallocate/action` | Azure Portal | VM1 desalocada; voltou às 09:02 UTC pelo runbook `TurnOn-VMs` |

## Autoria

- **As três operações foram do Pedro.** Ele confirmou por escrito em 15/10/2026.
- No activity log, as três têm o mesmo chamador, que é a conta de usuário logada no `az` da VM1: os hashes do `caller` e do `user.name` do `az account show` são iguais.

## Estado depois das operações

- Em 15/10 por volta das 13:30 UTC (`az resource show` do agendamento), o auto-shutdown da VM1 estava Enabled, às 20:00. Sessões abertas na VM1 caem nesse horário.
- O Pedro decidiu em 15/10 que ele continua ativo (resposta 1 à seção 16 do relatório da Fase 0).
