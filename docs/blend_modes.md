# reverseaffinity Photo — Modos de Mesclagem (Blend Modes)

Guia visual e técnico dos 12 modos de mesclagem disponíveis.

---

## Visão Geral

Os modos de mesclagem (blend modes) determinam como os pixels de uma camada
superior interagem com os pixels das camadas abaixo. Cada modo usa uma fórmula
matemática diferente aplicada aos canais RGB.

**Legenda:**
- **B** = pixel base (camada inferior / accumulated result)
- **L** = pixel da camada superior (layer)
- Operações são realizadas por canal (R, G, B) com valores normalizados em [0, 1]

---

## 1. Normal (Normal)

| Propriedade | Valor |
|-------------|-------|
| **Fórmula** | `resultado = L` |
| **Descrição** | O pixel da camada superior substitui completamente o pixel inferior. O modo padrão de todas as camadas. |
| **Uso** | Pintura, composição básica, camadas de texto |

---

## 2. Multiply (Multiplicar)

| Propriedade | Valor |
|-------------|-------|
| **Fórmula** | `resultado = B × L` |
| **Descrição** | Escurece a imagem multiplicando os valores de cor. Qualquer valor multiplicado por branco (1.0) permanece inalterado; multiplicado por preto (0.0) resulta em preto. |
| **Uso** | — Aplicar sombras<br>— Escurecer imagens superexpostas<br>— Efeito de sobreposição com texturas escuras |

---

## 3. Screen (Tela)

| Propriedade | Valor |
|-------------|-------|
| **Fórmula** | `resultado = 1 − (1 − B) × (1 − L)` |
| **Descrição** | Clareia a imagem. É o inverso do Multiply. Valores escuros têm pouco efeito; valores claros clareiam o resultado. |
| **Uso** | — Aplicar realces (highlights)<br>— Clarear imagens subexpostas<br>— Efeito de brilho/luz |

---

## 4. Overlay (Sobreposição)

| Propriedade | Valor |
|-------------|-------|
| **Fórmula** | Se `B < 0.5`: `2 × B × L` senão: `1 − 2 × (1 − B) × (1 − L)` |
| **Descrição** | Combina Multiply e Screen dependendo da cor base. Aumenta o contraste sem cortar sombras ou realces. |
| **Uso** | — Aumentar contraste<br>— Texturas e padrões sobrepostos<br>— Efeito HDR |

---

## 5. Darken (Escurecer)

| Propriedade | Valor |
|-------------|-------|
| **Fórmula** | `resultado = min(B, L)` |
| **Descrição** | Mantém o pixel mais escuro entre a base e a camada superior, por canal. |
| **Uso** | — Substituir áreas claras por conteúdo escuro<br>— Efeitos de sombra projetada |

---

## 6. Lighten (Clarear)

| Propriedade | Valor |
|-------------|-------|
| **Fórmula** | `resultado = max(B, L)` |
| **Descrição** | Mantém o pixel mais claro entre a base e a camada superior, por canal. |
| **Uso** | — Substituir áreas escuras por conteúdo claro<br>— Efeitos de luz e brilho |

---

## 7. Color Dodge (Subexposição de Cor)

| Propriedade | Valor |
|-------------|-------|
| **Fórmula** | `resultado = B / (1 − L)` (limitado a 1.0) |
| **Descrição** | Clareia a base dividindo-a pelo inverso da camada superior. Cores escuras na camada superior têm pouco efeito; cores claras produzem clareamento intenso. |
| **Uso** | — Efeitos de luz intensa<br>— Brilhos especulares<br>— Realces dramáticos |

---

## 8. Color Burn (Superexposição de Cor)

| Propriedade | Valor |
|-------------|-------|
| **Fórmula** | `resultado = 1 − (1 − B) / L` (limitado a 0.0) |
| **Descrição** | Escurece a base dividindo o inverso da base pela camada superior. |
| **Uso** | — Escurecimento intenso<br>— Efeitos de sombra profunda<br>— Queima de cores (burn effect) |

---

## 9. Hard Light (Luz Forte)

| Propriedade | Valor |
|-------------|-------|
| **Fórmula** | Se `L < 0.5`: `2 × B × L` senão: `1 − 2 × (1 − B) × (1 − L)` |
| **Descrição** | Similar a Overlay, mas usa a camada **superior** para determinar a transição. Cores escuras na camada superior escurecem; cores claras clareiam. |
| **Uso** | — Aplicar texturas com contraste<br>— Efeitos de iluminação dramática |

---

## 10. Soft Light (Luz Suave)

| Propriedade | Valor |
|-------------|-------|
| **Fórmula** | Se `L < 0.5`: `2 × B × L + B² × (1 − 2 × L)` senão: `√B × (2 × L − 1) + 2 × B × (1 − L)` |
| **Descrição** | Iluminação suave e difusa, similar a um holofote suave. Menos agressivo que Overlay ou Hard Light. |
| **Uso** | — Ajustes sutis de iluminação<br>— Dodge & Burn suave<br>— Correção de tons |

---

## 11. Difference (Diferença)

| Propriedade | Valor |
|-------------|-------|
| **Fórmula** | `resultado = |B − L|` |
| **Descrição** | Subtrai os valores de cor. O resultado é o valor absoluto da diferença. Preto na camada superior não altera a base. |
| **Uso** | — Alinhamento de camadas<br>— Comparação de imagens<br>— Efeitos psicodélicos |

---

## 12. Exclusion (Exclusão)

| Propriedade | Valor |
|-------------|-------|
| **Fórmula** | `resultado = B + L − 2 × B × L` |
| **Descrição** | Similar a Difference, mas com menor contraste. O resultado é mais suave e menos saturado. |
| **Uso** | — Efeitos de cor abstratos<br>— Sobreposições sutis com contraste reduzido |

---

## Tabela Comparativa

```
Modo           | Escurece? | Clareia? | Contraste? | Fórmula chave
---------------|-----------|----------|------------|------------------------------
Normal         |    —      |    —     |     —      | L
Multiply       |    ✅     |    ✗     |     —      | B × L
Screen         |    ✗      |    ✅    |     —      | 1 − (1−B)(1−L)
Overlay        |    ✓      |    ✓     |    ✅      | 2BL / 1−2(1−B)(1−L)
Darken         |    ✅     |    ✗     |     —      | min(B, L)
Lighten        |    ✗      |    ✅    |     —      | max(B, L)
Color Dodge    |    ✗      |    ✅    |    Forte   | B / (1−L)
Color Burn     |    ✅     |    ✗     |    Forte   | 1 − (1−B)/L
Hard Light     |    ✓      |    ✓     |    ✅      | 2BL / 1−2(1−B)(1−L)
Soft Light     |    ✓      |    ✓     |    Suave   | Vários (ver fórmula)
Difference     |    —      |    —     |    —       | |B − L|
Exclusion      |    —      |    —     |    Suave   | B + L − 2BL
```

---

## Guia Rápido

| Efeito desejado | Modo recomendado |
|-----------------|-------------------|
| Escurecer | Multiply, Color Burn, Darken |
| Clarear | Screen, Color Dodge, Lighten |
| Aumentar contraste | Overlay, Hard Light, Soft Light |
| Corte/colagem realista | Normal com máscara |
| Textura sobreposta | Multiply, Overlay, Soft Light |
| Efeito neon/brilho | Screen, Color Dodge |
| Comparar diferenças | Difference |
| Efeito artístico | Exclusion, Difference |

---

## Como usar

1. Selecione uma camada no **Layers Panel**
2. No dropdown **Mode**, escolha o modo de mesclagem desejado
3. Ajuste a **Opacity** para controlar a intensidade do efeito

> **Dica:** Combine blend modes com opacidade reduzida para resultados mais sutis e controláveis.

---

© 2026 reverseaffinity.
