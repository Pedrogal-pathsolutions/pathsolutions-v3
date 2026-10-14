---
name: pathsol-desligamento-legado
description: Procedimento para desligar e limpar o sistema legado da PathSolutions nas VMs 1 e 2 antes da v3 — religar o banco se preciso, exportar rótulos e manifestos de datasets, extrair a referência visual, snapshots, parada e remoção de serviços, liberação de disco e desalocação da GPU — preservando as WSIs do Blob. Use sempre que um comando for mudar qualquer coisa no legado, para planejar ou executar o desligamento, ou num incidente antes dele.
---

# Desligamento do legado PathSolutions

Desligar o legado é rápido. O cuidado é com as poucas coisas que não voltam depois: os rótulos feitos por patologistas e a referência visual.

## O que nunca é apagado

- **As WSIs no Blob.** São a única cópia e a entrada do reprocessamento da v3.
- **Os snapshots** feitos aqui, até o go-live da v3.
- **As exportações** deste procedimento (`backup-legado`).

## Regras

- Uma ação por autorização explícita do Pedro. "Pode seguir" vale para a ação descrita, não para as próximas.
- Antes de pedir: o comando exato, o efeito esperado e se tem volta.
- Depois: registrar em `docs/operacao/<AAAA-MM-DD>-desligamento.md` o comando, o horário (UTC) e a saída resumida.
- Código, comentários e arquivos de configuração do legado não são copiados para o repositório da v3. As exceções são as exportações de dados e a lista de valores visuais deste procedimento.
- Nenhum dado de paciente em registro, relatório ou exportação. O caminho do blob pode conter número de caso: por isso os CSVs ficam fora do git e os relatórios trazem só contagens.

## Sequência

0. **Banco no ar.** A exportação de rótulos precisa do Postgres funcionando. Se ele estiver fora por disco cheio, a única ação para religá-lo é `sudo docker builder prune -af` (apaga só cache de build). Acompanhe com `df -h` e `pg_isready`. Se não voltar em 10 minutos, pare e reporte. Nada mais é limpo antes do passo 5.

1. **Código.** Tag `legado-final-<AAAA-MM-DD>` em todos os repositórios do legado e push (pede confirmação). Registrar os hashes. O clone local fica onde está, só para consulta de fatos, até o go-live.

2. **Rótulos (se D1 = exportar).** Localize no banco todas as anotações humanas e exporte para `~/backup-legado/`:
   - `rotulos_lamina.csv`, uma linha por rótulo: id interno da lâmina, caminho do blob da WSI, id interno do caso (a chave primária do banco, nunca o número real), laboratório, órgão, rótulo exatamente como está no banco, de onde veio (tabela e tela), quem rotulou, data. A coluna do caso e a do laboratório são o que permite separar o conjunto de teste por caso e por laboratório na v3.
   - `rotulos_qc.csv`: os rótulos de foco do admin (`admin_focus_label` ou equivalente), com id da lâmina, caminho do blob, rótulo, data.
   - `anotacoes_regiao.json`, se existirem: polígonos ou marcações de região, com coordenadas em pixels do nível 0 e o caminho do blob.
   - `manifesto_datasets.csv`: para cada dataset em disco, o nome, a fonte de download, a licença, o identificador de cada arquivo e o rótulo atribuído a ele. Datasets NC-ND entram como "descartado — licença" e nada mais.
   - `LEIA-ME.txt`: o que é cada coluna e cada valor de rótulo, com contagens por órgão e classe.

   Confira as contagens com o banco. Copie a pasta para o container `backup-legado` na storage account existente (nunca dentro do container das WSIs) e confira os checksums.

3. **Referência visual (se D4 = aproveitar).** Duas partes:
   - Você extrai do código os valores visuais: cores (com nome e uso), fontes, tamanhos, espaçamentos, raios, ícones, temas. Também a lista de telas e rotas, o que cada uma faz, e os atalhos de teclado e interações do viewer. Tudo como lista de valores em `docs/v3/referencia-visual.md`, sem copiar CSS nem componentes.
   - O Pedro tira as capturas de tela no navegador, porque as telas mostram dado de paciente e só ele pode escolher um caso ou cortar a imagem. Gere a lista de telas a capturar. Ele salva as imagens em `referencia-visual/`, na raiz do repositório da v3 (fora do git). Quando ele avisar, abra cada imagem e descreva o layout de cada tela no mesmo documento. Se alguma imagem mostrar nome, CPF ou número de caso, avise o Pedro e não a use.

   Se o sistema não subir, registre "capturas não feitas" e siga só com os valores extraídos do código.

4. **Snapshots** de todos os discos das duas VMs, sistema e dados. Confirmar com `az snapshot list -o table` que existem e registrar nomes e tamanhos.

5. **Parar e remover serviços**, nesta ordem: crons e agendadores, worker da VM2, backend e frontend, banco. Remover containers, imagens e volumes Docker do legado, units do systemd e entradas de crontab. Estado final: nada do legado rodando nas duas VMs.

6. **Liberar disco.** Só depois dos passos 2 e 4 confirmados: apagar os diretórios do legado em `/data` nas duas VMs, inclusive os datasets em `/data/wsi_stage/datasets`. Os datasets públicos podem ser baixados de novo pelo manifesto. Mostrar `df -h` antes e depois.

7. **VM2.** Manter driver NVIDIA e CUDA instalados, com as versões registradas. Depois da limpeza, desalocar a VM2 até a Fase 4.

8. **Extensão Chrome.** Registrar que o Pedro pediu aos usuários da Diagnose para desativá-la.

## Relatório

Estado das duas VMs, espaço livre em cada disco, snapshots com nome e tamanho, contagens das exportações por órgão e classe, onde estão as cópias, o que foi removido e o que ficou. Como voltar atrás: criar discos a partir dos snapshots e trocar na VM, mais a tag do código.

## Incidente antes do desligamento

Diagnóstico primeiro, sem mudar nada. Depois, uma ação por autorização, com efeito colateral explícito. Nada de correção estrutural: o legado vai ser desligado.
