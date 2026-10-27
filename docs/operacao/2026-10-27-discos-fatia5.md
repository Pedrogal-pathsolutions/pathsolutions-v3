# Fase 3, fatia 5: troca dos discos de dados e primeira partida da VM2 — registro de ações

Os passos são os 9 da seção "Plano da fatia 5 (discos)" do `docs/v3/03-base-infra.md`. Cada entrada traz o horário de início em UTC, o comando ou a ação e a saída resumida. Nenhum dado de paciente entra aqui.

## Autorização

- 27/10, início da sessão 5 (~12:50 UTC), no chat: o Pedro informou que aplicou o `discos.tfplan` (2 criados, 0 alterados, 0 destruídos), que os e-mails dos alertas das 08:54 de Brasília chegaram e que a mudança na regra `default-allow-ssh` às 11:42 UTC foi dele. Autorizou os 9 passos, com duas condições:
  1. na primeira partida da VM2, o congelamento de kernel e driver (padrão 11) é a primeira ação, antes de qualquer outra; já autorizado;
  2. a exclusão do P20 e do P15 só é pedida depois de reiniciar a VM, mostrar o `/data` montado no disco novo e o Docker de pé.
- As exclusões (passos 4 e 9) seguem a decisão 2: cada uma pede autorização na hora. A trava do `.claude/settings.json` nega `az disk delete` à sessão; o comando fica com o Pedro.

## Conferência do apply e estado inicial (só leitura)

- 12:50 UTC: `az account show`: PATHSOLUTIONS TECNOLOGIA EM SAUDE LTDA, `bd87a1ca-e4f5-460b-9f12-c89e114293f1`, Enabled, login de usuário.
- 12:51 UTC: `sha256sum discos.tfplan`: `09d553fd…bfdc`, igual ao do relatório. `az disk list -g rg-pathsol-v3`: `pathsol-dados-vm1-v3` (P10, 128 GiB) e `pathsol-dados-vm2-v3` (P6, 64 GiB), Premium_LRS, brazilsouth, sem zona, `DenyAll`, rede pública `Disabled`, `Unattached`, criados às 12:48:17, com as 3 tags.
- 12:52 UTC: `terraform plan -detailed-exitcode`: `No changes`, saída 0; 31 recursos e 2 data sources no estado.
- 12:53 UTC: `az vm list -d`: VM1 `VM running`, P20 na lun0 com cache ReadWrite; VM2 `VM deallocated`, P15 na lun0 com cache ReadOnly. Discos do `rg-prod-brsouth-001`: P20 Attached, P15 Reserved e os dois P4 de SO.
- 12:54 UTC: activity log desde 12:30: `disks/write` dos dois discos às 12:48:17, `Succeeded` às 12:48:21 e 12:48:22, pelo Azure CLI; nenhuma falha. Os `listKeys` e `sharedKeys` das 12:32 são do plan da sessão 4.
- 12:55 UTC: extensão da VM2: `NvidiaGpuDriverLinux` 1.9, `Succeeded`, `autoUpgradeMinorVersion true`, `enableAutomaticUpgrade` nulo, `settings` nulo. `patchMode` e `assessmentMode` `ImageDefault`. A VM2 não tem identidade.
- 12:57 UTC: VM1 por dentro. `/data` no `/dev/sdb` (lun0), ext4, rótulo `data`, UUID `3afbd359-…`, `rw,relatime,discard`, raiz `azureps:azureps 755`; fstab `UUID=3afbd359-… /data ext4 defaults,nofail,discard 0 2`. `/data/docker` `root:root 710`, `/data/containerd` `root:root 700`, `/var/lib/containerd` → `/data/containerd`. `daemon.json` `{"data-root": "/data/docker"}`. containerd, `docker.socket` e docker active/enabled, sem drop-ins e sem `RequiresMountsFor`. `docker info`: `/data/docker|overlayfs|[["driver-type","io.containerd.snapshotter.v1"]]|io.containerd.runc.v2,runc,|runc`, engine `18252361-…`, Docker 29.4.2; 0 containers, imagens, volumes e cache de build; socket `root:docker 660`. `/data` com 40 entradas (o `lost+found`, 28 pastas, 10 arquivos e o nó `backingFsBlockDev`, 8:16); 332K usados.
- 13:05 UTC: testes das portas de leitura, sem mudar nada:
  - `findmnt --verify`: saída 0 com o fstab real; 1 com UUID inexistente; 0 com tipo de fs desconhecido, que só gera aviso. O resumo sai pelo stderr. A porta do script exige saída 0 e nenhum `[E]` ou `[W]` na seção do `/data`, rodando como root; nos três testes ela deu OK, falha e falha.
  - `fuser -vm` (verboso) devolveu 0 sem nenhum processo; o modo silencioso devolveu 1. A porta lê a lista de PIDs do `fuser -m`, e não o código de saída.
  - Unit mascarada não carrega drop-in: a conferência do `RequiresMountsFor` vem depois do `unmask`. O `systemctl show` de uma unit com `RequiresMountsFor=/var/log/journal` mostra `-.mount` em `Requires` e `After`.
  - `/usr/bin/unattended-upgrade:1027-1045` (unattended-upgrades 2.9.1+nmu4ubuntu1, na VM1): pacote em hold não é atualizado.

## Passo 1: P10 na VM1 ligada

- 14:03:47 UTC: `az vm disk attach -g rg-prod-brsouth-001 --vm-name vm-appviewer-prod-001 --name <id do pathsol-dados-vm1-v3> --lun 1 --caching ReadOnly`.
  - Resultado: rc=0 às 14:03:55. Modelo da VM1: lun0 P20 (ReadWrite) e lun1 `pathsol-dados-vm1-v3` (ReadOnly); disco `Attached`, `managedBy` VM1; `ProvisioningState/succeeded`, `PowerState/running`. O kernel viu o disco às 14:03:51 como `sdc` (1:0:0:1, 128 GiB, "read cache: enabled"). Anexar um disco de outro grupo com a VM ligada funcionou (seção 7 do plano), sem reiniciar a VM1.
- 14:08:23 UTC: `trocar-data.sh checar` (só leitura): todas as portas passaram; nada mudou.

## Passo 2: `/data` da VM1 no P10

- 14:09:00 UTC: `sudo bash trocar-data.sh executar 1 0 137438953472 dados-vm1-v3 1000:1000 3afbd359-2c66-4644-ba14-cbdf5cd8ebb9` (sha256 do script `f5dc76bc…5b82`; o script fica no scratchpad da sessão). Sequência e portas:
  1. portas de leitura, as mesmas do modo `checar`;
  2. `mkfs.ext4 -F -m 0 -L dados-vm1-v3 -E root_owner=1000:1000 /dev/sdc`, com TRIM do disco inteiro (padrão do mkfs);
  3. `systemctl stop` e `mask --runtime` de `docker.socket`, `docker.service` e `containerd.service`; nenhum PID no `/data`;
  4. disco novo montado em `/run/pathsol-dados-novo`, `cp -a /data/containerd /data/docker`, árvore (tipo, modo, dono, tamanho, caminho) e sha256 dos arquivos comparados, raiz conferida, desmontagem;
  5. `umount /data`; fstab candidato com o UUID novo, diferente em uma linha só, conferido pelo `findmnt --verify` como root; `sed -i` no `/etc/fstab` e comparação com o candidato; `daemon-reload`; `mount /data`; árvore conferida de novo;
  6. drop-in `10-requires-data.conf` (`[Unit]` `RequiresMountsFor=/data`) em `/etc/systemd/system/containerd.service.d/` e `docker.service.d/`; `unmask --runtime`; `daemon-reload`; `data.mount` em `Requires` e `After` das duas units;
  7. `start` de containerd, `docker.socket` e docker; `docker info`, engine e socket comparados com os de antes.
  - Resultado: rc=0, concluído às 14:09:12, sem nenhuma porta parada. UUID novo `6a09d498-8a65-45d1-9547-5a8b04c11185`. Linha do fstab: `UUID=6a09d498-8a65-45d1-9547-5a8b04c11185 /data ext4 defaults,nofail,discard 0 2` (mesmas opções). Cópia: 39 entradas e 10 arquivos com o mesmo sha256. `docker info` igual (`/data/docker|overlayfs|[["driver-type","io.containerd.snapshotter.v1"]]|io.containerd.runc.v2,runc,|runc`), mesmo engine `18252361-…`, socket `root:docker 660`, 0 containers, imagens e volumes. O Docker recriou o `backingFsBlockDev` com o número do disco novo (8:32). `df`: `/dev/sdc` 125G, 332K usados.
- 14:10 UTC: conferência à parte (só leitura): o `/etc/fstab` não tem mais o UUID `3afbd359-…`; o `sdb` (8:16) não aparece no `mountinfo` de nenhum processo; `data.mount`, containerd, `docker.socket` e docker ativos; o journal não tem aviso nem erro entre 14:08:55 e 14:09:30; o ponto de montagem temporário não existe mais.

## Passo 3: P20 fora da VM1

- 14:11:24 UTC: antes, só leitura: P20 (`vm-appviewer-prod-001_DataDisk_0`, 512 GiB, criado em 30/04/2026) `Attached`; o `sdb` (8:16) não aparece no `mountinfo` de nenhum processo e o fstab não tem o UUID dele.
- 14:11:25 UTC: `az vm disk detach -g rg-prod-brsouth-001 --vm-name vm-appviewer-prod-001 -n vm-appviewer-prod-001_DataDisk_0`.
  - Resultado: rc=0 às 14:11:31. Modelo da VM1: só a lun1 (`pathsol-dados-vm1-v3`, ReadOnly); P20 `Unattached`, sem `managedBy`; VM1 `running`. No convidado: sem lun0 e sem `sdb`; `/data` no `sdc` (`dados-vm1-v3`); `data.mount`, containerd, `docker.socket` e docker ativos; `/` com 56% e `/data` com 1%.
  - Mensagem do kernel às 14:11:29, durante o detach: `sd 1:0:0:0: [sdb] Synchronizing SCSI cache`, 4 linhas do `hv_storvsc` com `cmd 0x35` (SYNCHRONIZE CACHE) e `host 0xc0000001`, e `[sdb] Synchronize Cache(10) failed: Result: hostbyte=DID_NO_CONNECT driverbyte=DRIVER_OK`. O fs do P20 tinha sido desmontado às 14:09:10 (`EXT4-fs (sdb): unmounting filesystem 3afbd359-…`; `data.mount: Deactivated successfully`). Nenhum erro de I/O no `sdc` desde 14:03. Leitura: o kernel pediu a descarga do cache a um disco que o host já tinha retirado (inferência; não conferida em documentação). Parado para perguntar ao Pedro, pela regra de parar diante de qualquer erro.
- ~21:07 UTC (registro gravado às 21:07:41; a pergunta saiu logo depois das 14:12): respostas do Pedro no chat:
  - seguir para a VM2;
  - no passo 8, em vez de reiniciar, desalocar e ligar de novo, que é o ciclo real da VM2; só depois mostrar o `/data` e o Docker e pedir a exclusão do P15;
  - a VM1 reinicia na partida de amanhã, pelo runbook; a sessão seguinte mostra o `/data` e o Docker e pede a exclusão do P20.
