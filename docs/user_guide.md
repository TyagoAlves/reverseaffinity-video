# reverseaffinity Photo — Guia do Usuário

> **A melhor edição de imagens para Linux — construída do zero.**
> Inspirado por Affinity Photo, Adobe Photoshop e DaVinci Resolve.

---

## Sumário

1. [Introdução](#1-introdução)
2. [Início Rápido](#2-início-rápido)
3. [Tour da Interface](#3-tour-da-interface)
4. [Referência de Ferramentas](#4-referência-de-ferramentas)
5. [Sistema de Camadas](#5-sistema-de-camadas)
6. [Guia de Seleções](#6-guia-de-seleções)
7. [Filtros e Ajustes](#7-filtros-e-ajustes)
8. [Atalhos de Teclado](#8-atalhos-de-teclado)
9. [Barra de Status](#9-barra-de-status)

---

## 1. Introdução

**reverseaffinity Photo** é um editor de imagens profissional desenvolvido em Python com PyQt5,
combinando a produtividade do Affinity Photo, o poder do Adobe Photoshop e a fluência do
DaVinci Resolve em uma experiência nativa para Linux.

### Principais características

- **15+ ferramentas** com atalhos profissionais de teclado
- **Pilha de camadas** com 12 modos de mesclagem (blend modes), opacidade e visibilidade
- **Ferramentas de seleção** com bordas animadas ("marching ants")
- **Galeria de filtros** — desfoque, nitidez, detecção de bordas, pixelização, posterização
- **Camadas de ajuste** não-destrutivas (Brilho/Contraste, HSL, Níveis)
- **Ferramenta Caneta/Bezier** com curvas cúbicas e alças de controle
- **Ferramenta Texto** com seleção de fonte, tamanho, negrito/itálico/sublinhado
- **Pincel de Cura (Healing Brush)** com casamento de cores
- **Painel de Cores** com valores RGB, HSL e Hex
- **Histórico** com 100 níveis de desfazer/refazer
- **Navegador** para visualização do zoom

---

## 2. Início Rápido

### Instalação

```bash
pip install -r requirements.txt
python main.py
```

### Criar um Novo Documento

1. Menu **File → New** (`Ctrl+N`)
2. Defina largura e altura (padrão: 1920×1080)
3. Clique **OK**

### Abrir uma Imagem

1. Menu **File → Open** (`Ctrl+O`)
2. Selecione o arquivo (PNG, JPEG, BMP, GIF, TIFF, WebP)
3. A imagem abre em uma nova tela com zoom ajustado

### Salvar

- **Save** (`Ctrl+S`) — salva no formato original
- **Save As** (`Ctrl+Shift+S`) — escolhe formato PNG, JPEG, TIFF, WebP ou BMP
- **Export as PNG / JPEG** — exporta a composição final

### Atalhos Essenciais

| Ação | Atalho |
|------|--------|
| Novo documento | `Ctrl+N` |
| Abrir | `Ctrl+O` |
| Salvar | `Ctrl+S` |
| Desfazer | `Ctrl+Z` |
| Refazer | `Ctrl+Shift+Z` |
| Ferramenta Mover | `V` |
| Ferramenta Pincel | `B` |
| Aumentar zoom | `Ctrl++` ou scroll com `Ctrl` |
| Diminuir zoom | `Ctrl+-` |

---

## 3. Tour da Interface

```
 ┌──────────────────────────────────────────────────────────────┐
 │ [File] [Edit] [Image] [Layer] [Filter] [View]   — □ ×       │  ← Menu Bar
 ├────────┬─────────────────────────────────────────┬───────────┤
 │        │  Size: [  3] Opacity: [100%] Color: [■] │           │  ← Tool Options Bar
 ├────────┴─────────────────────────────────────────┴───────────┤
 │ ┌────┐ ┌─────────────────────────────────────────┐ ┌───────┐ │
 │ │ V  │ │                                         │ │ Color │ │
 │ │ M  │ │        ┌──────────────────┐             │ │ FG:[■] │ │
 │ │ L  │ │        │                  │             │ │ BG:[■] │ │
 │ │ W  │ │        │      Canvas      │             │ │ R: 255 │ │
 │ ├────┤ │        │                  │             │ │ G: 000 │ │
 │ │ B  │ │        │                  │             │ │ B: 000 │ │
 │ │ N  │ │        └──────────────────┘             │ │ H: 000 │ │
 │ │ P  │ │                                         │ │ S: 100 │ │
 │ │ E  │ │                                         │ │ L: 050 │ │
 │ │ G  │ │                                         │ │ #000000│ │
 │ │ U  │ │                                         │ ├───────┤ │
 │ ├────┤ │                                         │ │Layers │ │
 │ │ S  │ │                                         │ │Mode: N│ │
 │ │ Y  │ │                                         │ │ ██████ │ │
 │ │ J  │ │                                         │ │ BG    │ │
 │ ├────┤ │                                         │ │ Layer1│ │
 │ │ C  │ │                                         │ ├───────┤ │
 │ ├────┤ │                                         │ │History│ │
 │ │ T  │ │                                         │ │ ▪ New │ │
 │ ├────┤ │                                         │ │ ▪ Brush│ │
 │ │ I  │ │                                         │ │ ▪ Fill │ │
 │ │ K  │ │                                         │ ├───────┤ │
 │ ├────┤ │                                         │ │Navig. │ │
 │ │ H  │ │                                         │ │ [  █ ] │ │
 │ │ Z  │ │                                         │ └───────┘ │
 │ └────┘ └─────────────────────────────────────────┘           │
 ├──────────────────────────────────────────────────────────────┤
 │ Ready                          X:  500  Y:  300  R:255 G:000 │  ← Status Bar
 └──────────────────────────────────────────────────────────────┘
```

### Regiões da Interface

| Região | Descrição |
|--------|-----------|
| **Menu Bar** | File, Edit, Image, Layer, Filter, View |
| **Tool Options Bar** | Tamanho do pincel, opacidade, cor, fonte, B/I/U |
| **Tool Palette (esquerda)** | 15+ ferramentas organizadas por categoria |
| **Canvas (centro)** | Área de edição com zoom, pan, réguas e grid |
| **Color Panel (direita)** | Seletor RGB/HSL/Hex, troca FG/BG |
| **Layers Panel (direita)** | Pilha de camadas, blend mode, opacidade |
| **History Panel (direita)** | Lista de estados para desfazer/refazer |
| **Navigator (direita)** | Miniatura para navegação no zoom |
| **Status Bar (inferior)** | Coordenadas X/Y, valores RGB do pixel |

---

## 4. Referência de Ferramentas

### Categoria: Select (Seleção)

#### Move Tool (Ferramenta Mover) — `V`

Move o conteúdo da camada ativa pela tela.

**Uso:**
1. Selecione a camada no painel Layers
2. Clique e arraste no canvas para mover o conteúdo
3. A camada se move na direção do arrasto

---

#### Rectangular Select (Seleção Retangular) — `M`

Cria uma seleção retangular.

**Uso:**
1. Pressione `M` (ou clique no botão na paleta)
2. Clique e arraste no canvas para definir o retângulo
3. Ao soltar, a seleção aparece com bordas animadas ("marching ants")
4. Qualquer pintura ou preenchimento será limitado à seleção

---

#### Elliptical Select (Seleção Elíptica) — `M` (com alternância)

Cria uma seleção elíptica.

**Uso:**
1. Alternne para Ellipse Select (via paleta de ferramentas)
2. Clique e arraste para definir a elipse
3. A seleção aparece com bordas animadas

---

#### Lasso Tool (Laço) — `L`

Seleção à mão livre.

**Uso:**
1. Pressione `L`
2. Clique e mantenha pressionado enquanto desenha o contorno
3. Solte o mouse para fechar a seleção
4. A área é convertida em uma seleção com bordas animadas

---

#### Magic Wand (Varinha Mágica) — `W`

Seleciona pixels adjacentes com cor similar.

**Uso:**
1. Pressione `W`
2. Clique em uma área da imagem
3. Pixels com cor similar (tolerância: 32) são selecionados
4. Use para selecionar fundos ou áreas de cor uniforme

**Dica:** Combine com Flood Fill (`K`) para preencher áreas selecionadas rapidamente.

---

### Categoria: Draw (Desenho)

#### Brush Tool (Pincel) — `B`

Pincel de pintura com suporte a opacidade e seleção de cor.

**Uso:**
1. Pressione `B`
2. Ajuste o **Size** e **Opacity** na barra de opções
3. Escolha a cor no painel Color ou com Color Picker (`I`)
4. Clique para pintar um ponto, arraste para pintar linhas
5. Use `[` e `]` para diminuir/aumentar o tamanho

---

#### Pencil Tool (Lápis) — `N`

Pincel de borda dura, ideal para pixel art.

**Uso:**
1. Pressione `N`
2. Clique e arraste para desenhar
3. Funciona como o Brush mas sem suavização (anti-aliasing)

---

#### Pen Tool (Caneta/Bezier) — `P`

Ferramenta de curvas Bezier para criar paths vetoriais precisos.

**Uso:**
1. Pressione `P`
2. Clique para adicionar pontos âncora
3. Arraste após clicar para criar alças de controle (curvas cúbicas)
4. Continue clicando para adicionar mais segmentos
5. Pressione `Enter` ou clique com botão direito para finalizar
6. Pressione `Esc` para cancelar o path atual

**Dica:** Funciona como a Pen Tool do Photoshop/Affinity — cada ponto pode ter alças de entrada e saída para controle fino da curva.

---

#### Eraser Tool (Borracha) — `E`

Apaga pixels da camada ativa.

**Uso:**
1. Pressione `E`
2. Clique e arraste sobre a área a apagar
3. Funciona com `CompositionMode_Clear` — apaga para transparência
4. Ajuste o tamanho com `[` / `]`

---

#### Gradient Tool (Gradiente) — `G`

Preenche a camada ou seleção com um gradiente linear.

**Uso:**
1. Pressione `G`
2. Defina a cor de foreground (FG) e background (BG)
3. Clique em um ponto inicial e arraste até o ponto final
4. O gradiente vai de FG → BG na direção do arrasto

---

#### Shape Tool (Forma) — `U`

Desenha retângulos com a cor ativa.

**Uso:**
1. Pressione `U`
2. Clique e arraste para definir o retângulo
3. A forma é desenhada na camada ativa com a cor atualmente selecionada

---

### Categoria: Text (Texto)

#### Text Tool (Ferramenta Texto) — `T`

Adiciona texto à camada ativa com seleção de fonte, tamanho e estilo.

**Uso:**
1. Pressione `T`
2. Clique no canvas para abrir o diálogo de texto
3. Digite o texto desejado
4. Selecione fonte (font), tamanho (size), negrito (B), itálico (I), sublinhado (U)
5. Clique **OK** para aplicar
6. O texto é renderizado na camada ativa

---

### Categoria: Retouch (Retoque)

#### Clone Stamp Tool (Carimbo) — `S`

Copia pixels de uma área para outra.

**Uso:**
1. Pressione `S`
2. **Definir origem:** segure `Alt` e clique na área a ser copiada
3. **Aplicar:** clique ou arraste na área de destino
4. O clone segue o cursor proporcionalmente à origem

---

#### Healing Brush (Pincel de Cura) — `J`

Copia textura de uma área ajustando cores para combinar com o destino.

**Uso:**
1. Pressione `J`
2. **Definir origem:** segure `Alt` e clique na área de textura
3. **Aplicar:** clique ou arraste na área a ser corrigida
4. O pincel copia a textura e ajusta as cores (média de cor) para casar com o destino

---

### Categoria: Crop (Corte)

#### Crop Tool (Corte) — `C`

Corta a imagem para um novo enquadramento.

**Uso:**
1. Pressione `C`
2. Clique e arraste para definir a área de corte
3. A área externa fica escurecida (overlay)
4. Pressione `Enter` para aplicar o corte
5. Pressione `Esc` para cancelar

---

### Categoria: Color (Cor)

#### Color Picker (Conta Gotas) — `I`

Captura a cor de um pixel na tela.

**Uso:**
1. Pressione `I`
2. Clique em qualquer pixel da imagem
3. A cor selecionada torna-se a cor de foreground (FG)
4. O painel Color é atualizado com os valores RGB/HSL/Hex

---

#### Flood Fill (Balde de Tinta) — `K`

Preenche uma área com cor similar.

**Uso:**
1. Pressione `K`
2. Escolha a cor desejada
3. Clique na área a preencher
4. Pixels com cor similar ao ponto clicado são substituídos pela cor ativa

**Dica:** Use com **Magic Wand** (`W`) para selecionar primeiro e depois preencher com `K` — o preenchimento respeita seleções ativas.

---

### Categoria: View (Visualização)

#### Hand Tool (Mão) — `H`

Navega pelo canvas quando o zoom está aplicado (pan).

**Uso:**
1. Pressione `H`
2. Clique e arraste para mover a visualização
3. Alternativamente, use o scroll do mouse (sem `Ctrl`)

---

#### Zoom Tool (Zoom) — `Z`

Aumenta e diminui o zoom da visualização.

**Uso:**
1. Pressione `Z`
2. Clique para aumentar o zoom
3. Segure `Alt` e clique para diminuir o zoom
4. Alternativa: `Ctrl++` / `Ctrl+-` / scroll com `Ctrl`

---

## 5. Sistema de Camadas

O sistema de camadas (layer stack) do reverseaffinity funciona como no Photoshop ou Affinity Photo:

### Conceitos Básicos

- **Camadas (Layers)** — imagens empilhadas que compõem o resultado final
- **Camada de Ajuste (Adjustment Layer)** — aplica filtros não-destrutivos (Brilho/Contraste, HSL, Níveis)
- **Opacidade (Opacity)** — controla a transparência de cada camada (0–100%)
- **Visibilidade** — ícone de olho para mostrar/esconder a camada
- **Bloqueio (Lock)** — impede alterações na camada

### Painel Layers

```
┌──────────────────────┐
│ Mode: [Normal    ▾]  │
│ Opacity: [████████]100│
│ [+][−][⧉][↑][↓]     │
│ ┌──────────────────┐ │
│ │ BG                │ │  ← camada de fundo
│ │ Layer 1           │ │  ← camada de pintura
│ │ ⚙ BC Adjustment   │ │  ← camada de ajuste
│ └──────────────────┘ │
└──────────────────────┘
```

### Modos de Mesclagem (Blend Modes)

| Modo | Descrição |
|------|-----------|
| Normal | Padrão — pixels superiores cobrem os inferiores |
| Multiply | Multiplica cores — escurece a imagem |
| Screen | Inverso de Multiply — clareia a imagem |
| Overlay | Combina Multiply e Screen — aumenta contraste |
| Darken | Mantém o pixel mais escuro |
| Lighten | Mantém o pixel mais claro |
| Color Dodge | Clareia com base na cor inferior |
| Color Burn | Escurece com base na cor inferior |
| Hard Light | Like Overlay, mas usa a cor da camada superior |
| Soft Light | Iluminação suave difusa |
| Difference | Subtrai cores — efeito negativo |
| Exclusion | Similar a Difference, mas com menor contraste |

> Consulte o guia detalhado em [`blend_modes.md`](blend_modes.md).

### Operações com Camadas

| Ação | Como Fazer |
|------|------------|
| Nova camada | `Ctrl+Shift+N` ou botão `+` no painel |
| Duplicar | Botão `⧉` no painel |
| Deletar | Botão `−` no painel |
| Mover para cima | Botão `↑` no painel |
| Mover para baixo | Botão `↓` no painel |
| Mudar blend mode | Dropdown "Mode" no painel |
| Ajustar opacidade | Slider "Opacity" no painel |
| Camada de ajuste | Menu **Layer → New Adjustment Layer** |
| Mesclar visíveis | **Layer → Merge Visible** |
| Achatar (Flatten) | **Layer → Flatten Image** |

---

## 6. Guia de Seleções

### Tipos de Seleção

- **Retangular** (`M`) — área retangular
- **Elíptica** (`M`, alternando) — área elíptica/circular
- **Laço** (`L`) — forma livre
- **Varinha Mágica** (`W`) — seleção por cor (tolerância: 32)

### Comportamento

- Seleções são exibidas com bordas animadas ("marching ants")
- Um overlay azul semi-transparente cobre a área selecionada
- Ferramentas de pintura (Brush, Pencil, Eraser) respeitam a seleção ativa
- Flood Fill (`K`) também respeita seleções

### Limpar Seleção

No momento, seleções são removidas ao iniciar uma nova seleção ou ao clicar fora (dependendo da ferramenta).

---

## 7. Filtros e Ajustes

### Galeria de Filtros

Acesse pelo menu **Filter → Filter Gallery** para abrir o diálogo com categorias.

#### Adjustments (Ajustes)

| Filtro | Descrição |
|--------|-----------|
| Brightness / Contrast | Ajusta brilho e contraste da imagem |
| Hue / Saturation | Modifica matiz, saturação e luminosidade (HSL) |
| Levels | Controla sombras, tons médios (gamma) e realces |
| Grayscale | Converte para escala de cinza |
| Invert | Inverte as cores (negativo) |
| Sepia | Aplica tom sépia vintage |

#### Blur (Desfoque)

| Filtro | Descrição |
|--------|-----------|
| Gaussian Blur | Desfoque gaussiano com raio ajustável |

#### Sharpen (Nitidez)

| Filtro | Descrição |
|--------|-----------|
| Sharpen | Nitidez com intensidade ajustável |
| Edge Detect | Detecta bordas usando operador Sobel |

#### Stylize (Estilizar)

| Filtro | Descrição |
|--------|-----------|
| Pixelate | Efeito de pixelização com tamanho de bloco ajustável |
| Posterize | Reduz número de níveis de cor |

### Camadas de Ajuste (Não-destrutivo)

Menu **Layer → New Adjustment Layer**:

- **Brightness / Contrast** — ajuste não-destrutivo com sliders
- **Hue / Saturation** — ajuste HSL não-destrutivo
- **Levels** — ajuste de níveis não-destrutivo

Camadas de ajuste são aplicadas em tempo real durante a composição, sem modificar a camada original.

---

## 8. Atalhos de Teclado

| Atalho | Ação |
|--------|------|
| `Ctrl+N` | Novo documento |
| `Ctrl+O` | Abrir imagem |
| `Ctrl+S` | Salvar |
| `Ctrl+Shift+S` | Salvar como |
| `Ctrl+Q` | Fechar |
| `Ctrl+Z` | Desfazer |
| `Ctrl+Shift+Z` | Refazer |
| `Ctrl+Shift+N` | Nova camada |
| `Ctrl++` | Zoom in |
| `Ctrl+-` | Zoom out |
| `Ctrl+0` | Zoom para ajustar (Fit) |
| `Ctrl+1` | Zoom 100% |
| `V` | Move Tool |
| `M` | Rectangular / Elliptical Select |
| `L` | Lasso |
| `W` | Magic Wand |
| `B` | Brush |
| `N` | Pencil |
| `P` | Pen (Bezier) |
| `E` | Eraser |
| `G` | Gradient |
| `U` | Shape |
| `S` | Clone Stamp |
| `Y` | History Brush |
| `J` | Healing Brush |
| `C` | Crop |
| `T` | Text |
| `I` | Color Picker |
| `K` | Flood Fill |
| `H` | Hand (Pan) |
| `Z` | Zoom |
| `[` | Diminuir tamanho do pincel |
| `]` | Aumentar tamanho do pincel |
| `Enter` | Finalizar path (Pen) / Aplicar corte (Crop) |
| `Esc` | Cancelar path (Pen) / Cancelar corte (Crop) |

> Consulte a referência completa em [`shortcuts.md`](shortcuts.md).

---

## 9. Barra de Status

```
Ready                          X:   500  Y:   300  R: 255  G: 000  B: 000
```

A barra de status na parte inferior da janela exibe:

| Campo | Descrição |
|-------|-----------|
| **Mensagem** | Status atual (ex: "Ready", "Saved: image.png") |
| **X / Y** | Coordenadas do cursor na imagem |
| **R / G / B** | Valores RGB do pixel sob o cursor |

---

© 2026 reverseaffinity. Construído com PyQt5, numpy e Pillow.
