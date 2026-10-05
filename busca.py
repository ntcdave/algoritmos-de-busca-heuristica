# -*- coding: utf-8 -*-
"""
Algoritmos de busca: aleatória, DFS, BFS e A*.

Neste arquivo, a busca aleatória original foi mantida e a Busca
Guiada por Heurística (Gulosa) foi adicionada para demonstrar o poder 
de uma heurística na escolha do caminho mais promissor.

A estrutura de dados usada para guardar a fronteira na heurística é 
uma fila de prioridade (heapq), que tira sempre o nó com menor valor 
na heurística (Distância de Manhattan).
"""

import random
import heapq
import itertools


def heuristica(celula, objetivo):
    """
    Heurística de Distância de Manhattan.
    Calcula a distância em 'L' (apenas horizontal e vertical) entre a célula e o objetivo.
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


def busca(inicio, objetivo, vizinhos):
    """Roda a busca inteira e devolve o histórico: uma lista com um estado
    (dicionário) por passo, na ordem em que aconteceram.
    """
    estado = novo_estado()
    estado["fronteira"].add(inicio)
    estado["pai"][inicio] = None
    historico = []

    # =================================================================
    # ESCOLHA O ALGORITMO AQUI PARA A APRESENTAÇÃO:
    # Digite "aleatoria" ou "heuristica"
    ALGORITMO = "aleatoria" 
    # =================================================================

    if ALGORITMO == "aleatoria":
        # BUSCA ALEATÓRIA (CEGA)
        fronteira = [inicio]
        while fronteira:
            celula = random.choice(fronteira) 
            fronteira.remove(celula)
            
            _expandir(estado, celula, objetivo, vizinhos, fronteira)
            historico.append(_copia_do_estado(estado))
            
            if estado["encontrado"]:
                return historico

    elif ALGORITMO == "heuristica":
        # BUSCA GULOSA (GUIADA PELA HEURÍSTICA DE MANHATTAN)
        contador = itertools.count()
        fronteira_prioridade = []
        
        heapq.heappush(fronteira_prioridade, (heuristica(inicio, objetivo), next(contador), inicio))

        while fronteira_prioridade:
            _, _, celula = heapq.heappop(fronteira_prioridade)

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
                
                prioridade = heuristica(viz, objetivo)
                heapq.heappush(fronteira_prioridade, (prioridade, next(contador), viz))

            historico.append(_copia_do_estado(estado))

    estado["falhou"] = True
    historico.append(_copia_do_estado(estado))
    return historico


if __name__ == "__main__":
    # Demonstração em modo texto, sem pygame: mostra a busca resolvendo 
    # um labirinto pequeno, passo a passo, no terminal.
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

    historico = busca(inicio, objetivo, vizinhos_exemplo)
    for estado in historico:
        print(f"passo {estado['passos']:2d}: atual={estado['atual']}  "
              f"fronteira={len(estado['fronteira']):2d}  visitados={len(estado['visitados']):2d}")

    print()
    estado_final = historico[-1]
    if estado_final["encontrado"]:
        print(f"Achou o objetivo em {estado_final['passos']} passos "
              f"(caminho com {len(estado_final['caminho'])} células).")
    else:
        print("Não achou o objetivo.")