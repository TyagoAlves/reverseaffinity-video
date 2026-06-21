# reverseaffinity — Arquitetura do Projeto

Documentação técnica para desenvolvedores que desejam contribuir ou estender o
projeto.

---

## 1. Estrutura de Diretórios

```
reverseaffinity/
├── main.py                  # Ponto de entrada: app QApplication + MainWindow
├── requirements.txt         # Dependências: PyQt5, numpy, Pillow
├── README.md                # Documentação principal
├── ROADMAP.md               # Roteiro de desenvolvimento
├── AGENTS.md                # Guia para agentes de IA
├── .gitignore
│
├── editor/                  # Engine principal (Python)
│   ├── __init__.py
│   ├── app_ui.py            # MainWindow, menus, toolbar, FilterGallery
│   ├── canvas.py            # CanvasView: render, zoom, pan, tool dispatch
│   ├── tools.py             # 15+ ferramentas registradas via SHORTCUT_MAP
│   ├── layers.py            # Layer, AdjustmentLayer, LayerStack, blend funcs
│   ├── filters.py           # Filtros: blur, sharpen, edge, pixelate, etc.
│   ├── history.py           # HistoryManager: undo/redo com snapshots
│   ├── panels.py            # ColorPanel, LayerPanel, HistoryPanel, ToolOptions
│   └── _colorspace.py       # rgb_to_hsl, hsl_to_rgb, rgb_to_lab
│
├── cpp_editor/              # Engine C++ (produção futura)
│   ├── CMakeLists.txt
│   ├── build.sh
│   ├── install_deps.sh
│   ├── include/
│   ├── src/
│   └── test/
│
├── assets/
│   └── icon.svg             # Ícone da aplicação
│
├── docs/                    # Documentação do usuário
│   ├── user_guide.md
│   ├── shortcuts.md
│   ├── blend_modes.md
│   └── project_architecture.md
│
└── plugins/                 # Sistema de plugins (futuro)
```

---

## 2. Diagrama de Dependências entre Módulos

```
main.py
  └── editor.app_ui ─────────────────────────────────────────────┐
        │                                                         │
        ├── editor.canvas ────────────────────────────────────────┤
        │     ├── editor.layers (LayerStack, blend)               │
        │     ├── editor.tools (SHORTCUT_MAP, Tool classes)       │
        │     └── editor.history (HistoryManager)                 │
        │                                                         │
        ├── editor.panels ────────────────────────────────────────┤
        │     ├── editor.layers (BLEND_MODES)                     │
        │     └── editor.canvas (via callback/getter)             │
        │                                                         │
        ├── editor.tools (TOOL_LIST, tool registration)           │
        │                                                         │
        └── editor.filters (FilterGalleryDialog calls)           │
              └── editor._colorspace (HSL conversion)            │
                    └── numpy                                     │
```

### Fluxo de Dependências

- **Unidirectional**: `app_ui → canvas → (layers, tools, history)`
- **Panels** acessam `canvas` via callback (`lambda: self.canvas`) — não há dependência circular
- **filters.py** é importado sob demanda por `app_ui` e `tools` (Healing Brush)
- **Numpy** é a dependência central para operações de pixel em `layers.py`, `filters.py` e `_colorspace.py`

---

## 3. Registro e Despacho de Ferramentas

### Registro

Cada ferramenta é uma subclasse de `Tool` em `tools.py:27`:

```python
class Tool:
    name = "tool"
    shortcut = ""
    def press(self, canvas, pos, modifiers): ...
    def move(self, canvas, last, pos, modifiers): ...
    def release(self, canvas, pos, modifiers): ...
```

Todas as ferramentas são registradas automaticamente no final do módulo:

```python
# tools.py:482-504
for _cls in [MoveTool, RectSelectTool, ..., CropTool]:
    SHORTCUT_MAP[_cls.shortcut.lower()] = _cls

TOOLS_BY_NAME[_cls.name.lower()] = _cls

TOOL_LIST = [
    ("Select", [MoveTool, RectSelectTool, ...]),
    ("Draw", [BrushTool, PencilTool, ...]),
    ...
]
```

### Despacho

1. **Por tecla**: `canvas.py:650-672` — `keyPressEvent` mapeia teclas para `self.set_tool("Nome")`
2. **Por clique na paleta**: `app_ui.py:68-71` — ToolPalette._select_tool chama `canvas.set_tool()`
3. **set_tool()**: `canvas.py:129-133` — busca em `TOOLS_BY_NAME` e instancia a ferramenta

```python
def set_tool(self, tool_name):
    cls = TOOLS_BY_NAME.get(tool_name.lower())
    if cls:
        self.tool = cls()
```

### Ciclo de Vida de uma Interação

```
MousePressEvent → self._save_state("ToolName")
                → self.tool.press(self, pos, mods)

MouseMoveEvent  → self.tool.move(self, last, pos, mods)

MouseReleaseEvent → self.tool.release(self, pos, mods)
```

---

## 4. Pipeline de Composição de Camadas

O pipeline de composição está em `layers.py:201-229` (método `LayerStack.composite()`):

```
                    ┌──────────┐
                    │ Numpy    │
                    │ result   │ ← zeros(h, w, 4) float32
                    └────┬─────┘
                         │
              ┌──────────▼──────────┐
              │ Para cada camada    │
              │ (da base ao topo):  │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │ Camada visível?     │─── Não → skip
              └──────────┬──────────┘
                         │ Sim
              ┌──────────▼──────────┐
              │ AdjustmentLayer?    │─── Sim → apply filter_func()
              │                     │        → atualiza result
              └──────────┬──────────┘
                         │ Não (raster layer)
              ┌──────────▼──────────┐
              │ QImage → numpy      │
              │ arr (uint8 → float) │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │ Blend Function      │
              │ BLEND_FUNCS[mode]   │
              │ blend_rgb =         │
              │   func(result, arr) │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │ Alpha blend:        │
              │ result = blend * a  │
              │       + result *    │
              │         (1 - a)     │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │ float → QImage      │
              │ (RGBA8888)          │
              └──────────┬──────────┘
                         │
                    ┌────▼────┐
                    │ Final   │
                    │ Image   │
                    └─────────┘
```

### Funções auxiliares

```python
_qimage_to_float_array(img)  # QImage → numpy float32 [0..1]
_float_array_to_qimage(arr, w, h)  # numpy float32 → QImage RGBA8888
```

### Modos de Mesclagem

As funções de blend operam em arrays numpy 2D float32 (canais RGB):

| Função | Modo |
|--------|------|
| `_blend_normal` | Normal |
| `_blend_multiply` | Multiply |
| `_blend_screen` | Screen |
| `_blend_overlay` | Overlay |
| `_blend_darken` | Darken |
| `_blend_lighten` | Lighten |
| `_blend_color_dodge` | Color Dodge |
| `_blend_color_burn` | Color Burn |
| `_blend_hard_light` | Hard Light |
| `_blend_soft_light` | Soft Light |
| `_blend_difference` | Difference |
| `_blend_exclusion` | Exclusion |

---

## 5. Arquitetura do Sistema de Filtros

### Filtros Diretos (filters.py)

Cada filtro é uma função pura que recebe `QImage` + parâmetros e retorna um novo `QImage`:

```python
def gaussian_blur(img: QImage, radius=3) -> QImage: ...
def sharpen(img: QImage, amount=1.0) -> QImage: ...
def edge_detect(img: QImage) -> QImage: ...
def pixelate(img: QImage, block=8) -> QImage: ...
def posterize(img: QImage, levels=4) -> QImage: ...
def grayscale(img: QImage) -> QImage: ...
def invert(img: QImage) -> QImage: ...
def sepia(img: QImage) -> QImage: ...
def brightness(img: QImage, val) -> QImage: ...
def contrast(img: QImage, factor) -> QImage: ...
def levels(img: QImage, shadow, mid, highlight) -> QImage: ...
def hue_saturation(img: QImage, h_rot, sat, light) -> QImage: ...
def curves(img: QImage, points) -> QImage: ...
```

### Filtros de Ajuste (para AdjustmentLayer)

Recebem `params: dict` para compatibilidade com o sistema de camadas de ajuste:

```python
def adjustment_brightness_contrast(img, params): ...
def adjustment_hsl(img, params): ...
def adjustment_levels(img, params): ...
```

### Galeria de Filtros (app_ui.py:74-223)

`FilterGalleryDialog` organiza filtros em categorias:

```
Filter Gallery Dialog
├── Adjustments
│   ├── Brightness / Contrast → slider dialog → _bc()
│   ├── Hue / Saturation     → slider dialog → _hs()
│   ├── Levels               → slider dialog → _levels()
│   ├── Grayscale            → _apply_filter("grayscale")
│   ├── Invert               → _apply_filter("invert")
│   └── Sepia                → _apply_filter("sepia")
├── Blur
│   └── Gaussian Blur        → input dialog radius → _blur()
├── Sharpen
│   ├── Sharpen              → input dialog amount → _sharpen()
│   └── Edge Detect          → _apply_filter("edge_detect")
└── Stylize
    ├── Pixelate             → input dialog block → _pixelate()
    └── Posterize            → input dialog levels → _posterize()
```

### Pipeline de Aplicação

```
_apply_filter("gaussian_blur"):
  1. Canvas._save_state("Gaussian Blur")  → snapshot history
  2. filters.gaussian_blur(img, radius)   → processamento numpy
  3. layer.image = result                  → substitui na camada ativa
  4. Canvas._refresh()                     → recomposição + display
```

---

## 6. Sistema de Histórico / Undo-Redo

### HistoryManager (history.py)

```python
class HistoryManager(QObject):
    def __init__(self, max_states=100): ...

    def push(self, description, layers, active_index):
        # Cria snapshot: [(name, image.copy(), visible, locked, opacity, blend)]
        # Descarta estados futuros (redo stack)
        # Adiciona ao deque (máx. 100 entradas)

    def undo(self, layer_stack):   # index -1, restaura snapshot
    def redo(self, layer_stack):   # index +1, restaura snapshot
    def jump_to(self, layer_stack, index):  # pulo direto (History Panel)
```

### Estrutura de Dados

```
HistoryManager
├── stack: deque(maxlen=100)
│   ├── HistoryEntry(description="New document", snapshot=[...], active_index=0)
│   ├── HistoryEntry(description="Brush", snapshot=[...], active_index=1)
│   └── HistoryEntry(description="Filter", snapshot=[...], active_index=2)
├── index: int  (current position, -1 = vazio)
└── max_states: 100
```

### Snapshot

Cada `HistoryEntry` armazena uma cópia profunda do estado de todas as camadas:

```python
snap = [(l.name, l.image.copy(), l.visible, l.locked, l.opacity, l.blend_mode)
        for l in layers]
```

### Restauração

```python
def _restore(self, layer_stack):
    layer_stack.layers.clear()
    for name, img, vis, locked, opacity, blend in entry.snapshot:
        l = Layer(img.width(), img.height(), name)
        l.image = img
        l.visible = vis
        l.locked = locked
        l.opacity = opacity
        l.blend_mode = blend
        layer_stack.layers.append(l)
    layer_stack.active_index = entry.active_index
```

### Quando o histórico é salvo

`Canvas._save_state(desc)` é chamado antes de qualquer operação destrutiva:

- `mousePressEvent` — antes de executar `tool.press()`
- Menu actions: Crop, Resize, Canvas Size, New/Delete/Duplicate/Move layer
- Filter Gallery: antes de aplicar qualquer filtro
- Fill, Clear, Merge Visible, Flatten

---

## 7. Fluxo de Eventos do Canvas

```
QGraphicsView
  │
  ├── wheelEvent → zoom (Ctrl+scroll) ou scroll padrão
  │
  ├── mousePressEvent → botão esquerdo: tool.press()
  │                     botão direito: PenTool.finalize()
  │                     botão meio: ScrollHandDrag
  │
  ├── mouseMoveEvent → tool.move() + emite mouse_moved(X, Y)
  │
  ├── mouseReleaseEvent → tool.release()
  │
  ├── keyPressEvent
  │   ├── Tool shortcuts → set_tool(name)
  │   ├── [ / ] → set_tool_size()
  │   ├── Enter → PenTool.finalize() / CropTool.apply()
  │   ├── Esc → PenTool.cancel() / CropTool.cancel()
  │   └── Ctrl+Z/Shift+Z → history.undo()/redo()
  │
  └── drawForeground → overlays: grid, selection, rubber band, lasso, pen, crop
```

---

## 8. Padrões de Design

### Strategy Pattern (Tools)

Cada ferramenta implementa a interface `Tool` com métodos `press/move/release`.
O canvas delega toda interação para a ferramenta ativa.

### Memento Pattern (History)

`HistoryManager` armazena snapshots completos do estado das camadas.
`push` = save memento, `undo`/`redo` = restore memento.

### Command Pattern (Filtros)

Filtros são funções puras (`QImage → QImage`) que podem ser aplicadas
destrutivamente na camada ativa ou não-destrutivamente via `AdjustmentLayer`.

### Observer Pattern (Signals)

```
CanvasView.mouse_moved → MainWindow._update_coords → StatusBar
CanvasView.status_changed → MainWindow.statusBar().showMessage
CanvasView.color_picked → MainWindow._sync_color_btn
CanvasView.history_changed → HistoryPanel.refresh
ColorPanel.colorChanged → CanvasView.set_foreground_color
```

---

© 2026 reverseaffinity.
