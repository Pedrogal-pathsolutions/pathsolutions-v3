# Missão: PathSolutions v3

Leia `CLAUDE.md`, `docs/arquitetura/arquitetura-pathsolutions_spec.md` e `docs/v3/02-plano-v3.md` antes de qualquer ação.

## Contexto

A PathSolutions é um SaaS de pré-laudo assistido por IA para laboratórios de patologia. A subscrição é da empresa, contratada via parceiro CSP (Microsoft Azure Plan, cobrança por uso).

A v3 é escrita do zero, seguindo a arquitetura de referência em `docs/arquitetura/`: VM1 como plano de controle (CPU) e VM2 como worker GPU, que é a divisão da spec. O legado foi desligado e apagado inteiro na Fase 1, inclusive banco, caches e as WSIs do Blob. Só o código ficou no GitHub, com tag. A v3 começa vazia.

O plano aprovado na Fase 2 (`docs/v3/02-plano-v3.md`) diz como as Fases 3 a 8 constroem. As decisões 1 a 7 valem como registradas abaixo, e os padrões 1 a 27 da seção 23.2, como estão no plano. Nos desvios da spec aprovados pela decisão 5, vale o plano.

## Critério de pronto da v1: go-live sem IA

A v1 entra no ar sem IA. A cabeça gástrica vem depois do go-live, na Fase 7. Para ela entrar sem retrabalho, o go-live já tem tudo o que a IA vai consumir.

1. Fluxo principal de ponta a ponta: extensão → upload direto ao Blob por SAS → `POST /v1/jobs` idempotente → fila → worker GPU (QC 1, tiling, QC 2 com fração de tecido e foco, Hibou-L) → `.h5` → COMPLETED → o workspace abre o caso e mostra a lâmina, com a grade de patches do `.h5` na camada de overlay. O heatmap usa essa camada quando houver cabeça aprovada (Fase 7).
2. Fila com as três garantias da spec: idempotência por `job_id`, visibility timeout maior que o pior tempo medido e dead-letter com alarme.
3. Isolamento entre laboratórios: login próprio com TOTP (padrão 3), tenant pelo JWT, RLS forçada e os testes da skill `pathsol-isolamento-tenant` passando.
4. Worker GPU ativo: toda lâmina aceita pelo QC vira `.h5` com `extractor_version` (padrão 5).
5. Roteador e registro de modelos no ar, com zero modelos. Toda lâmina segue sem IA, e a interface diz o motivo: sem modelo para o órgão, órgão não informado, órgão não reconhecido, material misto ou material inelegível (padrão 17).
6. Workspace com viewer de deep zoom, camada de overlay, revisão e assinatura. A assinatura grava o diagnóstico na taxonomia fixa do órgão (`estomago@1.0.0`; fora do estômago, "sem taxonomia"), a versão do modelo ativa ("nenhum") e se a IA foi vista. Código novo; o visual segue `docs/v3/referencia-visual.md`.
7. Trilha de auditoria de acesso por caso (quem abriu, quando, o quê) e aviso de QC_FAILED ao laboratório, com o motivo, no workspace e na extensão.
8. Operação: todo cache com teto, alertas de disco e de dead-letter, orçamento com alertas, VM2 desalocada com a fila vazia, aviso de indisponibilidade fora da VM1 (padrão 26) e backup do banco com restauração testada.

Tudo o mais é roadmap: registre em `docs/v3/roadmap.md` e não construa. Isso inclui filas de aprendizado ativo e de hard case, retreino automático, métricas 3 a 6 do QC 2, níveis de incerteza e detecção de outlier, sombra e canário, embeddings em float16, LoRA, taxonomia e cabeça de citologia, LIS além do PathoWeb e qualquer uso de API de LLM.

### Depois do go-live

Não fazem parte do go-live. Entram depois dele, cada um no gate da fase em que entrar:
- manifesto, CLI com desidentificação e envio do conjunto de treinamento (plano, seções 12 e 16);
- marcação dos patches de foco e calibração do corte (seção 15); até lá vale o corte relativo por lâmina;
- gravar no PathoWeb, falhando fechado;
- heatmap na camada de overlay, com a primeira cabeça aprovada.

## Decisões do Pedro

Antes da Fase 2:
- D1. Rótulos e anotações do legado: não exportar. O legado inteiro foi apagado.
- D2. Normalização de cor: sem Macenko.
- D3. Teto mensal de gasto da subscrição: R$ 5.000. Revisto com o volume (decisão 1).
- D4. Referência visual: valores extraídos do código do legado, sem capturas de tela.

Da Fase 2 (texto completo no plano, seção 23.1):
1. **Retenção:** WSI em Cold 30 dias depois do upload, mantida; redundância ZRS; retenção legal em cada container de WSI desde a Fase 3, antes do primeiro upload; `.h5` em Cool depois de 90 dias. Exclusão de WSI só por decisão nova do Pedro, por tenant. Revisar antes de ~1.000 lâminas/mês ou com o total acima de 70% do teto.
2. **Discos:** letra (a). Vale como pedido explícito de exclusão do P20 da VM1 e do P15 da VM2; cada exclusão ainda pede autorização na hora.
3. **VM1:** D8s_v5 na construção, com auto-shutdown às 23:00 de Brasília e o da VM2 às 23:30, mudados na Fase 3 com autorização. O tamanho e o horário de produção saem do teste de carga antes do go-live.
4. **Terraform:** roda com o login do `az` do Pedro, só durante o plan e o apply, com `az logout` no fim; nunca com a identidade gerenciada da VM1. O `codex` sai da VM1. O apply roda num terminal SSH comum, pelas mãos do Pedro, com o plano salvo e o Antigravity fechado.
5. **Contrato do `.h5` e spec:** aprovadas as 7 mudanças da seção 10.6 do plano. A troca de 6 bytes do SVS da Motic só vale se a exportação de teste confirmar o cabeçalho Motic no layout Aperio.
6. **Jurídico:** parecer e autorizações contratados logo após o APROVADO FASE 2. Nenhuma lâmina de laboratório com tecido chega à VM1 nem ao storage antes do gate; até lá, o aceite usa lâminas públicas e a lâmina em branco.
7. **Fases e gates:** aprovadas as mudanças da seção 19.4 do plano; estão incorporadas nas fases abaixo.

## Regras de execução

Ordem das fases: 3 → 4 → 5 → 6 → 8 (go-live sem IA) → 7 (cabeça gástrica). Cada fase termina com um relatório em `docs/v3/` e a frase `PARADO — aguardando APROVADO FASE N`. Não avance sem essa aprovação escrita.

Todo relatório traz: o que foi feito; evidências (comando e saída resumida); o que não foi possível verificar; riscos; decisões pedidas ao Pedro. "Não verifiquei" é uma resposta aceitável. Afirmar sem evidência não é.

Nas fases de construção:
- Uma fase pode levar várias sessões. Cada sessão executa só a fase indicada pelo Pedro e retoma pelo relatório parcial da fase e pelo git.
- Trabalhe por fatias, na ordem do plano (seção 19.2). Cada fatia termina com os testes passando, commit e push.
- Sem pesquisa ampla e sem rodada de revisão adversarial. Vai ao Pedro só a dúvida que bloqueia a fase, contraria o plano ou muda o custo em mais de R$ 300/mês. O resto segue o padrão do plano e fica registrado no relatório.
- O relatório da fase é curto. O detalhe fica no código, nos testes e no git.
- Respeite o auto-shutdown da VM1 (20:00 de Brasília até a mudança da decisão 3; depois, 23:00): pare, salve e faça commit 30 minutos antes.

## Fases

### Fases 0, 1 e 2: concluídas

- Fase 0, ambiente: aprovada em 15/10/2026. Relatório: `docs/v3/00-ambiente.md`.
- Fase 1, desligamento e apagamento do legado: de 15 a 19/10/2026. Relatório: `docs/v3/01-desligamento.md`.
- Fase 2, plano: aprovada em 27/10/2026. Relatório: `docs/v3/02-plano-v3.md`.

### Fase 3 — Base de infraestrutura

Use a skill `pathsol-infra`. Fatias e testes: plano, seção 19.2. Em resumo:
1. Decisão 4 aplicada antes do primeiro apply.
2. Terraform instalado na VM1, com autorização, e estado remoto; orçamento e action group logo depois.
3. Storage: container de WSI por tenant com retenção legal antes de qualquer upload, papel sem exclusão, trava e alertas de activity log; fila e dead-letter; conta do status; Key Vault; Log Analytics e alertas.
4. VM2 ligada pela primeira vez; discos da decisão 2 antes de qualquer `docker pull`.
5. VMs, uma ação por autorização: identidade da VM2, agente de monitoramento, tetos de logs; sobras do legado e NSG na ordem da seção 4.5 do plano, e só depois nginx e certificado novos; unit do status; runbook (padrão 27); auto-shutdown (decisão 3 e padrão 11).
6. Postgres, backup e restauração.
7. Testes da seção 19.2.
8. Quando a exportação de teste do Motic chegar, o leitor de metadados confere a lâmina e decide o caminho de leitura (seção 4.1; decisão 5).

Gate: restauração do banco testada; alertas disparados de verdade; proteção das WSIs testada (sobrescrever e apagar com cada identidade; os passos que apagam são feitos pelo Pedro).

### Fase 4 — Worker GPU e acervo `.h5`

Use as skills `pathsol-contrato-h5` e `pathsol-isolamento-tenant`.
- Primeiro, atualize a skill `pathsol-contrato-h5` com as mudanças da decisão 5 e mostre o diff ao Pedro antes de escrever código.
- Fatias: plano, seção 19.2, começando pelo benchmark na VM2.
- Lâminas de aceite: plano, seção 17. Lâmina de laboratório com tecido só depois do gate jurídico (decisão 6); antes dele, lâminas públicas e a lâmina em branco.
- Exceção aprovada à regra do `CLAUDE.md` sobre o `tenant_id`: o produtor de jobs de teste roda sem JWT, só na VM1, pelo operador e sem porta de rede, e sai do código na Fase 5.

Gate: testes 1 a 5 e 8 da skill; PNG da grade de patches do teste 6; visibility timeout fixado pelo pior tempo medido; teste 3 de isolamento; teste da mensagem forjada; prova do liga e desliga da VM2.

### Fase 5 — API, banco e roteador

Use as skills `pathsol-isolamento-tenant` e `pathsol-contrato-h5`. Fatias na ordem da seção 19.2 do plano: login e tenants com TOTP; SAS e `POST /v1/jobs`; casos e lâminas; tiles; roteador e registro de modelos vazio, com os estados "sem IA"; `extractor_version` ativa; assinatura gravando o rótulo; trilha de auditoria, com a retenção do log definida aqui; aviso de QC_FAILED.

Toda rota nova com os quatro testes de isolamento. Migrações só aditivas. A taxonomia `estomago@1.0.0` fica fixa antes da fatia de assinatura.

Gate: isolamento por rota; teste 7 da skill `pathsol-contrato-h5`.

### Fase 6 — Workspace e extensão

Workspace e extensão escritos do zero. Antes de começar, leia `docs/v3/referencia-visual.md` e reproduza as cores, a tipografia, as telas, os fluxos e os atalhos com código novo. Melhorias visuais vão para o roadmap.

Fatias na ordem da seção 19.2 do plano: moldura e dashboard; viewer com a camada de overlay, exercitada pela grade de patches; revisão e assinatura na taxonomia; estados "sem IA"; extensão com upload, status, "sem IA" e aviso de QC_FAILED; aviso de indisponibilidade. A extensão lê o caso do PathoWeb e falha fechada. Na v1, nada é gravado no LIS.

Gate: teste 6 completo da skill `pathsol-contrato-h5`, com a grade de patches no lugar do heatmap.

### Fase 8 — Go-live sem IA

- Critérios 1 a 8 conferidos um a um.
- Alarmes testados de verdade: disco, dead-letter e orçamento.
- Teste de carga e escolha do tamanho e do horário de produção da VM1 (decisão 3).
- Parecer jurídico e contrato de cada laboratório assinados antes da primeira lâmina de paciente (decisão 6).
- Aceite da Diagnose.
- Soft delete do storage ligado no MVP, quando o Pedro confirmar que as lâminas e os casos corretos estão carregados, por Terraform e com plano aprovado.

### Depois do go-live

Os itens da lista "Depois do go-live", cada um com o gate da fase em que entrar. O envio do conjunto segue a seção 16 do plano: primeiro um lote piloto e depois o resto, com a citologia por último, sem rótulo.

### Fase 7 — Cabeça gástrica

Começa quando as contagens chegarem ao mínimo do plano (seção 13) e houver base legal para treinar com casos de produção (decisão 6).
1. Rótulos da assinatura em produção, do conjunto enviado e dos dados públicos (padrão 20), cada um ligado à sua lâmina, com a origem registrada. Relatório de cobertura por órgão e classe, com o motivo de cada exclusão.
2. Contagens por classe, caso e laboratório contra o mínimo (padrão 19).
3. Antes de abrir o teste, o Pedro fixa a métrica primária e o mínimo de acertos (seção 14). O conjunto de teste é separado por caso e por laboratório antes de qualquer treino e travado (hash da lista).
4. Treino na VM2 como job da fila, com heartbeat e tempo máximo. Métricas por classe e por laboratório. O modelo fica como candidato até a aprovação do Pedro. Ativar é registrar a versão; a partir daí, o heatmap usa a camada de overlay.

## Comece agora

Confirme em até dez linhas o que entendeu da missão e das regras. Depois execute a fase indicada pelo Pedro.
