# Missão: PathSolutions v3

Leia `CLAUDE.md` e `docs/arquitetura/arquitetura-pathsolutions_spec.md` antes de qualquer ação.

## Contexto

A PathSolutions é um SaaS de pré-laudo assistido por IA para laboratórios de patologia. O sistema atual (legado) roda na subscrição da empresa, contratada via parceiro CSP (Microsoft Azure Plan, cobrança por uso): VM1 com viewer, API, banco e tiles; VM2 com GPU T4; Blob com as WSIs.

A v3 é escrita do zero, seguindo a arquitetura de referência em `docs/arquitetura/`. Nenhum código, comentário ou configuração do legado entra na v3. O legado será desligado e apagado inteiro, e as duas VMs passam a hospedar a v3: VM1 como plano de controle (CPU) e VM2 como worker GPU, que é a divisão da spec. O apagamento inclui banco, caches, dumps e as WSIs do Blob (decisão do Pedro em 15/10/2026). A v3 começa vazia: as lâminas e os casos de treinamento serão enviados pelo fluxo novo quando a v3 estiver de pé.

## Critério de pronto da v1

1. O fluxo principal da spec funciona de ponta a ponta: extensão → upload direto ao Blob por SAS → `POST /v1/jobs` idempotente → fila → worker GPU (QC 1, tiling, QC 2 com fração de tecido e foco, Hibou-L) → `.h5` → COMPLETED → o workspace abre o caso, mostra a lâmina e o heatmap.
2. A fila tem as três garantias da spec: idempotência por `job_id`, visibility timeout maior que o pior tempo medido e dead-letter com alarme.
3. Isolamento entre laboratórios: tenant pelo JWT, RLS forçada e os testes da skill `pathsol-isolamento-tenant` passando.
4. O roteador trata as exceções: órgão vazio, sinônimos e órgão sem modelo. Nesses casos o caso segue sem IA, e a interface diz isso.
5. Cabeças ABMIL só para os órgãos com rótulos suficientes. O mínimo de rótulos por classe, caso e laboratório é definido na Fase 2; a lista de órgãos sai na Fase 7, das contagens do conjunto enviado. Cada cabeça é validada em conjunto de teste travado e só é ativada com aprovação do Pedro. Sem rótulos, a v1 sai com o pipeline completo e todos os casos seguem sem IA.
6. Workspace com viewer de deep zoom, overlay de heatmap, revisão e assinatura. Código novo; o visual segue os valores visuais extraídos do código do legado na Fase 1.
7. Operação: todo cache com teto, alertas de disco e de dead-letter, orçamento com alertas, VM2 desalocada quando a fila está vazia.
8. Envio do conjunto de treinamento pelo fluxo novo.

Tudo o mais é roadmap. Registre em `docs/v3/roadmap.md` e não construa. Isso inclui explicitamente: filas de aprendizado ativo e de hard case, retreino automático, métricas 3 a 6 do QC 2 (dobra, artefatos, coloração, redundância), níveis de incerteza e detecção de outlier, sombra e canário, embeddings em float16, LoRA, citologia, LIS além do PathoWeb e qualquer uso de API de LLM.

## Decisões do Pedro

- D1. Rótulos e anotações do legado: não exportar. O legado inteiro é apagado (15/10/2026).
- D2. Normalização de cor: confirmo, sem Macenko.
- D3. Teto mensal de gasto da subscrição: R$ 5000
- D4. Referência visual do legado: extrair do código os valores visuais (cores, fontes, telas, atalhos), sem capturas de tela.

D1 e D4 são necessárias antes da Fase 1, porque depois dela não há volta. D2 e D3, antes da Fase 2.

Respostas do Pedro em 15/10/2026 a itens da seção 16 do relatório da Fase 0:
- item 0: o Pedro avisa a Diagnose em 15/10 e pede que desativem a extensão Chrome do legado;
- item 9: o Terraform é instalado na VM1 na Fase 3, com autorização;
- item 10: o aumento da cota T4 só é pedido se o plano da Fase 2 pedir.

## Regras de execução

Trabalhe em fases. Cada fase termina com um relatório em `docs/v3/` e a frase `PARADO — aguardando APROVADO FASE N`. Não avance sem essa aprovação escrita.

Todo relatório traz: o que foi feito; evidências (comando e saída resumida); o que não foi possível verificar; riscos; decisões pedidas ao Pedro. "Não verifiquei" é uma resposta aceitável. Afirmar sem evidência não é.

**Cada sessão executa só a fase indicada pelo Pedro.**

## Fases

### Fase 0 — Ambiente (somente leitura)

Concluída e aprovada em 15/10/2026. Relatório: `docs/v3/00-ambiente.md`.

- `az account show`: confirme nome e ID da subscrição e preencha o ID no `CLAUDE.md`. Essa é a única escrita da fase, além do relatório.
- Recursos (`az resource list -o table`) e o grupo de cada um.
- VM1 e VM2: estado, tamanho, discos e uso (`df -h`). Na VM2, via ssh (pede confirmação), registre também `nvidia-smi` e as versões do driver e do CUDA.
- WSIs no Blob: storage account, container, quantidade, tamanho total e formatos por extensão. Só números; nomes de blob podem conter número de caso e não entram no relatório.
- O que roda hoje nas duas VMs (`docker ps -a`, units do systemd, crontabs), só os nomes. Onde está o código do legado e o remoto git dele.
- Cota da família NCASv3_T4 em `brazilsouth`.
- Ferramentas instaladas: terraform, az, docker, python, node, psql, git. Não instale nada.
- Custo mensal dos últimos três meses por recurso, se a CLI permitir.

### Fase 1 — Desligar e apagar o legado

Use a skill `pathsol-desligamento-legado`, que traz a sequência:
1. tag e push do código;
2. valores visuais extraídos do código;
3. exclusão da storage account do legado pelo Pedro, conferida por você;
4. parada e remoção de tudo do legado nas duas VMs;
5. `/data` das duas VMs e pastas do legado no disco de SO apagados;
6. órfãos excluídos;
7. VM2 fora do `TurnOn-VMs` e desalocada.

Uma ação por autorização, com registro em `docs/operacao/`. Sem snapshots: o que for apagado não tem volta, exceto o código, que fica no GitHub com tag.

Relatório: `docs/v3/01-desligamento.md`.

### Fase 2 — Plano da v3 (sem código, sem infraestrutura)

- Stack e estrutura do repositório.
- Distribuição dos componentes entre VM1, VM2 e recursos novos, com custo mensal de cada recurso novo e o total comparado ao custo atual.
- Postgres: opções (container na VM1 com disco próprio, ou servidor gerenciado), com custo e risco.
- Mecanismo para ligar a VM2 quando chega job e desalocar quando a fila esvazia, com opções e custo.
- Taxonomia fixa de classes por órgão. O Pedro aprova a taxonomia.
- Formato de entrada do conjunto de treinamento: como cada caso enviado pelo fluxo novo traz órgão, laboratório e rótulo na taxonomia, e como o rótulo se liga à lâmina.
- Mínimo de rótulos por classe, caso e laboratório para treinar uma cabeça ABMIL, e a previsão das contagens do conjunto de treinamento a ser enviado, por órgão, classe, caso e laboratório, informada pelo Pedro. Se um órgão não tiver rótulos para treinar, diga se eles servem como conjunto de teste para um modelo treinado em dataset público.
- Calibração do limiar de foco do QC 2: de onde vêm os rótulos de foco, já que nada é exportado do legado.
- Plano de envio do conjunto de treinamento pelo fluxo novo: volume, ordem e conferência.
- Lâminas dos testes de aceite do worker (gate da Fase 4): origem (envio pelo Pedro ou dataset público com licença conferida), quantidade, órgãos e como chegam ao storage da v3, já que a API (Fase 5) e a extensão (Fase 6) ainda não existem na Fase 4.
- Ordem das fatias de construção.

Relatório: `docs/v3/02-plano-v3.md`.

### Fase 3 — Base de infraestrutura

Use a skill `pathsol-infra`. Terraform para os recursos novos: estado remoto, orçamento e alertas, Key Vault, storage e fila, observabilidade. Preparação das VMs com aprovação por ação.

### Fase 4 — Worker GPU e acervo `.h5`

Use a skill `pathsol-contrato-h5`. Primeira fatia: mensagem na fila → worker na VM2 → `.h5` → COMPLETED. O gate são os testes de aceite 1 a 5 e 8 da skill, mais uma conferência simples do 6: a grade de patches desenhada sobre a miniatura da lâmina, num PNG que o Pedro olha. O acervo `.h5` nasce dos envios pelo fluxo novo (critério 8).

### Fase 5 — API, banco e roteador

Use as skills `pathsol-isolamento-tenant` e `pathsol-contrato-h5`. Toda rota nova com os quatro testes de isolamento. O teste de aceite 7 da `pathsol-contrato-h5` (versão do extrator) entra no gate desta fase.

### Fase 6 — Workspace e extensão

Workspace e extensão escritos do zero. Antes de começar, leia `docs/v3/referencia-visual.md`, com os valores visuais extraídos do código do legado na Fase 1 (não há capturas de tela). Reproduza as cores, a tipografia, as telas, os fluxos e os atalhos com código novo. Melhorias visuais vão para o roadmap, não para a v1. A integração com o PathoWeb falha fechada: sem resposta da API, nada é gravado no LIS. O teste de aceite 6 completo da `pathsol-contrato-h5` (alinhamento no viewer) entra no gate desta fase.

### Fase 7 — Cabeças ABMIL

1. Os rótulos vêm com os casos enviados pelo fluxo novo, no formato definido na Fase 2, e não do legado. Importe-os para a tabela de rótulos da v3, cada um ligado à sua lâmina, com a origem registrada. Relatório de cobertura: quantos rótulos encontraram `.h5`, por órgão e classe, e quais ficaram de fora e por quê.
2. Confira as contagens de rótulos com `.h5`, por órgão, classe, caso e laboratório, contra o mínimo da Fase 2 e liste os órgãos que entram na v1, para aprovação do Pedro.
3. Separe o conjunto de teste por caso e por laboratório antes de qualquer treino e trave-o (hash da lista).
4. Treine, registre as métricas por classe e por laboratório, e deixe o modelo como candidato até a aprovação do Pedro.

### Fase 8 — Go-live

Critérios da v1 conferidos um a um, alarmes testados de verdade (disco, dead-letter, orçamento), aceite da Diagnose. Soft delete do storage da v3 ligado no MVP, quando o Pedro confirmar que as lâminas e os casos corretos estão carregados, por Terraform e com plano aprovado.

## Comece agora

Confirme em até dez linhas o que entendeu da missão e das regras. Depois execute a fase indicada pelo Pedro.
