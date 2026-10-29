# Fase 3, fatia 7: Postgres, backup e restauração — registro de ações

A fatia segue a seção 7 do plano (`docs/v3/02-plano-v3.md`): uma ação por autorização. Cada entrada traz o horário de início em UTC, o comando ou a ação e a saída resumida. Nenhum dado de paciente entra aqui.

## Apply (29/10)

O disco `pathsol-banco-v3`, o container `backup-banco`, o papel `pathsol-backup-banco-v3` com a atribuição da VM1 e a regra `backup-dump-35d` vieram no `fatias6-7.tfplan`, aplicado pelo Pedro às 01:23 UTC e conferido na sessão 7 (`docs/operacao/2026-10-28-fatia6-vms.md`).

## Disco do banco na VM1 (sessão 7)

Autorização do Pedro (~02:28 UTC, no chat): a sequência de 6 passos, parando em qualquer divergência. O Postgres fica para a próxima sessão.

1. 02:30:04 UTC, VM1 ligada: `az vm disk attach -g rg-prod-brsouth-001 --vm-name vm-appviewer-prod-001 --name <id do pathsol-banco-v3> --lun 2 --caching ReadOnly`.
   - Resultado: rc=0 às 02:30:10; `pathsol-banco-v3` na lun2 com `ReadOnly`, ao lado do `pathsol-dados-vm1-v3` na lun1; no convidado, `/dev/disk/azure/scsi1/lun2 -> sdc`, 64G. É o segundo disco de outro grupo anexado com a VM ligada (o primeiro foi o P10, na fatia 5).
2. a 5. 02:31:08 UTC: script com portas (scratchpad da sessão), como root. Portas: tamanho exato de 64 GiB, nenhuma assinatura (`wipefs -n`, `blkid`), disco fora do `mountinfo`, gravação recusada no `/srv/banco` imutável, uma linha só de diferença no fstab candidato e `findmnt --verify` com saída 0 e sem `[E]` ou `[W]` na linha nova.
   - `mkfs.xfs -L banco-v3 /dev/sdc` no disco inteiro: UUID `be0703f5-dd5b-4483-92e3-781563c72f5e`, `crc=1`, `reflink=1`, `bigtime=1`, blocos de 4 KiB.
   - `mkdir /srv/banco` e `chattr +i /srv/banco` antes de montar: com o disco ausente, nada se grava no disco de SO (`touch` recusado). A doc do Postgres 18 também manda pôr o diretório de dados dentro do ponto de montagem, para o banco falhar limpo se o volume sair (`creating-cluster`, lida em 29/10).
   - fstab: `UUID=be0703f5-dd5b-4483-92e3-781563c72f5e /srv/banco xfs defaults,nofail 0 2` (linha 7), como a doc da Azure para disco de dados; sem `discard`, porque o `fstrim.timer` roda e a mesma doc avisa do custo do `discard`. A cópia do fstab antigo ficou em `/tmp`.
   - Resultado: rc=0 às 02:31:09, sem nenhuma porta parada; `mount /srv/banco`: `/dev/sdc xfs rw,relatime,inode64,logbufs=8,logbsize=32k,noquota`.
6. Evidência (02:31 UTC): `findmnt --verify --verbose` sem aviso na linha do `/srv/banco` e saída 0; `df`: 64G, 1,3G usados (reserva interna do XFS); a raiz montada `755 root:root`, sem o bit imutável; `srv-banco.mount` ativo. No workspace, o `Perf` da VM1 traz o `/srv/banco` desde a amostra das 02:32:00 (2%), já coberto pelos alertas de disco.

Não testado: o boot com o disco novo. A prova é o próximo ciclo real da VM1 (auto-shutdown e runbook novo), conferida no journal e no `findmnt` depois da partida.
