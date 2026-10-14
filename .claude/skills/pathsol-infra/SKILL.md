---
name: pathsol-infra
description: Convenções e procedimento para infraestrutura Azure da PathSolutions v3 na subscrição pay-as-you-go (VM1 e VM2 reaproveitadas, recursos novos em Terraform). Use sempre que for escrever .tf, rodar terraform plan/apply, consultar cota ou custo, criar storage, fila, Key Vault, Postgres, alertas, preparar as VMs ou configurar ligar/desligar a GPU, mesmo que o pedido pareça pequeno.
---

# Infraestrutura PathSolutions v3

Complementa as skills oficiais de Azure e Terraform instaladas por plugin. Estas regras vencem quando houver conflito.

## Antes de qualquer comando

`az account show` precisa mostrar a subscrição da PathSolutions. Se mostrar outra, pare.

## O que é de quem

- **Existentes, fora do Terraform:** VM1, VM2, os discos delas, a rede e a storage account do legado. A v3 usa esses recursos, mas o Terraform só os lê como `data source`. Nunca `terraform import`. Um plano que cite qualquer um deles como create, update ou destroy está errado: pare e reporte.
- **Novos, no Terraform:** tudo da v3 fica em `rg-pathsol-v3`.
- Mudança em VM existente (disco novo, tamanho, auto-shutdown) é feita com `az`, uma ação por autorização, registrada em `docs/operacao/`.

## Convenções

- Região `brazilsouth`. Outra região só com aprovação do Pedro (residência de dado de saúde).
- Nome: `pathsol-<servico>-v3`, respeitando os limites de cada recurso (storage account: minúsculas, sem hífen).
- Tags obrigatórias: `projeto=pathsolutions`, `versao=v3`, `componente`.
- Estado remoto em storage account própria, criada numa etapa de bootstrap separada.
- Versões de provider fixadas.
- Segredos no Key Vault. Preferir identidade gerenciada a chaves de acesso.
- Postgres com SSL obrigatório, sem acesso público aberto, backup automático e restauração testada pelo menos uma vez.

## Procedimento

1. `terraform fmt` e `terraform validate`.
2. `terraform plan -out=<bloco>.tfplan`.
3. Resumo no relatório: recursos criados, alterados e destruídos, e custo mensal estimado de cada um.
4. Parar e pedir aprovação.
5. `terraform apply <bloco>.tfplan` só depois da aprovação.
6. Verificar com `az` que o recurso existe e responde.

Plano que destrói ou recria recurso com dado (storage, Postgres, Key Vault) aparece no topo do resumo.

## Custo (sem créditos, cada real sai do caixa)

- O primeiro recurso depois do estado é o orçamento da subscrição, com alertas em 50%, 80% e 100% do teto D3 do prompt, enviados ao e-mail do Pedro.
- Todo recurso novo entra no plano com custo mensal estimado e a fonte da estimativa (calculadora ou página de preços do Azure). Sem número inventado.
- Preferir reaproveitar o que já existe a criar recurso novo.
- VM2: desalocada quando a fila está vazia. O mecanismo de ligar sob demanda é escolhido pelo Pedro na Fase 2, entre opções com custo.

## Disco e caches

- Todo cache e diretório de trabalho tem teto configurado e limpeza automática.
- Alerta de disco em 80% e 90% nas duas VMs, com destino definido, testado de verdade antes do go-live.
- Banco em disco separado dos caches: cache cheio nunca pode derrubar o Postgres.

## Cota

Consulte com `az vm list-usage --location brazilsouth -o table` e reporte. Pedido de cota é feito pelo Pedro no portal.
