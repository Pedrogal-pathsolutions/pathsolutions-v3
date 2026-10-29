# Roadmap — fora da v1

O `PROMPT_V3.md` define a v1. O que fica de fora vem para cá e não é construído. Cada item traz a origem. Entrar na v1 depende de decisão do Pedro.

Criado na Fase 2 (20/10/2026) e revisto em 27/10/2026. "Plano" quer dizer `docs/v3/02-plano-v3.md`.

## Itens que o `PROMPT_V3.md` põe no roadmap

| Item | Origem |
|---|---|
| Fila de aprendizado ativo e fila de hard case | `PROMPT_V3.md`; spec, blocos `alq` e `hardq` |
| Retreino automático | `PROMPT_V3.md`; spec, bloco `retrain` |
| Métricas 3 a 6 do QC 2: dobra, artefatos, coloração e redundância | `PROMPT_V3.md`; spec, sub-fluxo do QC 2 |
| Níveis de incerteza e detecção de outlier | `PROMPT_V3.md`; spec, blocos `unc` e `outlier` |
| Sombra e canário | `PROMPT_V3.md`; spec, bloco `deploy` |
| Embeddings em float16 (medir o impacto nas cabeças antes) | `PROMPT_V3.md`; skill `pathsol-contrato-h5` |
| LoRA | `PROMPT_V3.md` |
| Citologia: taxonomia, cabeça e calibração do QC. Na v1, as lâminas de citologia passam pelo pipeline e viram `.h5`, sem rótulo (plano, seções 10.6 e 12.1). O Pedro quer a citologia logo depois do estômago. | `PROMPT_V3.md`; respostas do Pedro de 20 e 26/10 |
| LIS além do PathoWeb (PathoWatch e outros) | `PROMPT_V3.md` |
| Qualquer uso de API de LLM | `PROMPT_V3.md`; `CLAUDE.md` |

## Itens vindos do plano da Fase 2

| Item | Origem e condição |
|---|---|
| Órgãos além do estômago (por exemplo, cólon e reto, esôfago, duodeno, pele, mama, próstata, colo uterino, endométrio, vesícula, tireoide e linfonodo). A taxonomia de cada um segue o método do plano, seção 11. Toda lâmina já vira `.h5` desde o go-live (plano, padrão 5). | Respostas do Pedro de 20 e 26/10 |
| Segunda cabeça para o estômago: H. pylori binário em H&E (Teng 2025, PMC12187772: ABMIL com AUC 0,920 a 20×, em 1.020 lâminas, com IHQ como referência). Exige IHQ ou Giemsa como referência e muda a regra de um modelo por órgão da spec. | Plano, seção 11 |
| Saída multirrótulo por achado (atividade, atrofia, metaplasia), no lugar do softmax único | Plano, seção 11; foge da spec (softmax) |
| Formatos multiarquivo: MRXS e DICOM | Plano, seção 4.1 |
| Leitura nativa de `.kfb` (kfbslide, MIT) ou suporte oficial do OpenSlide (PR #669), como contingência se o KFBio não gravar SVS; testes de referência contra o SVS da mesma lâmina | Plano, seção 4.1 |
| Doar a exportação em branco do Motic (CC0) ao issue #228 do OpenSlide, se o Pedro e a Diagnose autorizarem; se o OpenSlide passar a reconhecer a Motic, a troca de bytes sai do código | Plano, seção 4.1 |
| Archive e smart tier para as WSIs. Archive é offline e reprocessar o acervo levaria meses; o smart tier não tem compatibilidade documentada com a retenção legal | Plano, seção 6.2 |
| Exportar o activity log por mais de 90 dias, para guardar a prova de quem tirou uma retenção (custo a estimar) | Plano, seção 6.4 |
| Logs de recurso do storage (operações do Blob) no Log Analytics, para ver tentativas negadas no plano de dados e as de identidades sem permissão, que o activity log não mostra (custo de ingestão a estimar) | Fase 3, fatia 8 (`docs/v3/03-base-infra.md`, riscos) |
| Desacoplar o worker do Postgres: resultado no Blob e numa fila de retorno, conciliado pela API. Gatilho: VM2 acima de ~250 h/mês ou fila esperando mais de 20 h. Muda o protocolo de commit da skill `pathsol-contrato-h5` | Plano, seção 8.4; padrão 7 |
| Serviço de tiles lendo por faixa do Blob, no lugar da cópia integral. Gatilho: acima de ~1.000 lâminas/mês | Plano, seção 6.1 |
| VM2 Spot (−69% por hora). Exige recriar a VM2 e cota Spot de pelo menos 4 vCPUs | Plano, seção 8.4 |
| Segunda GPU ou aumento da cota T4. Gatilho: VM2 acima de ~600 h/mês | Fase 0, item 10; plano, padrão 7 |
| Reserva ou savings plan. Gatilho: VM2 acima de ~430 h/mês; VM1 depois de medir o uso real; venda pelo parceiro CSP não verificada | Plano, seções 5.4 e 8.4 |
| Aviso ao LIS de QC_FAILED e de pedido de nova digitalização, gravado no PathoWeb. Na v1, o aviso aparece no workspace e na extensão; gravar no PathoWeb fica para depois do go-live | spec, blocos `tissue` e `fail`; plano, seção 19 |
| Classificador leve de foco treinado com os patches marcados, no lugar do corte por limiar | spec, bloco `patch`; plano, seção 15 |
| Calibração de foco com z-stack | Plano, seção 15 |
| Domínio próprio com HTTPS para a página de status (exige CDN ou Front Door) | Plano, seção 18 |
| Melhorias visuais em relação ao legado: legenda e barra de cores do heatmap, controle de opacidade e de limiar, correção das divergências de cor e de limiares registradas na referência visual | `docs/v3/referencia-visual.md`; regra da Fase 6 |
| MFA por TOTP, se o Pedro tirar da v1 o padrão 3 do plano | Plano, seção 4.3 |
