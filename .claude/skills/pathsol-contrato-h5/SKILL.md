---
name: pathsol-contrato-h5
description: Contrato do arquivo .h5 por lâmina na PathSolutions v3 — extractor_version, esquema, escrita segura, idempotência e testes de aceite do worker GPU. Use sempre que tocar no worker, na fila de jobs, em leitura de WSI, QC, tiling, extração Hibou-L, escrita ou leitura de .h5, heatmap por coordenadas, ou quando alguém sugerir mudar qualquer parâmetro da extração.
---

# Contrato do .h5 PathSolutions v3

O `.h5` é a unidade de trabalho do sistema: o worker escreve uma vez por lâmina e todo o resto lê. Os modelos ABMIL são treinados sobre um espaço de embeddings específico. Mudar qualquer parâmetro da extração muda esse espaço e invalida os modelos sem aviso: a predição continua saindo, confiante e errada. Por isso a extração é um contrato versionado.

Os valores e o porquê de cada regra estão no plano aprovado da Fase 2 (`docs/v3/02-plano-v3.md`, seções 4.1, 9.1 e 10), com as mudanças da decisão 5. Onde a spec diverge dessas seções, vale o plano.

## extractor_version

String canônica e determinística, composta por: sha256 dos pesos do Hibou-L, das configurações e dos `.py` do modelo (com pesos locais, só o hash fixa o código); pré-processamento (RGB, fator e filtro da reamostragem, média, desvio); normalização (`none` na v3, salvo decisão contrária do Pedro); token (CLS, sem os registradores); tamanho de patch, stride e mpp de trabalho; precisão de inferência e implementação da atenção. Os valores saem do plano (seção 10.2). Mudou qualquer um, é outra versão, e só com aprovação do Pedro.

- A string vai nos attrs, e um hash curto dela vai no caminho do blob.
- Precisão: fp16 por `torch.autocast`, só se uma amostra rodada também em fp32, antes do primeiro `.h5` do acervo, der cosseno por patch com média ≥ 0,999, sem NaN nem Inf. A saída é sempre float32.
- Se o processador oficial do Hibou-L divergir do pré-processamento do plano, a troca volta ao Pedro antes do primeiro `.h5`, com a atenção e a precisão.
- O worker falha se a classe carregada não for `Dinov2ModelWithRegisters` ou se a saída não tiver 261 tokens.
- As versões de torch, transformers, CUDA, Pillow, driver e o modelo da GPU vão nos attrs. Atualizar uma delas pede regressão (cosseno médio ≥ 0,999); se falhar, é outra versão.

## Mensagem da fila

`job_id`, `tenant_id`, `slide_id`, caminho do blob por UUID, código do órgão, tipo de material, `pipeline_version` e `attempt`. Só identificadores internos, porque a mensagem fica legível na dead-letter. O worker só processa se o `job_id` existir sob o `tenant_id` da mensagem, com a mesma lâmina e o mesmo blob; senão, manda a mensagem para a dead-letter sem processar. Idempotência, visibility timeout e dead-letter: plano, seção 9.1.

## Leitura da WSI

- O worker baixa a WSI para o disco temporário da VM2 e confere o sha256 do original com o do job, antes de qualquer ajuste. Lê por nível, em blocos, sem a lâmina inteira na RAM. A cópia é apagada no fim do job e na partida do worker, com teto no código.
- Leitor: OpenSlide ≥ 4.0.1, com a mesma função de abertura no worker e no serviço de tiles. Na v1, só `.svs`, um arquivo por lâmina, até 10 GiB; outro formato entra por scanner, depois que uma amostra abrir com níveis e mpp.
- mpp: o do nível 0 da lâmina, nunca o aumento nominal; entre 0,1 e 0,55 µm/px, com x e y a até 1% um do outro.
- Etiqueta e macro nunca são lidas, servidas nem registradas. Das propriedades, só saem do leitor as da lista de permissão (mpp, dimensões, níveis); o cabeçalho e o `openslide.barcode` podem ter o código de barras e nunca vão para log, banco nem `.h5`.
- Motic: só se a exportação de teste confirmar o cabeçalho "Motic" no layout Aperio, o worker e o cache de tiles trocam "Motic " por "Aperio" (6 bytes) numa cópia temporária. Conferem o cabeçalho antes e, depois, exigem dois níveis ou mais em ordem decrescente, os downsamples da conferência e o mpp do texto; senão, recusam. O sha256 é o do original, que não muda, e a cópia nunca volta ao storage. Sem a exportação, a troca não entra no código. Reserva: tiffslide com tifffile.

## Grade e QC

- QC 1, na miniatura (~2 a 8 µm/px), sem GPU: sem tecido, QC_FAILED "vidro vazio"; abaixo da área mínima do tipo de material, QC_FAILED "material insuficiente". Na citologia, o QC 1 só reprova vidro vazio.
- Grade a partir de (0, 0) do nível 0, sem sobreposição, com passo `round(224 × 0,5 / mpp)` px, reamostrado a 224 × 224 (0,50 µm/px). A coordenada é a do canto superior esquerdo.
- QC 2, por patch, na CPU, antes da GPU, a 0,50 µm/px: fração de tecido e foco (variância do Laplaciano e Tenengrad).
- Piso de extração: patch com 10% ou mais de tecido vai ao Hibou-L, e o `.h5` guarda os escores de todos esses. O limiar de uso (tecido e foco) fica na configuração versionada da cabeça, igual no treino e na inferência. O piso entra no `qc_version`.
- Foco, com parâmetros provisórios até a marcação de patches (plano, seções 10.5 e 15): patch fora de foco tem variância do Laplaciano, na luminância e só nos pixels de tecido, abaixo de 0,10 × o P90 da lâmina, contando só patches com mais de 50% de tecido. Com mais de 20% deles fora de foco, a lâmina termina em QC_FAILED "foco": sem Hibou-L, sem `.h5`, sem retry e fora do treino. Os escores vão para um arquivo no `slide-h5`, no caminho do `.h5`, com o `job_id` no nome. Abre-se um pedido de nova digitalização ("foco ou artefato"), no máximo 2 automáticos; a nova WSI é um job novo, ligado ao bloqueado. Abaixo de um mínimo de patches, fixado no `qc_version`, só alerta. Na citologia, o foco é gravado e não bloqueia.

## Estados terminais

Cada job termina num destes, e a soma de um lote fecha com o total. Só a falha técnica volta à fila.
- COMPLETED: `.h5` no Blob e ponteiro no banco.
- QC_FAILED com motivo ("vidro vazio", "material insuficiente" ou "foco"): sem `.h5`, sem retry.
- Formato não suportado, sem retry: o leitor não abre o arquivo; formato nativo do scanner; multiplano detectável; TIFF sem tiles ou sem pirâmide; Motic recusado na conferência; mpp fora da faixa, com o motivo "escala indisponível" visível para o laboratório.
- DEAD_LETTER: depois de 3 falhas técnicas.

## Esquema do arquivo

- `/embeddings` [N×1024] float32. Float16 é roadmap: só depois de medir o impacto nas cabeças ABMIL.
- `/coordinates` [N×2] int32, pixels do nível 0, canto superior esquerdo do patch.
- `/qc_scores` [N×K] float32, com as métricas de QC 2 da v1 (fração de tecido, variância do Laplaciano e Tenengrad) de cada patch extraído. Os nomes das colunas vão num attr.
- attrs: tenant_id, slide_id, wsi_sha256, mpp, mpp_source, reader (com versão), header_patch, tile_size e stride (em pixels do nível 0), extractor, extractor_version, qc_version, as versões de software e o modelo da GPU, p50 e p90 do foco da lâmina, n_patches, n_rejected (patches abaixo do piso de tecido), created_at.

## Escrita segura

Blob não tem rename atômico. O commit é o ponteiro no banco:

1. Gerar o `.h5` em disco local temporário e validar shapes e attrs.
2. Enviar ao Blob em caminho definitivo `tenant/slide/extractor_version/`, com o nome `<job_id>.h5`.
3. Conferir tamanho e checksum do blob enviado.
4. Só então gravar ponteiro e status COMPLETED no Postgres, na mesma transação.
5. Apagar o temporário local. O worker não acumula arquivos em disco.

Blob sem ponteiro é ignorado por todos os leitores. Reentrega de um `job_id` que já tem ponteiro encerra sem reprocessar. O retry do mesmo job regrava o mesmo nome; um job novo da mesma lâmina (por exemplo, com outro `qc_version`) grava outro blob e nunca sobrescreve um `.h5` com ponteiro.

## Leitura

A API compara o `extractor_version` do `.h5` com a versão ativa. Se diferir, marca a lâmina para reprocessamento e não roda inferência.

## Testes de aceite

Gates (decisão do Pedro em 15/10/2026):
- a Fase 4 fecha com os testes 1 a 5, 8 e 9, mais uma conferência simples do 6: a grade de patches desenhada sobre a miniatura da lâmina, num PNG que o Pedro olha;
- o teste 7 fecha na Fase 5;
- o teste 6 completo, no viewer, fecha na Fase 6.

Rodar em lâminas escolhidas com o Pedro, com a origem e o envio ao storage da v3 definidos no plano aprovado da Fase 2: pelo menos dois órgãos e uma lâmina difícil.

1. **Reprodutibilidade:** processar a mesma lâmina duas vezes dá o mesmo conjunto de patches extraídos e similaridade de cosseno por patch com média ≥ 0,999.
2. **Idempotência:** reentregar a mesma mensagem não cria segundo `.h5` nem segundo registro.
3. **Falha no meio:** matar o worker durante a escrita não deixa ponteiro gravado; o reprocessamento conclui normalmente, regravando o mesmo nome.
4. **Retry e dead-letter:** um job que falha por erro técnico volta com backoff; depois do máximo de tentativas vai para dead-letter e o alarme dispara de verdade.
5. **Sem tecido:** lâmina sem tecido termina em QC_FAILED "vidro vazio", sem usar GPU.
6. **Alinhamento:** as coordenadas desenhadas sobre o viewer caem no tecido. O Pedro confere visualmente em três lâminas.
7. **Versão:** um `.h5` com `extractor_version` diferente é recusado na inferência e marcado para reprocessar.
8. **Disco:** depois de processar todas as lâminas de teste, o disco do worker volta ao tamanho inicial.
9. **Foco:** cópias de uma lâmina nítida com borrão sintético forte em parte do tecido (Kohlberger 2019), geradas só no disco local da VM2, num diretório com teto no código e apagado no fim: a cópia com mais de 20% dos patches borrados termina em QC_FAILED "foco", sem `.h5` e com os escores gravados fora dele; a original segue para extração. A lâmina difícil passa pela mesma regra, e o resultado vai ao relatório.

Registre os resultados em `docs/v3/aceite-worker.md`. Falha em qualquer item bloqueia a fase em que ele fecha e exige diagnóstico antes de correção.
