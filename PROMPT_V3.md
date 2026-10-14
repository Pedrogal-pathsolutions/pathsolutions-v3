# Missão: PathSolutions v3

Leia `CLAUDE.md` e `docs/arquitetura/arquitetura-pathsolutions_spec.md` antes de qualquer ação.

## Contexto

A PathSolutions é um SaaS de pré-laudo assistido por IA para laboratórios de patologia. O sistema atual (legado) roda na subscrição pay-as-you-go da empresa: VM1 com viewer, API, banco e tiles; VM2 com GPU T4; Blob com as WSIs.

A v3 é escrita do zero, seguindo a arquitetura de referência em `docs/arquitetura/`. Nenhum código, comentário ou configuração do legado entra na v3. O legado será desligado e limpo, e as duas VMs passam a hospedar a v3: VM1 como plano de controle (CPU) e VM2 como worker GPU, que é a divisão da spec. As WSIs que estão no Blob ficam onde estão e serão reprocessadas pela v3 quando ela estiver pronta.

## Critério de pronto da v1

1. O fluxo principal da spec funciona de ponta a ponta: extensão → upload direto ao Blob por SAS → `POST /v1/jobs` idempotente → fila → worker GPU (QC 1, tiling, QC 2 com fração de tecido e foco, Hibou-L) → `.h5` → COMPLETED → o workspace abre o caso, mostra a lâmina e o heatmap.
2. A fila tem as três garantias da spec: idempotência por `job_id`, visibility timeout maior que o pior tempo medido e dead-letter com alarme.
3. Isolamento entre laboratórios: tenant pelo JWT, RLS forçada e os testes da skill `pathsol-isolamento-tenant` passando.
4. O roteador trata as exceções: órgão vazio, sinônimos e órgão sem modelo. Nesses casos o caso segue sem IA, e a interface diz isso.
5. Cabeças ABMIL só para os órgãos com rótulos suficientes, definidos na Fase 2. Cada uma é validada em conjunto de teste travado e só é ativada com aprovação do Pedro. Sem rótulos, a v1 sai com o pipeline completo e todos os casos seguem sem IA.
6. Workspace com viewer de deep zoom, overlay de heatmap, revisão e assinatura. Código novo; o visual segue a referência capturada na Fase 1, se houver.
7. Operação: todo cache com teto, alertas de disco e de dead-letter, orçamento com alertas, VM2 desalocada quando a fila está vazia.
8. Todas as WSIs do Blob reprocessadas para `.h5` da v3.

Tudo o mais é roadmap. Registre em `docs/v3/roadmap.md` e não construa. Isso inclui explicitamente: filas de aprendizado ativo e de hard case, retreino automático, métricas 3 a 6 do QC 2 (dobra, artefatos, coloração, redundância), níveis de incerteza e detecção de outlier, sombra e canário, embeddings em float16, LoRA, citologia, LIS além do PathoWeb e qualquer uso de API de LLM.

## Decisões do Pedro

- D1. Rótulos e anotações do legado (diagnóstico por lâmina, rótulos de QC, anotações de região, manifesto dos datasets): `<exportar antes de desligar | não exportar>`.
- D2. Normalização de cor: sem Macenko, conforme a decisão de 22/09: `<confirmo | quero com Macenko>`.
- D3. Teto mensal de gasto da subscrição, para os alertas de orçamento: `R$ <valor>`.
- D4. Referência visual do legado: `<aproveitar | não aproveitar>`. Se aproveitar, o agente extrai os valores visuais do código e o Pedro tira as capturas de tela durante a Fase 1.

D1 e D4 são necessárias antes da Fase 1, porque depois dela não há volta. D2 e D3, antes da Fase 2.

## Regras de execução

Trabalhe em fases. Cada fase termina com um relatório em `docs/v3/` e a frase `PARADO — aguardando APROVADO FASE N`. Não avance sem essa aprovação escrita.

Todo relatório traz: o que foi feito; evidências (comando e saída resumida); o que não foi possível verificar; riscos; decisões pedidas ao Pedro. "Não verifiquei" é uma resposta aceitável. Afirmar sem evidência não é.

**Nesta sessão, execute apenas a Fase 0.**

## Fases

### Fase 0 — Ambiente (somente leitura)

- `az account show`: confirme nome e ID da subscrição e preencha o ID no `CLAUDE.md`. Essa é a única escrita da fase, além do relatório.
- Recursos (`az resource list -o table`) e o grupo de cada um.
- VM1 e VM2: estado, tamanho, discos e uso (`df -h`). Na VM2, via ssh (pede confirmação), registre também `nvidia-smi` e as versões do driver e do CUDA.
- WSIs no Blob: storage account, container, quantidade, tamanho total e formatos por extensão. Só números; nomes de blob podem conter número de caso e não entram no relatório.
- O que roda hoje nas duas VMs (`docker ps -a`, units do systemd, crontabs), só os nomes. Onde está o código do legado e o remoto git dele.
- Cota da família NCASv3_T4 em `brazilsouth`.
- Ferramentas instaladas: terraform, az, docker, python, node, psql, git. Não instale nada.
- Custo mensal dos últimos três meses por recurso, se a CLI permitir.

Relatório: `docs/v3/00-ambiente.md`.

### Fase 1 — Desligar e limpar o legado

Só com D1 e D4 preenchidas. Use a skill `pathsol-desligamento-legado`: banco religado se estiver fora, código marcado, rótulos e referência visual conforme D1 e D4, snapshots, serviços parados e removidos, disco liberado, VM2 desalocada. Uma ação por autorização. As WSIs do Blob não são tocadas.

Relatório: `docs/v3/01-desligamento.md`.

### Fase 2 — Plano da v3 (sem código, sem infraestrutura)

- Stack e estrutura do repositório.
- Distribuição dos componentes entre VM1, VM2 e recursos novos, com custo mensal de cada recurso novo e o total comparado ao custo atual.
- Postgres: opções (container na VM1 com disco próprio, ou servidor gerenciado), com custo e risco.
- Mecanismo para ligar a VM2 quando chega job e desalocar quando a fila esvazia, com opções e custo.
- Taxonomia fixa de classes por órgão e tabela de correspondência entre cada valor de rótulo do legado e essa taxonomia. Rótulo sem correspondência clara fica de fora. O Pedro aprova a tabela.
- Órgãos com cabeça ABMIL na v1, conforme as contagens exportadas na Fase 1, por classe, caso e laboratório. Se um órgão não tiver rótulos para treinar, diga se eles servem como conjunto de teste para um modelo treinado em dataset público do manifesto.
- Calibração do limiar de foco do QC 2 com os rótulos de QC exportados.
- Plano de reprocessamento das WSIs do Blob.
- Ordem das fatias de construção.

Relatório: `docs/v3/02-plano-v3.md`.

### Fase 3 — Base de infraestrutura

Use a skill `pathsol-infra`. Terraform para os recursos novos: estado remoto, orçamento e alertas, Key Vault, storage e fila, observabilidade. Preparação das VMs com aprovação por ação.

### Fase 4 — Worker GPU e acervo `.h5`

Use a skill `pathsol-contrato-h5`. Primeira fatia: mensagem na fila → worker na VM2 → `.h5` → COMPLETED. Os testes de aceite da skill são o gate. Depois, reprocessamento das WSIs do Blob.

### Fase 5 — API, banco e roteador

Use as skills `pathsol-isolamento-tenant` e `pathsol-contrato-h5`. Toda rota nova com os quatro testes de isolamento.

### Fase 6 — Workspace e extensão

Workspace e extensão escritos do zero. Se D4 = aproveitar, leia `docs/v3/referencia-visual.md` e as imagens em `referencia-visual/` antes de começar: reproduza as cores, a tipografia, o layout, os fluxos e os atalhos com código novo. Melhorias visuais vão para o roadmap, não para a v1. A integração com o PathoWeb falha fechada: sem resposta da API, nada é gravado no LIS.

### Fase 7 — Cabeças ABMIL

1. Importe os rótulos do container `backup-legado` para a tabela de rótulos da v3, aplicando a correspondência aprovada na Fase 2, com origem `legado`. Cada rótulo se liga à lâmina da v3 pelo caminho do blob. Relatório de cobertura: quantos rótulos encontraram `.h5`, por órgão e classe, e quais ficaram de fora e por quê.
2. Separe o conjunto de teste por caso e por laboratório antes de qualquer treino e trave-o (hash da lista).
3. Treine, registre as métricas por classe e por laboratório, e deixe o modelo como candidato até a aprovação do Pedro.

### Fase 8 — Go-live

Critérios da v1 conferidos um a um, alarmes testados de verdade (disco, dead-letter, orçamento), aceite da Diagnose. Decisão do Pedro sobre apagar os snapshots do legado.

## Comece agora

Confirme em até dez linhas o que entendeu da missão e das regras. Depois execute a Fase 0.
