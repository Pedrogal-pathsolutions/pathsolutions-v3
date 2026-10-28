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
- 21:12 UTC: horário real conferido (a sessão esperou aprovações de 14:12 a 21:07). Auto-shutdown: VM2 às 19:00 de Brasília (22:00 UTC) e VM1 às 20:00 (23:00 UTC), ambos Enabled. Corte para commit: 22:30 UTC.
- 21:13 UTC: commit `12cc211` com os passos 1 a 3 e push da `main`; hash local igual ao remoto.

## Passo 5: P6 na VM2 desalocada

- 21:14:18 UTC: `az vm disk attach -g rg-prod-brsouth-001 --vm-name vm-appfoundation-prod-001 --name <id do pathsol-dados-vm2-v3> --lun 1 --caching ReadOnly`.
  - Resultado: rc=0 às 21:14:23. Modelo da VM2: lun0 P15 (ReadOnly) e lun1 `pathsol-dados-vm2-v3` (ReadOnly); disco `Reserved`, `managedBy` VM2; VM2 `VM deallocated`. O alias `azure-foundation` do ssh resolve para 10.0.0.4, usuário `azureps`, com `StrictHostKeyChecking false` (`ssh -G`).

## Passo 6: primeira partida da VM2 e congelamento

- Script `partir-congelar.sh`: recusa partir depois das 21:40 UTC; `az vm start --no-wait`; tenta o ssh a cada 2 s, até 7 min; na primeira resposta, grava o `congelar.sh` em `/tmp` e o executa como root na mesma conexão (com `bash -s`, o `apt-mark` ou o `dpkg` poderiam ler o resto do script pela entrada padrão); só se o congelamento der certo, roda a leitura `ler-vm2.sh` (só leitura).
- `congelar.sh`: confere que nenhum processo segura os locks do dpkg (se segurar, para sem mudar nada); seleciona os pacotes instalados cujo nome começa por `linux-`, `nvidia-`, `libnvidia-`, `cuda-drivers` ou `xserver-xorg-video-nvidia`, menos o `nvidia-container-toolkit` e a `libnvidia-container` (não são o driver); exige ao menos uma imagem de kernel e um pacote do driver; `apt-mark hold`; confere cada um no `apt-mark showhold`. Testado na VM1 numa cópia com o `apt-mark` trocado por `echo`: parou na porta do driver (0 pacotes) e, com a porta forçada, listou 25 pacotes `linux-*`, sem nenhum hold real.
- 21:16:11 UTC: `bash partir-congelar.sh` (sha256: `congelar.sh` `c360cb5c…`, `ler-vm2.sh` `97358652…`, `partir-congelar.sh` `d30be84c…`).
  - Partida: `az vm start --no-wait` às 21:16:11; boot do convidado às 21:16:38; ssh respondeu às 21:17:45.
  - **Congelamento, primeira ação na VM2:** de 21:17:46 a 21:17:48. `apt-daily` e `apt-daily-upgrade` inactive; locks do dpkg livres. `apt-mark hold` em 48 pacotes, todos conferidos no `showhold`: 3 imagens de kernel (`linux-image-7.0.0-1014-azure`, `linux-image-7.0.0-1017-azure` e o metapacote `linux-image-azure`), os demais pacotes `linux-*` (metapacotes `linux-azure`, `linux-headers-azure`, `linux-tools-azure`, `linux-cloud-tools-azure`; módulos, headers e tools dos dois kernels; headers das 6.17.0-1011 e 1013, que ficaram sem imagem; `linux-base`, `linux-base-sgx`, `linux-libc-dev`, `linux-tools-common`, `linux-cloud-tools-common`) e 17 do driver: `cuda-drivers`, `nvidia-driver`, `nvidia-dkms`, `nvidia-kernel-common`, `nvidia-kernel-source`, `nvidia-firmware`, `nvidia-modprobe`, `nvidia-persistenced`, `nvidia-settings`, `xserver-xorg-video-nvidia` e 7 `libnvidia-*`, todos 595.71.05-1ubuntu1, mais o `nvidia-firmware-580-server-580.126.20` (580.126.20-0ubuntu0.24.04.2, sobra do arquivo do Ubuntu). Resultado: `CONGELADO`, rc=0.
  - Leitura (21:17:50, só leitura): Ubuntu 24.04.4, kernel 7.0.0-1017-azure. Discos: `sda` P15 (lun0, ext4 UUID `e3fe7aa1-b82a-488a-a37b-86dc454b89ff`, sem rótulo, no `/data`), `sdb` P6 (lun1, vazio), `sdc` SO, `sdd1` temporário de 176 GiB no `/mnt`. fstab do `/data`: `UUID=e3fe7aa1-… /data ext4 defaults,nofail 0 2` (sem `discard`, ao contrário da VM1). Raiz do `/data` `root:root 755`; só `containerd` (700) e `docker` (710), sem `lost+found` (o `find -delete` da Fase 1 apagou); 39 entradas; `/data` 316K de 251G; `/` com 69%. `daemon.json`: `data-root` `/data/docker`, runtime `nvidia` padrão. containerd: `root = "/data/containerd"` no `config.toml`; `/var/lib/containerd` é uma pasta antiga no disco de SO (`root 700`, de 07/05), fora do uso. `docker info`: `/data/docker|overlayfs|[["driver-type","io.containerd.snapshotter.v1"]]|io.containerd.runc.v2,nvidia,runc,|nvidia`, engine `086dcf96-…`, Docker 29.4.3, 0 containers, imagens e volumes; socket `root:docker 660`. GPU: Tesla T4, driver 595.71.05, 16384 MiB, persistence Enabled; DKMS `nvidia/595.71.05` instalado para 7.0.0-1014 e 7.0.0-1017. Kernels 6.17 só em `rc`. unattended-upgrades 2.9.1+nmu4ubuntu1, com as mesmas conferências de hold (linhas 229 e 1042); `Unattended-Upgrade "1"`; origens `noble`, `noble-security` e ESM. `apt-daily-upgrade.timer` com próxima execução às 21:51:20 (última em 15/10 09:53); `apt-daily.timer` às 04:57 de 28/10. Sem `reboot-required`; última atualização em 15/10 09:53–09:54; `dpkg --audit` vazio; nenhuma unit em falha.
- 21:19:06 UTC (só leitura): o handler da extensão no disco é o `NvidiaGpuDriverLinux-1.13.0.2`, de 07/05/2026 (o modelo diz 1.9, com atualização automática de versão menor). O agente rodou `nvidia-vmext.sh enable` nesta partida, de 21:17:45.77 a 21:17:47.78, com status `Ready`; nenhum processo segura os locks do dpkg. `findmnt --verify` do fstab atual: rc=0, "Success, no errors or warnings detected".
- 21:19:07 UTC: `trocar-data.sh checar 1 0 68719476736 dados-vm2-v3 0:0 e3fe7aa1-…` (script `c988bd14…`: a porta do conteúdo do `/data` passou a aceitar a falta do `lost+found`): todas as portas passaram; nada mudou.

## Passo 7: `/data` da VM2 no P6

- 21:19:50 UTC: `sudo bash /tmp/pathsol-trocar.sh executar 1 0 68719476736 dados-vm2-v3 0:0 e3fe7aa1-b82a-488a-a37b-86dc454b89ff` na VM2 (script `c988bd14…`, a mesma sequência do passo 2).
  - Resultado: rc=0, concluído às 21:20:02, sem nenhuma porta parada. `mkfs.ext4 -F -m 0 -L dados-vm2-v3 -E root_owner=0:0 /dev/sdb`; UUID novo `9169a38c-9b8e-4ef7-bfbc-6daa54402e3a`. Linha do fstab: `UUID=9169a38c-9b8e-4ef7-bfbc-6daa54402e3a /data ext4 defaults,nofail 0 2` (mesmas opções de antes). Cópia: 39 entradas e 10 arquivos com o mesmo sha256. Drop-ins `10-requires-data.conf` no containerd e no docker, com `data.mount` em `Requires` e `After`. `docker info` igual (`…|io.containerd.runc.v2,nvidia,runc,|nvidia`), mesmo engine `086dcf96-…`, socket `root:docker 660`. `backingFsBlockDev` recriado no disco novo (8:16). `df`: `/dev/sdb` 63G, 328K usados.

## Passo 8: P15 fora, ciclo de desalocar e ligar, evidência

- Script `ciclo-vm2.sh` (`checar-p15.sh`, `ver-vm2.sh`): recusa começar depois das 21:50 UTC; porta do P15 no convidado (a lun0 tem o UUID antigo, não aparece no `mountinfo` de nenhum processo, o fstab não a cita e o `/data` está no P6); `az vm deallocate`; `az vm disk detach` do P15 com a VM desalocada, para o convidado não ver retirada a quente (como a do P20); conferência do modelo (só a lun1) e do P15 (`Unattached`); `az vm start`; ssh; evidência; `az vm deallocate` só se a evidência sair limpa.
- 21:21:20 UTC: `bash ciclo-vm2.sh` (sha256: `checar-p15.sh` `0fc39651…`, `ver-vm2.sh` `ac5cfeb9…`, `ciclo-vm2.sh` `35c69a89…`).
  - Porta do P15: lun0 = `/dev/sda` (8:0), UUID `e3fe7aa1-…`, em 0 `mountinfo`, 0 linhas do fstab com o UUID antigo, `/data` com o UUID do P6: `P15_LIVRE`.
  - 21:21:28: `az vm deallocate -g rg-prod-brsouth-001 -n vm-appfoundation-prod-001`; `PowerState/deallocated` às 21:22:03.
  - 21:22:03: `az vm disk detach -g rg-prod-brsouth-001 --vm-name vm-appfoundation-prod-001 -n vm-appfoundation-prod-001_DataDisk_0`, com a VM desalocada. Modelo da VM2: só `1 pathsol-dados-vm2-v3 ReadOnly`; P15 `Unattached`, sem `managedBy`.
  - 21:22:09: `az vm start`; `PowerState/running` às 21:23:55; boot do convidado às 21:22:37; ssh às 21:23:58.
  - Evidência: só a lun1 (`sda`, 64G, `dados-vm2-v3`, no `/data`); sem lun0. `/data` com o UUID `9169a38c-…`, 328K usados. `Mounted data.mount` às 21:22:43.48, `Started containerd.service` às 21:23:01.43 e `Started docker.service` às 21:23:17.99: o `/data` montou antes dos dois. `data.mount`, containerd, `docker.socket` e docker ativos. `docker info` igual, engine `086dcf96-…`, socket `root:docker 660`, 0 containers, imagens e volumes. GPU `Tesla T4, 595.71.05`. 48 holds. `apt-daily` e `apt-daily-upgrade` inactive. O agente rodou o `enable` da extensão NVIDIA às 21:23:38, `Ready`. `EVIDENCIA_OK`.
  - 21:24:05: `az vm deallocate`; `PowerState/deallocated` às 21:24:38.
  - A VM2 ficou ligada de 21:16:11 a 21:21:28 e de 21:22:09 a 21:24:38 (~8 min; R$ 4,67/h).

## Passo 9: exclusão do P15 (com o Pedro)

- 21:25:07 UTC: antes do pedido, só leitura: P15 (`vm-appfoundation-prod-001_DataDisk_0`, 256 GiB, criado em 30/04/2026) `Unattached`, sem `managedBy`; 0 travas no `rg-prod-brsouth-001`; VM2 desalocada só com o P6; VM1 ligada só com o P10.
- 21:25 UTC: pedido ao Pedro, no chat, com a evidência do passo 8 e o comando `az disk delete -g rg-prod-brsouth-001 -n vm-appfoundation-prod-001_DataDisk_0 --yes`, para ele rodar (a trava do `.claude/settings.json` nega o comando à sessão).
- ~22:34 UTC: resposta do Pedro: "Apaguei o P15".
- 22:34:16 e 22:34:35 UTC, conferência: **divergência.** O P15 ainda existe: `az disk show` rc=0, `Unattached`, `provisioningState Succeeded` (não `Deleting`), na subscrição `bd87a1ca-…`. O activity log não tem nenhum `Microsoft.Compute/disks/delete` desde 21:20. Parado: nada mais foi feito. Passava das 22:30 UTC, o corte de 30 min antes do auto-shutdown da VM1.

## Situação ao fim da sessão (22:35 UTC)

- VM1: ligada, `/data` no P10 (`dados-vm1-v3`), Docker de pé; P20 desanexado, `Unattached`. Falta: conferir o boot com o P10 na partida de 28/10 (runbook) e, com o `/data` e o Docker mostrados, pedir a exclusão do P20.
- VM2: desalocada, só com o P6 no `/data` (`dados-vm2-v3`); kernel e driver em hold (48 pacotes). P15 desanexado e ainda existente: a exclusão precisa ser conferida com o Pedro.

## 28/10: conferência do P15, partida da VM1 e passo 4

- 20:53 UTC: `az account show`: mesma subscrição, Enabled, login de usuário.
- 20:53 UTC, passo 9 conferido: `az disk show` do P15 deu `ResourceNotFound` (rc=3). No activity log, o `Microsoft.Compute/disks/delete` do `vm-appfoundation-prod-001_DataDisk_0` começou às 22:40:53 e terminou `Succeeded` às 22:41:12 UTC de 27/10, pelo usuário do Pedro no Azure Portal. A conferência das 22:34 veio antes da exclusão; a divergência era de horário.
- Fora desta fatia, no mesmo activity log: duas gravações no agendamento de auto-shutdown da VM1 pelo Portal, às 22:34:35 e 22:40:17 UTC de 27/10, sem o conteúdo visível no log. A VM1 desalocou às 23:00:35 pelo auto-shutdown, então ele seguia ligado às 20:00 de Brasília.
- 20:55 UTC, ciclo da VM1 depois da troca do `/data` (activity log): `deallocate` de 23:00:35 a 23:00:48 UTC de 27/10, pelo auto-shutdown (aplicativo `1a14be2a…`, sem identidade gerenciada); `start` de 09:01:31 a 09:02:53 UTC de 28/10, pela identidade da `asa-prod-brsouth-001` (runbook `TurnOn-VMs`). Boot do convidado às 09:01:57.
- 20:56 UTC, evidência na VM1 (só leitura):
  - só a lun1 (`sda`, 128G, `dados-vm1-v3`, UUID `6a09d498-…`), no `/data`, ext4 `rw,relatime,discard`; linha 6 do fstab com o UUID novo; `/data` com 332K usados e `/` com 55%;
  - `Mounted data.mount` às 09:02:04.45, `Listening on docker.socket` às 09:02:11.80, `Started containerd.service` às 09:02:16.03 e `Started docker.service` às 09:02:33.44;
  - `docker info` igual ao de 27/10 (`/data/docker|overlayfs|[["driver-type","io.containerd.snapshotter.v1"]]|io.containerd.runc.v2,runc,|runc`), engine `18252361-…`, Docker 29.4.2; 0 containers, imagens, volumes e cache de build; socket `root:docker 660`;
  - nenhum aviso das três units no boot; o único erro do boot inteiro é `/dev/sr0: Can't lookup blockdev`, que também aparece no boot anterior. As linhas `skip loading plugin` do containerd e `Deleting nftables` do dockerd são de nível `info` e aparecem também no boot anterior (20 ocorrências);
  - no desligamento de 27/10, às 23:00:36, docker e containerd pararam e o `data.mount` foi desmontado (journal do boot anterior): a desalocação pelo auto-shutdown desligou o convidado de forma limpa.
- 21:05 UTC, antes do pedido: P20 (`vm-appviewer-prod-001_DataDisk_0`, 512 GiB, Premium_LRS, criado em 30/04/2026) `Unattached`, sem `managedBy`; nenhuma trava no `rg-prod-brsouth-001`; modelo da VM1 só com a lun1.

## Passo 4: exclusão do P20 (com o Pedro)

- 21:05 UTC: pedido ao Pedro, no chat, com a evidência acima e o comando `az disk delete -g rg-prod-brsouth-001 -n vm-appviewer-prod-001_DataDisk_0 --yes`, para ele rodar (a trava do `.claude/settings.json` nega o comando à sessão). Resposta: "Rodei o comando".
- 21:07:30 UTC: `az disk show` do P20 deu `ResourceNotFound` (rc=3). Activity log: `disks/delete` de 21:07:14 a 21:07:30 UTC, `Succeeded`, pelo Azure CLI.

## Situação ao fim da fatia 5 (28/10, 21:10 UTC)

- `rg-prod-brsouth-001`: só os dois discos de SO. `rg-pathsol-v3`: `pathsol-dados-vm1-v3` (P10) `Attached` à VM1 e `pathsol-dados-vm2-v3` (P6) `Reserved` pela VM2 desalocada.
- Com o P20 e o P15 apagados e os dois discos novos: −R$ 733,04/mês (plano, seção 5.4).
- Fatia 5 concluída. Os tetos do Docker vêm na fatia 6, antes do primeiro `docker pull`.
