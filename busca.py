# -*- coding: utf-8 -*-
"""
Algoritmos de busca: aleatória, DFS, BFS, Gulosa (heurística) e A*.

Todos recebem (inicio, objetivo, vizinhos) e devolvem o mesmo formato:
uma lista de estados (um dicionário por passo), que o maze.py anima.

A diferença entre eles é só QUAL nó da fronteira é expandido:
  - aleatória .... sorteia um nó qualquer da fronteira (sem estratégia)
  - dfs .......... pilha (LIFO): mergulha fundo até travar, depois volta
  - bfs .......... fila (FIFO): expande em camadas, acha o caminho mais curto
  - gulosa ....... fila de prioridade só pela heurística h(n) = Manhattan até o objetivo
  - astar ........ fila de prioridade por f(n) = g(n) + h(n), onde g = custo até aqui

A heurística usada é a distância de Manhattan (só anda em cruz, como no labirinto).
"""

import heapq
import itertools
import random
from collections import deque


def heuristica(celula, objetivo):
    """
    Distância de Manhattan entre celula e objetivo.

    Funciona com qualquer unidade de coordenada (pixels ou grade),
    porque só importa a ORDEM dos valores, não a escala.
    """
    return abs(celula[0] - objetivo[0]) + abs(celula[1] - objetivo[1])


def novo_estado():
    """Um retrato do algoritmo em um instante da busca: só dados, sem lógica."""
    return {
        "visitados": set(),   # células já expandidas ("fechadas")
        "fronteira": set(),   # células conhecidas mas ainda não expandidas ("abertas")
        "pai": {},             # pai[celula] = célula anterior no caminho até ela
        "atual": None,         # célula sendo expandida neste passo
        "passos": 0,           # quantos nós já foram expandidos até agora
        "encontrado": False,   # True quando o objetivo foi alcançado
        "falhou": False,       # True quando a fronteira esvaziou sem achar o objetivo
        "caminho": [],         # caminho início -> objetivo, preenchido quando encontrado=True
    }


def _copia_do_estado(estado):
    """Tira uma 'foto' do estado atual, pra guardar no histórico sem que
    mudanças futuras no `estado` original afetem essa foto já tirada."""
    return {
        "visitados": set(estado["visitados"]),
        "fronteira": set(estado["fronteira"]),
        "atual": estado["atual"],
        "passos": estado["passos"],
        "encontrado": estado["encontrado"],
        "falhou": estado["falhou"],
        "caminho": list(estado["caminho"]),
    }


def _reconstruir_caminho(pai, objetivo):
    """Segue os "pais" de trás pra frente, do objetivo até o início."""
    caminho = []
    celula = objetivo
    while celula is not None:
        caminho.append(celula)
        celula = pai.get(celula)
    caminho.reverse()
    return caminho


def _expandir(estado, celula, objetivo, vizinhos, fronteira):
    """Passo comum às buscas aleatória / DFS / BFS:

    1. marca `celula` como visitada;
    2. se `celula` for o objetivo, monta o caminho e termina;
    3. senão, manda os vizinhos ainda não conhecidos pra fronteira.
    """

    estado["fronteira"].discard(celula)
    estado["visitados"].add(celula)
    estado["atual"] = celula
    estado["passos"] += 1

    if celula == objetivo:
        estado["encontrado"] = True
        estado["caminho"] = _reconstruir_caminho(estado["pai"], objetivo)
        return

    for viz in vizinhos(celula):
        if viz in estado["visitados"] or viz in estado["fronteira"]:
            continue
        estado["pai"][viz] = celula
        estado["fronteira"].add(viz)
        fronteira.append(viz)


def normalizar_algoritmo(nome):
    """Aceita apelidos ("A*", "a_star", "heuristica"...) e devolve o nome canônico."""
    n = str(nome).strip().lower().replace("_", "").replace("-", "").replace(" ", "")
    if n in ("aleatoria", "aleatoriaa", "aleatória", "random", "rand"):
        return "aleatoria"
    if n in ("dfs", "profundidade", "pilha"):
        return "dfs"
    if n in ("bfs", "largura", "fila"):
        return "bfs"
    if n in ("gulosa", "guloso", "heuristica", "heurística", "greedy", "heuristic"):
        return "gulosa"
    if n in ("astar", "a*", "a", "star"):
        return "astar"
    raise ValueError(
        f"algoritmo desconhecido: {nome!r} "
        "(use 'aleatoria', 'dfs', 'bfs', 'gulosa' ou 'astar')"
    )


ALGORITMOS = ("aleatoria", "dfs", "bfs", "gulosa", "astar")

DESCRICAO = {
    "aleatoria": "Aleatória: sorteia da fronteira (sem heurística)",
    "dfs": "DFS: pilha, mergulha fundo (sem heurística)",
    "bfs": "BFS: fila em camadas, caminho mais curto (sem heurística)",
    "gulosa": "Gulosa: só h(n) = Manhattan até o objetivo",
    "astar": "A*: f(n) = g(n) + h(n), curto + eficiente",
}


def busca(inicio, objetivo, vizinhos, algoritmo="aleatoria"):
    """Roda a busca inteira e devolve o histórico: uma lista com um estado
    (dicionário) por passo, na ordem em que aconteceram.
    """
    algoritmo = normalizar_algoritmo(algoritmo)

    estado = novo_estado()
    estado["fronteira"].add(inicio)
    estado["pai"][inicio] = None
    historico = []

    # ------------------------- buscas sem heurística -------------------------
    if algoritmo == "aleatoria":
        fronteira = [inicio]
        while fronteira:
            celula = random.choice(fronteira)
            fronteira.remove(celula)
            _expandir(estado, celula, objetivo, vizinhos, fronteira)
            historico.append(_copia_do_estado(estado))
            if estado["encontrado"]:
                return historico

    elif algoritmo == "dfs":
        fronteira = [inicio]  # pilha: pop() tira o último = LIFO
        while fronteira:
            celula = fronteira.pop()
            if celula in estado["visitados"]:
                continue
            _expandir(estado, celula, objetivo, vizinhos, fronteira)
            historico.append(_copia_do_estado(estado))
            if estado["encontrado"]:
                return historico

    elif algoritmo == "bfs":
        fronteira = deque([inicio])  # fila: popleft() tira o mais antigo = FIFO
        while fronteira:
            celula = fronteira.popleft()
            if celula in estado["visitados"]:
                continue
            _expandir(estado, celula, objetivo, vizinhos, fronteira)
            historico.append(_copia_do_estado(estado))
            if estado["encontrado"]:
                return historico

    # ------------------------- buscas com heurística -------------------------
    elif algoritmo == "gulosa":
        contador = itertools.count()
        heap = [(heuristica(inicio, objetivo), next(contador), inicio)]
        while heap:
            _, _, celula = heapq.heappop(heap)
            if celula in estado["visitados"]:
                continue
            estado["fronteira"].discard(celula)
            estado["visitados"].add(celula)
            estado["atual"] = celula
            estado["passos"] += 1
            if celula == objetivo:
                estado["encontrado"] = True
                estado["caminho"] = _reconstruir_caminho(estado["pai"], objetivo)
                historico.append(_copia_do_estado(estado))
                return historico
            for viz in vizinhos(celula):
                if viz in estado["visitados"] or viz in estado["fronteira"]:
                    continue
                estado["pai"][viz] = celula
                estado["fronteira"].add(viz)
                heapq.heappush(heap, (heuristica(viz, objetivo), next(contador), viz))
            historico.append(_copia_do_estado(estado))

    elif algoritmo == "astar":
        contador = itertools.count()
        g = {inicio: 0}  # custo do início até cada célula
        heap = [(heuristica(inicio, objetivo), next(contador), inicio)]
        while heap:
            _, _, celula = heapq.heappop(heap)
            if celula in estado["visitados"]:
                continue
            estado["fronteira"].discard(celula)
            estado["visitados"].add(celula)
            estado["atual"] = celula
            estado["passos"] += 1
            if celula == objetivo:
                estado["encontrado"] = True
                estado["caminho"] = _reconstruir_caminho(estado["pai"], objetivo)
                historico.append(_copia_do_estado(estado))
                return historico
            for viz in vizinhos(celula):
                novo_g = g[celula] + 1
                if viz in estado["visitados"] and novo_g >= g.get(viz, float("inf")):
                    continue
                if viz not in estado["fronteira"] or novo_g < g.get(viz, float("inf")):
                    estado["pai"][viz] = celula
                    g[viz] = novo_g
                    estado["fronteira"].add(viz)
                    f = novo_g + heuristica(viz, objetivo)
                    heapq.heappush(heap, (f, next(contador), viz))
            historico.append(_copia_do_estado(estado))

    estado["falhou"] = True
    historico.append(_copia_do_estado(estado))
    return historico


if __name__ == "__main__":
    # Demonstração em modo texto, sem pygame: resolve um labirinto pequeno
    # com CADA algoritmo e compara (ótimo pra apresentação sobre heurística).
    grade_exemplo = [
        "#########",
        "#S..#...#",
        "#.#.#.#.#",
        "#.#...#.#",
        "#.#####.#",
        "#.......#",
        "#.#####E#",
        "#########",
    ]

    paredes = set()
    inicio = objetivo = None
    for y, linha in enumerate(grade_exemplo):
        for x, c in enumerate(linha):
            if c == "#":
                paredes.add((x, y))
            elif c == "S":
                inicio = (x, y)
            elif c == "E":
                objetivo = (x, y)

    largura, altura = len(grade_exemplo[0]), len(grade_exemplo)

    def vizinhos_exemplo(celula):
        cx, cy = celula
        livres = []
        for nx, ny in ((cx, cy - 1), (cx, cy + 1), (cx - 1, cy), (cx + 1, cy)):
            if 0 <= nx < largura and 0 <= ny < altura and (nx, ny) not in paredes:
                livres.append((nx, ny))
        return livres

    print("Labirinto de exemplo (S=início, E=objetivo):")
    for linha in grade_exemplo:
        print(" ", linha)
    print()
    print(f"{'algoritmo':<10} {'passos':>7} {'caminho':>8}")
    print("-" * 28)
    random.seed(0)
    for algo in ALGORITMOS:
        hist = busca(inicio, objetivo, vizinhos_exemplo, algoritmo=algo)
        fim = hist[-1]
        if fim["encontrado"]:
            print(f"{algo:<10} {fim['passos']:>7} {len(fim['caminho']):>8}")
        else:
            print(f"{algo:<10} {'falhou':>7} {'--':>8}")
