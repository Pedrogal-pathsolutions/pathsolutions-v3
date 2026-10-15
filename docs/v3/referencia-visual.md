# Referência visual do legado

Valores extraídos em 15/10/2026 do código do legado: repositório `Pathsolutions_V2`, branch `fix/audit-2026-09`. O relatório da Fase 0 registra o HEAD `ec70dbf` (`docs/v3/00-ambiente.md:336`). Não foi verificado se a árvore de trabalho lida coincide com esse commit. Por decisão do Pedro (D4), não há capturas de tela. Tudo vem da leitura do código, sem executar o app, e a aparência real não foi verificada no navegador. Os valores e comportamentos estão descritos com palavras próprias, sem CSS nem componentes copiados. A v3 reproduz a interface com código novo, e o que for melhoria em relação ao legado vai para `docs/v3/roadmap.md`.

**Como ler a coluna Origem**
- Os caminhos são relativos a `frontend/src/`. Os que começam com `frontend/` partem da raiz do frontend. `ea/` é `chrome-extension-assistant/` e `em/` é `chrome-extension-macroscopy/`.
- Quando o cabeçalho da coluna Origem traz um arquivo, todas as linhas da tabela são desse arquivo.
- Numa mesma célula ou item, `:N` repete o último arquivo citado.
- `gray-800`, `rounded-lg`, `shadow-lg` e nomes parecidos são classes padrão do Tailwind, e o valor numérico delas não está no código. As equivalências em px assumem a escala padrão (1 unidade = 4 px) e também não estão no código.
- As contagens de classes vêm de grep em `frontend/src/**/*.tsx` e são aproximadas.

## Cores

### Base do tema

- O Tailwind ativa o tema escuro por classe (`frontend/tailwind.config.js:3`).
- O `extend` só acrescenta:
  - as famílias de fonte (`:10-13`);
  - as paletas `primary` e `accent` (`:14-40`);
  - a animação `pulse-slow` (`:41-43`).
- Não há plugins (`:46`).
- O PostCSS usa tailwindcss e autoprefixer (`frontend/postcss.config.js:2-5`).
- Há um único CSS global, `index.css`. Não há variáveis CSS nem arquivo de tema ou de tokens.

### Paletas da marca

O comentário do CSS global chama a `primary` de ciano (`index.css:93`).

| Passo | `primary` (ciano) | `accent` (verde) | Origem (`frontend/tailwind.config.js`) |
|---|---|---|---|
| 50 | #ecfeff | #ecfdf5 | :16 e :29 |
| 100 | #cffafe | #d1fae5 | :17 e :30 |
| 200 | #a5f3fc | #a7f3d0 | :18 e :31 |
| 300 | #67e8f9 | #6ee7b7 | :19 e :32 |
| 400 | #22d3ee | #34d399 | :20 e :33 |
| 500 | #06b6d4 | #10b981 | :21 e :34 |
| 600 | #0891b2 | #059669 | :22 e :35 |
| 700 | #0e7490 | #047857 | :23 e :36 |
| 800 | #155e75 | #065f46 | :24 e :37 |
| 900 | #164e63 | #064e3b | :25 e :38 |
| 950 | #083344 | — | :26 |

**Onde cada paleta aparece**
- **`primary`:** ação principal no dashboard, no login, na navegação, nas filas e na paginação. No tema claro, `primary-800` é o fundo da barra de navegação e do cabeçalho do viewer (`components/Navigation.tsx:49`; `components/Header.tsx:32`).
- **`accent`:** estados "aprovado" e "QC ok" no dashboard (`components/CasesDashboard.tsx:624`).

### Cores fixas fora das paletas

| Elemento | Valor | Origem |
|---|---|---|
| Contêiner do OpenSeadragon | fundo #1f2937 | `index.css:31-33` |
| Barra de rolagem (WebKit) | 8 px de largura; trilho #f1f5f9; polegar #94a3b8 com raio de 4 px; polegar em hover #64748b | `index.css:36-52` |
| Barra de rolagem (Firefox) | fina, #94a3b8 sobre #f1f5f9 | `index.css:55-58` |
| Foco visível (botão, campo, seleção, área de texto, link e elemento com tabindex) | contorno de 3 px #0891b2, afastado 2 px, mais um halo de 5 px em rgba(8,145,178,0.2) | `index.css:93-103` |
| Skeleton | gradiente #e2e8f0 → #f1f5f9 → #e2e8f0, raio de 4 px, ciclo de 1,5 s | `index.css:128-143` |
| Fundo escurecido no mobile | rgba(0,0,0,0.5) com desfoque de 2 px | `index.css:174-177` |

A barra de rolagem e o skeleton não têm variante escura e ficam claros nos dois temas.

### Notificações do workspace (react-hot-toast)

| Item | Valor | Origem (`App.tsx`) |
|---|---|---|
| Posição | canto inferior direito | :132 |
| Duração | 3000 ms; 5000 ms no erro | :134, :137 |
| Fundo e texto | #164e63 (= `primary-900`) e #ecfeff (= `primary-50`), 14 px | :135 |
| Ícone de sucesso | #059669 (= `accent-600`) sobre #fff | :136 |
| Ícone de erro | #ef4444 sobre #fff | :137 |

### Frequência das famílias de cor

Conta as classes de fundo, texto, borda, anel e outras.

| Família | Ocorrências (aprox.) |
|---|---|
| gray | 2404 |
| blue | 269 |
| red | 252 |
| primary | 220 |
| green | 151 |
| amber | 118 |
| yellow | 51 |
| accent | 47 |
| rose | 45 |
| purple | 39 |
| orange | 31 |
| indigo | 22 |
| teal, emerald | 5 cada |
| slate, pink | 4 cada |

**Classes mais usadas**
- Fundo: `bg-white` 185, `dark:bg-gray-800` 176, `dark:bg-gray-800/60` 53, `bg-gray-50` 48.
- Texto: `dark:text-gray-100` 170, `dark:text-gray-200` 140, `text-gray-700` 135, `text-white` 128, `text-gray-500` 124, `text-gray-900` 119.
- Borda: `dark:border-gray-700` 151, `border-gray-300` 128, `dark:border-gray-600` 65, `border-gray-200` 60.
- Anel de foco: `focus:ring-primary-500` 39, `focus:ring-blue-500` 10.

### Papéis semânticos

| Papel | Claro | Escuro | Origem |
|---|---|---|---|
| Fundo das páginas com barra de navegação | `primary-50` a 40% | `gray-900` | `App.tsx:103` |
| Cartão, superfície | branco | `gray-800` | `components/CasesDashboard.tsx:404` |
| Superfície secundária (cabeçalho de tabela e de cartão, aba inativa) | `gray-50` | `gray-800` a 60% | `components/CasesDashboard.tsx:534`; `components/RightPanel.tsx:349`, `:367` |
| Borda | `gray-300` / `gray-200` | `gray-700` / `gray-600` | `components/CasesDashboard.tsx:404`; `components/RightPanel.tsx:323` |
| Texto principal / secundário / terciário | `gray-900` / `gray-700`–`600` / `gray-500` | `gray-100` / `gray-200`–`300` / `gray-400` | `components/CasesDashboard.tsx:405-407` |
| Barra de navegação e cabeçalho do viewer | `primary-800`, texto branco, sombra `lg` | `gray-900`, com borda inferior `gray-800` | `components/Navigation.tsx:49`; `components/Header.tsx:32` |
| Link da barra: inativo / ativo | texto `primary-100`, hover branco a 10% / fundo branco a 15%, sombra `sm` | igual | `components/Navigation.tsx:40-44` |
| Botão Upload na barra | `primary-600`, hover `primary-500` | igual | `components/Navigation.tsx:96` |
| Avatar / pílula do usuário | `primary-500` / `primary-700` | `primary-500` / `gray-800` | `components/Navigation.tsx:114-116`; `components/Header.tsx:102-103` |
| Botão primário | `primary-600`, hover `primary-700`, anel de foco de 2 px `primary-500` afastado 2 px | igual, com afastamento sobre `gray-800` | `components/LoginPage.tsx:348` |
| Botão de ação no viewer e nos painéis | `blue-600`, hover `blue-700` | igual | `components/ReportViewer.tsx:472`; `components/RightPanel.tsx:942`; `components/ViewerContainer.tsx:606` |
| Campo de texto | borda `gray-300`, fundo branco, foco com anel de 2 px `primary-500` | borda `gray-600`, fundo `gray-900` ou `gray-800` | `components/LoginPage.tsx:322`; `components/CasesDashboard.tsx:465` |
| Aprovado | no dashboard, `accent-50` com texto `accent-700`; no painel, `green-50` e `green-500` | `accent-900` a 30% com `accent-300` | `components/CasesDashboard.tsx:624`; `components/RightPanel.tsx:457-469` |
| Erro, reprovado | `red-50` com `red-600`/`700`, borda `red-200`/`300` | `red-900` a 30% com `red-300`, borda `red-700`/`800` | `components/CasesDashboard.tsx:630`; `components/LoginPage.tsx:306-307` |
| Atenção | `amber-50` com `amber-700` | `amber-900` a 30% com `amber-300` | `components/CasesDashboard.tsx:613` |
| Pendente, alteração não salva | `yellow-50`/`100` com `yellow-600`/`700` | `yellow-900` a 30% com `yellow-300` | `components/ReportViewer.tsx:561`; `components/CaseCard.tsx:63` |
| Processando | chip `blue-50` com `blue-600`; cartão `purple-50` com borda `purple-300` | chip `blue-900` a 30% com `blue-300`; cartão `purple-900` a 30% | `components/CasesDashboard.tsx:671`, `:427` |
| Sugestão da IA (pré-laudo) | `rose-50`, borda `rose-200`/`300`, título `rose-800`, barra `rose-500` | `rose-900` a 20%, borda `rose-700`/`800`, texto `rose-200`/`300` | `components/RightPanel.tsx:420-445`; `components/ReportViewer.tsx:428-431` |
| Dica | `blue-50`, borda `blue-200`, texto `blue-800`, ícone `blue-600` | `blue-900` a 30%, `blue-700`, `blue-300` | `components/ReportViewer.tsx:673-676` |

Os estados seguem um padrão:
- no claro, fundo `-50` ou `-100` com texto `-600` ou `-700`;
- no escuro, fundo `-900` a 30% com texto `-300`.

### Outros mapeamentos de cor

| Uso | Valores | Origem |
|---|---|---|
| Selo do tipo de lâmina (o comentário diz "cores aprovadas pelo Pedro") | HE roxo (`purple`), IHC laranja (`orange`), Especial `teal`, Papanicolau rosa (`pink`). Claro: fundo `-100` e texto `-700`; escuro: fundo `-900` a 30% e texto `-300`. Indefinido: rótulo "—"; claro `gray-100` com `gray-600`; escuro `gray-700` a 60% com `gray-300` | `utils/slideLabel.ts:112-119` |
| Status do laudo | Rascunho: `gray-100` com `gray-800`. Importado: `green-100` com `green-800` | `components/ReportViewer.tsx:317-325` |
| Seções do editor de laudo | Microscopia em azul (`blue-50`, borda `blue-200`, título `blue-900`). Conclusão em índigo (`indigo-50`, `indigo-200`, `indigo-900`) | `components/ReportViewer.tsx:578-597`; `components/WideReportEditorModal.tsx:176-182` |
| Títulos de seção na leitura do laudo | `blue-900`, sublinhado de 2 px `blue-300` | `components/ReportViewer.tsx:362-366` |
| Botões do laudo | Editar `blue-600`; Salvar `green-600`; Cancelar `gray-600`; Importar no LIS `indigo-600`; Segunda opinião `orange-600`; Manter sugestão `emerald-600`; Apagar sugestão `rose-600` | `components/ReportViewer.tsx:433, 437, 472, 486, 505, 517, 539` |
| Status de lote (só tema escuro) | Pendente: fundo `yellow-900` a 40%, texto `yellow-300`, borda `yellow-700`. Em andamento: o mesmo em `blue`. Concluído: o mesmo em `green`. Cancelado: `gray-800` com `gray-500` | `components/BatchesPanel.tsx:80-83` |
| Status de lâmina no lote | `yellow-600`, `blue-600`, `green-600`, `gray-400` | `components/BatchesPanel.tsx:439-442` |
| Ground truth | Em andamento `blue-100`/`700`; enviado `amber`; revisado `green`. No escuro, `-500` a 20% com `-300` | `components/GroundTruthPanel.tsx:244-248` |
| Marcação de foco pelo admin | Com foco `green-600`; Sem foco `red-600`; Ruim `amber-600`; todas com borda `-700` | `components/FocusLabelControl.tsx:23-25` |
| Decisão de calibração de QC | Aplicada `green-600`; em revisão `amber-600`; demais `gray-500` | `pages/QcCalibrationPage.tsx:48` |
| Chat | Mensagem própria: `blue-500` com texto branco. De outra pessoa: branco (`gray-800` no escuro), com borda | `components/CollaborationChat.tsx:197-200` |
| Paginação | página atual `primary-600` | `components/PaginationControls.tsx:127-130` |
| Focus score no dashboard | a partir de 70, `accent` com ✓; a partir de 50, `yellow`; abaixo de 50, `red` | `components/CasesDashboard.tsx:643-655` |

### Telas com fundo próprio

**Login e redefinir senha**
- Gradiente diagonal `slate-900` → `primary-950` (#083344) → `slate-900`, igual nos dois temas (`components/LoginPage.tsx:263`; `pages/ResetPasswordPage.tsx:55`).
- Por cima, um canvas animado com 4 hélices de DNA (`components/LoginPage.tsx:19-24`) e 50 partículas (`:48`).
- As hélices usam uma paleta "inspirada em nucleotídeos", segundo o comentário (`:26-32`):

  | Cor | Equivale a |
  |---|---|
  | rgb(8,145,178) | `primary-600` |
  | rgb(20,184,166) | nenhuma das paletas da marca |
  | rgb(6,182,212) | `primary-500` |
  | rgb(14,116,144) | `primary-700` |

- As partículas são rgba(8,145,178), com opacidade de 0,03 a 0,09 (`:205-209`).

**Acesso de convidado**
- Gradiente `primary-50` → `primary-100`; no escuro, `gray-900` (`pages/GuestAccessPage.tsx:64`).

### Divergências de cor no código

- **Duas cores de ação convivem.**
  - A `primary` (ciano) aparece no dashboard, no login e na navegação.
  - O `blue` do Tailwind aparece no viewer, nos painéis, nos interruptores e no chat.
  - São ≈ 270 classes `blue` contra ≈ 220 `primary`.
  - O favicon é azul (#2563eb), e as extensões usam roxo (#667eea → #764ba2).
- **Opacidades fora dos passos usuais:** branco a 97% (`components/AnnotationClassSelector.tsx:100`) e `gray-900` a 92% (`components/CellCountHUD.tsx:36`). Se essas classes geram CSS depende da versão do Tailwind (não verificado).

## Tipografia

### Famílias e carregamento

| Item | Valor | Origem |
|---|---|---|
| Corpo | Noto Sans | `index.css:68-71`; `frontend/tailwind.config.js:11` |
| Títulos (h1 a h6 e `font-heading`) | Figtree | `index.css:78-80`; `frontend/tailwind.config.js:12` |
| Carregamento | Google Fonts com `display=swap`: Figtree nos pesos 300, 400, 500, 600 e 700; Noto Sans nos pesos 300, 400, 500 e 700 | `frontend/index.html:7-9` |
| Pilha do corpo | Noto Sans, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Oxygen, Ubuntu, Cantarell, Fira Sans, Droid Sans, Helvetica Neue, sans-serif | `index.css:69-71` |
| Pilha dos títulos | Figtree, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif | `index.css:79` |
| `font-sans` e `font-heading` do Tailwind | Noto Sans ou Figtree, seguidas de system-ui, -apple-system, sans-serif | `frontend/tailwind.config.js:11-12` |
| `code` e `kbd` | source-code-pro, Menlo, Monaco, Consolas, Courier New, monospace | `index.css:82-86` |
| `font-mono` | não redefinida | `frontend/tailwind.config.js:10-13` |
| Suavização | antialiased | `index.css:72-73` |

**Uso das classes de família:** `font-heading` ≈ 49; `font-mono` ≈ 37 (editor de laudo, kbd e IDs); `font-sans` 1.

**Divergência: peso 600 sem fonte.** O peso 600 (semibold) é o mais usado, mas a Noto Sans é carregada sem ele (`frontend/index.html:9`); só a Figtree tem 600. Como o navegador resolve isso (síntese ou peso vizinho) não foi verificado.

**Texto desenhado em canvas:**
- o rótulo de medida das anotações usa Arial bold de 13 px (`components/AnnotationTools.tsx:48`);
- os rótulos das detecções usam 10 px bold (`components/ViewerContainer.tsx:316-319`, `:357-360`).

### Tamanhos, pesos e espaçamento

| Classe | Ocorrências (aprox.) |
|---|---|
| `text-xs` | 303 |
| `text-sm` | 265 |
| `text-lg` | 32 (+2 com `md:`) |
| `text-xl` | 23 |
| `text-[10px]` | 22 |
| `text-3xl` | 13 |
| `text-2xl` | 12 |
| `text-base` | 10 |
| `text-[11px]` | 9 |
| `text-4xl` | 4 |
| `text-[9px]` | 3 |
| `text-[8px]` | 1 |
| `text-5xl` | 1 |

- **Pesos:** semibold ≈ 205, medium ≈ 133, bold ≈ 97, normal 2.
- **Altura de linha:** `leading-relaxed` 8 (laudo), `leading-tight` 4, `leading-none` 2.
- **Espaçamento entre letras:**
  - `tracking-wide` 11, nos rótulos em maiúsculas;
  - 0,5em no campo do código do convidado (`pages/GuestAccessPage.tsx:98`).
- **Outros:** `uppercase` 35; algarismos tabulares 14.

### Hierarquia

| Elemento | Estilo | Origem |
|---|---|---|
| Título de página | `text-2xl`, Figtree, bold | `components/CasesDashboard.tsx:395` |
| Título de modal | `text-xl`, Figtree, bold | `components/SettingsModal.tsx:111` |
| Seção de modal | `text-lg`, Figtree, semibold | `components/SettingsModal.tsx:128` |
| Título de cartão | `text-lg`, Figtree, bold | `components/RightPanel.tsx:462` |
| Marca na barra de navegação | `text-lg`, Figtree, bold; subtítulo em `text-xs` | `components/Navigation.tsx:56-57` |
| Cabeçalho de tabela | `text-xs`, semibold, maiúsculas | `components/CasesDashboard.tsx:536` |
| Rótulo de campo | `text-sm`, medium | `components/CasesDashboard.tsx:459` |
| Número de indicador | `text-3xl`, bold | `components/CasesDashboard.tsx:406` |
| Editor de laudo | `text-sm`, monoespaçada, `leading-relaxed` | `components/ReportViewer.tsx:584` |
| Leitura do laudo | `text-sm`, sans, `leading-relaxed` | `components/ReportViewer.tsx:603` |

## Espaçamento, raios e sombras

### Espaçamento

O espaçamento segue a escala padrão do Tailwind, sem customização (`frontend/tailwind.config.js:8-45`).

**Classes mais usadas**
- **Padding:** `py-2` 180, `px-4` 167, `px-3` 115, `px-2` 89, `py-3` 84, `p-4` 68, `py-0.5` 59, `py-1` 55, `p-2` 39, `py-1.5` 37, `p-6` 35.
- **Gap:** `gap-2` 117, `gap-1` 54, `gap-3` 42, `gap-1.5` 41, `gap-4` 16.
- **Espaço vertical entre filhos:** `space-y-4` 19, `space-y-2` 19, `space-y-1` 15, `space-y-6` 9.
- **Margem:** `mb-1` 62, `mb-2` 61, `mb-4` 43, `mb-3` 34, `mt-2` 29.

| Padrão | Valor (horizontal × vertical) | Origem |
|---|---|---|
| Botão | 16 × 8 px (`px-4 py-2`) | `components/ReportViewer.tsx:472` |
| Pílula de status | 8 × 2 px (`px-2 py-0.5`) | `components/CasesDashboard.tsx:613` |
| Célula de tabela | 16 × 12 px (`px-4 py-3`) | `components/CasesDashboard.tsx:572` |
| Cartão | 16 px (`p-4`) | `components/CasesDashboard.tsx:404` |
| Cabeçalho de modal | 24 × 16 px (`px-6 py-4`) | `components/SettingsModal.tsx:110` |
| Campo | 12 × 8 px (`px-3 py-2`) ou 16 × 12 px (`px-4 py-3`) | `components/CasesDashboard.tsx:465`; `components/LoginPage.tsx:322` |

### Medidas fixas do layout

| Elemento | Medida | Origem |
|---|---|---|
| Contêiner das páginas com barra | centralizado, padding de 24 px | `App.tsx:105` |
| Barra de navegação | 56 px; 64 px a partir de `md` | `components/Navigation.tsx:51` |
| Cabeçalho do viewer | 48 px; 64 px a partir de `md` | `components/Header.tsx:34` |
| Limite do celular | abaixo de 768 px | `hooks/useIsMobile.ts:3` |
| Alvo de toque mínimo (abaixo de 768 px) | 44 × 44 px | `index.css:179-184` |
| Menu do usuário | 224 px | `components/Navigation.tsx:124` |
| Coluna do login | até 448 px | `components/LoginPage.tsx:286` |

### Modais

| Modal | Tamanho | Origem |
|---|---|---|
| Configurações do visualizador | até 672 px (`max-w-2xl`) e 90% da altura | `components/SettingsModal.tsx:108` |
| Upload | até 896 px (`max-w-4xl`) e 90% da altura | `components/UploadModal.tsx:22-23` |
| Editor amplo de laudo | 95% da largura × 92% da altura | `components/WideReportEditorModal.tsx:141` |
| Troca de senha | até 448 px (`max-w-md`) | `components/ChangePasswordModal.tsx:71` |
| Primeiro acesso | até 512 px (`max-w-lg`) | `components/FirstLoginGate.tsx:16` |
| Confirmação de máscara | até 672 px (`max-w-2xl`), 80% da altura | `components/MaskSelector.tsx:216` |

### Raios

**Contagem:**
- `rounded-lg` 265, `rounded` 136, `rounded-full` 106, `rounded-xl` 21, `rounded-md` 11;
- `rounded-t-lg` 6, `rounded-b-lg` 4, `rounded-2xl` 3, `rounded-t-2xl` 2;
- um uso cada de `-sm`, `-tl`, `-r-lg`, `-l-lg` e `-b-2xl`.

| Raio | Onde | Origem |
|---|---|---|
| `lg` | botões, campos, cartões | `components/LoginPage.tsx:322`, `:348`; `components/CasesDashboard.tsx:404` |
| `full` | pílulas, avatares, botões de objetiva, interruptores | `components/CasesDashboard.tsx:613`; `components/Header.tsx:103`; `components/ObjectiveIndicator.tsx:103`; `components/SettingsModal.tsx:138` |
| `xl` | modais, cartão do login, HUD de contagem, menu do usuário | `components/LoginPage.tsx:297`; `components/ChangePasswordModal.tsx:71`; `components/CellCountHUD.tsx:36`; `components/Navigation.tsx:124` |
| `2xl` | cartão do convidado, folha inferior do mobile | `pages/GuestAccessPage.tsx:76`; `components/RightPanel.tsx:322` |
| `rounded` (padrão) | `kbd` e chips pequenos | `components/SettingsModal.tsx:332` |
| 4 px (valor no código) | minimapa, barra de rolagem, skeleton | `components/ViewerContainer.tsx:545`; `index.css:47`, `:142` |
| 3 px (valor no código) | rótulos de detecção | `components/ViewerContainer.tsx:318`, `:359` |

### Sombras e fundos de modal

**Contagem:** `shadow-lg` 22, `shadow-2xl` 16, `shadow-md` 8 (+2 em hover), `shadow-sm` 8, `shadow-xl` 5, `shadow` 3.

**Onde cada sombra aparece**
- `shadow-2xl`: modais e cartão do login (`components/SettingsModal.tsx:108`; `components/LoginPage.tsx:297`).
- `shadow-lg`: controles flutuantes (`components/AnnotationToolbar.tsx:171`).
- `shadow-sm` passando a `shadow-md` no hover: cartões do mobile (`components/CaseCard.tsx:44`).

**Sombras com valor no código**
- Foco: ver Cores.
- Minimapa: deslocamento de 2 px, desfoque de 8 px, preto a 20% (`components/ViewerContainer.tsx:546`).
- Brilho das detecções: ver Heatmap e overlay.

**Fundo atrás de modais**
- Preto a 50% com desfoque leve (`components/SettingsModal.tsx:107`; `components/UploadModal.tsx:22`).
- Preto a 40% (`components/WideReportEditorModal.tsx:209`).
- `gray-900` a 70% (`components/FirstLoginGate.tsx:15`).
- O desfoque leve (`backdrop-blur-sm`) aparece 17 vezes.

### Movimento

| Item | Valor | Origem |
|---|---|---|
| Transição global | 150 ms, curva (0.4, 0, 0.2, 1), em cor, fundo, borda, preenchimento, traço, opacidade, sombra e transformação | `index.css:60-65` |
| Movimento reduzido | `prefers-reduced-motion` zera animações e transições | `index.css:105-115` |
| Spinner | 1 s, linear; `animate-spin` tem ≈ 31 usos | `index.css:117-126` |
| Skeleton | 1,5 s | `index.css:128-143` |
| Folha inferior (mobile) | entra em 0,3 s e sai em 0,2 s | `index.css:147-163` |
| Gaveta (mobile) | 0,25 s | `index.css:165-172` |
| `pulse-slow` | 2 s; está definida e não tem nenhum uso | `frontend/tailwind.config.js:42` |

**Divergências de animação** (efeito não verificado no navegador)
- **`pulse` redefinida.** O CSS global redefine a animação `pulse` com escala até 1,5 e opacidade 0,5 (`index.css:12-24`). É o mesmo nome usado pelo `animate-pulse` do Tailwind. Usos possivelmente afetados:
  - `components/SlideTray.tsx:104`;
  - `pages/CaseViewerPage.tsx:902`;
  - `pages/GuestViewerPage.tsx:237`.
- **Classes de plugins não instalados.** A configuração não tem plugins, mas o código usa classes que dependem deles:
  - `animate-in` e `slide-in-from-bottom-4` (`components/BulkConfirmPanel.tsx:124`);
  - `prose` e `prose-sm` (`components/FirstLoginGate.tsx:131`).

### Camadas da interface (z-index)

| Camada | z-index | Origem |
|---|---|---|
| Interface comum | `z-10` a `z-50` | — |
| Fundo e gaveta do mobile | 60 e 70 | `pages/CaseViewerPage.tsx:977-1004` |
| Modais | 9999 | `components/SettingsModal.tsx:107` |
| Portão de primeiro acesso e confirmações | 10000 | `components/FirstLoginGate.tsx:15`; `components/MaskSelector.tsx:215` |

As camadas dentro do viewer estão em Heatmap e overlay.

## Ícones

**Biblioteca**
- O frontend usa só o `lucide-react`, importado em 31 arquivos, com 73 ícones distintos.
- Ele vai num chunk próprio, junto com o react-hot-toast (`frontend/vite.config.ts:32`).
- A versão não foi verificada, porque o `package.json` ficou fora do escopo.

**Ícones mais usados** (número de arquivos que importam)

| Arquivos | Ícones |
|---|---|
| 14 | X |
| 8 | Loader2 |
| 7 | Check |
| 5 cada | Microscope, FileText, Clock |
| 4 cada | Trash2, Sun, Moon, Globe, ShieldCheck, RefreshCw, ClipboardList, ChevronRight, CheckCircle2, CheckCircle, BarChart3, AlertTriangle, AlertCircle |
| 3 cada | Upload, HelpCircle, ArrowRight, ArrowLeft |

**Ícones com função fixa**

| Uso | Ícone | Origem |
|---|---|---|
| Logo da barra e do acesso de convidado | Microscope | `components/Navigation.tsx:54`; `pages/GuestAccessPage.tsx:69` |
| Logo do cabeçalho do viewer | Cpu | `components/Header.tsx:50` |
| Selo do login (círculo `primary-600`) | ShieldCheck | `components/LoginPage.tsx:289-290` |
| Tema e idioma | Sun e Moon; Globe | `components/Header.tsx:89`, `:97` |
| Itens da barra | Dashboard e Avaliação FM usam o mesmo BarChart3; Fila de Anotação, ClipboardList; Laboratórios, Building2; Usuários, Users; Upload, Upload | `components/Navigation.tsx:65-100` |
| Ferramentas do viewer | Selecionar, Move; Régua, Ruler; Seta, ArrowRight; Marcador, Highlighter; Retângulo, Square; Círculo, Circle; heatmap de tumor, Flame; desfazer, Undo2; apagar, Trash2 | `components/AnnotationToolbar.tsx:7`, `:65-70` |
| Abas do painel | IA, BarChart3; Anotações, Pencil; Laudo, FileText; Colaborar, Users | `components/RightPanel.tsx:370-405` |
| Botões flutuantes do mobile | Layers (lâminas) e BarChart3 (painel) | `pages/CaseViewerPage.tsx:924`, `:937` |

**Tamanhos usados junto de ícones:** `w-4 h-4` (16 px) 80, `w-5 h-5` (20 px) 63, `w-3 h-3` 26, `w-3.5 h-3.5` 25, `w-6 h-6` 15, `w-8 h-8` 6, `w-12 h-12` 4, `w-10 h-10` 3, `w-16 h-16` 2.

**SVG em linha**
- Aparece em 14 arquivos, com grade de 24, traço 2 e pontas arredondadas.
- A barra de ferramentas tem 13 desses ícones (`components/AnnotationToolbar.tsx:77-288`):
  - tela cheia;
  - girar nos dois sentidos;
  - câmera;
  - olho e olho cortado;
  - engrenagem;
  - nuvem com seta;
  - no mobile, X e ajustes.
- O indicador do modo grade tem um ícone de grade (`pages/CaseViewerPage.tsx:893-895`).
- Os desenhos parecem do Heroicons v1 (não verificado).

**Emojis na interface**
- Em toasts:
  - 👆 (`components/SAMOverlay.tsx:180`);
  - ⚠️ (`components/ReportViewer.tsx:245`);
  - ✅ (`components/BatchesPanel.tsx:169`; `pages/AnnotationQueuePage.tsx:83`);
  - 🎯 e 🗑️ (`components/BulkConfirmPanel.tsx:68`, `:102`, `:113`);
  - ⏭️ (`pages/FMAnnotationPage.tsx:191`).
- No contador de envios do upload: ⏫ (`components/SlideUpload.tsx:301`).

**Favicon:** SVG de 32 × 32 com quadrado de raio 6 em #2563eb e um "P" branco em Arial bold 18 (`frontend/public/favicon.svg:1-4`; `frontend/index.html:5`).

Os ícones das extensões estão na seção Extensões.

## Temas

| Item | Valor | Origem |
|---|---|---|
| Temas | Claro (padrão) e Escuro | `i18n/pt.json:17-18`; `contexts/SettingsContext.tsx:17`, `:29` |
| Mecanismo | classe `dark` e `color-scheme` no elemento raiz | `contexts/SettingsContext.tsx:45-48` |
| Persistência | localStorage `pathsolutions_ui_prefs` e perfil do usuário no backend | `contexts/SettingsContext.tsx:28`, `:69-89` |
| Preferência do sistema operacional | não é seguida: o único `matchMedia` do código é o do limite do celular, e não há `prefers-color-scheme` | `hooks/useIsMobile.ts:11` |
| Onde alternar | cabeçalho do viewer, menu do usuário, tela de login | `components/Header.tsx:83-90`; `components/Navigation.tsx:134-145`; `components/LoginPage.tsx:268-275` |
| Idioma | PT (padrão) e EN, nos mesmos lugares e na mesma persistência do tema | `i18n/index.ts:12-27`; `contexts/SettingsContext.tsx:28-29` |

**Cobertura**
- 38 arquivos `.tsx` têm variantes escuras.
- Componentes sem nenhuma variante: ViewerContainer, AnnotationToolbar, AnnotationTools, ScaleBar, CountingGrid, CellCountHUD, BulkConfirmPanel, SAMOverlay, TumorHeatmapOverlay, PasswordStrengthIndicator, CaseViewerPage e AnnotationSessionPage.
- **Sempre escuros:**
  - viewer;
  - sessão de ground truth;
  - HUD de contagem;
  - painel de confirmação em lote;
  - chips de status de lote;
  - fundo do login.
- **Sempre claros:**
  - barra de ferramentas do viewer;
  - grade de contagem;
  - chip "Segmentando" do SAM;
  - indicador de força de senha;
  - barra de rolagem;
  - skeleton.
- As extensões não têm tema escuro.

## Heatmap e overlay

No viewer, três camadas distintas são chamadas de heatmap ou de detecção:
- o heatmap de tumor da IA;
- o heatmap de visualização, que marca no minimapa os campos já vistos;
- as caixas de detecção.

### Heatmap de tumor (IA)

| Parâmetro | Valor | Origem (`components/TumorHeatmapOverlay.tsx`) |
|---|---|---|
| Rampa de cor | transparente → laranja rgb(255,120,40) (#FF7828) → vermelho profundo rgb(200,12,12) (#C80C0C) | :32-33 |
| Gama da cor | 0,7, para avermelhar cedo | :35 |
| Opacidade | opacidade máxima × suavização (smoothstep) de t. t = (prob − prob mínima) / (prob de saturação − prob mínima), limitado a 0–1 | :67, :137-138 |
| Probabilidade mínima | 0,12; abaixo dela, transparente | :93 |
| Opacidade máxima | 0,6 | :94 |
| Probabilidade de saturação | 0,6 | :34, :95 |
| Normalização | nenhuma: a opacidade é absoluta pela probabilidade, sem mínimo ou máximo por lâmina | :16-20 |
| Suavização | 1 texel por patch, desfoque de caixa com raio de 1 patch, filtragem bilinear | :36, :177, :199 |
| Passo padrão | 224 px no nível 0, quando o backend não informa | :218 |
| Teto da textura | 4096 por dimensão | :37 |
| Camada | z-index 950, abaixo das células (997) e das anotações (998) | :60, :96 |
| Modo blocos (reserva, desligado) | matiz HSL 240 × (1 − p), de azul a vermelho, saturação 0,95, luminosidade 0,5, opacidade máxima × p | :29, :84-87, :241 |

**Comportamento**
- É desenhado em PixiJS e acompanha pan, zoom e rotação (`:339-356`).
- Começa desligado (`pages/CaseViewerPage.tsx:55`).
- Só liga pelo botão de chama, que fica vermelho quando ligado (`components/AnnotationToolbar.tsx:250-262`). Não tem atalho de teclado.
- A interface não expõe nenhum parâmetro: o viewer passa só a lâmina, o caso e o estado ligado ou desligado (`pages/CaseViewerPage.tsx:844-848`).
- Não tem legenda nem barra de cores.
- Se o backend responde 404, nada aparece e não há aviso (`:316-337`).

### Heatmap de visualização (campos já vistos)

| Parâmetro | Valor | Origem (`components/ViewerContainer.tsx`) |
|---|---|---|
| Onde aparece | só no minimapa, em canvas com z-index 10 | :434 |
| Cor por aumento | 10x: rgba(34,197,94,0.30), verde. 20x: rgba(59,130,246,0.30), azul. 40x: rgba(239,68,68,0.32), vermelho. São os rgb de #22c55e, #3b82f6 e #ef4444 | :462-465 |
| Registra a partir de | 10x | :398 |
| Amostragem | no máximo a cada 500 ms | :387 |
| Histórico | até 500 registros | :408-409 |
| Lado mínimo da marca | 6 px | :470 |

Vem ligado por padrão (`components/SettingsModal.tsx:28`), e a tecla H alterna (`pages/CaseViewerPage.tsx:255-260`).

### Detecções da IA no viewer

| Tipo | Cor por faixa | Desenho | Origem |
|---|---|---|---|
| Hotspot de Ki67 | acima de 30%: #ef4444; acima de 15%: #f59e0b; demais: #22c55e | borda de 3 px; preenchimento na cor a ≈ 8% (alfa hex 15); brilho de 12 px a ≈ 38% (alfa hex 60); rótulo "Ki67 N%" em branco, 10 px bold, padding 2 × 6 px, raio 3 px; região do tamanho do tile informado pela análise, padrão 1024 px | `components/ViewerContainer.tsx:294-335` |
| H. pylori | confiança a partir de 0,9: #22c55e; a partir de 0,75: #eab308; abaixo: #ef4444 | borda de 2 px; preenchimento a ≈ 13% (alfa hex 20); brilho de 10 px a ≈ 50% (alfa hex 80); rótulo "N%" em branco, 10 px bold, padding 2 × 4 px, raio 3 px; região de 200 px | `components/ViewerContainer.tsx:337-364` |

O botão do olho liga e desliga as detecções e fica verde quando elas estão ligadas. Elas vêm ligadas por padrão (`components/AnnotationToolbar.tsx:229-247`; `components/SettingsModal.tsx:29`).

### Destaque ao navegar entre detecções

- Um anel de 40 px com borda de 3 px #FFEB3B aparece centrado na detecção. Ele pulsa por 1,8 s e é removido após 1800 ms (`components/DetectionNavigator.tsx:70-97`).
- O elemento também recebe a classe de destaque do CSS global, que define 1,2 s (`index.css:26-28`). A animação em linha, de 1,8 s, prevalece pela especificidade do CSS.
- A animação usada é a `pulse` redefinida, com escala até 1,5 (`index.css:12-24`).

### Ki67 fora das caixas

| Onde | Faixas e cores | Origem |
|---|---|---|
| HUD de contagem manual | a partir de 30%: `red-400`; a partir de 5%: `amber-400`; demais: `green-400`; sem valor: `gray-400` | `components/CellCountHUD.tsx:29-33` |
| Painel (grau) | baixo `green-500`; intermediário `amber-500`; alto `red-500`. Barra de 12 px em trilho `gray-200`. Escala de referência ≤5, 5–30 e ≥30, em chips `green-200`, `amber-200` e `red-200` | `components/RightPanel.tsx:585-587`, `:615-618`, `:666-668` |
| Régua do navegador de detecções | gradiente `green-500` → `amber-400` → `red-500`, de 0 a 50%, com marcas em 14% e 30% | `components/DetectionNavigator.tsx:207-225` |
| Diferença entre IA e contagem manual na sessão de ground truth (pontos percentuais) | acima de 10: `red-600`; acima de 5: `amber-600`; demais: `green-600` | `components/GroundTruthPanel.tsx:199-201` |

**Divergência: os limiares de Ki67 mudam conforme o lugar.**
- Caixas no viewer: 15% e 30% (`components/ViewerContainer.tsx:297`).
- HUD: 5% e 30% (`components/CellCountHUD.tsx:31-32`).
- Régua: 14% e 30% (`components/DetectionNavigator.tsx:210-212`).
- Referência do painel: 5 e 30 (`components/RightPanel.tsx:666-668`).

### H. pylori fora das caixas

- Barra de confiança do navegador: gradiente `green-500` → `emerald-400` (`components/DetectionNavigator.tsx:230`).
- Painel: positivo em vermelho e negativo em verde. A intensidade vai de "+" a "++++", em `text-2xl` bold `red-600` (`components/RightPanel.tsx:503-528`).
- Cabeçalho do viewer: quando a análise dá positivo, aparece uma pílula vermelha "H. pylori: POSITIVO", ou "H.p+" no celular (`components/Header.tsx:73-78`).

### Cores das objetivas

| Objetiva | Cor | Tecla | Zoom do viewport | Origem (`components/ObjectiveIndicator.tsx`) |
|---|---|---|---|---|
| 2x | #22c55e | 1 | 1 | :22 |
| 4x | #3b82f6 | 2 | 3 | :23 |
| 10x | #f97316 | 3 | 8 | :24 |
| 20x | #ef4444 | 4 | 15 | :25 |
| 40x | #991b1b | 5 | 30 | :26 |

**Divergência: as cores por aumento não batem.** Nos botões de objetiva, 10x é laranja, 20x é vermelho e 40x é vermelho escuro. No heatmap de visualização do minimapa, 10x é verde, 20x é azul e 40x é vermelho (`components/ViewerContainer.tsx:462-465`).

### Classes de ground truth

O comentário diz que a paleta é "consistente com backend CLASS_COLORS e QuPath" (`components/AnnotationClassSelector.tsx:13`).

| Grupo | Rótulo | Cor | Tecla | Origem (`components/AnnotationClassSelector.tsx`) |
|---|---|---|---|---|
| Tecido | Tumor Viável | #C40000 | T | :17 |
| Tecido | Tumor In Situ | #E84040 | U | :18 |
| Tecido | Estroma | #3F6F6F | S | :19 |
| Tecido | Inflamação | #E9C46A | I | :20 |
| Tecido | Necrose | #264653 | N | :21 |
| Tecido | Artefato | #888888 | A | :22 |
| Tecido | Background (sem tecido) | #CCCCCC | B | :23 |
| Célula | Ki67 + | #E07C47 | P | :27 |
| Célula | Ki67 − | #4895EF | − | :28 |
| Célula | Linfócito | #9B5DE5 | L | :29 |
| Célula | Macrófago | #F15BB5 | M | :30 |
| Célula | Plasmócito | #A3D977 | R | :31 |
| Célula | Endotelial | #007F00 | E | :32 |
| Célula | Apoptótica | #E0251A | Y | :33 |
| Célula | Mitose | #00E040 | F | :34 |

**Pontos de célula** (PixiJS; `hooks/usePixiCellOverlay.ts:19-24`, `:74`, `:147-151`)
- Raio fixo de 6 px na tela; em hover, 9 px com borda branca de 2 px.
- Opacidade 0,9 no ponto manual e 0,5 no ponto da IA.
- Cor de reserva #888888.
- z-index 997.

### Regiões SAM e rótulos FM

| Elemento | Valores | Origem |
|---|---|---|
| Regiões SAM, rótulos conhecidos | tumor #ef4444; h_pylori #f59e0b; inflamacao #f97316; estroma #06b6d4; necrose #6b7280 | `components/SAMOverlay.tsx:120-123` |
| Regiões SAM, demais rótulos | paleta de 20 cores escolhida por hash do nome: #8b5cf6, #ec4899, #22c55e, #3b82f6, #14b8a6, #a855f7, #e11d48, #84cc16, #0ea5e9, #d946ef, #f43f5e, #10b981, #6366f1, #eab308, #0891b2, #c026d3, #fb923c, #2dd4bf, #818cf8, #f472b6 | `components/SAMOverlay.tsx:124-129` |
| Regiões SAM, desenho | preenchimento na cor a 20% (alfa hex 33), contorno na cor, rótulo bold alinhado à direita; pulso de entrada de 0,6 s | `components/SAMOverlay.tsx:138-151`, `:165`, `:256-260` |
| Rótulos da anotação FM | Tumor #ef4444; Inflamação #f97316; H. pylori #f59e0b; Estroma #06b6d4; Necrose #6b7280; Displasia #ec4899; Metaplasia #8b5cf6; Mucosa normal #22c55e; Artefato #94a3b8; Outro #a855f7; cor de reserva #8b5cf6 | `pages/FMAnnotationPage.tsx:26-41` |

### Anotações livres

| Item | Valor | Origem |
|---|---|---|
| Cores disponíveis | #ef4444, #22c55e, #3b82f6 | `components/AnnotationToolbar.tsx:10-12` |
| Cor padrão | #3b82f6; no viewer do convidado, #ef4444 | `components/AnnotationToolbar.tsx:58`; `pages/CaseViewerPage.tsx:82`; `pages/GuestViewerPage.tsx:60` |
| Traço | 3 px, com pontas e junções arredondadas | `components/AnnotationTools.tsx:228-237` |
| Marcador livre | contorno fechado; preenchimento a 30% e traço a 80% | `components/AnnotationTools.tsx:225-227` |
| Seta | ponta de 15 px, aberta 30° | `components/AnnotationTools.tsx:320-321` |
| Rótulo de medida | Arial bold de 13 px, fundo branco a 85%, borda de 1 px na cor da anotação, padding de 4 px | `components/AnnotationTools.tsx:46-72` |
| Camada | canvas com z-index 998 | `components/AnnotationTools.tsx:135` |

### Ordem das camadas no viewer

| Camada | z-index | Origem |
|---|---|---|
| Canvas do heatmap de visualização (minimapa) | 10 | `components/ViewerContainer.tsx:434` |
| Moldura do minimapa | 100 | `components/ViewerContainer.tsx:543` |
| Heatmap de tumor | 950 | `components/TumorHeatmapOverlay.tsx:96` |
| Pontos de célula | 997 | `hooks/usePixiCellOverlay.ts:74` |
| Anotações | 998 | `components/AnnotationTools.tsx:135` |

## Telas e rotas do workspace

### Perfis e permissões

Há três perfis: `admin`, `pathologist` e `tecnico` (`utils/roles.ts:6`). O admin passa em todas as permissões (`:28`).

| Permissão | Perfis, além do admin | Origem (`utils/roles.ts`) |
|---|---|---|
| dashboard, caseViewer | patologista e técnico | :9, :11 |
| upload, deleteRejectedSlides | técnico | :10, :16 |
| caseViewer.annotations, caseViewer.reports, caseViewer.lis | patologista | :12-14 |
| fmAnnotationQueue, fmEvaluation, batches, calibration | patologista | :18-21 |
| caseViewer.qcLabel, deleteSlide, laboratories, users | nenhum (só admin) | :15, :17, :22-23 |

### Rotas

| Rota | Tela | Quem acessa | Layout | Origem |
|---|---|---|---|---|
| qualquer rota protegida, sem sessão | Login | quem não está autenticado | tela cheia | `App.tsx:46-48` |
| (depois do login) | Primeiro acesso | autenticado com troca de senha ou termos pendentes | sobreposição | `App.tsx:50-51`; `components/FirstLoginGate.tsx:150-155` |
| `/privacy` | Privacidade | público | página simples | `App.tsx:67-69` |
| `/reset-password?token=` | Redefinir senha | público | tela cheia | `App.tsx:70-72` |
| `/guest/:shareToken` | Acesso de convidado | convidado, com autenticação própria | tela cheia | `App.tsx:75-81` |
| `/guest/:shareToken/view` | Viewer do convidado | convidado com token | estação de trabalho | `App.tsx:79` |
| `/case/:caseId?slide=N` | Visualizador de caso | admin, patologista e técnico | tela cheia, sem barra de navegação | `App.tsx:55-59`, `:84-95`; `utils/roles.ts:11` |
| `/annotation-session/:caseId/:slideId` (com `batchId` e `batchSlideId` na query) | Sessão de ground truth | qualquer autenticado: a rota não checa permissão | tela cheia | `App.tsx:92` |
| `/` | Dashboard | todos os autenticados | barra de navegação e contêiner | `App.tsx:98`, `:107` |
| `/batches` | Lotes de anotação GT | admin e patologista; sem link na barra | barra e contêiner | `App.tsx:108` |
| `/calibration` | Calibração | admin e patologista; sem link na barra | barra e contêiner | `App.tsx:109` |
| `/qc-calibration` | Calibração de QC | só admin; sem link na barra | barra e contêiner | `App.tsx:110` |
| `/annotation-queue` | Fila de anotação FM | admin e patologista | barra e contêiner | `App.tsx:111` |
| `/fm-annotation/:queueItemId` | Anotação FM | admin e patologista | dentro do layout com barra | `App.tsx:84`, `:112` |
| `/fm-evaluation` | Avaliação FM | admin e patologista | barra e contêiner | `App.tsx:113` |
| `/laboratories` | Laboratórios | só admin | barra e contêiner | `App.tsx:114` |
| `/users` | Usuários | só admin | barra e contêiner | `App.tsx:115`; `pages/UsersPage.tsx:9-11` |
| qualquer outra | redireciona para `/` | — | — | `App.tsx:116` |

O upload não tem rota: é um modal aberto pela barra de navegação.

### Barra de navegação por perfil

| Perfil | Itens | Origem |
|---|---|---|
| Técnico | Dashboard e Upload | `components/Navigation.tsx:24-29` |
| Patologista | Dashboard, Fila de Anotação e Avaliação FM | `components/Navigation.tsx:24-29` |
| Admin | Dashboard, Fila de Anotação, Avaliação FM, Laboratórios, Usuários e Upload | `components/Navigation.tsx:24-29` |

### Moldura comum

**Barra de navegação** (`components/Navigation.tsx`), nas rotas com layout de dashboard
- **Esquerda:** Microscope, "PathSolutions" e o subtítulo "Dashboard de Controle de Qualidade", este só no desktop (`:53-59`; `i18n/pt.json:27`).
- **Links:** estilo "fantasma", com ícone; o ativo ganha fundo branco a 15% (`:39-44`, `:62-92`).
- **Upload:** botão destacado (`:93-103`).
- **Menu do usuário** (`:106-170`):
  - pílula com avatar de iniciais (círculo de 28 px), nome e seta;
  - abre no hover e no clique;
  - a lista tem 224 px, com Alterar Senha, Tema (Claro/Escuro), Idioma (PT/EN) e Sair, em vermelho.
- **Celular:** avatar e menu hambúrguer, com os mesmos itens em lista vertical (`:172-268`).
- **Conteúdo:** contêiner centralizado com padding de 24 px (`App.tsx:103-105`).

**Cabeçalho do viewer** (`components/Header.tsx`)
- Mesma cor da barra; 48 px no celular e 64 px no desktop (`:32-34`).
- **Esquerda** (`:36-56`; `i18n/pt.json:51`):
  - seta "voltar ao dashboard", oculta para o patologista;
  - ícone Cpu, "PathSolutions" e "Visualizador de Lâminas".
  - Para o patologista, clicar no logo não faz nada (`:47`).
- **Centro** (`:59-71`):
  - "Caso" e o identificador em destaque, depois um divisor, "Órgão" e o nome do órgão traduzido;
  - a pílula de H. pylori positivo (ver Heatmap e overlay).
- **Direita:** tema, idioma PT/EN e pílula com iniciais e nome (`:82-111`).

**Elementos globais**
- **Toasts:** ver Cores.
- **Erro de renderização:** "Erro no visualizador", com os botões "Recarregar página" e "Voltar ao Dashboard" (`App.tsx:126`; `components/ErrorBoundary.tsx:56`, `:62`).
- **Título da aba:** "PathSolutions v2.0 - Sistema de Patologia Digital" (`frontend/index.html:10`).
- **Sessão:**
  - é revalidada a cada 5 min (`contexts/AuthContext.tsx:120-138`);
  - o rodapé do login diz "PathSolutions v2.0 — Sessão expira em 3 horas" (`i18n/pt.json:79`); o prazo não foi verificado no backend.

### Login (`components/LoginPage.tsx`)

- **Fundo:** ver Cores, em "Telas com fundo próprio".
- **Canto superior direito:** botões de tema e idioma (`:267-284`).
- **Coluna central** de até 448 px:
  - círculo de 64 px `primary-600` com ShieldCheck, "PathSolutions" e o slogan "Sistema de Patologia Digital" (`:286-294`; `i18n/pt.json:69`);
  - cartão branco, com raio `xl` e sombra `2xl`, contendo (`:297-370`):
    - o título "Entrar";
    - os campos "Usuário ou Email" e "Senha";
    - o botão "Entrar", que vira "Autenticando...";
    - o link "Esqueci minha senha".
- **Usuário:** é convertido para minúsculas antes do envio (`:252-254`).
- **"Esqueci minha senha":** troca o cartão por um formulário de email. O texto avisa que o link expira em 1 h (`components/ForgotPasswordForm.tsx:24`; `i18n/pt.json:571-581`).

### Primeiro acesso (`components/FirstLoginGate.tsx`)

Aparece como sobreposição `gray-900` a 70%, com um cartão de até 512 px e z-index 10000 (`:14-18`).

1. **Troca de senha forçada** (`:20-71`)
   - Campos: senha temporária, nova senha (mínimo de 8 caracteres) e confirmação.
   - Depois da troca, faz logout para um novo login.
2. **Termos** (`:80-148`)
   - Bloco "Recomendações de segurança", com 4 itens; um deles é sobre LGPD.
   - Bloco "Termos de Uso", com versão, alternância PT/EN, caixa rolável e checkbox de aceite.
   - Botão "Aceitar e continuar".

### Redefinir senha e Privacidade

- **`/reset-password`:**
  - mesmo fundo do login;
  - nova senha e confirmação, com indicador de força que exige pelo menos 8 caracteres, uma maiúscula, uma minúscula e um número (`pages/ResetPasswordPage.tsx:12`, `:41`, `:55`, `:78`; `components/PasswordStrengthIndicator.tsx:8-13`).
- **`/privacy`:**
  - política de privacidade da extensão, pública, exigida pela Chrome Web Store;
  - coluna de até 768 px, com 10 seções (`pages/PrivacyPage.tsx:1-4`, `:13-14`; `i18n/pt.json:1094-1155`).

### Dashboard de Controle de Qualidade (`/`, `components/CasesDashboard.tsx`)

Os blocos aparecem nesta ordem, de cima para baixo.

1. **Cartão de título:** "Dashboard de Controle de Qualidade" e subtítulo (`:394-399`).
2. **Cinco indicadores:** 2 colunas no celular e 5 no desktop, com dados do laboratório inteiro (`:87-94`, `:227-262`).

   | Indicador | Destaque | Texto extra | Origem |
   |---|---|---|---|
   | Total de Lâminas | — | nº de casos | `components/CasesDashboard.tsx:403-441` |
   | QC Aprovado | borda de 2 px `accent-500` (#10b981) | — | `components/CasesDashboard.tsx:403-441` |
   | QC Reprovado | borda de 2 px vermelha | — | `components/CasesDashboard.tsx:403-441` |
   | Taxa de Aprovação | — | percentual | `components/CasesDashboard.tsx:403-441` |
   | Em Processamento | roxo | "X de Y concluídos" e, em âmbar, "N p/ revisar" | `components/CasesDashboard.tsx:403-441` |

3. **Cartões por órgão,** com a contagem de casos (`:444-453`).
4. **Filtros:**
   - busca por ID ou nome de arquivo, feita no servidor, com espera de 400 ms (`:132-138`);
   - órgão;
   - status de QC, que filtra só a página já carregada (`:178-198`, `:456-494`).
5. **Tabela no desktop** (`:536-838`)
   - **Colunas:**
     - expandir;
     - Status QC;
     - ID do Caso, com o nome do arquivo embaixo;
     - Órgão;
     - Scanner;
     - Focus Score;
     - Data, em dd/mm/aaaa hh:mm no fuso de São Paulo;
     - Cache;
     - Miniatura. Na linha do caso, essa coluna mostra o alfinete "fixar caso" (`:677-691`).
   - **Chips de status do caso** (`:264-276`, `:602-634`):
     - Processando, com spinner;
     - Na fila, em cinza;
     - Revisar, em âmbar;
     - QC pendente, em âmbar com "?";
     - Aprovado, em `accent`;
     - Reprovado, em vermelho.
   - Admin e técnico também veem um botão de reprocessar (`:591-601`).
   - **Pílula do focus score:** ver Cores (`:643-655`).
   - **Linha do caso:** fica vermelho-clara quando o QC reprovou (`:566`); um clique abre `/case/{id}` (`:567-570`).
   - **Sublinhas por lâmina,** com borda esquerda de 4 px (`:694-838`):
     - X de exclusão, só para admin;
     - chip de QC e chip da coloração;
     - ícone de arquivada;
     - ícone de cache, com o botão "Excluir" quando o QC da lâmina reprovou;
     - miniatura de 64 × 48 px.
   - **No celular:** um cartão por caso, com ID, % de QC, órgão, scanner, chips por lâmina, data e o botão "Ver Detalhes" ou "Ver Problema" (`components/CaseCard.tsx:37-135`).
6. **Paginação:** "Mostrando X a Y de Z", com 10, 25, 50 ou 100 itens por página; o padrão é 10 (`components/PaginationControls.tsx:62-90`; `components/CasesDashboard.tsx:77`).
7. **Caixa de instruções para o técnico** (`:868-878`).
8. **Modal "Excluir lâmina de TODO o sistema":** avisa que a ação é irreversível e que o caso some se for a última lâmina (`:881-919`).

A página se atualiza sozinha a cada 30 s (`:120-128`).

### Modais da barra de navegação

- **Upload** (`components/UploadModal.tsx:22-57`; conteúdo em `components/SlideUpload.tsx:289-466`)
  - Até 896 px de largura e 90% da altura.
  - Rodapé: "Limite: 2 uploads simultâneos | Máx: 3GB por arquivo".
  - Conteúdo:
    - título com contadores;
    - campo "Macroscopia (Opcional)";
    - área de arrastar ou clicar, com borda tracejada;
    - lista de arquivos com barra de progresso: azul durante o envio e amarela em "Salvando no servidor...";
    - botões Tentar Novamente e Remover;
    - caixa "Como funciona", com 5 passos.
- **Alterar Senha** (`components/ChangePasswordModal.tsx:51`, `:70-71`).

### Visualizador de caso (`/case/:caseId`)

É uma coluna em tela cheia com fundo `gray-900` (`pages/CaseViewerPage.tsx:778`). O cabeçalho fica em cima e, embaixo, ficam a bandeja de lâminas, o viewer e o painel de diagnóstico.

**Bandeja de lâminas, à esquerda** (`components/SlideTray.tsx`)

| Item | Valor | Origem |
|---|---|---|
| Largura | 224 px (14rem) | `components/SlideTray.tsx:45-46` |
| Cabeçalho | "Laminas" (texto fixo, sem acento e fora do i18n), X para fechar e chip "N disponíveis" em `green-100` com `green-700` | `components/SlideTray.tsx:49-66` |
| Cartão de lâmina | miniatura com 96 px de altura; selo de categoria no canto superior direito; faixa inferior com o código do bloco e, se houver, o marcador IHC ou Especial | `components/SlideTray.tsx:70-129`, `:90` |
| Lâmina ativa | anel de 2 px `blue-500`, faixa `blue-500` com texto branco e ponto pulsante de 8 px | `components/SlideTray.tsx:80-81`, `:104`, `:110-111` |
| Rodapé | "N/P para navegar" | `components/SlideTray.tsx:133-135` |
| Fechada | vira uma aba azul na borda esquerda; o estado fica em localStorage `slideTrayOpen` | `components/SlideTray.tsx:30-41`; `pages/CaseViewerPage.tsx:62-65` |
| Classificação do selo | precedência Especial → Papanicolau → IHC → HE; cores em Cores | `utils/slideLabel.ts:63-70` |
| Ocultar | configuração "Esconder lista de lâminas" | `pages/CaseViewerPage.tsx:785` |

**Área central (OpenSeadragon)**

| Elemento | Posição e visual | Origem |
|---|---|---|
| Fundo | `gray-900` na área e #1f2937 no contêiner interno; tiles ainda não carregados em #ffffff, para casar com o fundo da lâmina | `components/ViewerContainer.tsx:561`, `:173-174`; `index.css:32` |
| Minimapa | canto configurável, padrão superior esquerdo. Tamanhos: P 156 × 104, M 234 × 130 (padrão), G 312 × 182 px. Fundo #1a1a2e com opacidade 0,9. Moldura de 2 px em preto a 30%, raio de 4 px, sombra de 8 px em preto a 20%, margem de 10 px | `components/ViewerContainer.tsx:99-106`, `:140-141`, `:536-556`; `components/SettingsModal.tsx:26-27` |
| Barra de ferramentas (desktop) | no topo, à direita; passa para a esquerda quando o minimapa está no canto superior direito. Branco a 95% com desfoque leve, raio `lg`, sombra `lg`, padding de 12 × 8 px. Sem variante escura | `components/AnnotationToolbar.tsx:168-171` |
| Botões da barra | 36 px, raio `lg`, ícone de 16 px. Ativo: `blue-500` com texto branco, sombra `md` e escala 1,1. Inativo: hover `gray-100`. Separadores de 1 × 32 px em `gray-300` | `components/AnnotationToolbar.tsx:175`, `:182`, `:294`, `:301-303` |
| Estados ligados | tela cheia `blue-500`; detecções da IA `green-500`; heatmap de tumor `red-500`, cor escolhida para casar com o heatmap | `components/AnnotationToolbar.tsx:176`, `:233`, `:249-254` |
| Outros botões da barra | upload com texto `blue-600` e borda `blue-200`; apagar `red-600` | `components/AnnotationToolbar.tsx:283`, `:352` |
| Seletor de objetiva | pílula branca a 95% (`gray-800` a 95% no escuro), redonda, sombra `lg`, centrada embaixo. Mostra o aumento exato em `text-sm` bold tabular e, acima de 40x, "digital" em 9 px `amber-600` (`amber-300` no escuro). Tem 5 botões redondos de 48 px em `text-sm` bold: o ativo tem fundo na cor da objetiva, texto branco e escala 1,1; os inativos têm texto na cor da objetiva sobre `gray-100` (`gray-700` no escuro). O botão acende a partir de 70% do zoom nominal; o tooltip é "Zoom Nx (Tecla k)". Só no desktop | `components/ObjectiveIndicator.tsx:70`, `:82-115`; `pages/CaseViewerPage.tsx:859` |
| Barra de escala | canto inferior esquerdo. Caixa preta a 55% com desfoque, raio `md`, anel de 1 px branco a 15%, sombra `lg`. Texto branco `text-xs` semibold tabular. Barra branca em forma de "I", com 120 px fixos e traço de 2 px; o valor sai em µm ou mm | `components/ScaleBar.tsx:18`, `:93-104` |
| Etiqueta da lâmina | à direita, abaixo da barra de ferramentas; larguras P 128, M 192 (padrão) e G 256 px; botão de recolher | `components/LabelViewer.tsx:23`, `:28-35`, `:41-60` |
| Navegador de detecções | canto inferior direito; ver Interações do viewer | `pages/CaseViewerPage.tsx:862-871` |
| Modo grade | pílula `blue-600` "MODO GRADE (G)", com ícone de grade | `pages/CaseViewerPage.tsx:891-898`; `i18n/pt.json:758` |
| Varredura rápida | pílula `red-600` pulsante "VARREDURA RÁPIDA", com o botão "Parar (G/ESC)" | `pages/CaseViewerPage.tsx:900-912`; `i18n/pt.json:759-760` |
| Zoom limitado | faixa no topo, `amber-500` a 90% com texto branco: "Zoom máximo limitado — Lâmina arquivada" | `components/ViewerContainer.tsx:569-575` |
| Carregando | `gray-900` a 80%, com spinner branco de 48 px | `components/ViewerContainer.tsx:579-586` |
| Erro | `gray-900` a 90%, "!" em `red-500` `text-4xl` e botão `blue-600`. Antes do erro, há 3 novas tentativas automáticas, a 2, 4 e 6 s | `components/ViewerContainer.tsx:91`, `:194-207`, `:588-612` |
| HUD de contagem | canto inferior direito. `gray-900` a 92% com desfoque, raio `xl`, sombra `2xl`, borda `gray-700`, padding de 12 px, largura mínima de 170 px | `components/CellCountHUD.tsx:36` |
| Grade de contagem | branco a 95% com desfoque, raio `lg`, sombra `xl`, borda `gray-300`. Células de 40 × 40 px; as contadas ficam em `blue-100` com `blue-700`. Grades 3 × 3, 5 × 5 (padrão) e 7 × 7. Sem variante escura. Nada a abre (ver O que não foi encontrado) | `components/CountingGrid.tsx:15-18`, `:61`, `:89`, `:111`, `:124` |

**Controles da barra de ferramentas, em ordem**
1. Tela cheia.
2. Girar 90° no sentido anti-horário e no horário.
3. Capturar foto.
4. Olho "Detecções da IA".
5. Chama "heatmap de tumor (IA)".
6. Configurações.
7. Ferramentas: Selecionar (V), Régua (R), Seta (A), Marcador (F), Retângulo (Q) e Círculo (C) (`components/AnnotationToolbar.tsx:65-70`).
8. Três cores.
9. Contador "N anot.".

A barra só aparece para quem pode anotar, isto é, admin e patologista (`pages/CaseViewerPage.tsx:806`).

**Painel de diagnóstico, à direita** (`components/RightPanel.tsx`)

| Item | Valor | Origem |
|---|---|---|
| Largura | 384 px por padrão, ajustável de 320 a 800 px pela alça da borda esquerda (`blue-500`); fica guardada em localStorage `rightPanelWidth` | `components/RightPanel.tsx:146-147`, `:158-159`, `:184`, `:327-340` |
| Moldura | borda esquerda e sombra `xl` | `components/RightPanel.tsx:323` |
| Fechado | vira uma aba azul na borda direita | `components/RightPanel.tsx:301-314` |
| Cabeçalho | "Painel de Diagnóstico", em Figtree semibold, sobre `gray-50` (`gray-800` a 60% no escuro) | `components/RightPanel.tsx:349-350`; `i18n/pt.json:184` |
| Aba ativa e inativa | ativa: fundo branco, texto e sublinhado de 2 px `blue-600` (`blue-400` no escuro). Inativa: `gray-50` com texto `gray-600` | `components/RightPanel.tsx:365-367` |

| Aba | Ícone | Quem vê | Origem |
|---|---|---|---|
| IA (aba inicial) | BarChart3 | sempre | `components/RightPanel.tsx:91`, `:364` |
| Anotações | Pencil | quem pode anotar | `components/RightPanel.tsx:375` |
| Laudo | FileText | quem pode editar laudo | `components/RightPanel.tsx:387` |
| Colaborar | Users | quem pode editar laudo | `components/RightPanel.tsx:399`; `i18n/pt.json:190` |

**Aba IA,** de cima para baixo:
- cartão rosado "Suspeita de neoplasia (IA)", com as barras "Extensão do achado" e "Pico" (`:419-447`; `i18n/pt.json:194`);
- aviso de lâmina arquivada;
- cartão de QC em verde, vermelho ou amarelo, com o status e a "Qualidade de Foco %" (`:456-486`);
- controle do admin para rotular o foco, com os botões "Com foco", "Sem foco", "Ruim (dobra/corte)" e "Limpar" (`components/FocusLabelControl.tsx:22-26`);
- cartão da análise, que é um destes (`:500-736`; `i18n/pt.json:246`):
  - H. pylori;
  - Ki67;
  - o cartão âmbar genérico "Script específico em desenvolvimento";
- cartão "Macroscopia" (`:740-748`). Ele depende de um campo que o viewer não preenche (`pages/CaseViewerPage.tsx:314-330`); se aparece não foi verificado.

**Aba Anotações:** cartões com ícone, hora, autor, medida, descrição editável e os botões "Ver" e "Excluir" (`:760-894`).

**Aba Laudo** (`components/ReportViewer.tsx:425-680`)
- Cartão "Laudo Microscópico", com o status Rascunho ou "Importado para LIS".
- Botões "Editar Laudo", "Importar para LIS" e "Solicitar 2ª Opinião".
- Texto formatado e aviso de alteração não salva.
- **Editor amplo** (`components/WideReportEditorModal.tsx:139-223`)
  - Modal de 95% × 92% da tela, sobre o viewer.
  - À esquerda, ocupando 3/5: MICROSCOPIA e CONCLUSÃO empilhadas, em fonte monoespaçada.
  - À direita, ocupando 2/5: o seletor de máscaras.
  - Rodapé com Salvar, Importar para LIS e Fechar.
  - Ao fechar com alterações, oferece "Salvar e fechar", "Descartar alterações" e "Continuar editando".
- **Seletor de máscaras** (`components/MaskSelector.tsx:23-231`)
  - Tipo de exame: Histopatologia, Imuno-histoquímica ou Citologia.
  - Até 8 sugestões da IA, com a primeira pré-selecionada.
  - Busca com até 120 resultados.
  - Navegação por seção, subcategoria e letra A–Z, com até 200 itens.
  - Pede confirmação no primeiro uso de cada máscara.
  - Insere o texto sem reescrever.

**Aba Colaborar** (`:911-1092`)
- Caixa azul "Colaboradores", com o modal "Selecionar Médicos".
- Caixa roxa "Compartilhamento Externo": convites ativos, cada um com o botão Revogar, e formulário de nome e email.
- "Chat de Discussão", com 400 px de altura.

**Celular, abaixo de 768 px**
- **Sem bandeja nem painel fixos.** Em vez deles, há dois botões redondos de 48 px em `blue-600`, com contador `red-500` de 20 px e texto de 10 px (`pages/CaseViewerPage.tsx:915-1036`, `:921-934`):
  - o da esquerda abre a bandeja como gaveta de 256 px (`:980`);
  - o da direita abre o painel como folha inferior de até 75% da altura, com raio `2xl` no topo e puxador de 40 × 4 px (`:1004`; `components/RightPanel.tsx:322`, `:346`).
- **Barra de ferramentas:** vira um botão flutuante redondo de 48 px no topo, branco a 95% quando fechado e `gray-700` quando aberto. Ele expande uma lista de itens com raio `lg` e sombra `md`; o item ativo fica em `blue-500` (`components/AnnotationToolbar.tsx:74-166`, `:132-133`, `:151-154`).
- **Sem seletor de objetiva, etiqueta e grade** (`pages/CaseViewerPage.tsx:859`; `index.css:157-184`).

**Configurações do visualizador** (`components/SettingsModal.tsx`)
- Modal de até 672 px, com as seções Exibição, Minimapa, Camadas e Atalhos (`:106-404`).
- Os valores ficam no perfil e em cache, em localStorage `pathsolutions_viewer_settings` (`:32`, `:41-94`).

| Configuração | Padrão | Origem (`components/SettingsModal.tsx`) |
|---|---|---|
| Sempre em tela cheia | não | :21 |
| Sempre girar 90° | não | :22 |
| Esconder lista de lâminas | não | :23 |
| Mostrar etiqueta | sim | :24 |
| Tamanho da etiqueta | 50, numa faixa de 20 a 100; não tem efeito (ver Interações do viewer) | :25, :168-187 |
| Posição do minimapa | superior esquerdo | :26 |
| Tamanho do minimapa | médio | :27 |
| Heatmap de visualização | ligado | :28 |
| Detecções da IA | ligadas | :29 |

### Consulta externa (convidado)

**`/guest/:shareToken`** (`pages/GuestAccessPage.tsx:29-57`, `:64-123`)
- Cartão com raio `2xl` e o ícone Microscope.
- Um único campo para o código de 6 dígitos, em fonte grande, monoespaçada e espaçada.
- Botão "Acessar Caso".
- Trata os erros 401, 410, 429 e 404.

**`/guest/:shareToken/view`** (`pages/GuestViewerPage.tsx`)
- **Cabeçalho:** "Consulta Externa", a coloração com a posição "(i/n)", o nome do convidado, um botão de chat e um botão de sair (`:270-332`).
- **Bandeja:** só aparece com mais de uma lâmina (`:337-345`).
- **Minimapa:** no canto inferior direito. Não há heatmap de visualização nem detecções (`:26-36`).
- **Barra de ferramentas** (`:60`, `:359-374`):
  - sem IA, sem heatmap de tumor e sem configurações;
  - com desfazer e apagar tudo;
  - cor padrão #ef4444.
- **Marcações:** só locais, com um aviso na tela (`:403-410`).
- **Barra de escala:** só com mpp real; sem ele, mostra "escala indisponível" (`:388-397`; `i18n/pt.json:61`).
- **Painel de chat:** 320 px (`:414-434`).

### Anotação, ML e administração (resumo)

| Rota | Conteúdo | Origem |
|---|---|---|
| `/batches` | "Batches de Anotação GT": cartões de lote que expandem, com status, prioridade, prazo e barra de progresso; ações Iniciar, Concluir, + Lâminas e ✕; modais de criação e de seleção de lâminas | `components/BatchesPanel.tsx:246-413`, `:555`, `:727` |
| `/annotation-session/...` | sessão GT de Ki67, em tela escura `gray-950`. Barra flutuante no topo: Voltar, "GT — slide", Anotando/Navegando, Classes, Células/Tecido e "Próxima →". Seletor de classes, contador de células e painel de 288 px com os hotspots do QuPath e o painel Ground Truth, que exige no mínimo 100 células tumorais para enviar | `pages/AnnotationSessionPage.tsx:231-263`, `:397-609` |
| `/calibration` | indicadores, tabela por scanner, recalibrar, ajuste manual, histórico com Reverter e "Como funciona" | `pages/CalibrationPage.tsx:228-486` |
| `/qc-calibration` | limiar ativo de HE e de IHC, reversão e histórico com "Aprovar"; textos fixos em português, sem i18n | `pages/QcCalibrationPage.tsx:50-113` |
| `/annotation-queue` | "Anotação FM": cartão "N lâminas precisam da sua opinião", com estimativa de 2 min por lâmina e o botão "Iniciar sessão"; 4 indicadores; "Popular Fila" para admin | `pages/AnnotationQueuePage.tsx:114-268` |
| `/fm-annotation/:id` | faixa de instrução e barra superior com cronômetro; viewer em fundo preto, com segmentação SAM por clique; painel de 288 px com paleta de rótulos, laudo, "Modelo Pergunta" e lista de regiões; barra inferior com Voltar, Pular, Concluir e Próxima | `pages/FMAnnotationPage.tsx:258-551`, `:302`, `:352` |
| `/fm-evaluation` | indicadores, tabela por órgão com "Retreinar" e histórico de modelos com "Ativar" | `pages/FMEvaluationPage.tsx:97-262` |
| `/laboratories` | formulário com Nome, Slug, Email e Ativo, e uma tabela | `pages/LaboratoriesPage.tsx:121-231` |
| `/users` | filtros de busca, laboratório e status; formulário com nome, email, username, senha, especialidade, CRM, perfil (Patologista, Técnico QC ou Administrador) e laboratório; tabela | `components/PathologistManagement.tsx:54-56`, `:176-461` |

**Divergências de rota e permissão**
- `/annotation-session` não checa permissão (`App.tsx:92`).
- `/fm-annotation` usa a altura da tela inteira, mas é renderizada sob a barra de navegação (`pages/FMAnnotationPage.tsx:259`).
- A fila de anotação decide se o usuário é admin lendo o localStorage, não o contexto de autenticação (`pages/AnnotationQueuePage.tsx:47-55`).

## Fluxos principais

### Abrir caso

1. **No PathoWeb:**
   - a extensão detecta o caso, consulta as lâminas e mostra o botão flutuante com a contagem;
   - o clique abre `/case/{caso}` em nova aba (`ea/scripts/fab.js:84-93`);
   - um item de "Colaborações Pendentes" ou a notificação do sistema levam à mesma URL (`ea/scripts/collab-panel.js:688-693`, `:778-797`).
2. **Pelo dashboard:** um clique na linha ou no cartão abre o caso na mesma aba (`components/CasesDashboard.tsx:518-521`, `:567-570`).
3. **Sem sessão:** o login aparece no lugar da página, ou o token vem da extensão (`ea/scripts/auth-sync.js:13-76`). Depois vêm o portão de primeiro acesso e a checagem da permissão de abrir casos (`App.tsx:46-59`).
4. **Carregamento:** a primeira lâmina aparece logo; resultados e laudo chegam em segundo plano; as demais lâminas são pré-aquecidas (`pages/CaseViewerPage.tsx:286-355`).
5. **Lâmina inicial:** o parâmetro `?slide=N` escolhe a lâmina e é atualizado a cada troca (`pages/CaseViewerPage.tsx:56-59`, `:134-148`).

### Ver lâmina

1. A lâmina abre na visão geral (`components/ViewerContainer.tsx:185-187`).
2. A navegação é por objetivas, teclado ou mouse (ver Atalhos de teclado e Interações do viewer).
3. A troca de lâmina é pela bandeja ou por N/P. Os resultados e o laudo da lâmina são recarregados (`pages/CaseViewerPage.tsx:379-414`).
4. Há rotação, foto em PNG com as anotações e tela cheia (`pages/CaseViewerPage.tsx:578-619`).
5. Para anotar, escolhe-se a ferramenta e desenha-se na lâmina. Cada anotação é gravada no servidor, por lâmina (`pages/CaseViewerPage.tsx:444-474`).

### Ver heatmap

1. **Heatmap de tumor:** o botão de chama busca o heatmap da lâmina e o desenha por cima (`components/TumorHeatmapOverlay.tsx:316-337`). Não há legenda nem aviso quando o heatmap não existe.
2. **Heatmap de visualização:** já vem ligado no minimapa; a tecla H alterna.
3. **Detecções:** já vêm ligadas; o navegador de detecções aparece no canto inferior direito.

Os valores estão em Heatmap e overlay.

### Revisar

- **"Revisar" no dashboard** é estado do pipeline (revisão necessária ou falha), não revisão clínica (`components/CasesDashboard.tsx:264-269`).
- **O laudo** é revisado na aba Laudo ou no editor amplo, com o seletor de máscaras.
- **Marcador da IA** (`utils/aiMarker.ts:1-46`; `components/ReportViewer.tsx:215-239`)
  - O texto da IA entra no laudo com o marcador "【SUGESTÃO IA …】".
  - "Manter" tira o marcador e a "(confiança XX%)"; "Apagar" tira a linha.
  - Enquanto houver marcador, a importação fica bloqueada.
  - O veredito vai para o backend.
- **"Solicitar 2ª Opinião" no laudo** usa uma lista fixa de médicos fictícios (`components/ReportViewer.tsx:63-69`, omitida aqui) e só mostra um toast, sem chamar a API (`:296-315`).
- **A colaboração real** fica na aba Colaborar: o colega convidado vê o caso no painel da extensão (`components/RightPanel.tsx:234-247`).

### Assinar

**O workspace não tem assinatura**
- Os textos dizem que a assinatura acontece no PathoWeb (`components/ReportViewer.tsx:4`; `i18n/pt.json:1015`, `:1025`).
- A função de assinar existe na camada de API, mas nenhuma tela a chama (`utils/api.ts:57-66`).

**Caminho real**
1. "Importar para LIS" envia microscopia e conclusão separadas ao backend (`components/ReportViewer.tsx:224-258`).
2. No PathoWeb, a extensão vê a importação pendente e busca o texto.
3. A extensão mostra o painel de importação, com o botão da seção ativa.
4. O clique substitui o conteúdo do editor do PathoWeb (`ea/scripts/page-bridge.js:96`).
5. Com as duas seções feitas, ou ao clicar "Fechar", a extensão confirma a importação no backend.
6. O patologista assina no próprio PathoWeb (`ea/scripts/report-importer.js:12-18`, `:77-184`, `:370-491`).

**Erros**
- Qualquer erro que não seja 409 mostra "Laudo aprovado (LIS offline - será sincronizado)" e marca o laudo como importado (`components/ReportViewer.tsx:272-277`; `components/WideReportEditorModal.tsx:132-135`; `i18n/pt.json:1035`, `:1068`).
- A sincronização posterior não foi verificada.
- "Importado" é só estado local: o laudo sempre reabre como Rascunho (`components/ReportViewer.tsx:57`).

### Enviar lâmina

1. Admin ou técnico clica em "Upload" na barra, e o modal abre. A macroscopia é opcional.
2. **Validação** (`components/SlideUpload.tsx:33-35`, `:104-142`):
   - formatos .svs, .ndpi, .scn e .mrxs;
   - até 3 GB por arquivo;
   - nome só com letras, números, hífen e sublinhado;
   - o caso é derivado do prefixo do nome: até 3 letras seguidas de 6 ou mais dígitos.
3. **Envio** (`components/SlideUpload.tsx:35`, `:37-69`, `:155-246`, `:198`):
   - até 2 envios simultâneos;
   - multipart pela API, com timeout de 30 min;
   - renovação da sessão a cada 5 min.
   - A WSI passa pela API; a regra da v3 é upload direto ao Blob.
4. **Ao terminar:** aparece um toast. O dashboard só se atualiza no ciclo de 30 s (`components/Navigation.tsx:274-276`).

## Atalhos de teclado

### Visualizador de caso

Até quatro ouvintes de teclado ficam ativos ao mesmo tempo:
- o hook de navegação;
- a página;
- o seletor de objetivas;
- o navegador de detecções, quando há detecções.

Todos ignoram o teclado com foco em campo de texto. O hook também ignora campos de seleção e conteúdo editável (`hooks/useKeyboardNavigation.ts:61-62`; `pages/CaseViewerPage.tsx:193-194`).

| Tecla | Ação | Origem |
|---|---|---|
| ↑ ↓ ← → ou W S A D | move a vista 50%; com Shift, 75%; no modo grade, 100%. No máximo um movimento por quadro | `hooks/useKeyboardNavigation.ts:31-56`, `:69-99` |
| + ou = / − ou _ | zoom ×1,2 / ÷1,2 | `hooks/useKeyboardNavigation.ts:15`, `:116-126` |
| 0 ou Home | vista inicial (lâmina inteira) | `hooks/useKeyboardNavigation.ts:127-135` |
| 1 a 5 | objetivas 2x, 4x, 10x, 20x e 40x; há dois ouvintes (ver Conflitos) | `components/ObjectiveIndicator.tsx:49-64`; `hooks/useKeyboardNavigation.ts:136-150` |
| Espaço | só impede a rolagem da página | `hooks/useKeyboardNavigation.ts:109-113` |
| V (sem Shift) | Selecionar; na prática, só devolve a navegação por mouse | `pages/CaseViewerPage.tsx:201-203`; `components/AnnotationTools.tsx:364-369` |
| R | Régua | `pages/CaseViewerPage.tsx:204-206` |
| F | Marcador livre | `pages/CaseViewerPage.tsx:207-209` |
| Q | Retângulo | `pages/CaseViewerPage.tsx:210-212` |
| C | Círculo | `pages/CaseViewerPage.tsx:213-215` |
| Esc | solta a ferramenta e para a varredura rápida | `pages/CaseViewerPage.tsx:216-219` |
| N / P | próxima / anterior lâmina. Só com mais de uma lâmina e sem detecções de H. pylori visíveis | `pages/CaseViewerPage.tsx:197`, `:222-235` |
| N / P, com o navegador de detecções aberto | próxima / anterior detecção; no fim, volta ao início | `components/DetectionNavigator.tsx:103-122` |
| G | liga e desliga o modo grade | `pages/CaseViewerPage.tsx:247-251` |
| Shift+G | liga e desliga a varredura rápida | `pages/CaseViewerPage.tsx:239-246` |
| H | liga e desliga o heatmap de visualização do minimapa; não é o heatmap de tumor | `pages/CaseViewerPage.tsx:255-260` |
| Ctrl/Cmd+Z | desfaz a última mudança nas anotações, só no estado local | `pages/CaseViewerPage.tsx:263-272`, `:506-518` |
| Ctrl/Cmd+Shift+Z | refaz, só no estado local | `pages/CaseViewerPage.tsx:265-266`, `:521-532` |

- R, F, C, G e H não agem com Ctrl/Cmd. Q, N e P não checam modificadores (`pages/CaseViewerPage.tsx:204-260`).
- **Varredura rápida** (`pages/CaseViewerPage.tsx:622-666`, `:900-912`):
  - vai ao zoom 15, que corresponde a 20x;
  - a cada 800 ms, avança 80% da largura, em linhas da esquerda para a direita e de cima para baixo, até o fim da lâmina;
  - para com Esc, com Shift+G ou com o botão "Parar".

### Viewer do convidado (`pages/GuestViewerPage.tsx`)

| Tecla | Ação | Origem |
|---|---|---|
| Ctrl/Cmd+Z | desfaz a última marcação da lâmina atual; as marcações ficam só na sessão | `pages/GuestViewerPage.tsx:54-58`, `:150-156`, `:163-173` |
| 1 a 5 | objetivas; aqui não há conflito, porque o hook de navegação não é usado | `pages/GuestViewerPage.tsx:399` |

Não há atalhos de navegação nem de ferramenta. Setas, WASD, +/−, 0/Home, V/R/F/Q/C, N/P, G e H não têm tratamento, embora os tooltips mostrem as letras (`components/AnnotationToolbar.tsx:305-306`). Se os atalhos nativos do OpenSeadragon funcionam aqui não foi verificado.

### Sessão de ground truth (`pages/AnnotationSessionPage.tsx`)

| Tecla | Ação | Origem |
|---|---|---|
| Esc | alterna entre anotar e navegar, com aviso de 1,2 s | `pages/AnnotationSessionPage.tsx:231-244` |
| Ctrl/Cmd+Z (só com "z" minúsculo) | remove o último ponto manual e o apaga no servidor se já estava gravado; pilha de 50 | `pages/AnnotationSessionPage.tsx:203`, `:246-259` |
| Modo Tecido: T U S I N A B | Tumor Viável, Tumor In Situ, Estroma, Inflamação, Necrose, Artefato, Background | `components/AnnotationClassSelector.tsx:16-24`, `:71-77` |
| Modo Célula: P − L M R E Y F | Ki67 +, Ki67 −, Linfócito, Macrófago, Plasmócito, Endotelial, Apoptótica, Mitose | `components/AnnotationClassSelector.tsx:26-35`, `:78-85` |

- As teclas de classe funcionam mesmo com o painel escondido e não checam modificadores (`components/AnnotationClassSelector.tsx:63-91`).
- Esta tela não tem teclado de zoom ou pan nem seletor de objetivas (`pages/AnnotationSessionPage.tsx:13-19`).

### Anotação FM com SAM

- Enter no campo de rótulo novo adiciona e ativa o rótulo (`pages/FMAnnotationPage.tsx:399`).
- O comentário do componente promete Shift+arrastar para pan, rolagem para zoom e Ctrl+Z para desfazer (`components/SAMOverlay.tsx:4-12`). Na prática:
  - não há tratamento de Ctrl+Z: a pilha de desfazer, de até 20 itens, é preenchida e nunca usada (`:59`, `:212-215`; `pages/FMAnnotationPage.tsx:75`);
  - Shift só faz o clique ser ignorado (`components/SAMOverlay.tsx:177`).

### Extensões

| Tecla | Onde | Ação | Origem |
|---|---|---|---|
| Ctrl/Cmd+S (só com "s" minúsculo) | módulo de exame do PathoWeb | captura a macroscopia 300 ms depois, sem bloquear o salvar do PathoWeb | `em/scripts/macroscopy_listener.js:160-165`, `:203-221` |
| Enter | login do painel de colaboração | no campo de usuário, vai para a senha; na senha, entra | `ea/scripts/collab-panel.js:398-403` |

Nenhum dos dois manifests declara atalhos de navegador (`ea/manifest.json`; `em/manifest.json`).

### Conflitos e divergências

1. **As teclas 1 a 5 têm dois ouvintes, com alvos diferentes.**
   - O hook leva aos zooms 2, 4, 10, 20 e 40 (`hooks/useKeyboardNavigation.ts:136-150`). Pela régua de magnificação, isso equivale a ≈ 3x, 5x, 13x, 27x e 53x, este já digital (`utils/magnification.ts:15-21`, `:46-66`).
   - O seletor leva a 1, 3, 8, 15 e 30 (`components/ObjectiveIndicator.tsx:21-27`, `:54-58`).
   - Qual prevalece não foi verificado. Hipótese: o seletor, porque se registra depois.
2. **A Seta anuncia o atalho A** (`components/AnnotationToolbar.tsx:67`), mas A move a vista para a esquerda (`hooks/useKeyboardNavigation.ts:90-94`), e nenhuma tecla seleciona a Seta.
3. **N/P podem acionar dois ouvintes num caso de Ki67 com hotspots e várias lâminas.** A página só desliga a troca de lâmina quando há detecções de H. pylori (`pages/CaseViewerPage.tsx:197`), e o navegador também monta para Ki67. Os dois reagem; o efeito combinado não foi verificado.
4. **A ajuda descreve o G de outro jeito.**
   - Ela diz "Segure G + setas" e "G+Seta" (`i18n/pt.json:342`, `:330`), mas no código G liga e desliga.
   - O botão diz "Parar (G/ESC)" (`i18n/pt.json:760`), mas quem para é Shift+G ou Esc.
5. **H muda só o estado da página e não grava a configuração;** quem grava é o modal (`pages/CaseViewerPage.tsx:255-259`; `components/SettingsModal.tsx:72-94`). Se o modal mostra a mudança feita por H não foi verificado.
6. **Desfazer e refazer não chamam a API,** mas criar e excluir anotação gravam no servidor (`pages/CaseViewerPage.tsx:455-473`, `:487`, `:506-532`).
7. **Sem permissão de anotação, como no caso do técnico, a barra inteira some,** inclusive tela cheia, rotação, captura, detecções e heatmap de tumor (`pages/CaseViewerPage.tsx:43`, `:806-826`).
8. **A lista de atalhos do modal está incompleta:** faltam N/P, Ctrl+Z, Ctrl+Shift+Z, G sozinho, Espaço e a Seta (`components/SettingsModal.tsx:322-389`).
9. **O comentário do seletor de classes não bate com as teclas configuradas.** Ele lista X no lugar de R e não lista U (`components/AnnotationClassSelector.tsx:5`). Valem as teclas da tabela (`:18`, `:31`).
10. **No convidado, Ctrl+Z não ignora campos de texto** (`pages/GuestViewerPage.tsx:165-170`). Pelo código, no campo do chat ele desfaria a marcação e bloquearia o desfazer do texto (não verificado).

## Interações do viewer

Quatro telas usam o mesmo contêiner OpenSeadragon (`components/ViewerContainer.tsx`):
- o visualizador de caso;
- o viewer do convidado;
- a sessão de ground truth;
- a anotação FM.

As extensões não têm viewer.

### Zoom, pan e minimapa

| Parâmetro | Valor | Origem (`components/ViewerContainer.tsx`) |
|---|---|---|
| Gestos (rolagem, arrastar, clique para zoom, pinça) | padrão do OpenSeadragon; o código não configura gestos | :128-176 |
| Animação | 0,3 s, com rigidez da mola 10 | :151, :154 |
| Afastamento máximo | imagem com 80% do tamanho da área | :145 |
| Ampliação máxima | 40 px de tela por pixel da imagem | :146 |
| Restrição | a imagem não sai da área visível, nem durante o arraste | :147-148 |
| Botões nativos do OpenSeadragon | escondidos; as imagens deles apontam para a versão 4.1.0 no jsDelivr | :130, :157 |
| Ao abrir a lâmina | volta à vista inicial | :185-187 |
| Interação no minimapa | padrão do OpenSeadragon (não verificada) | :134-141 |

- A versão instalada do OpenSeadragon não foi verificada.
- O código assume pinça no celular (`pages/CaseViewerPage.tsx:858`).

### Rotação

- Botões de ±90° na barra; não há atalho de teclado (`components/AnnotationToolbar.tsx:192-213`; `pages/CaseViewerPage.tsx:578-590`).
- A configuração "Sempre rotacionar 90°" aplica 90° a cada lâmina aberta (`pages/CaseViewerPage.tsx:155-178`).
- A etiqueta gira junto com a lâmina (`components/LabelViewer.tsx:73`, `:83`).
- O botão "Ver" de uma anotação restaura o zoom e a rotação gravados, ou vai ao zoom 20 quando não há registro (`components/RightPanel.tsx:855-877`).
- Essa restauração não atualiza o estado de rotação que os botões e a etiqueta usam (`pages/CaseViewerPage.tsx:98`). Pode haver divergência entre eles (não verificado).

### Medida e desenho (`components/AnnotationTools.tsx`)

**Como se desenha**
- Com uma ferramenta ativa, exceto Selecionar, a navegação por mouse é desligada. Desenha-se apertando, arrastando e soltando (`:363-558`).
- Só há eventos de mouse: não há toque nem caneta.
- Ao soltar com pelo menos 2 pontos, a anotação é criada e guarda o centro, o zoom e a rotação da vista. Depois a ferramenta se solta sozinha (`:517-536`; `pages/CaseViewerPage.tsx:451-452`).

**Medidas**
- **Régua** (`:20-24`, `:290-309`, `:461-475`; `utils/annotationMath.ts:160-188`):
  - com o mpp real da lâmina: µm abaixo de 1 mm; mm com 2 casas abaixo de 10 mm; mm com 1 casa acima disso;
  - sem mpp: px.
- **Áreas de retângulo, círculo (centro e raio) e marcador** (`:243-289`; `utils/annotationMath.ts:122-154`):
  - com mpp: µm² abaixo de 1 mm²; mm² abaixo de 100 mm²; cm² acima disso;
  - sem mpp: px² ou Mpx².
- **Marcador livre:** registra pontos com pelo menos 5 px de imagem entre si (`:98`, `:398-407`).

**Edição na aba Anotações:** clicar na descrição abre a edição, e "Excluir" pede confirmação (`components/RightPanel.tsx:840-853`, `:882-886`; `pages/CaseViewerPage.tsx:478`).

**Divergência: o comportamento sem mpp muda conforme o lugar.**
- A barra de escala assume 0,226 µm/px (`components/ScaleBar.tsx:29`; `pages/CaseViewerPage.tsx:854`).
- A régua passa a medir em px.
- O viewer do convidado esconde a escala.

### Camadas

Todas as camadas são só liga/desliga. Não há seletor de camadas nem controle de opacidade.

- **Detecções da IA:** botão do olho e configuração (`components/AnnotationToolbar.tsx:229-247`; `components/ViewerContainer.tsx:526-530`; `components/SettingsModal.tsx:302-318`).
- **Heatmap de tumor:** só pelo botão da chama; começa desligado.
- **Heatmap de visualização:** tecla H ou configuração.
- **Etiqueta da lâmina:** liga e desliga na configuração; no próprio quadro há os tamanhos P/M/G e um botão de recolher (`components/LabelViewer.tsx:41-60`; `pages/CaseViewerPage.tsx:874-880`).
  - O slider "Tamanho da etiqueta" grava um valor que nenhum componente lê (`components/SettingsModal.tsx:168-187`; `components/LabelViewer.tsx:23-32`).
- **Grade de contagem** (`components/CountingGrid.tsx:15-18`, `:21-71`, `:101-143`):
  - arrasta pelo cabeçalho;
  - clique soma 1 e botão direito subtrai 1;
  - tamanhos 3 × 3, 5 × 5 e 7 × 7;
  - botão Limpar.
  - Nada abre a grade: a ferramenta interna que a ativa não é enviada por nenhum botão nem tecla (`pages/CaseViewerPage.tsx:88-95`).

### Navegador de detecções (`components/DetectionNavigator.tsx`)

| Entrada | Efeito | Origem |
|---|---|---|
| Quando aparece | com detecções reais de H. pylori ou com hotspots de Ki67, desde que as detecções estejam ligadas | `pages/CaseViewerPage.tsx:764-775`, `:862-871` |
| Botões "← Anterior" e "Próxima →" | vão para a detecção anterior ou seguinte, sem voltar ao início; ficam desabilitados nas pontas | `components/DetectionNavigator.tsx:155-189` |
| Campo numérico | pula para a detecção de número N | `components/DetectionNavigator.tsx:165-178` |
| Slider | confiança mínima de 0 a 100% (de 0 a 50% no Ki67); ao mudar, volta ao item 1 | `components/DetectionNavigator.tsx:253-265` |
| Ir para uma detecção | centraliza mantendo o zoom e mostra o destaque amarelo (ver Heatmap e overlay) | `components/DetectionNavigator.tsx:40-100` |

### Troca de lâmina, chat e outros botões

**Troca de lâmina**
- Clique na miniatura da bandeja. O índice da lâmina vai para o parâmetro `slide` da URL (`components/SlideTray.tsx:77-79`; `pages/CaseViewerPage.tsx:56-59`, `:134-148`, `:150-153`).
- No celular, o botão do canto inferior esquerdo mostra quantas lâminas há e abre a gaveta. Tocar numa lâmina troca a lâmina e fecha a gaveta (`pages/CaseViewerPage.tsx:918-928`, `:974-995`).

**Chat** (`components/CollaborationChat.tsx:112-117`, `:141-173`, `:211-224`, `:236-245`, `:252`)
- A opção "Incluir localização atual da lâmina" anexa centro, zoom e lâmina à mensagem.
- O botão "Localização" troca de lâmina quando preciso, esperando até 5 s pela abertura, e vai ao ponto sem animação.
- Enter envia a mensagem.

**Outros botões**
- **Tela cheia:** a configuração "sempre em tela cheia" tenta entrar ao carregar (`pages/CaseViewerPage.tsx:180-187`, `:564-570`).
- **Captura:** gera um PNG da vista com as anotações por cima (`pages/CaseViewerPage.tsx:593-619`).
- **Menu do celular** (`components/AnnotationToolbar.tsx:74-165`):
  - tem tela cheia, captura, IA, heatmap de tumor, configurações, régua, seta, marcador e retângulo;
  - não tem círculo, Selecionar nem rotação.

### Viewer do convidado

- **Barra:** tela cheia, ±90°, captura com as marcações, ferramentas, cores, desfazer e apagar tudo com confirmação (`pages/GuestViewerPage.tsx:158-161`, `:359-374`).
- **Chat:** liga e desliga no cabeçalho (`:315-321`).

### Sessão de ground truth

- **Início:** a tela começa em modo de navegação (`pages/AnnotationSessionPage.tsx:59`).
- **Modo anotação** (`:164-226`, `:266-271`, `:392`, `:400`):
  - a navegação por mouse é desligada e o cursor vira cruz;
  - o clique esquerdo marca um ponto da classe ativa, só no modo Célula;
  - os outros botões do mouse são ignorados;
  - o menu de contexto fica bloqueado sobre o viewer.
- **Modo Tecido:** trocar para ele sai do modo anotação. Esta tela não desenha regiões de tecido (`:273-276`).
- **Hotspots:** anterior e próximo, voltando ao início no fim; o clique na lista centraliza mantendo o zoom (`:281-294`, `:519-569`).
- **Hover nos pontos:** o hook dos pontos aceita destaque em hover, mas a página não informa o ponto em hover (`hooks/usePixiCellOverlay.ts:61`).

### Anotação FM com SAM

- **Paleta:** um clique escolhe ou solta o rótulo (`pages/FMAnnotationPage.tsx:377`).
- **Segmentação:** um clique rápido com o botão esquerdo, sem Shift nem Ctrl, segmenta com o rótulo ativo e salva. Sem rótulo ativo, aparece um aviso (`components/SAMOverlay.tsx:170-240`).
- **Clique-para-zoom:** fica desligado enquanto o SAM está montado (`:62-72`).
- **Cursor:** vira cruz quando há rótulo ativo (`:280-285`).
- **Lista de regiões:** um X aparece no hover e remove a região (`pages/FMAnnotationPage.tsx:492-507`).
- **Painel de patches semelhantes:** começa com todos selecionados; em "Revisar", clicar na miniatura marca ou desmarca (`components/BulkConfirmPanel.tsx:33-35`, `:153`, `:213-269`).
- **Faixa de instrução:** pode ser fechada, e isso fica salvo no navegador (`pages/FMAnnotationPage.tsx:87-89`, `:216-219`).

## Extensões (assistant e macroscopy)

Nenhuma das duas extensões tem popup, atalho de navegador, tema escuro ou viewer. As duas usam o mesmo gradiente roxo de marca, diferente das cores do app.

### PathSolutions Assistant (`ea/`)

**Manifest e página de opções**
- **Manifest:**
  - versão 1.5.0 (`ea/manifest.json:4`);
  - permissões activeTab e storage;
  - hosts: PathoWeb, o domínio do app, localhost, trycloudflare e um domínio antigo de terceiro (`ea/manifest.json:2-17`).
- **Página de opções** (`ea/options/options.html:9-46`; `ea/options/options.css:16-32`; `ea/options/options.js:8-69`):
  - coluna de 520 px;
  - cabeçalho no gradiente da marca, com a versão "v1.2.0";
  - campos:
    - URL do Backend;
    - URL do Frontend;
    - Intervalo de Verificação, de 2000 a 60000 ms, padrão 5000;
    - Campo CKEditor de Microscopia, padrão `microFragmento`;
  - botões Salvar e Testar Conexão.

**Valores visuais**

| Elemento | Valores | Origem |
|---|---|---|
| Gradiente da marca | 135°, #667eea → #764ba2. Aparece no cabeçalho do painel, nos botões, no FAB, no toast de informação e nas opções | `ea/styles/collab-panel.css:21`, `:103`, `:268`; `ea/styles/fab.css:16`; `ea/styles/toast.css:36`; `ea/options/options.css:26`, `:104` |
| Hover nas opções | #5a6fd6 → #6a4096 | `ea/options/options.css:109` |
| #667eea sozinho | foco de campo, ícones, contador, spinner | `ea/styles/collab-panel.css:92-93`, `:145`, `:196`, `:200`, `:327` |
| Fonte das opções, do FAB e dos toasts | pilha do sistema: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif | `ea/options/options.css:10`; `ea/styles/fab.css:55`; `ea/styles/toast.css:11` |
| FAB | círculo de 56 px no gradiente, a 90 px do rodapé e 24 px da direita, z-index 999. Sombra de 16 px em #667eea a 40%; no hover, sombra de 20 px a 60% e escala 1,08. Microscópio em SVG de 28 px. Contador #ef4444 de 20 px com o nº de lâminas | `ea/styles/fab.css:3-57`; `ea/scripts/fab.js:13` |
| Toasts | canto superior direito; 13 px semibold; raio de 8 px; sombra de 16 px em preto a 20%. Largura de até 360 px, ou 420 px com ações. Ficam 4 s e saem em 0,3 s. Gradientes: sucesso #11998e → #38ef7d; erro #e53e3e → #fc5c7d; informação no gradiente da marca. Botões de ação brancos com texto #059669, ou brancos a 25% | `ea/styles/toast.css:3-44`, `:76-84`; `ea/scripts/toast.js:28-31` |
| Painel de colaboração | fundo #fff, borda #d2d6de, raio de 3 px, sombra de 1 px em preto a 10%. Fonte Source Sans Pro, Helvetica Neue, Helvetica, Arial, 13 px, texto #333. Selo "PS" em branco a 20%, raio de 4 px, 11 px bold. Contador #ef4444 que pulsa a cada 2 s. Erro: #fff5f5, #c53030, #fed7d7. Cinzas de #555 a #f5f5f5. Item novo destacado em #667eea a 15% por 2 s. Spinner de 14 px em #ddd com topo #667eea, 0,8 s | `ea/styles/collab-panel.css:6-16`, `:32-63`, `:123-131`, `:140-347`; `ea/scripts/collab-panel.js:310` |
| Painel de importação de laudo | fundo #fff; borda de 2 px na cor da seção (microscopia #059669, conclusão #2563eb); raio de 12 px; 300 px de largura, a 80 px do rodapé e 20 px da direita; sombra de 32 px em preto a 18%. Título #1e1b4b, 14 px bold. Botão principal na cor da seção, com raio de 8 px. Botão Fechar em #f3f4f6, #374151 e #d1d5db. Status em #9ca3af, #374151 e #6b7280. z-index 999999 | `ea/scripts/report-importer.js:243-366` |
| Página de opções | fundo #f5f5f5, texto #1a202c. Cartão branco, raio de 12 px, sombra de 12 px em preto a 8%. Título de 20 px bold. Rótulos de 13 px semibold em #4a5568. Campos com borda #e2e8f0 e raio de 8 px; foco #667eea com halo de 3 px a 15%. Dicas de 11 px em #a0aec0. Botão secundário #edf2f7 com #4a5568. Status: sucesso #f0fff4, #276749, #c6f6d5; erro #fff5f5, #c53030, #fed7d7; informação #ebf8ff, #2b6cb0, #bee3f8 | `ea/options/options.css:9-145` |
| Ícones | microscópio em SVG em linha (parece o Microscope do lucide; não verificado). Classes Font Awesome da página hospedeira: `fa-user-md` (#667eea, 14 px) e `fa-bell` (12 px), com os emojis 🧑‍⚕️ e 🔔 de reserva. "×" para sair. ✓, ○ e ✕ no importador. PNGs de 16, 48 e 128 declarados no manifest (não abertos) | `ea/scripts/fab.js:13`; `ea/scripts/collab-panel.js:494-500`, `:517`, `:532-536`; `ea/scripts/report-importer.js:265-359`; `ea/manifest.json:65-69` |

**Comportamento no PathoWeb** (só em `/moduloExame/`; `ea/manifest.json:21-52`)
1. **Detector de caso, sem interface** (`ea/scripts/case-detector.js:27-111`; `ea/scripts/settings-bridge.js:11-12`).
   - Lê o número do caso no contêiner de dados do paciente da barra de ferramentas.
   - O formato é "A ou H seguido de 8 a 9 dígitos".
   - Varre a página a cada 2 s durante 60 s e depois a cada 10 s.
2. **Verificador, sem interface** (`ea/scripts/slide-checker.js:4`, `:41-76`).
   - Consulta as lâminas do caso a cada 5 s.
   - Um comentário diz que o endpoint é público, sem autenticação.
3. **FAB** (`ea/scripts/fab.js:2-4`, `:39-104`).
   - Some quando o PathoWeb abre um modal; a checagem é a cada 500 ms.
   - O clique abre `/case/{caso}` em nova aba.
4. **Toasts,** com botões de ação (`ea/scripts/toast.js:57-66`).
5. **Painel de importação de laudo** (`ea/scripts/report-importer.js:243-366`).
   - Mostra "Laudo - {caso}" e o progresso "✓/○ Micro ✓/○ Concl".
   - Tem o botão da seção ativa ("Importar Microscopia" ou "Importar Conclusão") e o botão "Fechar".
6. **Painel de colaboração na barra lateral do PathoWeb** (`ea/scripts/collab-panel.js:203-797`; `ea/scripts/settings-bridge.js:15`).
   - Fica abaixo de "Exames a liberar" ou na coluna que contém "Andamento".
   - Cabeçalho no gradiente, com "PS" e um selo pulsante.
   - Deslogado, mostra um formulário de login.
   - Logado, mostra:
     - nome e CRM;
     - "Colaborações Pendentes";
     - uma lista de até 220 px com "Ver Laminas", "2a opiniao" e quem pediu.
   - Atualiza a cada 30 s e mostra notificação do sistema.

**No app:** a extensão copia para o localStorage o token do login feito por ela (`ea/scripts/auth-sync.js:13-76`).

**No editor do PathoWeb:** a extensão injeta o texto a partir do contexto da página, com até 10 tentativas a cada 500 ms (`ea/scripts/page-bridge.js:70-133`).

### Macroscopy Capture (`em/`)

**Manifest:** versão 3.6.0, permissão storage, sem popup e sem ícones declarados (`em/manifest.json:2-23`). Os três PNGs da pasta têm 0 byte; isso foi visto pelo tamanho dos arquivos, sem abri-los.

**Interface na página:** nenhuma. O selo de captura existe no código, mas está desligado na configuração (`em/scripts/macroscopy_listener.js:26`, `:248`). Se fosse ligado, teria (`:265-297`):
- o gradiente da marca, com texto branco de 13 px semibold;
- padding de 12 × 20 px e raio de 24 px;
- sombra de 16 px em preto a 30%;
- posição no canto inferior direito, com z-index 999999;
- entrada e saída em 0,3 s, ficando visível por 3 s, com o emoji 🔬.

**Página de opções** (`em/options/options.html:7-66`; `em/options/options.js:12-86`)
- Coluna de 460 px, com cabeçalho no gradiente.
- Campos: URL do Backend, Chave API (X-Internal-Key) e ID do Laboratório.
- A caixa "Valores salvos" mostra os 8 primeiros caracteres da chave.
- Mesmo padrão visual da Assistant, com campos monoespaçados.
- Cores:
  - erro: #fff5f5, #9b2c2c, #feb2b2;
  - informação: #ebf8ff, #2a4365, #bee3f8;
  - valores salvos: #f7fafc, #718096.

**Captura**
- **Gatilhos** (`em/scripts/macroscopy_listener.js:160-198`): Ctrl/Cmd+S, ou um clique que caia num destes elementos, ou até 5 níveis abaixo dele:
  - botão com o texto "salvar";
  - elemento com title ou aria-label de salvar;
  - botão salvar do editor.
- **Depois do gatilho** (`:15-29`, `:213-220`, `:300-554`):
  - espera 300 ms;
  - lê o texto do campo de macroscopia (no mínimo 20 caracteres), o número do caso e a tabela de frações (região, grupo e quantidade);
  - envia com a chave interna e o laboratório, com 3 tentativas a cada 2 s.

### Divergências e pontos de atenção

- **Versões divergentes.**
  - Assistant: 1.5.0 no manifest e "v1.2.0" na página de opções (`ea/manifest.json:4`; `ea/options/options.html:12`; `ea/options/options.js:54`).
  - Macroscopy: 3.6.0 no manifest e "3.2.0" no cabeçalho de versão enviado ao backend (`em/manifest.json:4`; `em/scripts/macroscopy_listener.js:415`).
- **Ativação do painel de colaboração.** O comentário diz que ele só ativa na página inicial, mas o código ativa em qualquer página de `/moduloExame` (`ea/scripts/collab-panel.js:4-5`, `:34-37`).
- **Botão "Fechar" do importador.** Ele confirma a importação no backend mesmo sem ter injetado o texto (`ea/scripts/report-importer.js:487-491`).
- **Dados expostos pela Macroscopy.**
  - Ela escreve no console do navegador o número do caso e os 100 primeiros caracteres da macroscopia (`em/scripts/macroscopy_listener.js:151`, `:225-226`).
  - Ela envia `user_agent` e `page_url` junto com a captura (`:438-439`).

## O que não foi encontrado no código

**Procurado e não encontrado**

*Estilo e tema*
- Variáveis CSS ou arquivo de tema ou de tokens, em `frontend/src`, `frontend/index.html`, nas configurações e no CSS das extensões.
- Customização de sombras, raios, espaçamentos ou breakpoints no Tailwind (`frontend/tailwind.config.js:8-45`).
- Regras de tema escuro no CSS (`.dark` ou `prefers-color-scheme`). O tema não segue o sistema operacional.
- Tema escuro nas extensões.
- Outra biblioteca de ícones além do lucide-react.

*Heatmap e camadas*
- Legenda ou barra de cores de heatmap.
- Colormap nomeado (viridis, jet, magma, inferno, turbo).
- Controle de opacidade ou de limiar do heatmap de tumor.
- Controle de opacidade em qualquer outra camada, seletor de camadas, troca de coloração ou de canal.

*Telas e rotas*
- Popup ou atalhos de navegador (`commands`) nas extensões.
- Rota de upload: o upload é só um modal.
- Tela de assinatura.
- Lista "meus casos" por patologista no workspace. A única lista por usuário é "Colaborações Pendentes", no PathoWeb.
- Página 404.
- Links para `/batches`, `/calibration` e `/qc-calibration` na barra de navegação.
- Mensagem explícita de "sem IA", "órgão não reconhecido" ou "sem modelo".
  - Aparece só o cartão genérico "Script específico em desenvolvimento" (`components/RightPanel.tsx:719-736`).
  - Órgão vazio vira "Outro" (`utils/organLabels.ts:39-43`).

*Viewer*
- Gatilho que abra a grade de contagem (`pages/CaseViewerPage.tsx:88-95`; `components/AnnotationToolbar.tsx:64-71`).
- Atalho de rotação, rotação em ângulo livre e espelhamento.
- Configuração explícita de gestos do OpenSeadragon (rolagem, clique, duplo clique, pinça, inércia). A exceção é o clique-para-zoom, desligado no SAM.
- Tratamento próprio de roda do mouse, duplo clique ou toque.
- Desenho por toque ou caneta.
- Seleção, edição ou arraste de uma anotação existente.
- Medida de ângulo ou de perímetro.
- Atalho que funcione para a Seta.
- Ctrl+Z no fluxo SAM.
- Gravação no servidor do desfazer e refazer.

*Extensões*
- Atalhos além de Ctrl/Cmd+S (Macroscopy) e Enter no login (Assistant).

*Código e dados*
- Telas que chamem `generateReport`, `saveMacroscopy`, `requestCollaboration`, `fetchQCResult` ou `signReport`, de `utils/api.ts` (`signReport` em `:57-66`).
- Nome do paciente no frontend: não aparece. O viewer carrega sexo e idade, mas não os exibe.
- A miniatura de reserva `/images/placeholder-slide.jpg` é referenciada (`pages/CaseViewerPage.tsx:678`), mas não existe em `frontend/public/`.

**Não verificado**
- Versões de Tailwind, lucide-react e OpenSeadragon: o `package.json` e o `node_modules` ficaram fora do escopo da leitura.
- Se os atalhos nativos do OpenSeadragon funcionam com o canvas em foco.
- A aparência real de qualquer tela: o app não foi executado.
- READMEs, instruções de instalação e PNGs das extensões: fora do escopo, não foram abertos.
- O prazo real da sessão no backend.
