# Fase 4 — Worker GPU e acervo `.h5`

Relatório parcial. A fase começou em 30/10/2026 (~16:15 UTC), na sessão 1, depois do APROVADO FASE 3, e segue as fatias da seção 19.2 do plano (`docs/v3/02-plano-v3.md`). O gate jurídico não fechou e a exportação do Motic não chegou: o aceite usa as lâminas públicas de reserva da seção 17 e a lâmina em branco. O detalhe de cada ação nas VMs e no Azure fica em `docs/operacao/`.

## Situação por fatia

| Fatia | Situação |
|---|---|
| Skill `pathsol-contrato-h5` com a decisão 5 | feita (`643baf8`): diff mostrado ao Pedro antes do código e aprovado, com os 7 pontos de fora do texto da decisão 5 |
| 1. Benchmark na VM2 | em curso: imagem do worker, leitor, grade, métricas de QC 2, extrator e benchmark com 40 testes, mais 2 com os pesos reais; quatro lâminas TCGA-STAD escolhidas; falta rodar na VM2 |
| 2. Pesos do Hibou-L | feita na VM1: o Pedro baixou a revisão fixada pelo terminal dele (17:21 UTC), com o script de `ed28b16`; hashes e licença conferidos; código lido antes de rodar; atenção fixada em eager. Faltam a cópia no container `modelos` (depois do apply) e a cópia na VM2 (com o benchmark) |
| 3 a 11 | não começadas |

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

## Plano do Terraform: container dos pesos e papéis da VM1

`terraform plan -out=fase4-modelos.tfplan` em 30/10, ~17:00 UTC: **5 a criar, 0 a alterar, 0 a destruir.** No JSON do plano, 64 `no-op` e 5 `create`; nenhum recurso com dado, de VM, disco ou rede muda. sha256: `463d7f08f9159d5ddac3c6e6ff86a681e9e32d824e731e8759ab3347494e7caf`.

| Recurso | O quê | Custo/mês |
|---|---|---:|
| `azurerm_storage_container.modelos` | `modelos` na `pathsolwsiv3`, privado, sem retenção legal, `prevent_destroy` (`wsi.tf`). Recebe a revisão fixada do Hibou-L (seção 10.1). Nenhuma regra de ciclo de vida o alcança; o soft delete de 14 dias da conta vale para ele | ~R$ 0,26 (1,21 GB em Hot ZRS a R$ 0,2127/GB; o plano estimava ~R$ 0,19, em LRS) |
| `vm1-modelos` | VM1: `pathsol-blob-sem-exclusao-v3` no `modelos`, para enviar os pesos e lê-los de volta | R$ 0 |
| `vm1-wsi-publico` | VM1: o mesmo papel no `wsi-publico`, para o script do operador enviar as lâminas públicas de reserva com SAS de delegação só de criação (seção 17). A SAS nunca dá mais que a atribuição: o `wsi-diagnose` fica fora do alcance | R$ 0 |
| `vm1-delegacao` | VM1: `Storage Blob Delegator` na conta, porque a chave de delegação é pedida à conta (fatia 8 da Fase 3) | R$ 0 |
| `vm1-fila-envio` | VM1: `Storage Queue Data Message Sender` na fila `jobs`, para o produtor de jobs de teste (decisão 7), que sai na Fase 5 | R$ 0 |
| **Total** | | **~R$ 0,26** |

Nenhum papel novo tira a retenção legal: o papel sem exclusão não tem `containers/*` de plano de controle, e o `Storage Blob Delegator` só pede a chave de delegação. No apply, o `pathsol-role-assignment-v3` dispara 4 vezes e o `pathsol-storage-write-v3` pode disparar pelo container novo; são do apply, não incidente. O apply é do Pedro, pelo SSH, com o Antigravity fechado.

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

## O que não foi possível verificar

- A vazão e o tempo por lâmina na VM2: saem do benchmark.
- O tempo de download do Blob para a VM2: o benchmark baixa do GDC, e o caminho real (`wsi-publico`) só é medido no aceite (fatia 11).

## Riscos

- **Imagem grande:** 9,47 GB a cada `docker save | docker load` na VM2 (`/data` de 64 GB, com o teto de 2 imagens).

## Decisões pedidas ao Pedro

- Aplicar o `fase4-modelos.tfplan` (sha256 acima) como última ação de uma sessão.
