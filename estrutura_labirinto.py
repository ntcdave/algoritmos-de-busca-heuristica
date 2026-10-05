# -*- coding: utf-8 -*-
"""Estrutura de dados do labirinto: o mapa e a função vizinhos()."""

CELL = 16  # tamanho de uma célula do labirinto (unidade de coordenada, não é pixel de tela)

# Mapa do labirinto: W = parede, E = objetivo/saída, espaço = caminho livre.
MAPA = [
    "WWWWWWWWWWWWWWWWWWWW",
    "W                  W",
    "W         WWWWWW   W",
    "W   WWWW       W   W",
    "W   W        WWWW  W",
    "W WWW  WWWW        W",
    "W   W     W W      W",
    "W   W     W   WWW WW",
    "W   WWW WWW   W W  W",
    "W     W   W   W W  W",
    "WWW   W   WWWWW W  W",
    "W W      WW        W",
    "W W   WWWW   WWW   W",
    "W     W    E   W   W",
    "WWWWWWWWWWWWWWWWWWWW",
]

LARGURA = len(MAPA[0])  # nº de células na horizontal
ALTURA = len(MAPA)      # nº de células na vertical
INICIO = (32, 32)       # célula onde a busca sempre começa


def carregar_mapa(mapa=MAPA, cell=CELL):
    """Lê o mapa (lista de strings) e devolve (paredes, objetivo)."""
    paredes = set()
    objetivo = None
    x = y = 0
    for linha in mapa:
        for coluna in linha:
            if coluna == "W":
                paredes.add((x, y))
            elif coluna == "E":
                objetivo = (x, y)
            x += cell
        y += cell
        x = 0
    assert objetivo is not None, "o mapa precisa ter um 'E' marcando o objetivo"
    return paredes, objetivo


PAREDES, OBJETIVO = carregar_mapa()


def vizinhos(coord, paredes=PAREDES, largura=LARGURA, altura=ALTURA, cell=CELL):
    """Devolve as células vizinhas (cima, baixo, esquerda, direita) dentro do mapa e livres de parede."""
    cx, cy = coord
    candidatos = [(cx, cy - cell), (cx, cy + cell), (cx - cell, cy), (cx + cell, cy)]
    livres = []
    for nx, ny in candidatos:
        dentro_do_mapa = 0 <= nx < largura * cell and 0 <= ny < altura * cell
        if dentro_do_mapa and (nx, ny) not in paredes:
            livres.append((nx, ny))
    return livres
