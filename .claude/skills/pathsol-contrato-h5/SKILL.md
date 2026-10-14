---
name: pathsol-contrato-h5
description: Contrato do arquivo .h5 por lâmina na PathSolutions v3 — extractor_version, esquema, escrita segura, idempotência e testes de aceite do worker GPU. Use sempre que tocar no worker, na fila de jobs, em leitura de WSI, QC, tiling, extração Hibou-L, escrita ou leitura de .h5, heatmap por coordenadas, ou quando alguém sugerir mudar qualquer parâmetro da extração.
---

# Contrato do .h5 PathSolutions v3

O `.h5` é a unidade de trabalho do sistema: o worker escreve uma vez por lâmina e todo o resto lê. Os modelos ABMIL são treinados sobre um espaço de embeddings específico. Mudar qualquer parâmetro da extração muda esse espaço e invalida os modelos sem aviso: a predição continua saindo, confiante e errada. Por isso a extração é um contrato versionado.

## extractor_version

String determinística composta por: sha256 dos pesos do Hibou-L, pré-processamento (resize, média, desvio), normalização (`none` na v3, salvo decisão contrária do Pedro), agregação do token (CLS ou média), tamanho de patch, stride, mpp de trabalho, precisão de inferência. Os valores saem do plano aprovado na Fase 2. Mudou qualquer um, é outra versão, e só com aprovação do Pedro.

## Esquema do arquivo

- `/embeddings` [N×1024] float32. Float16 é roadmap: só depois de medir o impacto nas cabeças ABMIL.
- `/coordinates` [N×2] int32, pixels do nível 0.
- `/qc_scores` [N×K] float32, com as métricas de QC 2 da v1 (fração de tecido e foco). Os nomes das colunas vão num attr.
- attrs: tenant_id, case_id, slide_id, wsi_sha256, mpp, magnification, tile_size, stride, extractor, extractor_version, qc_version, n_patches, n_rejected, created_at.

## Escrita segura

Blob não tem rename atômico. O commit é o ponteiro no banco:

1. Gerar o `.h5` em disco local temporário e validar shapes e attrs.
2. Enviar ao Blob em caminho definitivo `tenant/slide/extractor_version/`.
3. Conferir tamanho e checksum do blob enviado.
4. Só então gravar ponteiro e status COMPLETED no Postgres, na mesma transação.
5. Apagar o temporário local. O worker não acumula arquivos em disco.

Blob sem ponteiro é ignorado por todos os leitores. Reentrega de um `job_id` que já tem ponteiro encerra sem reprocessar.

## Leitura

A API compara o `extractor_version` do `.h5` com a versão ativa. Se diferir, marca a lâmina para reprocessamento e não roda inferência.

## Testes de aceite (gate da Fase 5)

Rodar em lâminas escolhidas com o Pedro: pelo menos dois órgãos e uma lâmina difícil.

1. **Reprodutibilidade:** processar a mesma lâmina duas vezes dá o mesmo conjunto de patches aceitos e similaridade de cosseno por patch com média ≥ 0,999.
2. **Idempotência:** reentregar a mesma mensagem não cria segundo `.h5` nem segundo registro.
3. **Falha no meio:** matar o worker durante a escrita não deixa ponteiro gravado; o reprocessamento conclui normalmente.
4. **Retry e dead-letter:** um job que falha por erro técnico volta com backoff; depois do máximo de tentativas vai para dead-letter e o alarme dispara de verdade.
5. **Sem tecido:** lâmina sem tecido termina em QC_FAILED, sem usar GPU.
6. **Alinhamento:** as coordenadas desenhadas sobre o viewer caem no tecido. O Pedro confere visualmente em três lâminas.
7. **Versão:** um `.h5` com `extractor_version` diferente é recusado na inferência e marcado para reprocessar.
8. **Disco:** depois de processar todas as lâminas de teste, o disco do worker volta ao tamanho inicial.

Registre os resultados em `docs/v3/aceite-worker.md`. Falha em qualquer item bloqueia a fase e exige diagnóstico antes de correção.
