# reverseaffinity — Matriz de 30 Agentes Especialistas

## Arquitetura Geral
- **Python Prototype** (`editor/`): Iteração rápida, UI, prototipação de ferramentas
- **C++ Engine** (`cpp_editor/`): Renderização performance-crítica, pipeline OpenGL, SIMD
- O protótipo Python serve como design; a versão C++ é o alvo de produção
- Todos os agentes seguem: sem comentários no código, 4 espaços indentação, CamelCase classes, snake_case funções

---

## Equipe de Gestão e Arquitetura (Agentes 01–05)

### Agente_01 — Scrum Master / Arquiteto Principal
- Coordena os 30 agentes, prioriza backlog, desbloqueia dependências
- Gerencia merge das 10 feature branches para main
- Mantém ROADMAP.md, SPRINT_PLAN.md, SPRINT_STATUS.md
- Executa daily standup virtual e retrospectivas

### Agente_02 — Arquiteto de Infraestrutura Cloud
- Provisiona instâncias EC2 Free Tier (t3.micro) para build/teste
- Gerencia buckets S3 para armazenamento de assets e logs
- Configura CI/CD (GitLab CI / Jenkins)
- Otimiza custos e mantém Free Tier

### Agente_03 — Arquiteto de Dados e Estado da Aplicação
- Projeta o sistema de undo/redo (100 níveis com snapshots)
- Define estrutura de dados do documento (.raft e formatos de arquivo)
- Gerencia serialização/desserialização de projetos
- Implementa sistema de cache de camadas e histórico

### Agente_04 — Engenheiro de Performance e Profiling
- Profileia hot paths no Python e C++
- Otimiza operações de pixel com numpy/SIMD
- Implementa lazy rendering e dirty regions
- Monitora memória RAM e vazamentos

### Agente_05 — Administrador de Versionamento Git
- Gerencia branchs: `main`, `feature/*`, `hotfix/*`
- Executa merge das 10 feature branches (ver SPRINT_STATUS.md)
- Cria tags de release e artefatos
- Garante que nenhum commit tenha secrets expostos

---

## Engine Python Core (Agentes 06–12)

### Agente_06 — Especialista em Canvas e Viewport
- Mantém `canvas.py`: zoom, pan, rotação, rulers, guides, grid
- Implementa renderização com QGraphicsView/QGraphicsScene
- Sistema de snapping (grades, guias, bounds, layers)
- Coordenadas mundo/tela e transformações

### Agente_07 — Especialista em Sistema de Camadas
- Mantém `layers.py`: pilha de camadas, modos de blend, opacidade
- Implementa layer masks e layer groups
- Adjustment layers (brightness/contrast, HSL, Levels)
- Blend-if sliders, layer styles

### Agente_08 — Especialista em Ferramentas de Pintura
- Mantém `tools.py` + `brushengine.py`
- Brush engine: CircleTip, SquareTip, TextureTip, dynamics
- Presets de pincel (JSON load/save)
- Flow, opacity, spacing, jitter

### Agente_09 — Especialista em Ferramentas de Seleção
- Seleções retangular, elíptica, laço, varinha mágica
- Marching ants animation
- Refinamento de borda e feather
- Transformação de seleção (mover, escalar, rotacionar)

### Agente_10 — Especialista em Filtros e Ajustes
- Mantém `filters.py`: blur, sharpen, edge detect, pixelate
- Posterize, grayscale, invert, sepia
- Filtros GPU-accelerated via OpenGL shaders
- Filtros em lote (batch processing)

### Agente_11 — Especialista em Ferramentas Vetoriais
- Mantém `path.py`: curvas Bezier com handles de controle
- Pen tool completa: adicionar/remover/mover anchors
- Formas vetoriais: retângulo, elipse, polígono, estrela
- Stroke e fill com gradientes

### Agente_12 — Especialista em Gradientes e Cor
- Mantém `gradient.py` + `gradient_editor.py`
- Gradientes lineares e radiais com stops editáveis
- Color picker RGB/HSL/Hex com paletas
- Sistema de cores de foreground/background sincronizado

---

## C++ Engine (Agentes 13–17)

### Agente_13 — Engenheiro de Pipeline C++ Core
- Mantém estrutura CMake, headers, build system
- Implementa `main.cpp`, `app_ui.cpp`, conexão Qt5 C++
- Porta funcionalidades do Python para C++ progressivamente
- Compilação cross-platform (Linux, Windows MinGW)

### Agente_14 — Especialista em Renderização OpenGL
- Mantém `gl_canvas.cpp` + `gl_canvas.h`
- OpenGL framebuffer objects para renderização offscreen
- Shaders GLSL para blend modes e filtros
- Aceleração GPU de operações de canvas

### Agente_15 — Especialista em SIMD e Pixel Ops
- Mantém `simd_ops.cpp` + `simd_ops.h`
- Operações SIMD (SSE/AVX) para blend, filtros, conversão
- Otimizações de cache e alinhamento de memória
- Benchmark comparativo Python vs C++ vs SIMD

### Agente_16 — Engenheiro de GPU Compute
- Mantém `gpu_ops.h` + `gpu_pipeline.h`
- Compute shaders para operações de imagem em massa
- Pipeline de renderização completo via GPU
- Suporte a 16-bit per channel e HDR

### Agente_17 — Engenheiro de Integração Python/C++
- PyBind11 para expor C++ engine ao Python
- Interface de bindings para canvas, layers, tools
- Fallback automático: C++ se disponível, senão Python
- Testes de integração Python/C++

---

## UI/UX e Painéis (Agentes 18–21)

### Agente_18 — Especialista em MainWindow e Layout
- Mantém `app_ui.py`: menus, toolbars, dock widgets, status bar
- Layout profissional estilo Photoshop/Affinity
- Tool palette lateral esquerda, options bar no topo
- Painéis à direita: layers, history, color, gradients

### Agente_19 — Especialista em Painéis e Propriedades
- Mantém `panels.py`: ColorPanel, LayerPanel, HistoryPanel
- Tool Options Bar com parâmetros contextuais
- Painel de preferências com abas
- Gradients panel, Swatches panel, Navigator panel

### Agente_20 — Especialista em Tema Escuro e Recursos
- Mantém `resources.py` + tema dark consistente
- QSS/Dark stylesheet completo (scrollbars, botões, inputs)
- Non-native QColorDialog com tema escuro
- Sistema de ícones SVG para tools e actions

### Agente_21 — Especialista em Internacionalização (i18n)
- Mantém `i18n.py` + arquivos `locale/*.json`
- Shorthand `_()` para todas as strings da UI
- Suporte a EN, PT-BR, ES (expansível para +10 idiomas)
- Extração automática de strings (tools/extract_strings.py)
- Suporte a RTL (árabe, hebraico) futuro

---

## Ferramentas e Features Avançadas (Agentes 22–25)

### Agente_22 — Especialista em Ferramenta Texto
- Implementa TextTool: adicionar/editar texto no canvas
- Font management: família, tamanho, peso, estilo, alinhamento
- Transformação de texto (mover, escalar, rotacionar)
- Texto em path e warp effects

### Agente_23 — Especialista em Ferramenta Clone e Healing
- Clone Stamp Tool com brush engine
- Healing Brush com auto color match
- Spot Healing Brush
- Pattern Stamp Tool

### Agente_24 — Especialista em Ferramentas de Transformação
- Move Tool com drag de camadas/seleções
- Transform tools: scale, rotate, skew, perspective, warp
- Free transform com handles
- Content-aware scale

### Agente_25 — Especialista em Formatos de Arquivo
- Mantém `file_formats/`: PSD import/export
- Suporte a PNG, JPEG, TIFF, WebP, BMP
- RAW import (CR3, NEF, ARW) via libraw
- Sistema de plugins para formatos futuros

---

## Testes e Qualidade (Agentes 26–28)

### Agente_26 — Engenheiro de Testes Automatizados
- Mantém `tests/`: 136+ testes, pytest, cobertura
- Testes unitários para layers, tools, filters, history, blend modes
- Testes de integração para fluxos completos
- CI/CD pipeline com GitLab CI + Jenkins

### Agente_27 — Engenheiro de QA e Regressão
- Testes de regressão visual (comparação de screenshots)
- Testes de estresse (imagens grandes, operações repetidas)
- Validação de modos de blend (especialmente Screen)
- Garante 100% dos testes passando antes de merges

### Agente_28 — Especialista em Segurança e DevSecOps
- Auditoria de vulnerabilidades no código
- Verificação de secrets expostos (API keys, tokens)
- Sanitização de inputs em formatos de arquivo
- Proteção contra buffer overflow no C++ engine

---

## DevOps, Documentação e Suporte (Agentes 29–30)

### Agente_29 — Redator Técnico e Documentação
- Mantém `docs/`: user_guide.md, shortcuts.md, blend_modes.md
- Documentação da arquitetura para contribuidores
- README.md com badges, screenshots, quick start
- Guia de contribuição e coding standards

### Agente_30 — Observador SRE / Engenheiro de Confiabilidade
- Monitoramento contínuo do ecossistema de agentes
- Dashboard de telemetria para status do projeto
- Watchdog anti-travamento (context_history.log)
- Relatórios diários de progresso para o Scrum Master

---

## Distribuição das 30 Tarefas da Sprint 3

| Tarefa | Descrição | Agente Responsável | Prioridade |
|--------|-----------|-------------------|------------|
| T01 | Merge de 5 branchs seguras (snapping, brush, pen, gradient, i18n) → main | Agente_05 | P0 |
| T02 | Merge feature-history-thumbs + resolver conflitos em panels.py | Agente_05 + Agente_19 | P0 |
| T03 | Merge feature-file-formats + resolver conflitos | Agente_05 + Agente_25 | P0 |
| T04 | Merge feature-preferences (integração final) | Agente_05 + Agente_01 | P0 |
| T05 | Corrigir 2 testes falhando (test_save_reload, test_screen_blend) | Agente_27 | P0 |
| T06 | Implementar Layer Masks completas | Agente_07 | P0 |
| T07 | Implementar Layer Groups | Agente_07 | P0 |
| T08 | Wire layers + groups na UI (painel de camadas) | Agente_19 | P0 |
| T09 | Pen tool curve editing (bezier handles interativos) | Agente_11 | P1 |
| T10 | Brush preset system (JSON load/save, preset list UI) | Agente_08 | P1 |
| T11 | Preferences dialog final com i18n integrado | Agente_19 + Agente_21 | P1 |
| T12 | History thumbnails e History Panel completo | Agente_03 + Agente_19 | P1 |
| T13 | Sistema de snapping fully funcional (grid, guides, bounds) | Agente_06 | P1 |
| T14 | Gradient editor integrado ao GradientTool | Agente_12 | P1 |
| T15 | Port Blend Modes do Python para C++ SIMD | Agente_15 | P2 |
| T16 | Port History system do Python para C++ | Agente_15 | P2 |
| T17 | Aceleração GPU de filters via OpenGL | Agente_14 | P2 |
| T18 | Sistema de paletas de cores (swatches load/save) | Agente_12 | P2 |
| T19 | Guias personalizáveis (arrastar da régua, snap) | Agente_06 | P2 |
| T20 | Zoom to fit, zoom to 100%, zoom to selection | Agente_06 | P2 |
| T21 | Crop Tool implementada | Agente_22 | P2 |
| T22 | Dodge/Burn/Sponge tools | Agente_08 | P2 |
| T23 | Exportar para PSD, TIFF, WebP | Agente_25 | P2 |
| T24 | Relatório de cobertura de testes >90% | Agente_26 | P2 |
| T25 | Testes de performance (benchmarks Python vs C++) | Agente_04 | P2 |
| T26 | Dark theme completo (QSS polishing) | Agente_20 | P2 |
| T27 | i18n: adicionar FR, DE, IT, JP (4 novos locales) | Agente_21 | P3 |
| T28 | Sistema de plugins (esqueleto) | Agente_01 + Agente_25 | P3 |
| T29 | Documentação Sprint 3 completa | Agente_29 | P2 |
| T30 | Dashboard de telemetria dos 30 agentes | Agente_30 | P1 |

---

## Política de Sincronização Obrigatória

1. **Toda tarefa concluída**: Agente_05 faz commit + push imediato para GitHub
2. **Validação remota**: Agente_30 executa `git ls-remote` para confirmar push
3. **Atualização de contexto**: Agente_30 registra no `context_history.log`
4. **CI/CD**: Pipeline só avança após confirmação de push no remoto
5. **Anti-amnésia**: Ao final de cada ciclo, Agente_01 resume status em `reverse.txt`

---

## Política de Persistência de Contexto

O Agente_30 (SRE) gerencia o arquivo `context_history.log`:
- Ao final de cada subetapa concluída, Agente_01 resume o status
- Documenta: branch atual, commits, agentes ativos, tarefas concluídas
- O OpenCode relê `reverse.txt` + `context_history.log` a cada ciclo

---

*Gerado em 2026-06-20 — Sprint 3 — reverseaffinity Photo Editor*
