# Arquitetura PathSolutions — especificação completa

Sistema SaaS multitenant de patologia digital em Azure Brazil South. Extração de características desacoplada da inferência: o Hibou-L roda uma vez por lâmina (GPU) e congela o resultado em HDF5; os modelos ABMIL por órgão consomem esse arquivo em CPU.

Blocos marcados como `PROPOSTA` não constam no diagrama Mermaid original — vieram do plano técnico e precisam de confirmação.

## 1. Blocos do mapa principal

### `scanner` — Scanner Motic
*plano de controle (CPU)*

Fronteira física do sistema

- Digitaliza a lâmina corada
- WSI em pirâmide multi-resolução
- Foco e coloração ditam a rejeição no QC

**Como funciona**
1. Digitaliza a lâmina corada em pirâmide multi-resolução.
2. A magnificação de varredura define o nível de trabalho do tiling (tipicamente 20×).
3. Qualidade de foco e coloração aqui determina a taxa de rejeição no QC 2.

**Parâmetros**

| parâmetro | definição |
|---|---|
| Formato de saída | depende do modelo Motic — confirmar |
| mpp do nível 0 | precisa estar no metadado do arquivo |

**Sai para:** ext (WSI (.svs / .tiff / .mrxs))

**Onde quebra**
- Foco irregular eleva a rejeição de patches
- Formato proprietário pode exigir conversão antes da leitura

### `lis` — LIS do laboratório
*plano de controle (CPU)*

Fonte de verdade do caso

- PathoWatch: integração nativa
- PathoWeb: extração autorizada
- Fonte de case_id, órgão e material

**Como funciona**
1. Fornece case_id, órgão, tipo de material e identificação do paciente.
2. O campo de órgão é o que seleciona o modelo mais adiante.
3. PathoWatch tem integração nativa; PathoWeb depende de extração autorizada.

**Sai para:** ext (case_id · órgão · tenant)

**Onde quebra**
- Órgão ausente ou com grafia divergente quebra o roteamento
- O direito de acesso ao PathoWeb vem da licença do fornecedor, não da posse do dado

**Em aberto**
- Formalizar autorização escrita antes de extração programática em cada novo cliente

### `ext` — Extensão / Gateway do LIS
*plano de controle (CPU)*

Evita mudar o LIS do cliente

- Casa a WSI com o caso do LIS
- Upload direto ao Blob (URL assinada)
- Não exige alterar o LIS do cliente

**Como funciona**
1. Casa o arquivo WSI com o caso aberto no LIS.
2. Pede URL assinada à API e sobe o arquivo direto ao Blob.
3. Envia POST /v1/jobs com metadados e hash do arquivo.

**Parâmetros**

| parâmetro | definição |
|---|---|
| Idempotência | wsi_sha256 + case_id |
| Upload | por blocos, com retomada |

**Entra de:** scanner (WSI (.svs / .tiff / .mrxs)) · lis (case_id · órgão · tenant)

**Sai para:** api (POST /v1/jobs) · blobwsi (upload com URL assinada)

**Onde quebra**
- WSI sem case_id vira job órfão
- Mudança de layout do LIS do fornecedor quebra a extração
- Upload interrompido sem retomada desperdiça banda

### `api` — API FastAPI + JWT
*plano de controle (CPU)*

Plano de controle — não processa imagem

- Resolve o tenant pelo token, nunca pelo cliente
- Cria o job e devolve URL assinada
- Expõe status, predição e heatmap

**Como funciona**
1. Autentica por JWT e resolve o tenant pelo token.
2. Cria o job no Postgres e publica a mensagem na fila.
3. Devolve URL assinada de escopo e prazo curtos para o upload.
4. Serve status, predição e heatmap ao workspace.

**Parâmetros**

| parâmetro | definição |
|---|---|
| Rotas | /v1/jobs · /cases/{id}/inference · /heatmap · /review · /models |
| tenant_id | sempre do token, nunca de parâmetro |

**Entra de:** ext (POST /v1/jobs)

**Sai para:** db (cria job · grava auditoria) · queue (job_id · wsi_uri · tenant · organ)

**Onde quebra**
- Arquivo grande passando pela API em vez de ir direto ao Blob causa timeout
- Aceitar tenant_id do cliente seria vazamento entre laboratórios

### `db` — PostgreSQL
*plano de controle (CPU)*

Estado e trilha de auditoria

- Casos, jobs, tenants, modelos, auditoria
- Guarda o ponteiro do .h5, não o conteúdo
- Row-Level Security por tenant_id

**Como funciona**
1. Guarda tenants, casos, lâminas, jobs, modelos, predições, revisões e log de acesso.
2. Armazena o ponteiro do .h5, nunca o conteúdo.
3. Row-Level Security por tenant_id, no mesmo padrão do LIS próprio.

**Entra de:** api (cria job · grava auditoria) · jobdone (status do job · métricas de GPU)

**Onde quebra**
- Sem RLS, uma consulta mal escrita cruza dados de laboratórios diferentes

**Em aberto**
- Definir retenção do log de auditoria e política de acesso para suporte

### `blobwsi` — WSI — Azure Blob
*armazenamento*

Imagem original, isolada por tenant

- Container ou prefixo por tenant
- Maior parcela do custo de storage
- Política de retenção a definir

**Como funciona**
1. Container ou prefixo por tenant, com URL assinada de escopo curto.

**Entra de:** ext (upload com URL assinada)

**Sai para:** worker (leitura em streaming)

**Onde quebra**
- Maior parcela do custo de armazenamento

**Em aberto**
- Política de retenção da WSI: manter, arquivar em camada fria ou descartar após prazo

### `queue` — Fila de jobs — Azure Queue
*GPU / offline*

Desacopla API e GPU

- Desacopla API e GPU; permite scale-to-zero
- Retry com backoff e dead-letter
- Visibility timeout > pior tempo medido

**Como funciona**
1. Recebe a mensagem do job e entrega a um worker por vez.
2. Visibility timeout segura a mensagem enquanto o worker processa.
3. Falha técnica volta à fila com backoff; estouro de tentativas vai para dead-letter.

**Parâmetros**

| parâmetro | definição |
|---|---|
| Mensagem | job_id, tenant_id, case_id, wsi_uri, organ, pipeline_version, attempt |
| Escala | permite scale-to-zero da VM GPU |

**Entra de:** api (job_id · wsi_uri · tenant · organ)

**Sai para:** worker (entrega 1 job)

**Onde quebra**
- Visibility timeout menor que o processamento gera duplicidade
- Dead-letter sem alarme significa caso perdido em silêncio

### `worker` — GPU Worker
*GPU / offline*

Executa o pipeline offline inteiro

- 1 job = 1 lâmina
- Idempotente por job_id: reentrega não duplica
- Publica progresso e métricas de GPU

**Como funciona**
1. Consome um job por vez: uma lâmina por execução.
2. Lê a WSI em streaming, roda QC, tiling, normalização e extração.
3. Escreve o .h5 e atualiza status e métricas.

**Entra de:** queue (entrega 1 job) · blobwsi (leitura em streaming)

**Sai para:** load

**Onde quebra**
- GPU única é ponto de falha e teto de vazão
- Processamento não idempotente geraria dois .h5 para o mesmo job

**Em aberto**
- Definir tempo de partida aceitável no scale-to-zero e comportamento em pico

### `load` — Leitura da WSI em streaming
*GPU / offline*

Leitura sem estourar memória

- Por nível da pirâmide, em blocos
- A lâmina inteira nunca entra na RAM

**Como funciona**
1. Abre a pirâmide e lê por nível, em blocos.
2. O nível 0 só é lido nas regiões com tecido.

**Entra de:** worker

**Sai para:** qc1

**Onde quebra**
- Formato não suportado pelo leitor
- Leitura em blocos pequenos faz a latência de rede dominar o tempo

### `qc1` — QC fase 1 — miniatura
*GPU / offline*

Decide se a lâmina merece GPU

- Detecção de tecido em baixa magnificação
- Otsu no canal de saturação + morfologia
- Saída: máscara e área de tecido em mm²

**Como funciona**
1. Lê um nível baixo da pirâmide (1,25–5×), de custo desprezível.
2. Converte RGB para HSV: o canal de saturação separa vidro de tecido.
3. Aplica Otsu no canal de saturação — limiar por lâmina, não fixo.
4. Morfologia: abertura, fechamento e preenchimento de buracos, com kernel em µm.
5. Componentes conexos: descarta fragmentos abaixo da área mínima.
6. Filtra artefatos: caneta, etiqueta, bolha e borda da lamínula.
7. Calcula área de tecido em mm², nº de fragmentos e maior fragmento.

**Parâmetros**

| parâmetro | definição |
|---|---|
| Nível de leitura | ~2–8 µm/px |
| Limiar de área | em mm², a calibrar por tipo de material |
| Kernel morfológico | definido em µm, convertido por mpp |

**Recebe**
- Miniatura da WSI

**Entra de:** load

**Entrega**
- Máscara de tecido
- Bounding boxes
- Área e contagem de fragmentos

**Sai para:** tissue

**Onde quebra**
- Marcação de caneta lida como tecido, se o filtro de matiz não existir
- Limiar percentual reprova biópsia endoscópica válida

**Em aberto**
- Calibrar limiares separados para biópsia, peça cirúrgica e citologia

### `tissue` — Existe tecido?
*decisão · nó de decisão*

Porta de QC da lâmina

- porta de QC

**Como funciona**
1. Compara a área de tecido com o limiar do tipo de material.
2. Abaixo do limiar, o job encerra como QC_FAILED antes de qualquer GPU.

**Entra de:** qc1

**Sai para:** fail (não) · tiling (sim)

**Em aberto**
- QC_FAILED precisa de mensagem de volta ao LIS: é resultado clínico, não erro técnico

### `fail` — Job encerrado — QC_FAILED
*falha*

Fim legítimo de um job

- Motivo: material insuficiente
- Resultado clínico, não erro técnico
- Precisa voltar ao LIS como aviso

**Como funciona**
1. Status terminal com motivo registrado.
2. Não consome GPU e não gera .h5.

**Entra de:** tissue (não)

**Em aberto**
- Definir quem é avisado no laboratório e em quanto tempo

### `tiling` — Tiling
*GPU / offline*

Onde a geometria é fixada

- Grade de patches sobre a máscara
- Tamanho, stride e magnificação travados
- Coordenadas X/Y gravadas no nível 0

**Como funciona**
1. Gera a grade de patches sobre a máscara de tecido.
2. Tamanho, stride e magnificação ficam travados por versão de pipeline.
3. Registra X e Y de cada patch em pixels do nível 0.

**Parâmetros**

| parâmetro | definição |
|---|---|
| Tamanho do patch | a definir e travar (ordem de 224–512 px) |
| Stride | sem sobreposição, ou sobreposição a definir |
| Magnificação | tipicamente 20× |

**Entra de:** tissue (sim)

**Sai para:** qc2 · consol (coordenadas X/Y)

**Onde quebra**
- Mudar qualquer parâmetro invalida os .h5 já gerados
- Coordenada gravada em nível diferente do viewer desalinha o heatmap

### `qc2` — QC fase 2 — por patch
*GPU / offline*

Seis métricas por patch, não um sim/não

- 6 métricas: tecido, foco, dobra, artefato, cor
- Vetor de scores por patch, não só sim/não
- Rejeição alta = alerta de re-scan

**Como funciona**
1. Fração de tecido no patch, recalculada na resolução de trabalho.
2. Nitidez: variância do Laplaciano e Tenengrad, normalizados pelo percentil da lâmina.
3. Dobra de tecido: diferença entre saturação e luminância.
4. Artefatos: bolha, caneta, poeira e borda da lamínula.
5. Coloração: densidade óptica de H e E após deconvolução de cor.
6. Consolida tudo num vetor de K scores, gravado no .h5.

**Parâmetros**

| parâmetro | definição |
|---|---|
| Fração de tecido | limiar entre 30% e 50%, a calibrar |
| Nitidez | corte relativo por lâmina, não absoluto |
| Alvo de rejeição | medir antes de fixar |

**Recebe**
- Patches do tiling

**Entra de:** tiling

**Entrega**
- Patches aceitos
- Vetor de scores [N×K]
- Contagem de rejeição por motivo

**Sai para:** patch · consol (scores de QC)

**Onde quebra**
- Métrica de foco absoluta confunde textura densa com nitidez
- Dobra de tecido passa no teste de foco e engana o modelo se não for medida
- Rejeição alta sem alerta esconde problema de scanner ou de coloração

**Em aberto**
- Filtrar antes ou depois do Hibou? Antes é barato mas trava o limiar; depois é flexível e custa GPU e storage

### `patch` — Patch aceitável?
*decisão · nó de decisão*

Regra de aceitação do patch

- limiar a calibrar

**Como funciona**
1. Combina os K scores por limiar, ou por classificador leve treinado com patches rotulados.

**Entra de:** qc2

**Sai para:** reject (não) · norm (sim)

**Em aberto**
- Calibrar com 500–1000 patches rotulados por tipo de material, escolhendo o corte pela curva ROC

### `reject` — Patch descartado
*falha*

Descartado, mas contabilizado

- Não consome GPU
- Contagem por motivo vai ao .h5

**Como funciona**
1. Não gasta GPU nem espaço.
2. O motivo entra na contagem agregada da lâmina.

**Entra de:** patch (não)

**Em aberto**
- Definir o limite de rejeição que dispara pedido de re-scan

### `norm` — Normalização Macenko
*modelo · **PROPOSTA (fora do Mermaid)***

Presente no plano técnico, ausente no Mermaid

- Reduz variação de coloração entre labs
- Está no plano técnico, ausente no Mermaid
- Sem LoRA, é a principal defesa de domínio

**Como funciona**
1. Macenko estima a matriz de coloração da própria lâmina.
2. Projeta a imagem para uma referência comum de H e E.
3. Reduz a variação entre laboratórios e scanners antes da extração.

**Entra de:** patch (sim)

**Sai para:** hibou (patches normalizados)

**Onde quebra**
- Sem LoRA por laboratório, é a principal defesa contra variação de domínio
- Aplicar normalização diferente do treino do extrator piora o resultado

**Em aberto**
- Confirmar se saiu do diagrama por decisão ou por esquecimento
- Se ficar, a versão do normalizador entra nos metadados do .h5

### `hibou` — Hibou-L — ViT-L/14 (DINOv2)
*modelo*

Congelado, igual para todos os tenants

- Pesos congelados: sem LoRA, sem fine-tuning
- Lote em fp16 até saturar os 16 GB da T4
- Mesmo extrator para todos os tenants

**Como funciona**
1. Pré-processa o patch conforme o pré-treino do modelo.
2. ViT-L/14: sub-patches de 14×14, 24 blocos de atenção, dimensão 1024.
3. Pré-treino DINOv2 sobre lâminas de patologia.
4. Agrega o token (CLS ou média) num vetor de 1024 dimensões.

**Parâmetros**

| parâmetro | definição |
|---|---|
| Precisão | fp16 no lote |
| Lote | limitado pelos 16 GB da T4 — medir |
| Pesos | congelados, hash registrado |

**Entra de:** norm (patches normalizados)

**Sai para:** emb

**Onde quebra**
- A licença do peso precisa de auditoria antes de uso comercial
- Trocar a versão transforma todo o acervo de .h5 em legado

### `emb` — Embedding 1024d por patch
*modelo*

Única saída da GPU

- Única saída da GPU
- Mudar a versão torna todo .h5 legado

**Como funciona**
1. Um vetor de 1024 dimensões por patch aceito.
2. A imagem não é armazenada novamente.

**Entra de:** hibou

**Sai para:** consol

**Em aberto**
- fp16 corta storage pela metade — validar impacto na acurácia antes de adotar

### `consol` — Consolidação HDF5
*GPU / offline*

Uma escrita por lâmina

- Escrita única por lâmina
- Grava temporário e renomeia ao fim
- Evita .h5 parcial lido como válido

**Como funciona**
1. Empacota embeddings, coordenadas, scores de QC e metadados.
2. Grava em nome temporário e renomeia ao final.

**Entra de:** emb · tiling (coordenadas X/Y) · qc2 (scores de QC)

**Sai para:** h5 (escrita única do .h5) · jobdone

**Onde quebra**
- Falha no meio da escrita deixaria arquivo parcial lido como válido
- Sem extractor_version, não há como saber o que reprocessar depois

### `h5` — Acervo .h5 — embeddings
*armazenamento*

O ativo reutilizável do sistema

- /embeddings   [N×1024] float16
- /coordinates  [N×2] int32 (nível 0)
- /qc_scores    [N×K] float32
- attrs: tenant, mpp, tile, extractor_version

**Como funciona**
1. Sustenta inferência, retreino e novos órgãos sem reabrir nenhuma WSI.
2. Lido em CPU: milissegundos por caso.

**Parâmetros**

| parâmetro | definição |
|---|---|
| /embeddings | [N×1024] float16 |
| /coordinates | [N×2] int32, nível 0 |
| /qc_scores | [N×K] float32 |
| attrs | tenant, mpp, tile, stride, extractor_version, qc_version |

**Entra de:** consol (escrita única do .h5)

**Sai para:** fetch (embeddings + coordenadas)

**Onde quebra**
- Custo cresce linearmente com o volume de lâminas
- Pode superar a receita por lâmina — resolver antes de escalar

### `jobdone` — Job COMPLETED
*sucesso*

Lâmina pronta para inferência

- Status e ponteiro do .h5 no Postgres
- Lâmina pronta para inferência em CPU

**Como funciona**
1. Status COMPLETED e ponteiro do .h5 gravado no caso.
2. Métricas de GPU e duração publicadas.

**Entra de:** consol

**Sai para:** db (status do job · métricas de GPU)

### `work` — Workspace React
*plano de controle (CPU)*

Onde o patologista trabalha

- Viewer de deep zoom + overlay de heatmap
- Roda na mesma VM CPU do plano de controle

**Como funciona**
1. Viewer de deep zoom sobre a WSI, com overlay do heatmap.
2. Revisão e assinatura acontecem aqui.

**Sai para:** fetch (abre o caso)

**Onde quebra**
- Heatmap desalinha se a magnificação do tiling e a do viewer divergirem

### `fetch` — API busca o .h5 no Blob
*plano de controle (CPU)*

Caminho crítico sem GPU

- Sem GPU no caminho crítico
- Extrator incompatível → reprocessar

**Como funciona**
1. Carrega embeddings e coordenadas do Blob para a memória.

**Entra de:** work (abre o caso) · h5 (embeddings + coordenadas)

**Sai para:** router

**Onde quebra**
- Versão de extrator incompatível deve levar a reprocessamento, nunca a inferência silenciosa

### `router` — Roteador de modelos
*plano de controle (CPU)*

O ponto frágil do desenho

- Órgão → ABMIL + versão ativa
- Sem regra para órgão vazio ou sem modelo
- Ponto de erro silencioso hoje

**Como funciona**
1. Lê o órgão dos metadados do LIS.
2. Normaliza o termo por dicionário de sinônimos.
3. Seleciona o modelo do órgão e a versão ativa para o tenant.

**Entra de:** fetch · lismeta (órgão) · models (versão ativa)

**Sai para:** proj (N × 1024d)

**Onde quebra**
- Órgão errado escolhe o modelo errado e devolve predição confiante e inválida

**Em aberto**
- Definir comportamento para órgão vazio, grafia divergente, material misto e órgão sem modelo

### `lismeta` — Metadados do LIS
*plano de controle (CPU)*

Metadado que decide a rota

- Órgão do caso (LIS)
- seleciona o modelo

**Como funciona**
1. Órgão e tipo de material vêm do cadastro do caso no LIS.

**Sai para:** router (órgão)

**Onde quebra**
- Campo livre no LIS: a qualidade varia por laboratório e por digitador

### `models` — Registro de modelos ABMIL
*armazenamento*

Registro versionado

- Um modelo por órgão, versionado
- Versão ativa por tenant
- Guarda métricas e quem aprovou

**Como funciona**
1. Um modelo por órgão, com histórico de versões.
2. Guarda métricas, conjunto de validação e quem aprovou.
3. A versão ativa pode ser fixada por tenant.

**Entra de:** deploy (nova versão em produção)

**Sai para:** router (versão ativa)

### `proj` — Projeção
*modelo*

Entrada do ABMIL

- 1024d → dimensão interna

**Como funciona**
1. Linear 1024 → D, com ReLU e dropout.
2. D interno a definir, na ordem de 256–512.

**Entra de:** router (N × 1024d)

**Sai para:** att

### `att` — Atenção por instância
*modelo*

Atenção com gate

- Peso por patch (MIL)

**Como funciona**
1. Ramo tanh(V·h) multiplicado por sigmoid(U·h) gera o score do patch.
2. Softmax sobre os N patches: os pesos somam 1.
3. Os pesos viram o heatmap ao serem cruzados com as coordenadas.

**Entra de:** proj

**Sai para:** clas · heat (pesos de atenção)

**Onde quebra**
- Atenção é evidência visual de apoio, não explicação causal nem delimitação de lesão

### `clas` — Classificador
*modelo*

Predição por lâmina

- Predição por lâmina

**Como funciona**
1. Linear sobre o vetor agregado, seguido de softmax.
2. Treinado apenas com o rótulo da lâmina (MIL).

**Entra de:** att

**Sai para:** outp

### `outp` — Saídas
*modelo*

Três saídas

- Predição · atenção · incerteza

**Como funciona**
1. Predição, pesos de atenção e escore de incerteza.

**Entra de:** clas

**Sai para:** heat (predição) · unc

### `heat` — Heatmap de atenção
*modelo*

Devolve a predição ao espaço da imagem

- Atenção × coordenadas
- Overlay sobre a imagem

**Como funciona**
1. Cruza os pesos de atenção com as coordenadas do .h5.
2. Renderiza como overlay sobre a WSI no viewer.

**Entra de:** att (pesos de atenção) · outp (predição)

**Sai para:** sign (overlay na imagem)

### `unc` — Incerteza / tipo
*decisão · nó de decisão*

Encaminhamento, não decisão clínica

- limiares a calibrar

**Como funciona**
1. Entropia e margem entre as duas maiores classes medem confiança.
2. Distância no espaço de embeddings detecta caso fora do domínio.
3. Três estados: verde, amarelo e laranja.

**Entra de:** outp

**Sai para:** normal (alta confiança) · uncert (incerto) · outlier (anomalia)

**Onde quebra**
- Softmax sem calibração superestima confiança
- Limiares indefinidos tornam imprevisível o volume que cai em revisão

**Em aberto**
- Adotar temperature scaling ou predição conforme antes de fixar limiar clínico

### `normal` — Verde — alta confiança
*sucesso*

Alta confiança

- Segue para revisão com heatmap

**Como funciona**
1. Segue para revisão com heatmap.
2. Alimenta a métrica de concordância entre IA e patologista.

**Entra de:** unc (alta confiança)

**Sai para:** sign (liberado para laudo)

### `uncert` — Amarelo — confiança baixa
*decisão*

Confiança baixa

- Entropia alta ou margem pequena

**Como funciona**
1. Vai para a fila de aprendizado ativo, com prioridade de revisão.

**Entra de:** unc (incerto)

**Sai para:** alq

### `outlier` — Laranja — outlier / OOD
*aprendizado contínuo*

Fora do domínio de treino

- Longe do domínio de treino

**Como funciona**
1. Vai para a fila de hard case, com revisão obrigatória.
2. Volume alto aqui indica domínio novo, não caso raro.

**Entra de:** unc (anomalia)

**Sai para:** hardq

### `sign` — Revisão e assinatura
*sucesso*

Entrega clínica e rótulo de treino

- Nenhum estado dispensa o patologista
- Registrar se a IA foi vista antes ou depois

**Como funciona**
1. O patologista revisa com o heatmap como apoio e assina.
2. O laudo assinado vira ground truth com a versão do modelo ativa.

**Entra de:** heat (overlay na imagem) · normal (liberado para laudo)

**Sai para:** label (laudo assinado = rótulo)

**Em aberto**
- Registrar se a IA foi vista antes ou depois da conclusão — sem isso não há como medir efeito real na acurácia

### `alq` — Fila de aprendizado ativo
*aprendizado contínuo*

Casos incertos

- Casos incertos, revisão priorizada

**Como funciona**
1. Concentra o que tem maior valor de rotulagem.

**Entra de:** uncert

**Sai para:** review

**Onde quebra**
- Sem limite de tamanho, vira acúmulo que ninguém revisa

### `hardq` — Fila de hard case
*aprendizado contínuo*

Outliers e anomalias

- Outliers e anomalias

**Como funciona**
1. Casos fora do domínio, que sinalizam limite de escopo do modelo.

**Entra de:** outlier

**Sai para:** review

### `review` — Revisão do especialista
*aprendizado contínuo*

Rotulagem pelo especialista

- Laudo real como rótulo
- Guarda versão do modelo e concordância

**Como funciona**
1. Registra diagnóstico validado, versão do modelo e se houve discordância.

**Entra de:** alq · hardq

**Sai para:** label

### `label` — Ground truth estruturado
*aprendizado contínuo*

Ground truth estruturado

- Taxonomia fixa de classes
- Grava no Postgres e na base de treino

**Como funciona**
1. Taxonomia fixa de classes por órgão.
2. Grava no Postgres e na base de aprendizado ativo.

**Entra de:** sign (laudo assinado = rótulo) · review

**Sai para:** aldata (ground truth validado)

**Onde quebra**
- Sem taxonomia fixa, o rótulo não é treinável

### `aldata` — Base de aprendizado ativo
*armazenamento*

Base curada de casos difíceis

- Casos difíceis com laudo real
- Separação por caso e por laboratório

**Como funciona**
1. Casos incertos e outliers com laudo real.

**Entra de:** label (ground truth validado)

**Sai para:** retrain (só os .h5, sem reabrir WSI)

**Onde quebra**
- Viés de seleção: treinar só no que o modelo errou distorce a distribuição
- Separação por caso e por laboratório é obrigatória para não vazar treino no teste

### `retrain` — Retreino só da cabeça ABMIL
*aprendizado contínuo*

A vantagem estrutural da arquitetura

- Consome os .h5 já existentes
- Nenhuma WSI é reaberta: ciclo de horas
- Extrator congelado = GPU quase zero

**Como funciona**
1. Treina apenas a cabeça ABMIL do órgão.
2. Consome os .h5 existentes: nenhuma WSI é reaberta.
3. Ciclo de horas, com custo de GPU quase nulo.

**Entra de:** aldata (só os .h5, sem reabrir WSI)

**Sai para:** valid

**Onde quebra**
- Esquecimento catastrófico se o treino usar só casos difíceis

### `valid` — Validação e versionamento
*aprendizado contínuo*

Portão entre experimento e produção

- Hold-out travado por caso e por lab
- Métricas por classe, órgão e cliente
- Faltam drift e auditoria de equidade

**Como funciona**
1. Conjunto de teste travado, separado por caso e por laboratório.
2. Métricas por classe, órgão e cliente.
3. Comparação de não inferioridade com a versão em produção.
4. Aprovação registrada com quem, quando e com quais dados.

**Entra de:** retrain

**Sai para:** deploy (aprovado)

**Em aberto**
- Faltam protocolo de mudança predeterminado, monitoramento de drift e auditoria de equidade

### `deploy` — Publicação da nova versão
*aprendizado contínuo*

Liberação gradual

- Sombra → 1 tenant → todos
- Rollback de um passo

**Como funciona**
1. Sombra, depois um tenant, depois todos.
2. Rollback de um passo sempre disponível.

**Entra de:** valid (aprovado)

**Sai para:** models (nova versão em produção)

**Onde quebra**
- Promoção global direta muda o resultado de todos os clientes ao mesmo tempo

## 2. Sub-fluxos detalhados

### QC fase 1 — detecção de tecido na miniatura

**Entrada — nível baixo da pirâmide**  
- Miniatura ou nível de ~2–8 µm/px (1,25–5×)
- Custo desprezível: o nível 0 não é tocado
- Todo o QC 1 roda em CPU, antes da GPU

**1 · Conversão de espaço de cor**  
- RGB → HSV; o canal S separa vidro de tecido
- Vidro: claro e dessaturado. Tecido: saturado
- Alternativa: densidade óptica (−log da intensidade)

**2 · Limiar de Otsu no canal S**  
- Limiar calculado por lâmina, não fixo global
- Absorve variação de exposição entre scanners
- Saída: máscara binária bruta

**3 · Morfologia**  
- Abertura remove poeira e ruído isolado
- Fechamento une fragmentos do mesmo corte
- Preenchimento de buracos (lúmen, adiposo)
- Kernel definido em µm e convertido por mpp

**4 · Componentes conexos**  
- Descarta fragmentos abaixo da área mínima
- Guarda bounding box de cada fragmento
- Nº de fragmentos é sinal clínico útil

**Filtro de artefatos**  
- Caneta: matiz fora da faixa de H&E
- Etiqueta, borda da lamínula, bolha grande
- Sombra de montagem e sujeira do vidro
- Sem esse filtro, tinta vira 'tecido'

**5 · Métricas da lâmina**  
- Área de tecido em mm² (não em pixels)
- Nº de fragmentos e maior fragmento
- % da área útil da lâmina

**Área ≥ limiar?** *(decisão)*  
- limiar por tipo de material

**QC_FAILED**  
- Motivo: material insuficiente
- Job encerrado antes de gastar GPU
- Aviso volta ao LIS para nova lâmina

**Máscara de tecido → tiling**  
- Máscara + bounding boxes
- Define onde a grade de patches é gerada

**Decisão em aberto — limiar em mm², não em %** — *PROPOSTA*  
- Biópsia endoscópica ocupa menos de 1% da lâmina
- Limiar percentual reprovaria material válido
- Calibrar por tipo: biópsia, peça cirúrgica, citologia
- Sem calibração, a taxa de QC_FAILED é imprevisível

Ligações: a0→a1 · a1→a2 · a2→a3 · a3→a4 · a4→a4b [matiz e forma] · a4→a5 · a5→a6 · a6→a7 [não] · a6→a8 [sim] · a8→a9

### QC fase 2 — as seis métricas por patch

**Entrada — patch no nível de trabalho**  
- Roda em CPU, antes de ocupar a GPU
- Rejeitar aqui economiza inferência

**1 · Fração de tecido no patch**  
- Máscara recalculada na resolução de trabalho
- Patch majoritariamente vidro é descartado
- Limiar típico entre 30% e 50% — a calibrar

**2 · Nitidez (foco)**  
- Variância do Laplaciano + Tenengrad (Sobel)
- Normalizar pelo percentil da própria lâmina
- Valor absoluto confunde textura densa com foco
- Corte relativo sobrevive à troca de scanner

**3 · Dobra de tecido**  
- Diferença entre saturação e luminância
- Dobra: mais escura e mais saturada que o entorno
- Dobra passa no teste de foco e engana o modelo

**4 · Artefatos**  
- Bolha: borda circular, interior sem textura
- Caneta: matiz fora da faixa de H&E
- Poeira, risco no vidro, borda da lamínula

**5 · Coloração**  
- Deconvolução de cor separa H e E
- Densidade óptica média de cada canal
- Detecta sub e sobrecoloração da lâmina

**6 · Redundância** — *PROPOSTA*  
- Patch quase idêntico ao vizinho agrega pouco
- Opcional: amostrar para cortar custo de GPU
- Não está no desenho atual

**Vetor de scores [K] por patch**  
- Os K valores vão inteiros para o .h5
- Permite auditar a rejeição depois do fato
- Base do alerta operacional ao laboratório

**Todos os limiares OK?** *(decisão)*  
- regra por métrica

**Patch descartado**  
- Motivo do descarte é contabilizado
- Não gasta GPU nem espaço no .h5

**Patch aceito**  
- Segue para normalização e extração

**Agregado da lâmina**  
- % rejeitado por motivo
- Acima do limite: alerta de re-scan
- Rejeição alta = scanner ou coloração

**Decisão em aberto — filtrar antes ou depois do Hibou?** — *PROPOSTA*  
- Antes (desenho atual): barato, mas mudar o limiar exige reprocessar a lâmina inteira
- Depois: guarda embedding de todo patch e filtra na inferência — flexível, custa GPU e storage
- Meio-termo: guardar embedding só dos patches na faixa de dúvida
- A escolha decide se calibrar QC é ajuste de config ou reprocessamento de acervo

Ligações: b0→b1 · b1→b2 · b2→b3 · b3→b4 · b4→b5 · b5→b6 · b6→b7 · b7→b8 · b8→b9 [não] · b8→b10 [sim] · b10→b11 [contagem por motivo] · b10→b12

### Extração de características — Hibou-L congelado

**Lote de patches aceitos**  
- Tamanho do lote limitado pelos 16 GB da T4
- Lote maior usa melhor a GPU e consome mais RAM

**1 · Pré-processamento**  
- Redimensiona para a entrada do modelo
- Normaliza por média e desvio do pré-treino
- Precisa ser idêntico ao usado no treino do Hibou

**2 · ViT-L/14**  
- Divide o patch em sub-patches de 14×14 px
- 24 blocos de atenção, dimensão interna 1024
- Pré-treino DINOv2 sobre lâminas de patologia
- Pesos congelados, hash registrado por versão

**3 · Agregação do token**  
- Token CLS ou média dos tokens → vetor 1024d
- A escolha precisa ser fixa e versionada
- Trocar depois invalida comparação com o acervo

**Saída — N × 1024 em fp16**  
- Única coisa que sai da GPU
- A imagem não é armazenada de novo

**Licença a auditar**  
- CellViT-Hibou-L: CC-BY-NC-SA-4.0
- Incompatível com uso comercial
- Confirmar a licença do peso em produção

**Versão no arquivo**  
- extractor_version grava no .h5
- É o que diz qual acervo reprocessar
- Sem isso, atualizar vira retrabalho cego

**Por que congelar compensa**  
- Um extrator só para todos os tenants: dado de um cliente não entra no modelo de outro
- Retreino consome .h5, não WSI — ciclo de horas em vez de semanas
- GPU vira custo único por lâmina, não por experimento
- Preço: nenhuma adaptação ao scanner ou à coloração de cada laboratório

Ligações: c0→c1 · c1→c2 · c2→c3 · c3→c4 · c2→c5 · c3→c6 · c4→c7

### ABMIL — como a predição da lâmina é formada

**Entrada — N × 1024 de um caso**  
- N = patches aceitos da lâmina
- Uma 'bolsa' de instâncias sem rótulo individual

**1 · Projeção**  
- Linear 1024 → D, ReLU e dropout
- D interno a definir (ordem de 256–512)
- Reduz custo e regulariza

**2 · Atenção com gate**  
- Ramo tanh(V·h) multiplicado por sigmoid(U·h)
- Score por patch; softmax sobre os N soma 1
- O gate deixa o modelo ignorar região irrelevante

**3 · Agregação**  
- z = Σ wᵢ · hᵢ — um vetor por lâmina
- O tamanho de N não muda a dimensão de z

**4 · Classificador**  
- Linear sobre z → logits → softmax
- Treinado só com o rótulo da lâmina (MIL)

**5 · Incerteza**  
- Entropia da distribuição de classes
- Margem entre as duas maiores probabilidades
- OOD: distância no espaço de embeddings

**Saídas**  
- Predição por lâmina
- wᵢ por patch → heatmap
- Escore de incerteza → encaminhamento

**Treino MIL**  
- Rótulo por lâmina, não por pixel
- Dispensa anotação manual exaustiva
- É o que torna o laudo assinado um rótulo

**Calibração ausente**  
- Softmax puro superestima confiança
- Temperature scaling ou predição conforme
- Sem isso, limiar clínico não se sustenta

**O que a atenção é e o que não é**  
- É onde o modelo concentrou peso para decidir — evidência visual para conferência
- Não é explicação causal nem marcação de lesão
- Não deve ser apresentada ao patologista como delimitação diagnóstica

Ligações: d0→d1 · d1→d2 · d2→d3 · d3→d4 · d4→d5 · d5→d6 · d2→d7 · d5→d8 · d6→d9

### Ciclo de vida do job — fila, retry e dead-letter

**QUEUED**  
- Mensagem na fila com job_id e tenant_id
- Idempotente: a mesma lâmina não gera dois .h5

**RUNNING**  
- Worker toma a mensagem (visibility timeout)
- Heartbeat de progresso enquanto processa
- Timeout precisa superar o pior tempo medido

**Resultado?** *(decisão)*  
- três saídas

**COMPLETED**  
- .h5 gravado e ponteiro no Postgres

**QC_FAILED**  
- Terminal e clínico, não técnico
- Precisa de aviso de volta ao LIS

**Tentativas < máx?** *(decisão)*  
- falha técnica

**Retry com backoff**  
- Volta para QUEUED com attempt+1
- Backoff exponencial evita tempestade

**DEAD_LETTER**  
- Exige alarme ativo
- Silêncio aqui significa caso perdido
- Reprocessamento manual após diagnóstico

**Três garantias que sustentam a fila**  
- Idempotência por job_id: reentrega nunca duplica trabalho
- Visibility timeout maior que o pior caso: evita dois workers na mesma lâmina
- Dead-letter com alarme: falha silenciosa é pior do que falha ruidosa

Ligações: e0→e1 · e1→e2 · e2→e3 [sucesso] · e2→e4 [sem tecido] · e2→e5 [falha técnica] · e5→e6 [sim] · e6→e0 [volta à fila] · e5→e7 [não] · e7→e8

### Arquivo .h5 — a unidade de trabalho do sistema

**Um arquivo por lâmina**  
- Escrita única do worker, leitura por todo o resto
- Grava em nome temporário e renomeia ao fim

**/embeddings — [N × 1024] float16**  
- Vetor do Hibou-L por patch aceito
- fp16 corta o armazenamento pela metade
- Validar impacto na acurácia antes de adotar

**/coordinates — [N × 2] int32**  
- X, Y em pixels do nível 0
- É o que reconstrói o heatmap sobre a imagem
- Sem elas, a atenção não volta ao espaço da lâmina

**/qc_scores — [N × K] float32**  
- As K métricas de QC daquele patch
- Permite auditar a rejeição sem reprocessar

**attrs — identidade e versões**  
- tenant_id, case_id, slide_id, wsi_sha256
- mpp, magnificação, tile_size, stride
- extractor, extractor_version, qc_version
- n_patches, n_rejected, created_at

**Escreve**  
- GPU Worker, uma vez por lâmina

**Lê na inferência**  
- API carrega em CPU, sem GPU
- Milissegundos por caso

**Lê no retreino**  
- Treino do ABMIL sem reabrir WSI
- Ciclo de horas, GPU quase zero

**O risco que mora aqui**  
- Trocar a versão do Hibou-L transforma todo o acervo em legado
- Sem extractor_version gravado, não há como saber o que reprocessar
- Custo do acervo pode superar a receita por lâmina — decidir retenção antes de escalar

Ligações: g0→g1 · g1→g2 · g2→g3 · g3→g4 · g1→g5 · g2→g6 · g4→g7 · g4→g8

### Roteador de modelos — e os caminhos de exceção que faltam

**Metadado de órgão do LIS**  
- Campo livre na maioria dos LIS
- A qualidade do dado decide a rota

**Órgão preenchido?** *(decisão)*  
- porta 1

**Exceção — não existe hoje** — *PROPOSTA*  
- Caso deveria ir a triagem manual
- Hoje o comportamento é indefinido

**Normalização do termo** — *PROPOSTA*  
- Dicionário de sinônimos e grafias
- 'gástrico', 'antro', 'estômago' → estomago
- Sem isso, o mesmo órgão vira rotas diferentes

**Há modelo para o órgão?** *(decisão)*  
- porta 2

**Caso segue sem IA** — *PROPOSTA*  
- A interface precisa dizer isso ao patologista
- Silêncio seria pior: parece que a IA concordou

**Versão ativa para o tenant**  
- Contrato pode congelar a versão do cliente
- Evita mudar resultado no meio de um caso
- Registro guarda quem aprovou cada versão

**Carrega o ABMIL do órgão**  
- Modelo pequeno, roda em CPU
- Inferência em milissegundos

**Por que este é o ponto frágil do desenho**  
- Todo o roteamento depende de um campo de texto do LIS do cliente
- Órgão errado escolhe o modelo errado e devolve predição confiante e inválida
- Nenhum dos caminhos de exceção acima existe no diagrama atual

Ligações: r0→r1 · r1→r2 [não] · r1→r3 [sim] · r3→r4 · r4→r5 [não] · r4→r6 [sim] · r6→r7 · r7→r8

### Governança de versão — do candidato à produção

**Modelo candidato**  
- Retreino da cabeça ABMIL sobre os .h5

**1 · Conjunto de teste travado**  
- Separado por caso e por laboratório
- Nunca usado em treino nem em seleção
- Vazamento aqui invalida toda a validação

**2 · Métricas**  
- Por classe, por órgão e por laboratório
- Sensibilidade priorizada sobre acurácia global
- Matriz de confusão por tipo de erro clínico

**3 · Não inferior à produção?** *(decisão)*  
- porta de aprovação

**Rejeitado**  
- Registra motivo e métricas
- Candidato fica no histórico

**4 · Aprovação registrada**  
- Quem aprovou, quando e com quais dados
- Hash dos conjuntos de treino e teste
- Base da trilha de auditoria

**5 · Sombra**  
- Roda em paralelo sem exibir resultado
- Compara com a versão ativa em casos reais

**6 · Canário — 1 tenant**  
- Liberação para um laboratório
- Métricas acompanhadas por período fixo

**7 · Liberação geral**  
- Versão ativa para todos os tenants
- Rollback de um passo, sempre disponível

**O que falta para isso ser defensável**  
- Protocolo de mudança predeterminado (tipo PCCP): o que muda sem nova validação clínica
- Monitoramento formal de drift: o desempenho cai devagar e ninguém percebe
- Auditoria de equidade por subgrupo demográfico
- Regra escrita de quando atualizar deixa de ser ajuste e vira produto novo

Ligações: v0→v1 · v1→v2 · v2→v3 · v3→v4 [não] · v3→v5 [sim] · v5→v6 · v6→v7 · v7→v8 · v8→v9

## 3. Todas as ligações do mapa principal

```
scanner -> ext   : WSI (.svs / .tiff / .mrxs)
lis -> ext   : case_id · órgão · tenant
ext -> api   : POST /v1/jobs
ext -> blobwsi   : upload com URL assinada
api -> db   : cria job · grava auditoria
api -> queue   : job_id · wsi_uri · tenant · organ
queue -> worker   : entrega 1 job
blobwsi -> worker   : leitura em streaming
worker -> load
load -> qc1
qc1 -> tissue
tissue -> fail   : não
tissue -> tiling   : sim
tiling -> qc2
qc2 -> patch
patch -> reject   : não
patch -> norm   : sim
norm -> hibou   : patches normalizados
hibou -> emb
emb -> consol
tiling -> consol   : coordenadas X/Y
qc2 -> consol   : scores de QC
consol -> h5   : escrita única do .h5
consol -> jobdone
jobdone -> db   : status do job · métricas de GPU
work -> fetch   : abre o caso
h5 -> fetch   : embeddings + coordenadas
fetch -> router
lismeta -> router   : órgão
models -> router   : versão ativa
router -> proj   : N × 1024d
proj -> att
att -> clas
clas -> outp
att -> heat   : pesos de atenção
outp -> heat   : predição
outp -> unc
unc -> normal   : alta confiança
unc -> uncert   : incerto
unc -> outlier   : anomalia
heat -> sign   : overlay na imagem
normal -> sign   : liberado para laudo
uncert -> alq
outlier -> hardq
alq -> review
hardq -> review
sign -> label   : laudo assinado = rótulo
review -> label
label -> aldata   : ground truth validado
aldata -> retrain   : só os .h5, sem reabrir WSI
retrain -> valid
valid -> deploy   : aprovado
deploy -> models   : nova versão em produção
```
