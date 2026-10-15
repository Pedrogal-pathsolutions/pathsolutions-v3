# PathSolutions v3 — regras permanentes do repositório

SaaS multitenant de pré-laudo assistido por IA em patologia digital. Dados de pacientes de laboratórios brasileiros (LGPD). Arquitetura de referência em `docs/arquitetura/`; ela é a fonte de verdade. Relatórios das fases em `docs/v3/`. Registros de ações no legado em `docs/operacao/`.

## Conta e recursos

- Uma subscrição só: PATHSOLUTIONS TECNOLOGIA EM SAUDE LTDA, pay-as-you-go, sem créditos. ID: `bd87a1ca-e4f5-460b-9f12-c89e114293f1`.
- Antes de qualquer comando `az` ou `terraform`, confirme a subscrição ativa com `az account show`.
- VM1, VM2, rede e a storage account das WSIs já existem. A v3 usa esses recursos, mas eles ficam fora do Terraform: entram só como `data source`. Nunca `terraform import`, nunca no state.
- Recursos novos da v3 ficam no grupo `rg-pathsol-v3` e são criados só por Terraform.
- Tudo custa dinheiro: nenhum recurso novo sem custo mensal estimado no plano aprovado.

## Legado

- A v3 é escrita do zero. Nenhum código, comentário, configuração ou arquivo do legado é copiado para cá. As únicas coisas que vêm do legado são dados: as exportações de rótulos no container `backup-legado` e a referência visual (lista de valores em `docs/v3/referencia-visual.md` e capturas em `referencia-visual/`).
- O legado pode ser lido apenas para extrair fatos (onde estão as WSIs, como a API do PathoWeb responde, versões do driver da GPU). Os fatos são registrados com palavras próprias.
- Antes da Fase 1, o legado é somente leitura. A Fase 1 desliga e limpa o legado seguindo a skill `pathsol-desligamento-legado`, uma ação por autorização do Pedro.
- As WSIs no Blob nunca são apagadas, movidas ou alteradas. São a única cópia e a entrada do reprocessamento.
- Os snapshots do legado só são apagados depois do go-live, com pedido escrito do Pedro.

## Gates

Cada fase termina com relatório e parada. Só avance com "APROVADO FASE N" escrito pelo Pedro. Não existe "continuo porque era trivial".

## Evidência

Não afirme como algo se comporta sem evidência (arquivo:linha, saída de comando, consulta). Se não verificou, escreva "não verificado".

## Dados clínicos

- `tenant_id` vem só do JWT validado. Nunca de path, query, body ou header livre.
- Toda tabela com dado de tenant tem RLS ativa e forçada.
- A WSI não passa pela API: upload direto ao Blob com SAS de escopo e prazo curtos.
- Nenhum dado de paciente (nome, CPF, número de caso real) em logs, commits, testes, fixtures, capturas de tela ou relatórios. Use identificadores internos ou sintéticos.

## ML

- Extrator: Hibou-L congelado, conforme a spec. Sem normalização Macenko (decisão D2 do prompt). O adaptador VICReg e o modelo `raw_aug_v1` do legado não entram na v3.
- Antes de usar os pesos, confirme o sha256 e a licença do arquivo exato. O Hibou-L base e o CellViT-Hibou-L têm licenças diferentes.
- Todo `.h5` grava `extractor_version`. Um `.h5` com versão diferente da ativa leva a reprocessamento, nunca a inferência.
- Só as cabeças ABMIL são treinadas, sempre com conjunto de teste travado, separado por caso e por laboratório. Modelo novo fica como candidato até o Pedro aprovar com as métricas.
- Órgão vazio, não reconhecido ou sem modelo: o caso segue sem IA, e a interface diz isso.
- Resultado em um único caso é sinal, não validação. Nunca apresente n=1 como prova.

## Operação

- Todo cache e todo diretório que cresce tem teto de tamanho e regra de limpeza no código. Disco com alerta em 80% e 90%. Dois incidentes (julho e outubro de 2026) derrubaram a produção por disco cheio.
- O banco fica em disco separado dos caches.
- A VM2 fica desalocada quando a fila está vazia.

## Escopo

- A v1 está definida em `PROMPT_V3.md`. Ideia boa fora dela vai para `docs/v3/roadmap.md`.
- Nenhuma dependência de API de LLM paga.
- Código simples e legível, com comentários só onde o porquê não é óbvio. Nada de código morto, de TODO sem dono ou de abstração para um uso futuro hipotético.

## Infraestrutura

- `terraform plan` salvo e resumido antes de todo `apply`; `apply` só com aprovação.
- Nunca `terraform destroy` nem exclusão de recurso Azure sem pedido explícito.

## Idioma

Relatórios e documentação em português do Brasil. Código, identificadores e comentários de código em inglês.
