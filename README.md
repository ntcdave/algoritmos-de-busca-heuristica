# Algoritmos de Busca

Visualizador de algoritmos de busca em labirinto, feito para aulas de IA.
Só a **busca aleatória** está implementada.

O código é dividido em três arquivos, cada um com uma responsabilidade só,
justamente para separar "o que é algoritmo de busca" de "o que é só
desenho na tela":

| Arquivo | O que tem | Depende de pygame? |
|---|---|---|
| [`busca.py`](busca.py) | A busca em si, numa única função `busca()` | **Não** |
| [`estrutura_labirinto.py`](estrutura_labirinto.py) | O mapa do labirinto e a função `vizinhos()` | **Não** |
| [`maze.py`](maze.py) | Janela, cores, teclado — a visualização | Sim |

`busca.py` não sabe nada sobre pygame nem sobre desenho — só recebe um
início, um objetivo e uma função de vizinhos, roda a busca inteira e
devolve o histórico de passos (uma lista comum, nada mais exótico que
isso). A busca em si segue a forma de um `while` que tira uma célula da
**fronteira**, chama `_expandir(...)` e guarda uma "foto" do estado no
histórico com `_copia_do_estado(...)`.

Não são usadas generator functions (`yield`) pra animar a busca — só
`list`, `while` e `return`. Toda a função roda de uma vez e devolve a
lista completa de passos; quem anima (`maze.py`) só vai andando por essa
lista, item por item.

## Rodando sem pygame (modo texto)

`busca.py` roda sozinho, sem instalar nada além do Python padrão:

```bash
python3 busca.py
```

Isso resolve um labirinto pequeno de exemplo com a busca aleatória e
imprime o progresso passo a passo no terminal:

```
passo  1: atual=(1, 1)  fronteira= 2  visitados= 1
passo  2: atual=(1, 2)  fronteira= 2  visitados= 2
...
Achou o objetivo em 26 passos (caminho com 12 células).
```

## Rodando a visualização gráfica

Requer [pygame](https://www.pygame.org/):

```bash
pip install pygame
python3 maze.py
```

### Controles

| Tecla | Ação |
|---|---|
| `R` | Reinicia a busca |
| `+` / `-` | Aumenta/diminui a velocidade |
| `ESC` | Sai |

### Legenda de cores

- **Branco** — parede
- **Azul claro** — início
- **Vermelho** — objetivo
- **Azul escuro** — célula já visitada (nó "fechado")
- **Amarelo** — célula na fronteira (nó "aberto": conhecido, mas ainda não expandido)
- **Laranja** — célula sendo expandida neste exato passo
- **Verde** — caminho final, desenhado quando o objetivo é encontrado

## Os algoritmos

Todos compartilham a mesma ideia: manter uma **fronteira** (nós conhecidos
mas ainda não explorados) e, a cada passo, tirar um nó dela, marcá-lo como
visitado e colocar seus vizinhos novos na fronteira. A diferença entre eles
é **qual nó é escolhido a cada passo**, ou seja, que estrutura de dados
guarda a fronteira:

- **Busca aleatória** — escolhe um nó qualquer da fronteira. Sem
  estratégia; serve de linha de base pra comparar com os outros.
- **DFS (Depth-First Search)** — a fronteira é uma **pilha**: sempre expande
  o nó mais recentemente descoberto, "mergulhando" no labirinto até não dar
  mais e então voltando. Acha *um* caminho, não necessariamente o mais curto.
- **BFS (Breadth-First Search)** — a fronteira é uma **fila**: expande os
  nós na ordem em que foram descobertos, avançando em "camadas" por
  distância. Com custo de passo uniforme (como neste labirinto), sempre
  acha o caminho mais curto.
- **A\*** — a fronteira é uma **fila de prioridade**, ordenada por
  `custo_até_aqui + heurística(nó, objetivo)`. A heurística usada é a
  distância de Manhattan até o objetivo. Também acha o caminho mais curto,
  mas geralmente visitando bem menos células que a BFS, porque prioriza
  nós que parecem estar mais perto do objetivo.

## Estrutura interna (o estado e o histórico)

`busca(inicio, objetivo, vizinhos)` roda o algoritmo do início ao fim e
devolve uma **lista de dicionários** — um por passo, na ordem em que
aconteceram, como os quadros de um filme. Cada dicionário (`estado`) tem
as chaves:

- `estado["visitados"]` — conjunto de células já expandidas naquele passo
- `estado["fronteira"]` — conjunto de células conhecidas mas ainda não expandidas
- `estado["atual"]` — célula sendo expandida naquele passo
- `estado["passos"]` — quantos nós já tinham sido expandidos até ali
- `estado["encontrado"]` / `estado["falhou"]` — se a busca já tinha terminado, e como
- `estado["caminho"]` — lista de células do início ao objetivo (preenchida a partir do passo em que `encontrado=True`)

`maze.py` guarda essa lista inteira (`historico`) e um índice (`indice`).
A cada frame ele só avança o índice em 1 e desenha `historico[indice]` — não
faz nenhuma decisão de busca, só olha a "foto" daquele passo e pinta os
quadrados correspondentes na tela.
