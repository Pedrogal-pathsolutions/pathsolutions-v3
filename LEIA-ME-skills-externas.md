# Skills externas para o pathsolutions-v3

Quatro skills de terceiros, copiadas sem alteração de conteúdo (só duas referências internas renomeadas), com as licenças originais dentro de cada pasta.

| Skill | Origem | Licença | Quando entra |
|---|---|---|---|
| `test-driven-development` | obra/superpowers (`bb92a77`) | MIT | Fases 4 a 7: teste antes do código |
| `systematic-debugging` | obra/superpowers (`bb92a77`) | MIT | Qualquer erro: diagnóstico antes da correção |
| `verification-before-completion` | obra/superpowers (`bb92a77`) | MIT | Antes de dizer que algo está pronto |
| `impeccable` | pbakaus/impeccable (`6af45ac`, motor 0.1.15) | Apache 2.0 | Fase 6: workspace e extensão |

## O que ficou de fora, e por quê

- **Resto do superpowers** (brainstorming, writing-plans, subagent-driven-development, executing-plans, using-git-worktrees, finishing-a-development-branch, using-superpowers e o hook de início de sessão): essas partes impõem um fluxo próprio, obrigatório e autônomo, que concorre com as fases e os gates do `PROMPT_V3.md` e gera mais documento de planejamento.
- **claude-mem**: grava tudo o que o agente vê, inclusive saídas de comando, e resume com IA. O resumo vai para o serviço deles, para uma chave de API paga ou para o seu plano. Na v3 isso incluiria dados de casos de laboratório, com cópia fora dos sistemas controlados (LGPD). E o projeto já guarda o estado nos relatórios e no git, de propósito.
- **vercel-labs/skills**: não é uma skill, é um instalador de skills por linha de comando. Precisa de Node, que a VM1 ainda não tem. O pacote já traz as skills prontas.

## Instalação

1. Termine a sessão atual da Fase 1 antes. Skills novas só valem em sessão nova.
2. No VS Code, arraste `skills-externas.zip` para a pasta `pathsolutions-v3`.
3. Numa sessão nova do Claude Code, peça:

```
Descompacte skills-externas.zip na raiz do repositório, confira que as 4
pastas ficaram em .claude/skills/, apague o zip, acrescente ao CLAUDE.md a
seção abaixo, faça o commit e o push.
```

## Seção para o CLAUDE.md

```
## Skills externas

- test-driven-development, systematic-debugging e verification-before-completion
  (de obra/superpowers) valem dentro das fases. Elas não substituem os gates:
  nenhuma fase avança sem "APROVADO FASE N".
- impeccable: só para a interface (Fase 6). A referência visual em
  docs/v3/referencia-visual.md prevalece. Use critique, audit, polish, harden,
  clarify, adapt, layout e typeset dentro dela. bolder, delight, overdrive,
  colorize e animate só com pedido do Pedro. Na primeira execução, o impeccable
  baixa um binário próprio; isso pede autorização.
```
