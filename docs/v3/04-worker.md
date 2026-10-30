# Fase 4 — Worker GPU e acervo `.h5`

Relatório parcial. A fase começou em 30/10/2026 (~16:15 UTC), na sessão 1, depois do APROVADO FASE 3, e segue as fatias da seção 19.2 do plano (`docs/v3/02-plano-v3.md`). O gate jurídico não fechou e a exportação do Motic não chegou: o aceite usa as lâminas públicas de reserva da seção 17 e a lâmina em branco. O detalhe de cada ação nas VMs e no Azure fica em `docs/operacao/`.

## Situação por fatia

| Fatia | Situação |
|---|---|
| Skill `pathsol-contrato-h5` com a decisão 5 | feita (`643baf8`): diff mostrado ao Pedro antes do código e aprovado, com os 7 pontos de fora do texto da decisão 5 |
| 1. Benchmark na VM2 | feita (30/10, 17:42–18:57 UTC): 4 lâminas TCGA-STAD, fp16 e fp32, CPU, tempo por lâmina e partida (a frio, na fatia 9). O benchmark achou um defeito na escolha do nível da miniatura, corrigido em `42fdfe3`. Resultado abaixo e em `docs/v3/04-benchmark-vm2.json` |
| 2. Pesos do Hibou-L | feita na VM1: o Pedro baixou a revisão fixada pelo terminal dele (17:21 UTC), com o script de `ed28b16`; hashes e licença conferidos; código lido antes de rodar; atenção fixada em eager. Faltam a cópia no container `modelos` (depois do apply) e a cópia na VM2 (com o benchmark) |
| 3. Esquema mínimo com RLS forçada | feita (`9a19fee`, aplicada às 19:34 UTC com autorização): base `pathsol` vazia, com `tenants`, `slides` e `jobs`, estados e motivos da decisão 5; 16 testes num PostgreSQL 18.6 temporário |
| 4 a 11 | não começadas |

## Decisões do Pedro (30/10)

- **Skill:** aprovado o diff com as mudanças da decisão 5 e os 7 pontos: `case_id` fora dos attrs (a ligação da lâmina ao caso fica só no banco); `magnification` fora, com `tile_size` e `stride` em pixels do nível 0; Pillow na regressão de versões; mpp fora da faixa termina em "formato não suportado", com o motivo "escala indisponível" visível para o laboratório; escores da lâmina bloqueada por foco no `slide-h5`, junto do caminho do `.h5`; teste 9 (foco) no gate da Fase 4.
- **Faixa de mpp:** vale a regra do padrão 2 e da seção 4.1 (0,1 a 0,55 µm/px, com x e y a até 1% um do outro) sobre a da seção 10.3 do plano (0,1 a 1,0 µm/px, x igual a y).
- **Owner herdado da subscrição:** as 2 atribuições do grupo da Quatto são do parceiro CSP, que dá suporte ao orçamento. Risco aceito, nada muda. A regra do `CLAUDE.md` sobre papéis na conta de WSI vale para as identidades da v3 (pergunta deixada pela Fase 3).
- **Fatia 1:** pesos antes do benchmark, download pelo terminal do Pedro, imagem do worker, as quatro lâminas TCGA-STAD só no disco temporário da VM2 e um plano do Terraform com o container dos pesos e os papéis da VM1.

## Pesos do Hibou-L (fatia 2)

- **Download:** `/data/modelos/hibou-L/31a3b9fee16554c8552cb643d311733bce8faf7c/`, 7 arquivos e o `manifesto.json`. O token só passou pelo prompt do terminal do Pedro.
- **Conferência por dois caminhos independentes do script:** `sha256sum` do `model.safetensors` igual ao do plano (`a63d1699…b79c`); `git hash-object` dos 6 arquivos fora do LFS igual aos blobs da listagem da API salva antes do download; manifesto igual aos dois.
- **Licença do arquivo exato:** `license: apache-2.0` no README da revisão, sem arquivo LICENSE, como o plano registrou para o parecer (decisão 6).
- **Código lido antes de rodar** (`configuration_dinov2.py`, 188 linhas; `modeling_dinov2.py`, 997): sem rede, subprocesso, `eval`/`exec` ou escrita em disco; o único `requests` está num exemplo de docstring. Importa `transformers.onnx`, que existe na 4.57.6. ViT-L/14 com 24 camadas, 16 cabeças, FFN SwiGLU, `layerscale` e 4 registradores inseridos depois do CLS: 1 + 4 + 256 = 261 tokens. Em 224 × 224 os embeddings de posição entram sem interpolação. O `pooler_output` é o CLS depois da `layernorm` final.
- **Atenção: eager.** A atenção do código fixado é uma só (`Dinov2SelfAttention`, matmul e softmax explícitos), e a classe não declara suporte a SDPA. Trocar a atenção exigiria mudar o código, que tem o hash no `extractor_version`: seria outra versão, só com aprovação do Pedro.
- **Processador oficial não diverge do plano:** o `preprocessor_config.json` tem a média e o desvio do plano, redimensionamento bicúbico pelo menor lado até 224 e recorte central de 224. Num quadrado, isso é o bicúbico do Pillow que o worker usa. Provado no teste com os pesos reais (`test_modelo_real.py`): o tensor que chega ao modelo pelo caminho do worker é igual ao do processador oficial, com tolerância de 1e-5, num quadrado de 448 px. Por isso a troca não volta ao Pedro.

## Benchmark na VM2 (fatia 1)

Imagem `pathsol-worker:42fdfe3` (torch `2.14.1+cu132`, CUDA 13.2, cuDNN 9.24, transformers 4.57.6, Pillow 12.3.0, OpenSlide 4.0.1), Tesla T4 com o driver 595.71.05, 4 vCPUs. Atenção eager. O container rodou sem rede e com os pesos só para leitura. JSON completo em `docs/v3/04-benchmark-vm2.json`; registro em `docs/operacao/2026-10-30-fase4-sessao1.md`.

**GPU** (`embed`: envio, normalização, modelo e volta; 10 s por linha; a 1ª execução deu os mesmos números, a menos de 0,2):

| Lote | fp16, patches/s | memória | fp32, patches/s | memória |
|---:|---:|---:|---:|---:|
| 32 | 78,0 | 1,61 GiB | 21,0 | 1,70 GiB |
| 64 | 72,2 | 2,06 GiB | 19,6 | 2,25 GiB |
| 128 | 72,9 | 2,97 GiB | 21,2 | 3,35 GiB |
| 256 | 74,6 | 4,78 GiB | 19,1 | 5,55 GiB |

A T4 satura já com lote 32; fp16 é ~3,7 vezes mais rápido que fp32. As duas faixas do plano (fp16 de 50 a 110, fp32 de 14 a 30) contêm o medido.

**Por lâmina** (fp16, lote 32, 3 processos lendo, piso de 10% de tecido):

| Lâmina | Papel | mpp | Lado (nível 0) | Candidatos | Extraídos | Abaixo do piso | Miniatura | Extração | Patches/s | GPU ocupada | Cosseno fp16 × fp32 (média; mínimo) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `acad5023` | biópsia | 0,2520 | 444 | 8.123 | 4.618 | 3.505 | 1,2 s | 69,8 s | 66,2 | 93,9% | 0,99999; 0,99993 |
| `489a4eee` | biópsia | 0,2325 | 482 | 2.140 | 1.907 | 233 | 0,5 s | 31,5 s | 60,6 | 85,5% | 0,999999; 0,999993 |
| `4ecadacd` | biópsia | 0,4943 | 227 | 5.316 | 4.809 | 507 | 6,5 s | 75,1 s | 64,0 | 94,4% | 0,999999; 0,999993 |
| `b1f6b0eb` | peça | 0,2525 | 444 | 25.503 | 20.738 | 4.765 | 3,9 s | 321,3 s | 64,5 | 98,6% | 0,999998; 0,99999 |

O que isso diz, com n = 4 lâminas de uma só fonte (sinal, não validação):
- **A GPU limita, não a CPU.** De ponta a ponta, a GPU fica ocupada de 85% a 99% do tempo: a CPU segura o ritmo, salvo de 1% a 15%. O gatilho da NC8as (CPU limitando mais de 30%, padrão 7) não dispara. A medida isolada da CPU (600 candidatos por lâmina, com 1, 2 e 3 processos) saiu distorcida pela partida dos processos: 50 a 216 patches/s com 1 processo, e menos com 2 ou 3 na lâmina a 0,49 µm/px, que quase não reamostra. Vale a ocupação da GPU.
- **fp16 passa no critério do plano com folga:** em 1.024 patches reais, o cosseno médio fica acima de 0,99999 e o mínimo em 0,99993, sem NaN nem Inf (o limiar é 0,999). A validação formal, antes do primeiro `.h5` do acervo, fica na fatia 7, com o código final.
- **Tempo por lâmina na VM2, miniatura e extração:** de 32 a 82 s nas três do papel de biópsia (1.907 a 4.809 patches) e 325 s na peça (20.738 patches), a ~64 patches/s. Cada 1.000 patches custam ~16 s de VM2 (~R$ 0,02). Fora: download do Blob e envio do `.h5`, medidos no aceite (fatia 11).
- **Contra o plano (seção 8.4):** "~1 min por biópsia" confere com as três primeiras. A peça mediu 5,4 min, acima dos ~3 min do pior caso do plano. Se o volume for de peças grandes como essa, a coluna "só peças" sobe: a 1.000 lâminas/mês, ~97 h de VM2 em vez de 57 h (~+R$ 186/mês). A mistura de biópsias e peças segue desconhecida, e as biópsias endoscópicas reais devem ter menos patches que essas lâminas do TCGA (não medido).
- **Visibility timeout:** o pior tempo medido (325 s, sem download nem envio) dá ~11 min no dobro, abaixo do piso de 30 min da seção 9.1. Ele é fixado no aceite, com a lâmina de 4,76 GiB do TCGA-CESC.
- **Partida:** do `az vm start` ao SSH, 2 min 17 s (o `az` voltou em 2 min 16 s); do `docker run` ao modelo pronto, 5 a 6 s, com a imagem e os pesos ainda no cache, porque tinham acabado de ser copiados. A partida a frio, com o worker subindo no boot, é medida na fatia 9.
- **Download do GDC:** ~3,2 a 3,4 MB/s por conexão (1,6 GB em 476 s). Para o padrão 20 (dados públicos processados direto da fonte, Fase 7), isso põe na VM2 ~3 a 4 min de download para cada lâmina de ~700 MB, sem paralelismo; conexões em paralelo não foram testadas.

**Defeito achado pelo benchmark (`42fdfe3`).** A 1ª execução (imagem `a4b2d28`) parou na peça: "a pirâmide não tem nível baixo para a miniatura". Com mpp 0,2525, os 4 µm/px do QC 1 pedem 15,84×, um pouco abaixo do nível de 16× (4,04 µm/px, 33 MP). O `get_best_level_for_downsample` do OpenSlide devolvia o nível de 4× (535 MP), acima do teto, e o leitor recusava um SVS normal de 40× da Aperio como "formato não suportado". Na `acad5023`, o mesmo defeito passou calado: leu 180 MP e gastou 13,3 s na miniatura. A correção usa o nível mais grosso que não passa do alvo por mais de 5% ou, se nenhum couber no teto, o mais fino até 2 vezes o alvo (8 µm/px, o limite do QC 1 no plano), e tem teste de regressão com o caso real. O Pedro respondeu "Corrija e siga".

## Esquema mínimo com RLS forçada (fatia 3)

- **Onde:** migrações do Alembic em `services/api/` (seção 4.4 do plano; o FastAPI entra na Fase 5). O Alembic só gera o SQL, em modo offline. O superusuário aplica pelo `psql`, dentro do container do banco, com `SET ROLE pathsol_dono`, e por isso toda tabela pertence ao papel dono. Nada mudou no `pg_hba` nem na rede, e não há credencial nova. Script do operador: `deploy/vm1/banco/pathsol_esquema.py pathsol-api:<commit>`, que aplica papéis e base (idempotente) e depois as migrações a partir da revisão do banco.
- **Papéis** (todos NOLOGIN, sem superusuário, sem BYPASSRLS): `pathsol_dono`, dono das tabelas; `pathsol_worker`, que lê o job e a lâmina e só atualiza as 9 colunas de estado do job, sem `INSERT` nem `DELETE` (ganha LOGIN e senha na fatia 5); `pathsol_produtor`, que só lê o próprio tenant e insere lâmina e job, por `SET ROLE` do operador (decisão 7; sai na Fase 5). Fora o dono, só o worker tem `CONNECT` na base.
- **Tabelas:** `tenants` (o container de WSI é `wsi-<slug>`), `slides` e `jobs`, com RLS ativa e forçada e a política `tenant = app.tenant_id`. Restrições: a chave do job para a lâmina inclui o tenant; o motivo bate com o estado (QC_FAILED com vidro vazio, material insuficiente ou foco; formato não suportado com formato ou escala indisponível); COMPLETED se e só se houver ponteiro do `.h5`, com tamanho, sha256 e `extractor_version`; o ponteiro do `.h5` e o dos escores de foco começam pelo próprio tenant e pela lâmina, com o `job_id` no nome; o nome do blob da WSI é o UUID da própria lâmina, nunca o nome do arquivo do scanner, que pode trazer o número do caso.
- **Política com `nullif`:** a skill escreve `current_setting('app.tenant_id', true)::uuid`. Depois de uma transação com `SET LOCAL`, o Postgres deixa a variável como texto vazio na sessão, e o cast daria erro em vez de zero linhas. Com `nullif(…, '')`, a sessão sem tenant lê nada, como a skill pede ("sem tenant definido, a query não retorna nada"); o teste cobre o caso.
- **Testes** (16, num PostgreSQL 18.6-1.pgdg13+2 temporário dentro da imagem de teste, a mesma versão da produção, sem rede): os testes 2 e 3 de isolamento da skill no nível do banco (gravar em outro tenant é recusado; sem tenant, zero linhas), RLS forçada, papéis sem posse, as restrições acima e o caminho da restauração mensal (dump, `globais.sql` e `pg_restore --create --exit-on-error`, com RLS e dono preservados). Cinco defeitos aplicados de propósito na migração foram pegos, cada um pelo teste esperado. Um deles revelou que os testes travavam em vez de falhar; ganharam `lock_timeout` e conexão própria por subteste.
- **Backup:** a base nova entra sozinha no `pg_dump` diário (o `pathsol_banco.py` lista toda base que aceita conexão), e os papéis vão no `globais.sql`.

## Plano do Terraform: container dos pesos e papéis da VM1

`terraform plan -out=fase4-modelos.tfplan` refeito em 30/10, ~19:50 UTC, com o papel do Key Vault pedido pelo Pedro (opção A, abaixo): **6 a criar, 0 a alterar, 0 a destruir.** No JSON do plano, 64 `no-op` e 6 `create`; nenhum recurso com dado, de VM, disco ou rede muda. sha256: `fb70baede0eeee4e6829b4831c18359656f97458ddabb797ece5f928c55f6fda`. O primeiro plano (~17:00 UTC, 5 a criar, `463d7f08…7caf`) foi substituído e não vale mais.

| Recurso | O quê | Custo/mês |
|---|---|---:|
| `azurerm_storage_container.modelos` | `modelos` na `pathsolwsiv3`, privado, sem retenção legal, `prevent_destroy` (`wsi.tf`). Recebe a revisão fixada do Hibou-L (seção 10.1). Nenhuma regra de ciclo de vida o alcança; o soft delete de 14 dias da conta vale para ele | ~R$ 0,26 (1,21 GB em Hot ZRS a R$ 0,2127/GB; o plano estimava ~R$ 0,19, em LRS) |
| `vm1-modelos` | VM1: `pathsol-blob-sem-exclusao-v3` no `modelos`, para enviar os pesos e lê-los de volta | R$ 0 |
| `vm1-wsi-publico` | VM1: o mesmo papel no `wsi-publico`, para o script do operador enviar as lâminas públicas de reserva com SAS de delegação só de criação (seção 17). A SAS nunca dá mais que a atribuição: o `wsi-diagnose` fica fora do alcance | R$ 0 |
| `vm1-delegacao` | VM1: `Storage Blob Delegator` na conta, porque a chave de delegação é pedida à conta (fatia 8 da Fase 3) | R$ 0 |
| `vm1-fila-envio` | VM1: `Storage Queue Data Message Sender` na fila `jobs`, para o produtor de jobs de teste (decisão 7), que sai na Fase 5 | R$ 0 |
| `vm1-kv-segredos` | VM1: `Key Vault Secrets Officer` no `pathsol-kv-v3`, para o script do operador gravar a senha do `pathsol_worker` (opção A do Pedro). A VM2 ganha `Key Vault Secrets User` só nesse segredo, num plano da próxima sessão, depois que ele existir: o cofre também vai guardar a chave do JWT (Fase 5) | R$ 0; operações do cofre em centavos |
| **Total** | | **~R$ 0,26** |

Nenhum papel novo tira a retenção legal: o papel sem exclusão não tem `containers/*` de plano de controle, e o `Storage Blob Delegator` só pede a chave de delegação.

**Senha do worker (fatia 5), decisão do Pedro de 30/10: opção A, Key Vault.** O script do operador gera a senha na VM1, faz o `ALTER ROLE pathsol_worker LOGIN PASSWORD` e grava o segredo no `pathsol-kv-v3` com a identidade da VM1 (token do IMDS só nesse script, com autorização). O worker lê pela identidade da VM2. A opção B (arquivo do root na VM2, sem Terraform) ficou de fora por contrariar o "segredos no Key Vault" da skill `pathsol-infra`. Consequência: o worker só conecta de verdade na sessão seguinte ao 2º apply. No apply, o `pathsol-role-assignment-v3` dispara 4 vezes e o `pathsol-storage-write-v3` pode disparar pelo container novo; são do apply, não incidente. O apply é do Pedro, pelo SSH, com o Antigravity fechado.

## Escolhas desta fase, fora do texto do plano

- **Versões fixadas no `uv.lock`** (lockfile único do workspace): Python 3.13.18 (`python:3.13-slim` por digest `sha256:2d44738e…86bb`), uv 0.13.2 (por digest), torch `2.14.1+cu132` do índice do PyTorch (CUDA 13.2.2: runtime 13.2.86; o cuBLAS 13.4.1.3 é o que o próprio `cuda-toolkit` 13.2.2 fixa), transformers 4.57.6, openslide-bin 4.0.1.2 com openslide-python 1.4.6, Pillow 12.3.0, numpy 2.5.4, opencv-python-headless 4.14.0.94, h5py 3.16.0; tifffile 2026.9.20 só nos testes. Ficaram de fora versões com menos de ~2 semanas (torch 2.15.0, Pillow 13.0.0, openslide-python 1.4.7). O nvJitLink (13.4.92) e o `cuda-bindings` (13.4.4) vêm de faixas que a wheel do torch declara.
- **Imagem do worker** de 9,47 GB, montada na VM1; o `.dockerignore` da raiz só deixa entrar no contexto o que o worker usa. Ela roda sem rede para o hub (`HF_HUB_OFFLINE=1`), como usuário sem privilégio, e lê os pesos de um volume só de leitura.
- **mpp usado na grade:** a média de x e y, que a regra acima já obriga a diferir menos de 1%.
- **Parâmetros provisórios do QC, a calibrar no aceite (entram no `qc_version`):** miniatura do QC 1 a 4 µm/px; limiar de tecido por Otsu na saturação, nunca abaixo de 15 (de 255), para o vidro vazio e o ruído dele não virarem tecido; foco medido só nos pixels de tecido cuja vizinhança 3 × 3 também é tecido, porque os núcleos 3 × 3 do Laplaciano e do Sobel na borda do tecido veem o vidro.
- **Lâminas do benchmark:** a reserva pública não tem biópsia gástrica. Das 442 lâminas diagnósticas abertas do TCGA-STAD no GDC (todas SVS; mediana de 686 MiB), três de ~150 MiB fazem o papel de biópsia e uma de ~1,5 GiB, o de peça. O tamanho do arquivo é o único sinal de área de tecido sem abrir a lâmina; o número real de patches sai do benchmark. Licença conferida antes do download: CC BY 3.0 no registro do Zenodo das lâminas TCGA-STAD (`10.5281/zenodo.12690037`, versão de 10/2026), apontado pelo IDC. A página do TCIA traz CC BY 3.0 só para as imagens de CT da coleção.

| Papel | Arquivo no GDC | Tamanho | md5 |
|---|---|---:|---|
| biópsia | `acad5023-32f0-48aa-b4dd-80df4b06fd4d` | 151,0 MiB | `b74688c1e5946f3770daa5dca010f987` |
| biópsia | `489a4eee-7f35-451f-b97f-30229c582ffd` | 151,0 MiB | `b9d6605d9eb8eaea7cfc11c01f794fce` |
| biópsia | `4ecadacd-3ed0-4b61-a2b1-6ccba5d96a6e` | 144,5 MiB | `14ffdb169484898b7f4d4758abd58e2f` |
| peça | `b1f6b0eb-9032-4f2c-91f9-00ef3e5106d0` | 1.533,2 MiB | `ad2ecd206d85d8a2e46ed4a86b54d9fa` |

## Evidências (comando e saída resumida)

| Comando | Saída resumida |
|---|---|
| `az account show` | PATHSOLUTIONS TECNOLOGIA EM SAUDE LTDA; `bd87a1ca-e4f5-460b-9f12-c89e114293f1`; Enabled; login de usuário |
| `az vm get-instance-view` (VM2) | `PowerState/deallocated` |
| API do Hugging Face, revisão `31a3b9fe…faf7c` (sem token) | 7 arquivos; `model.safetensors` 1.214.686.200 B, sha256 `a63d1699…b79c`, igual ao do plano; licença `apache-2.0` no card; gated `auto`; classe `Dinov2ModelWithRegisters` com código próprio (`configuration_dinov2.py`, `modeling_dinov2.py`) |
| PyPI e índice cu132 do PyTorch | as versões acima existem; `torch-2.14.1+cu132-cp313-cp313-manylinux_2_28_x86_64.whl` publicado |
| `docker buildx imagetools inspect` | `python:3.13-slim` = 3.13.18, Debian trixie, `sha256:2d44738e…86bb`; `ghcr.io/astral-sh/uv:0.13.2` = `sha256:b9fddcde…2ba4` |
| `uv lock` (no container) | 51 pacotes; torch do índice `cu132`, o resto do PyPI |
| `docker build --target worker` | imagem de 9,47 GB; `/data` da VM1 de 1% para 17% (21 GB) |
| testes do script de download (Python 3.12 do host) | 14 testes `OK` |
| testes do worker (`--network none`, na imagem de teste) | 40 testes `OK` (2 pulados sem os pesos); três defeitos aplicados de propósito numa cópia (foco sem erosão, teto de mpp em 1,0, área não escaneada sem fundo branco) foram pegos, cada um pelo teste esperado |
| `sha256sum`; `git hash-object`; `manifesto.json` (pesos baixados) | os 7 arquivos iguais à listagem da revisão e ao plano |
| `test_modelo_real.py` com os pesos montados só para leitura, CPU da VM1, `--network none` | 2 testes `OK`: classe e 261 tokens; pixels iguais aos do processador oficial (tolerância de 1e-5) |
| `terraform fmt -check`; `validate`; `plan -out=fase4-modelos.tfplan`; `show -json` | formato ok; válido; 5 a criar, 0 a alterar, 0 a destruir; 64 `no-op` |
| API do GDC (`/files`, TCGA-STAD, Diagnostic Slide, open) | 442 lâminas SVS; tamanho mínimo ~0, p10 35, mediana 686, p90 1.533 e máximo 2.685 MiB |

| `az vm start`; leitura pelo SSH; `docker load`; `tar` dos pesos; `curl` do GDC (VM2, 17:42–18:11 UTC) | partida em 2 min 17 s até o SSH; T4, driver 595.71.05, 48 holds, Docker vazio; imagem com o mesmo ID da VM1; sha256 dos pesos igual na VM2; md5 das 4 lâminas `OK` |
| `docker run --gpus all --network none … pathsol_worker.benchmark` (imagens `a4b2d28` e `42fdfe3`) | 1ª: rc=1 na 4ª lâmina (defeito acima); 2ª: rc=0 em 13 min 23 s, JSON em `docs/v3/04-benchmark-vm2.json` |
| `az vm deallocate` (18:56:35–18:57:12 UTC); `az vm get-instance-view` | `PowerState/deallocated`; VM2 ligada 1 h 14 min (~R$ 5,80) |
| `journalctl --list-boots` (VM2) | o boot anterior ao de 30/10 foi de 29/10, 15:01:32 a 15:01:38 (6 s), depois de um que terminou às 15:00:54. Responde à pendência da Fase 3: o deallocate interrompido pelo start desligou o SO, e o start gerou um boot de 6 s |

## O que não foi possível verificar

- O tempo de download do Blob para a VM2 e o de envio do `.h5`: o benchmark baixou do GDC. O caminho real (`wsi-publico` e `slide-h5`) é medido no aceite (fatia 11).
- A partida a frio do worker (boot até o modelo pronto, com o disco frio): medida na fatia 9.
- O tamanho de biópsias endoscópicas reais em patches: as lâminas do papel de biópsia são do TCGA, de peças cirúrgicas.
- Se o `/mnt/pathsol-bench` vazio saiu com a desalocação: o `rm -r` apagou o conteúdo, mas não o diretório, porque o `/mnt` é do root (o Pedro mandou seguir sem o `rmdir`). A próxima partida da VM2 confere.

## Riscos

- **Imagem grande:** 9,47 GB a cada `docker save | docker load` na VM2 (~1,5 a 2,5 min; `/data` de 64 GB, com o teto de 2 imagens).
- **Peças grandes custam mais que o previsto:** uma peça do TCGA levou 5,4 min de extração, contra ~3 min no pior caso do plano. A 6.000 lâminas/mês só de peças, a VM2 passaria das ~430 h do gatilho de reserva (padrão 7).
- **Dados públicos lentos na fonte:** ~3,3 MB/s por conexão no GDC, a partir da VM2.

## Decisões pedidas ao Pedro

- Aplicar o `fase4-modelos.tfplan` (sha256 acima) como última ação de uma sessão.
