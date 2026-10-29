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

## Boot com o disco do banco (sessão 8, 29/10)

Ciclo real de 28 para 29/10 (detalhe em `docs/operacao/2026-10-28-fatia6-vms.md`, "Sessão 8"): o Pedro desalocou a VM1 pelo Portal às 02:51:14 UTC, e o runbook novo a ligou às 09:01. No desligamento, `XFS (sdc): Unmounting Filesystem be0703f5-…` às 02:51:15,10. Na partida, `XFS (sdc): Mounting V5 Filesystem be0703f5-…` e `Ending clean mount` às 09:01:51,74; `srv-banco.mount` ativo às 09:01:51,75, antes do containerd (09:01:57,72) e do docker (09:01:59,20). `findmnt /srv/banco`: `/dev/sdc xfs rw,relatime,inode64,logbufs=8,logbsize=32k,noquota`; `lsblk`: lun2 → `sdc`, 64G, rótulo `banco-v3`. O boot com o disco novo está provado.

Achado para o Postgres: no desligamento, o `/srv/banco` desmontou em paralelo com a parada do docker, sem ordem entre os dois. A unit do Postgres precisa de `RequiresMountsFor=/srv/banco` e `After=docker.service`.

## Postgres, pgBackRest, pg_dump, verificação e restauração (sessão 8, 29/10)

Autorização do Pedro (~11:40 UTC, no chat): a sequência de 8 passos do script `fatia7.sh` (scratchpad da sessão), parando em qualquer divergência, com uma condição: no passo 4, mostrar o `pg_hba` só com `hostssl`, `scram-sha-256` e o IP privado da VM2 como única origem de rede. O arquivo tinha também `hostssl` para 127.0.0.1; essa linha saiu antes da instalação. Código nos commits `4ae05a8`, `edabd58` e `e1d220f`.

Fatos levantados antes, só com leitura:
- Na VM1, o UID 999 é o `azureotelcollector` (coletor do agente de monitoramento) e o GID 999 é o `systemd-journal`. A imagem oficial roda o Postgres como 999; a derivada usa 5432, livre no host.
- `postgres:18.6-trixie`: índice `sha256:979bccfd…e0e4`, manifesto amd64 `sha256:f4b419e3…db6f`, criado em 28/10, `STOPSIGNAL SIGINT`, volume `/var/lib/postgresql`.
- PGDG trixie: `InRelease` de 28/10 com assinatura válida da chave `B97B 0AFC AA1A 47F0 44F2 44A0 7FCC 7D46 ACCC 4CF8`; `Packages.bz2` conferido pelo sha256 do `InRelease`; `pgbackrest_2.60.0-1.pgdg13+1_amd64.deb`, sha256 `609dae5ee9c413e25fde3bd0fc2fd2140cb93d137baeedf152ffa1998786ab60`.
- IPs privados das duas VMs com alocação `Dynamic` (VM1 10.0.0.5, VM2 10.0.0.4).

Passos (horários UTC):
1. 11:46 e 11:52–11:53: `docker pull` da base e `docker build`. O primeiro build parou na porta do Dockerfile (sobrou o 999 em `/etc/postgresql` e no grupo de `/var/log/postgresql`); com a autorização do Pedro, o `chown` virou dois `find` que mapeiam dono e grupo. Imagem `sha256:cd900302…`, `postgres` com UID e GID 5432; `initdb` e `pgbackrest help` com as opções usadas (`auto` entre os tipos de chave do Azure).
2. 11:54:12: `/etc/pathsol/banco` com os 3 arquivos (iguais ao repositório por `cmp`), chave EC P-256 (`root:5432`, 0640) e certificado autoassinado `CN=pathsol-banco-v3`, de 29/10/2026 a 28/10/2028, `CA:FALSE`, `serverAuth`, IPs 10.0.0.5 e 127.0.0.1, SHA-256 `1F:57:6A:ED:…:75:6D`; `/usr/local/sbin/pathsol-banco` e as 7 units, `systemd-analyze verify` sem aviso. O `pathsol-status` novo (com `x-ms-date`) gravou `down` e `up`, HTTP 201.
3. 11:54:22: `pathsol-banco cria`: `/srv/banco/postgresql` e `/srv/banco/pgbackrest-spool` (5432:5432, 0700); `pg_controldata`: versão 1800, `Data page checksum version: 1`, `shut down`.
4. 11:54:31: `systemctl enable --now pathsol-banco`. PostgreSQL 18.6 (Debian 18.6-1.pgdg13+2); `ss`: 5432 só em 127.0.0.1 e 10.0.0.5; `ssl=on`, TLS 1.2 mínimo, `data_checksums=on`, `archive_mode=on`, `archive_timeout=300`, `wal_compression=lz4`; bancos com provedor builtin, C.UTF-8, UTF8. `pg_hba_file_rules`: linha 5 `local all postgres peer` e linha 7 `hostssl all all 10.0.0.4/255.255.255.255 scram-sha-256`, sem erro. TCP sem TLS: `no pg_hba.conf entry … no encryption`; com `verify-full` e o certificado fixado, o TLS passa e o `pg_hba` recusa 127.0.0.1 (`… SSL encryption`). Postmaster com `oom_score_adj -1000` e os 9 processos filhos com 0.
5. 11:57:32: `stanza-create` parou: `unable to verify certificate presented by 'pathsolwsiv3.blob.core.windows.net:443'`. A imagem oficial não traz o `ca-certificates` (estado `un`). Com a autorização do Pedro: `ca-certificates 20250419+deb13u1` na imagem (`sha256:7f04bd26…8f0b`) e restart do banco às 11:59–12:00. 12:01:01: `stanza-create` e `check` OK; o segmento `…0003` chegou ao repositório.
   - Achado no log: o servidor reiniciou inteiro, com recuperação de crash, 4 vezes (11:59:31, 11:59:32, 12:00:32 e 12:00:59). O `archive-push` assíncrono do pgBackRest cria um processo que se desliga dele; com o postmaster como PID 1 do container, o postmaster o herdava e, quando ele saía com erro (código 103: sem CA nas três primeiras, sem stanza na quarta), registrava `untracked child process … exited with exit code 103` e reiniciava todos os processos. Com a autorização do Pedro: `docker run --init` (o `docker-init`, tini 0.19.0 do pacote `docker-ce`, vira o PID 1) e `--timeout` no lugar do `--time` obsoleto; restart às 12:04:46.
   - Evidência depois do `--init`: `docker-init` como PID 1 (`oom -1000`), postmaster como filho (`-1000`, PID 7 dentro do container), processos do Postgres com 0; num `pg_switch_wal()`, o `archive-push:async` aparece como filho do `docker-init`, não do postmaster; segmento `…0006` arquivado, `failed_count 0`, e nenhuma linha de órfão ou reinício no container novo. O `check` levou 0,5 s (antes, 60 s).
6. 12:05:27: `systemctl start pathsol-banco-diario`: `OK backup: full em 2 s` (`20261029-120528F`, banco de 22,7 MB, 2,7 MB no repositório) e `OK dump: dump/20261029T120530Z/, 3 arquivos` (`globais.sql`, `canario.dump`, `postgres.dump` e o marcador `completo`), conferidos pela listagem com a identidade da VM1; 19 blobs em `pgbackrest/`.
7. 12:05:44: os 3 timers ligados (verificação a cada 15 min; diário às 06:00 e restauração no dia 1 às 10:00 de Brasília, com `Persistent`). Primeira verificação: `OK` em banco, arquivamento, backup, dump e nos dois certificados (app com 89,4 dias; banco com 730,0), e `FALHA restauracao: nenhum encontrado`, esperada antes do primeiro teste.
8. 12:05:57: `systemctl start pathsol-banco-restaura`: `OK restauracao: backup com WAL até a linha nova (1 linhas) e dump 20261029T120530Z`, em 14 s. O backup full é anterior ao banco `canario`: o banco, a tabela e a linha vieram só do replay do WAL, buscado no repositório pelo `archive-get` num container em rede bridge (o IMDS responde de dentro do container). Área de rascunho removida; marcador em `/var/lib/pathsol-banco/restauracao-ok`.
   - Repetição (12:06:25–12:06:44): `OK backup: diff em 1 s`, `OK dump: dump/20261029T120627Z/` e `OK restauracao: backup com WAL até a linha nova (2 linhas) e dump 20261029T120627Z`, agora com uma linha do canário no dump.

No Log Analytics, as linhas chegam com `Facility local0`, `ProcessName pathsol-banco` e, para a prioridade `err`, `SeverityLevel error` (não `err`): é o que os dois alertas leem.
