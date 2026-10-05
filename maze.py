#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Visualizador neon do labirinto — feito pra apresentação sobre HEURÍSTICAS.

O que ele mostra (além do labirinto bonitinho):
  - o "palpite" da heurística: mapa de calor (H) = h de Manhattan,
    fronteira colorida por h (a mais promissora ganha anel branco),
    linha tracejada do "atual" até o objetivo e o valor h(atual);
  - comparativo (C): roda os 5 algoritmos e mostra quem visitou menos;
  - modo jogável (M): você tenta escapar com setas/WASD e compara com a IA.

Controles:
  1..5 ..... troca o algoritmo (1 Aleatória, 2 BFS, 3 DFS, 4 Gulosa, 5 A*)
  ESPAÇO ... pausa / continua        R .... reinicia
  setas .... passo a passo (pausado)  + / - .. velocidade
  H ........ mapa de calor + guia     C .... comparativo de todos
  M ........ modo jogável (setas/WASD) ESC .. fecha overlay / sai
  (também dá pra clicar nos algoritmos, nos botões e na barra de progresso)
"""

import math
import random
import sys

import pygame

from estrutura_labirinto import (
    CELL, LARGURA, ALTURA, INICIO, OBJETIVO, PAREDES, vizinhos,
)
from busca import busca

# ---------------------------------------------------------------------------
# Tema neon escuro
# ---------------------------------------------------------------------------

BG          = (8, 12, 26)
HEADER_BG   = (10, 17, 34)
BOARD_BG    = (15, 23, 42)
BOARD_EDGE  = (51, 65, 92)
FREE        = (26, 36, 64)     # célula livre ainda não visitada
WALL        = (219, 228, 245)  # parede clara (contraste no projetor)
WALL_TOP    = (248, 250, 252)
WALL_SHADOW = (8, 13, 28)
VISITED     = (37, 99, 235)
VISITED_IN  = (96, 165, 250)
FRONT_DIM   = (150, 95, 20)    # fronteira com h ruim (longe do objetivo)
FRONT_TOP   = (253, 224, 71)   # fronteira com h bom (perto do objetivo)
BEST_RING   = (255, 255, 255)
ATUAL       = (255, 122, 26)
ATUAL_EDGE  = (255, 255, 255)
PATH_OUT    = (6, 120, 85)
PATH_IN     = (52, 211, 153)
START       = (34, 211, 238)
GOAL        = (244, 63, 94)
GUIDE       = (232, 121, 249)
TEXT        = (226, 232, 240)
MUTED       = (148, 163, 184)
ACCENT      = (34, 211, 238)
CARD        = (20, 30, 55)
CARD_EDGE   = (45, 60, 95)
GOOD        = (52, 211, 153)
WARN        = (251, 191, 36)

ORDEM = ["aleatoria", "bfs", "dfs", "gulosa", "astar"]
NOMES = {
    "aleatoria": ("Aleatória", "sorteio · sem heurística"),
    "bfs":       ("BFS",       "camadas · sem heurística"),
    "dfs":       ("DFS",       "fundo · sem heurística"),
    "gulosa":    ("Gulosa",    "só h · palpite puro"),
    "astar":     ("A*",        "g + h · curto + esperto"),
}
TECLA_PARA_ALGO = {"1": "aleatoria", "2": "bfs", "3": "dfs", "4": "gulosa", "5": "astar"}

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

TILE = 34
BOARD_W = LARGURA * TILE
BOARD_H = ALTURA * TILE
MARGIN = 18
HEADER_H = 74
SIDEBAR_W = 322
LEGEND_H = 30
FOOTER_H = 34
WIN_W = MARGIN * 3 + BOARD_W + SIDEBAR_W
WIN_H = HEADER_H + MARGIN + BOARD_H + 8 + LEGEND_H + MARGIN + FOOTER_H
BOARD_X = MARGIN
BOARD_Y = HEADER_H + MARGIN
SIDE_X = BOARD_X + BOARD_W + MARGIN

# ---------------------------------------------------------------------------
# Conversão pixel -> grade (estrutura_labirinto usa pixels múltiplos de CELL)
# ---------------------------------------------------------------------------

def px_para_grade(coord):
    return (coord[0] // CELL, coord[1] // CELL)

GRID_PAREDES = {px_para_grade(p) for p in PAREDES}
GRID_INICIO = px_para_grade(INICIO)
GRID_OBJETIVO = px_para_grade(OBJETIVO)

def h_grade(celula, objetivo=GRID_OBJETIVO):
    """Heurística de Manhattan em UNIDADES DE CÉLULA (pra exibir na tela)."""
    return abs(celula[0] - objetivo[0]) + abs(celula[1] - objetivo[1])

H_MAX = max(
    (h_grade((gx, gy)) for gy in range(ALTURA) for gx in range(LARGURA)
     if (gx, gy) not in GRID_PAREDES),
    default=1,
)

# ---------------------------------------------------------------------------
# Estado global (de propósito simples, como no original: histórico + índice)
# ---------------------------------------------------------------------------

algoritmo = "gulosa"   # padrão: heurística pura (impacto visual imediato)
historico = []         # estados já convertidos pra grade
indice = 0
tocando = True
fps = 14
heatmap = True
guia = True
comparando = False
comparativo = []
manual = False
player = GRID_INICIO
player_trilha = [GRID_INICIO]
player_passos = 0
t0_manual = 0
venceu_manual = False
particulas = []
confete_feito = False
t_encontrou = 0

algo_rects = []   # [(rect, algo)] — botões da sidebar (clique)
btn_pausar = None
btn_comparar = None
btn_calor = None
btn_jogar = None
barra_prog = None

FONTES = {}


def fonte(tamanho, negrito=False):
    chave = (tamanho, negrito)
    if chave not in FONTES:
        FONTES[chave] = pygame.font.SysFont(
            "segoeui,dejavusans,arial,sans", tamanho, bold=negrito)
    return FONTES[chave]


# ---------------------------------------------------------------------------
# Utilidades de desenho
# ---------------------------------------------------------------------------

def misturar(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def painel(surf, rect, fill=CARD, edge=CARD_EDGE, raio=14, borda=1):
    pygame.draw.rect(surf, fill, rect, border_radius=raio)
    if borda:
        pygame.draw.rect(surf, edge, rect, borda, border_radius=raio)


def texto(surf, s, pos, tamanho=14, cor=TEXT, negrito=False, centro=False):
    img = fonte(tamanho, negrito).render(s, True, cor)
    if centro:
        x, y = pos
        surf.blit(img, (x - img.get_width() // 2, y))
    else:
        surf.blit(img, pos)
    return img.get_width()


def centro_grade(gx, gy):
    return (BOARD_X + gx * TILE + TILE // 2, BOARD_Y + gy * TILE + TILE // 2)


def tile_rect(gx, gy, inset=0):
    return pygame.Rect(
        BOARD_X + gx * TILE + inset, BOARD_Y + gy * TILE + inset,
        TILE - inset * 2, TILE - inset * 2)


# ---------------------------------------------------------------------------
# Busca: roda e converte o histórico pra grade (1x por algoritmo)
# ---------------------------------------------------------------------------

def reset(novo_algo=None):
    global historico, indice, algoritmo, tocando, particulas
    global confete_feito, t_encontrou
    if novo_algo is not None:
        algoritmo = novo_algo
    bruto = busca(INICIO, OBJETIVO, vizinhos, algoritmo=algoritmo)
    historico = []
    for est in bruto:
        historico.append({
            "visitados": {px_para_grade(c) for c in est["visitados"]},
            "fronteira": {px_para_grade(c) for c in est["fronteira"]},
            "atual": px_para_grade(est["atual"]) if est["atual"] else None,
            "passos": est["passos"],
            "encontrado": est["encontrado"],
            "falhou": est["falhou"],
            "caminho": [px_para_grade(c) for c in est["caminho"]],
        })
    indice = 0
    tocando = True
    particulas = []
    confete_feito = False
    t_encontrou = 0


def estado_atual():
    return historico[indice] if historico else None


def lancar_confete():
    global confete_feito
    confete_feito = True
    gx, gy = GRID_OBJETIVO
    cx, cy = centro_grade(gx, gy)
    cores = [(34, 211, 238), (52, 211, 153), (253, 224, 71),
             (232, 121, 249), (251, 113, 133), (255, 255, 255)]
    for _ in range(130):
        ang = random.uniform(0, math.tau)
        vel = random.uniform(60, 320)
        particulas.append({
            "x": cx, "y": cy,
            "vx": math.cos(ang) * vel, "vy": math.sin(ang) * vel - 120,
            "cor": random.choice(cores),
            "vida": random.uniform(0.9, 1.8), "idade": 0.0,
            "tam": random.randint(2, 4),
        })


def calcular_comparativo():
    """Roda os 5 algoritmos rapidinho (sem animar) e resume o placar."""
    random.seed(123)  # aleatória fica reprodutível aqui; no ao vivo ela varia
    tabela = []
    for algo in ORDEM:
        h = busca(INICIO, OBJETIVO, vizinhos, algoritmo=algo)
        fim = h[-1]
        tabela.append({
            "algo": algo,
            "passos": fim["passos"],
            "visitados": len(fim["visitados"]),
            "caminho": len(fim["caminho"]) if fim["encontrado"] else 0,
            "ok": fim["encontrado"],
        })
    random.seed()  # devolve o acaso ao modo ao vivo
    return tabela


# ---------------------------------------------------------------------------
# Desenho: cabeçalho / tabuleiro / legenda / sidebar / overlays
# ---------------------------------------------------------------------------

def desenhar_cabecalho(surf, agora):
    surf.fill(HEADER_BG, (0, 0, WIN_W, HEADER_H))
    pygame.draw.line(surf, BOARD_EDGE, (0, HEADER_H - 1), (WIN_W, HEADER_H - 1))
    # logo: mini-labirinto 3x3
    lx, ly, s = 18, 20, 10
    pygame.draw.rect(surf, CARD, (lx - 6, ly - 6, s * 3 + 12, s * 3 + 12), border_radius=8)
    mini = ["101", "001", "100"]
    for j, linha in enumerate(mini):
        for i, ch in enumerate(linha):
            cor = ACCENT if ch == "1" else (60, 80, 115)
            pygame.draw.rect(surf, cor, (lx + i * s, ly + j * s, s - 2, s - 2), border_radius=2)
    texto(surf, "BUSCA NO LABIRINTO", (lx + s * 3 + 14, ly - 2), 21, TEXT, True)
    nome, desc = NOMES[algoritmo]
    modo = "MODO JOGÁVEL" if manual else f"{nome} · {desc}"
    texto(surf, f"heurística h = Manhattan  •  {modo}", (lx + s * 3 + 14, ly + 24), 13, MUTED)

    est = estado_atual()
    if manual:
        rotulo, cor = ("JOGUE! Leve o S até o objetivo", START) if not venceu_manual else ("* VOCÊ ESCAPOU!  (M volta)", GOOD)
    elif comparando:
        rotulo, cor = "COMPARANDO ALGORITMOS...", WARN
    elif not est or (not est["encontrado"] and not est["falhou"]):
        rotulo = "BUSCANDO..." if tocando else "PAUSADO"
        cor = WARN if tocando else MUTED
    elif est["encontrado"]:
        rotulo = f"ENCONTROU! caminho {len(est['caminho'])}"
        cor = GOOD
    else:
        rotulo, cor = "X SEM CAMINHO", (248, 113, 113)
    pill = pygame.Rect(WIN_W - 300, 18, 282, 38)
    painel(surf, pill, fill=(16, 28, 52), edge=cor, raio=19, borda=2)
    texto(surf, rotulo, (pill.centerx, pill.y + 10), 15, cor, True, centro=True)


def cor_calor(gx, gy):
    """Fundo da célula livre tingido por h: perto do objetivo = mais quente."""
    t = 1.0 - h_grade((gx, gy)) / max(H_MAX, 1)
    return (int(FREE[0] + 68 * t), int(FREE[1] + 8 * t), int(FREE[2] + 28 * t))


def desenhar_tabuleiro(surf, agora):
    painel(surf, pygame.Rect(BOARD_X - 8, BOARD_Y - 8, BOARD_W + 16, BOARD_H + 16),
           fill=BOARD_BG, edge=BOARD_EDGE, raio=18, borda=1)
    est = estado_atual()
    visitados = est["visitados"] if est else set()
    fronteira = est["fronteira"] if est else set()
    atual = est["atual"] if est else None
    caminho = est["caminho"] if est and est["encontrado"] else []

    # melhor palpite da fronteira (menor h) — a "estrela" da heurística
    melhor = min(fronteira, key=h_grade) if fronteira else None
    hs = [h_grade(c) for c in fronteira] if fronteira else [0]
    hmin, hmax = (min(hs), max(hs)) if hs else (0, 0)

    for gy in range(ALTURA):
        for gx in range(LARGURA):
            if (gx, gy) in GRID_PAREDES:
                r = tile_rect(gx, gy, inset=1)
                pygame.draw.rect(surf, WALL_SHADOW, (r.x, r.y + 2, r.w, r.h), border_radius=9)
                pygame.draw.rect(surf, WALL, r, border_radius=9)
                pygame.draw.line(surf, WALL_TOP, (r.x + 7, r.y + 2), (r.x + r.w - 7, r.y + 2), 2)
                continue
            base = cor_calor(gx, gy) if heatmap else FREE
            pygame.draw.rect(surf, base, tile_rect(gx, gy, inset=1), border_radius=9)
            if (gx, gy) in visitados and (gx, gy) != GRID_INICIO and (gx, gy) != GRID_OBJETIVO:
                pygame.draw.rect(surf, VISITED, tile_rect(gx, gy, inset=3), border_radius=8)
                pygame.draw.rect(surf, VISITED_IN, tile_rect(gx, gy, inset=3).inflate(-8, -14), border_radius=5)

    # fronteira: tamanho e brilho variam com h (o bom palpite "salta aos olhos")
    for (gx, gy) in fronteira:
        if (gx, gy) in visitados or (gx, gy) in (GRID_INICIO, GRID_OBJETIVO):
            pass
        h = h_grade((gx, gy))
        t = 1.0 - (h - hmin) / max(hmax - hmin, 1)
        cor = misturar(FRONT_DIM, FRONT_TOP, 0.25 + 0.75 * t)
        inset = 8 - int(4 * t)
        pygame.draw.rect(surf, cor, tile_rect(gx, gy, inset=inset), border_radius=7)
    if melhor is not None and not (est and est["encontrado"]) and not manual:
        r = tile_rect(*melhor, inset=4)
        pulso = 2 + int(1.5 * math.sin(agora * 6))
        pygame.draw.rect(surf, BEST_RING, r.inflate(pulso, pulso), 2, border_radius=9)

    # linha-guia: direção do palpite (atual -> objetivo)
    if guia and atual and not manual and not (est and (est["encontrado"] or est["falhou"])):
        ax, ay = centro_grade(*atual)
        bx, by = centro_grade(*GRID_OBJETIVO)
        dx, dy = bx - ax, by - ay
        dist = math.hypot(dx, dy)
        if dist > TILE:
            n = int(dist / 12)
            for i in range(1, n):
                t = i / n
                pygame.draw.circle(surf, GUIDE,
                                   (int(ax + dx * t), int(ay + dy * t)), 3)

    # caminho final (revelado aos poucos, com brilho)
    if caminho and not manual:
        revelado = len(caminho)
        if t_encontrou:
            revelado = min(len(caminho), 3 + int((agora - t_encontrou) * 28))
        pts = [centro_grade(*c) for c in caminho[:max(revelado, 2)]]
        if len(pts) >= 2:
            pygame.draw.lines(surf, PATH_OUT, False, pts, 12)
            pygame.draw.lines(surf, PATH_IN, False, pts, 6)
        for p in pts:
            pygame.draw.circle(surf, PATH_IN, p, 5)
            pygame.draw.circle(surf, (220, 255, 240), p, 2)

    # nó atual com pulso
    if atual and not manual and not (est and (est["encontrado"] or est["falhou"])):
        cx, cy = centro_grade(*atual)
        raio = TILE // 2 - 4 + int(2.5 * math.sin(agora * 8))
        pygame.draw.circle(surf, (255, 122, 26, 90), (cx, cy), raio + 7, 3)
        pygame.draw.circle(surf, ATUAL, (cx, cy), TILE // 2 - 5)
        pygame.draw.circle(surf, ATUAL_EDGE, (cx, cy), TILE // 2 - 5, 2)
        pygame.draw.circle(surf, (255, 255, 255), (cx - 3, cy - 3), 4)

    # trilha do jogador (modo manual)
    if manual:
        if len(player_trilha) >= 2:
            pts = [centro_grade(*c) for c in player_trilha]
            pygame.draw.lines(surf, (14, 90, 110), False, pts, 10)
            pygame.draw.lines(surf, (90, 220, 245), False, pts, 4)
        px, py = centro_grade(*player)
        pygame.draw.circle(surf, (140, 240, 255), (px, py), TILE // 2 - 2)
        pygame.draw.circle(surf, (8, 60, 80), (px, py), TILE // 2 - 2, 3)
        texto(surf, "S", (px, py - 11), 17, (8, 60, 80), True, centro=True)
    else:
        # robô do início
        sx, sy = centro_grade(*GRID_INICIO)
        pygame.draw.circle(surf, (20, 90, 110), (sx, sy), TILE // 2 - 1)
        pygame.draw.circle(surf, START, (sx, sy), TILE // 2 - 4)
        pygame.draw.circle(surf, (255, 255, 255), (sx, sy), TILE // 2 - 4, 2)
        texto(surf, "S", (sx, sy - 11), 17, (6, 50, 70), True, centro=True)

    # objetivo: alvo pulsante
    ex, ey = centro_grade(*GRID_OBJETIVO)
    onda = (agora * 40) % 22
    if onda < 11:
        pygame.draw.circle(surf, (244, 63, 94), (ex, ey), TILE // 2 + int(onda), 2)
    pygame.draw.circle(surf, (90, 15, 30), (ex, ey), TILE // 2 - 1)
    pygame.draw.circle(surf, GOAL, (ex, ey), TILE // 2 - 4)
    pygame.draw.circle(surf, (255, 255, 255), (ex, ey), TILE // 2 - 10)
    pygame.draw.circle(surf, GOAL, (ex, ey), TILE // 2 - 15)

    # confete
    for p in particulas:
        a = max(0, 1 - p["idade"] / p["vida"])
        if a <= 0:
            continue
        r = max(1, int(p["tam"] * a))
        pygame.draw.circle(surf, p["cor"], (int(p["x"]), int(p["y"])), r)


def desenhar_legenda(surf):
    y = BOARD_Y + BOARD_H + 12
    x = BOARD_X + 4
    itens = [
        (VISITED, "Visitado"), (FRONT_TOP, "Fronteira"),
        (ATUAL, "Atual"), (PATH_IN, "Caminho"),
        (BEST_RING, "Melhor h"), (GUIDE, "Guia h"),
        (WALL, "Parede"),
    ]
    for cor, nome in itens:
        pygame.draw.rect(surf, cor, (x, y, 13, 13), border_radius=4)
        pygame.draw.rect(surf, (0, 0, 0), (x, y, 13, 13), 1, border_radius=4)
        img = fonte(12).render(nome, True, MUTED)
        surf.blit(img, (x + 17, y - 1))
        x += 17 + img.get_width() + 14


def desenhar_sidebar(surf, agora):
    global algo_rects, btn_pausar, btn_comparar, btn_calor, btn_jogar, barra_prog
    algo_rects = []
    y = BOARD_Y
    w = SIDEBAR_W

    # --- algoritmos ---
    painel(surf, (SIDE_X, y, w, 208))
    texto(surf, "ALGORITMO  (teclas 1-5, ou clique)", (SIDE_X + 14, y + 8), 12, MUTED, True)
    est = estado_atual()
    for i, algo in enumerate(ORDEM):
        ry = y + 28 + i * 35
        r = pygame.Rect(SIDE_X + 8, ry, w - 16, 32)
        algo_rects.append((r, algo))
        sel = (algo == algoritmo)
        pygame.draw.rect(surf, (28, 45, 80) if sel else (17, 27, 52), r, border_radius=10)
        pygame.draw.rect(surf, ACCENT if sel else CARD_EDGE, r, 2 if sel else 1, border_radius=10)
        texto(surf, str(i + 1), (r.x + 10, r.y + 7), 13, ACCENT if sel else MUTED, True)
        nome, desc = NOMES[algo]
        estrela = "* " if algo in ("gulosa", "astar") else ""
        texto(surf, f"{estrela}{nome}", (r.x + 28, r.y + 3), 14, TEXT, sel)
        texto(surf, desc, (r.x + 28, r.y + 17), 11, MUTED)
        if sel:
            pygame.draw.circle(surf, GOOD if (est and est["encontrado"]) else ACCENT,
                               (r.right - 16, r.centery), 5)
    y += 208 + 10

    # --- estatísticas ---
    painel(surf, (SIDE_X, y, w, 132))
    texto(surf, "ESTATÍSTICAS", (SIDE_X + 14, y + 8), 12, MUTED, True)
    if manual:
        dur = (pygame.time.get_ticks() - t0_manual) / 1000 if t0_manual else 0
        vals = [("Seus passos", str(player_passos)), ("Tempo", f"{dur:.0f}s"),
                ("h até o alvo", str(h_grade(player))), ("Recorde A*", "—")]
    elif est:
        vals = [("Passos", str(est["passos"])), ("Visitados", str(len(est["visitados"]))),
                ("Fronteira", str(len(est["fronteira"]))),
                ("Caminho", str(len(est["caminho"])) if est["encontrado"] else "—")]
    else:
        vals = [("—", "—")] * 4
    for k, (rot, val) in enumerate(vals):
        cx = SIDE_X + 14 + (k % 2) * ((w - 28) // 2)
        cy = y + 28 + (k // 2) * 38
        texto(surf, rot.upper(), (cx, cy), 11, MUTED, True)
        texto(surf, val, (cx, cy + 13), 20, TEXT, True)
    total = max(len(historico) - 1, 1)
    prog = indice / total if not manual else 0
    barra_prog = pygame.Rect(SIDE_X + 14, y + 110, w - 28, 10)
    pygame.draw.rect(surf, (13, 22, 44), barra_prog, border_radius=5)
    if prog > 0:
        preench = barra_prog.copy()
        preench.width = int(barra_prog.width * prog)
        pygame.draw.rect(surf, ACCENT, preench, border_radius=5)
    pygame.draw.rect(surf, CARD_EDGE, barra_prog, 1, border_radius=5)
    y += 132 + 10

    # --- heurística ao vivo ---
    painel(surf, (SIDE_X, y, w, 76), edge=(120, 60, 140), borda=1)
    texto(surf, "HEURÍSTICA h = |dx| + |dy|", (SIDE_X + 14, y + 8), 12, (240, 180, 250), True)
    if not manual and est and est["atual"]:
        hat = h_grade(est["atual"])
        texto(surf, f"h(atual) = {hat}   •   quanto menor, mais quente", (SIDE_X + 14, y + 28), 13, TEXT)
        if algoritmo == "astar":
            texto(surf, "A*: escolhe menor f = g + h  (custo + palpite)", (SIDE_X + 14, y + 46), 12, MUTED)
        elif algoritmo == "gulosa":
            texto(surf, "Gulosa: escolhe menor h  (palpite puro)", (SIDE_X + 14, y + 46), 12, MUTED)
        else:
            texto(surf, "sem heurística: ignora o h (anda no escuro)", (SIDE_X + 14, y + 46), 12, MUTED)
    elif manual:
        texto(surf, f"sua h até o alvo = {h_grade(player)}  •  fuja do amarelo!", (SIDE_X + 14, y + 30), 13, TEXT)
    else:
        texto(surf, "aperte H: o calor mostra o palpite h", (SIDE_X + 14, y + 30), 13, MUTED)
    y += 76 + 10

    # --- ações ---
    bw = (w - 10 * 2 - 6) // 2
    btn_pausar = pygame.Rect(SIDE_X, y, bw, 34)
    btn_comparar = pygame.Rect(SIDE_X + bw + 6, y, bw, 34)
    rot_pausa = "|| Pausar" if (tocando and not manual) else "> Continuar"
    for r, rot in ((btn_pausar, rot_pausa), (btn_comparar, "Comparar (C)")):
        painel(surf, r, fill=(28, 45, 80), edge=ACCENT, raio=10, borda=1)
        texto(surf, rot, (r.centerx, r.y + 9), 13, TEXT, True, centro=True)
    y += 34 + 6
    btn_calor = pygame.Rect(SIDE_X, y, bw, 34)
    btn_jogar = pygame.Rect(SIDE_X + bw + 6, y, bw, 34)
    for r, rot in ((btn_calor, f"Calor h: {'ON' if heatmap else 'OFF'}"),
                   (btn_jogar, "Voltar (M)" if manual else "Jogar (M)")):
        painel(surf, r, fill=CARD, edge=CARD_EDGE, raio=10, borda=1)
        texto(surf, rot, (r.centerx, r.y + 9), 13, TEXT, True, centro=True)


def desenhar_rodape(surf):
    y = WIN_H - FOOTER_H
    surf.fill((6, 10, 22), (0, y, WIN_W, FOOTER_H))
    pygame.draw.line(surf, BOARD_EDGE, (0, y), (WIN_W, y))
    msg = ("1-5 algoritmo   •   ESPACO pausa   •   setas passo   •   +/- velocidade"
           "   •   H calor   •   C compara   •   M joga   •   R reinicia   •   ESC sai")
    texto(surf, msg, (WIN_W // 2, y + 9), 13, MUTED, centro=True)


def desenhar_comparativo(surf):
    surf.fill((4, 6, 14), (0, 0, WIN_W, WIN_H))
    larg, alt = 660, 470
    x0, y0 = (WIN_W - larg) // 2, (WIN_H - alt) // 2
    painel(surf, (x0, y0, larg, alt), fill=(14, 22, 44), edge=ACCENT, raio=18, borda=2)
    texto(surf, "COMPARATIVO - a heurística vale a pena?", (x0 + 26, y0 + 18), 19, TEXT, True)
    texto(surf, "barras = células visitadas (menos é melhor)   •   C ou ESC fecha",
          (x0 + 26, y0 + 44), 13, MUTED)
    if not comparativo:
        return
    vmax = max(c["visitados"] for c in comparativo) or 1
    vmin = min(c["visitados"] for c in comparativo)
    cmin = min((c["caminho"] for c in comparativo if c["ok"]), default=0)
    y = y0 + 80
    for c in comparativo:
        nome, _ = NOMES[c["algo"]]
        cor_barra = GOOD if c["visitados"] == vmin else (WARN if c["algo"] in ("gulosa", "astar") else ACCENT)
        texto(surf, nome, (x0 + 26, y), 15, TEXT, True)
        if c["algo"] in ("gulosa", "astar"):
            texto(surf, "usa h *", (x0 + 120, y + 1), 12, (240, 180, 250), True)
        barra = pygame.Rect(x0 + 200, y + 2, int(300 * c["visitados"] / vmax), 18)
        pygame.draw.rect(surf, (10, 18, 38), (x0 + 200, y + 2, 300, 18), border_radius=9)
        pygame.draw.rect(surf, cor_barra, barra, border_radius=9)
        info = f"{c['visitados']} visit.  •  caminho {c['caminho'] or '—'}"
        texto(surf, info, (x0 + 510, y + 1), 13, MUTED)
        if c["caminho"] == cmin and c["ok"]:
            texto(surf, "* menor caminho", (x0 + 510, y + 17), 11, GOOD, True)
        y += 52
    texto(surf, "BFS e A* sempre acham o menor caminho. A Gulosa é rápida, mas pode errar.",
          (x0 + 26, y + 6), 13, MUTED)
    texto(surf, "A* = caminho curto + poucas visitas: o melhor dos dois mundos.",
          (x0 + 26, y + 24), 13, GOOD, True)
    r = pygame.Rect(x0 + larg - 150, y0 + alt - 56, 124, 34)
    painel(surf, r, fill=(28, 45, 80), edge=ACCENT, raio=10, borda=1)
    texto(surf, "Fechar (C)", (r.centerx, r.y + 9), 13, TEXT, True, centro=True)


def desenhar_vitoria_manual(surf):
    larg, alt = 460, 210
    x0, y0 = (WIN_W - larg) // 2, (WIN_H - alt) // 2
    painel(surf, (x0, y0, larg, alt), fill=(12, 30, 32), edge=GOOD, raio=18, borda=2)
    texto(surf, "* VOCÊ ESCAPOU DO LABIRINTO!", (x0 + larg // 2, y0 + 24), 20, GOOD, True, centro=True)
    dur = (pygame.time.get_ticks() - t0_manual) / 1000 if t0_manual else 0
    texto(surf, f"{player_passos} passos   •   {dur:.1f}s", (x0 + larg // 2, y0 + 62), 17, TEXT, True, centro=True)
    texto(surf, "M volta pra IA   •   R joga de novo", (x0 + larg // 2, y0 + 96), 14, MUTED, centro=True)
    ref = next((c for c in comparativo if c["algo"] == "astar"), None)
    if ref:
        texto(surf, f"o A* resolve com caminho {ref['caminho']} — consegue empatar?",
              (x0 + larg // 2, y0 + 122), 13, ACCENT, centro=True)
    r = pygame.Rect(x0 + larg // 2 - 90, y0 + 150, 180, 36)
    painel(surf, r, fill=(28, 45, 80), edge=GOOD, raio=10, borda=1)
    texto(surf, "Jogar de novo (R)", (r.centerx, r.y + 10), 14, TEXT, True, centro=True)


# ---------------------------------------------------------------------------
# Lógica: avanço, manual, eventos
# ---------------------------------------------------------------------------

def avancar():
    global indice, t_encontrou
    if manual or comparando or not tocando or not historico:
        return
    if indice < len(historico) - 1:
        indice += 1
        if historico[indice]["encontrado"] and not t_encontrou:
            t_encontrou = pygame.time.get_ticks() / 1000
            lancar_confete()
    else:
        if historico[indice]["encontrado"] and not confete_feito:
            t_encontrou = pygame.time.get_ticks() / 1000
            lancar_confete()


def entrar_manual():
    global manual, player, player_trilha, player_passos, t0_manual, venceu_manual, comparativo
    manual = True
    comparando_off()
    player = GRID_INICIO
    player_trilha = [GRID_INICIO]
    player_passos = 0
    t0_manual = pygame.time.get_ticks()
    venceu_manual = False
    if not comparativo:
        comparativo.extend(calcular_comparativo())


def sair_manual():
    global manual
    manual = False


def comparando_off():
    global comparando
    comparando = False


def mover_jogador(dx, dy):
    global player, player_passos, venceu_manual
    if venceu_manual:
        return
    nx, ny = player[0] + dx, player[1] + dy
    if not (0 <= nx < LARGURA and 0 <= ny < ALTURA):
        return
    if (nx, ny) in GRID_PAREDES:
        return
    player = (nx, ny)
    player_trilha.append(player)
    player_passos += 1
    if player == GRID_OBJETIVO:
        venceu_manual = True


def trocar_algoritmo(novo):
    global comparando
    comparando = False
    if manual:
        sair_manual()
    if novo != algoritmo or not historico:
        reset(novo)
    else:
        reset()  # mesmo algoritmo: reembaralha (a aleatória muda)


# ---------------------------------------------------------------------------
# Loop principal
# ---------------------------------------------------------------------------

def main():
    global indice, tocando, fps, heatmap, guia, comparando, comparativo
    global manual, t_encontrou

    pygame.init()
    pygame.display.set_caption("Busca no Labirinto - Aleatoria, BFS, DFS, Gulosa, A*")
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    clock = pygame.time.Clock()
    agora = 0.0

    reset()
    if "--comparar" in sys.argv:
        comparativo = calcular_comparativo()
        comparando = True

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        agora = pygame.time.get_ticks() / 1000.0

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    if comparando:
                        comparando = False
                    elif manual:
                        sair_manual()
                    else:
                        running = False
                elif e.key == pygame.K_SPACE and not manual and not comparando:
                    tocando = not tocando
                elif e.key == pygame.K_r:
                    if manual:
                        entrar_manual()
                    else:
                        reset()
                elif e.key in (pygame.K_EQUALS, pygame.K_KP_PLUS, pygame.K_PLUS):
                    fps = min(fps + 4, 120)
                elif e.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    fps = max(fps - 4, 1)
                elif e.key == pygame.K_h:
                    heatmap = not heatmap
                    guia = heatmap
                elif e.key == pygame.K_c and not manual:
                    if not comparando:
                        comparativo = calcular_comparativo()
                    comparando = not comparando
                elif e.key == pygame.K_m:
                    entrar_manual() if not manual else sair_manual()
                elif e.key == pygame.K_RIGHT and not manual and not comparando:
                    tocando = False
                    if indice < len(historico) - 1:
                        indice += 1
                elif e.key == pygame.K_LEFT and not manual and not comparando:
                    tocando = False
                    indice = max(0, indice - 1)
                elif manual and not venceu_manual:
                    if e.key in (pygame.K_UP, pygame.K_w):
                        mover_jogador(0, -1)
                    elif e.key in (pygame.K_DOWN, pygame.K_s):
                        mover_jogador(0, 1)
                    elif e.key in (pygame.K_LEFT, pygame.K_a):
                        mover_jogador(-1, 0)
                    elif e.key in (pygame.K_RIGHT, pygame.K_d):
                        mover_jogador(1, 0)
                if not manual and not comparando and e.unicode in TECLA_PARA_ALGO:
                    trocar_algoritmo(TECLA_PARA_ALGO[e.unicode])
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos
                for r, algo in algo_rects:
                    if r.collidepoint(mx, my):
                        trocar_algoritmo(algo)
                        break
                else:
                    if btn_pausar and btn_pausar.collidepoint(mx, my) and not manual:
                        tocando = not tocando
                    elif btn_comparar and btn_comparar.collidepoint(mx, my) and not manual:
                        if not comparando:
                            comparativo = calcular_comparativo()
                        comparando = not comparando
                    elif btn_calor and btn_calor.collidepoint(mx, my):
                        heatmap = not heatmap
                        guia = heatmap
                    elif btn_jogar and btn_jogar.collidepoint(mx, my):
                        entrar_manual() if not manual else sair_manual()
                    elif barra_prog and barra_prog.collidepoint(mx, my) and not manual:
                        t = (mx - barra_prog.x) / max(barra_prog.width, 1)
                        indice = max(0, min(len(historico) - 1, int(t * (len(historico) - 1))))
                        if historico and historico[indice]["encontrado"] and not confete_feito:
                            t_encontrou = agora
                            lancar_confete()

        # física leve: animação contínua + confete
        if not comparando:
            avancar_timer = getattr(main, "_acc", 0.0) + dt
            if tocando and not manual and historico:
                intervalo = 1.0 / max(fps, 1)
                while avancar_timer >= intervalo:
                    avancar_timer -= intervalo
                    avancar()
                    if indice >= len(historico) - 1:
                        break
            main._acc = avancar_timer if (tocando and not manual) else 0.0
        for p in particulas:
            p["idade"] += dt
            p["vy"] += 260 * dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
        particulas[:] = [p for p in particulas if p["idade"] < p["vida"]]

        # desenho
        screen.fill(BG)
        if comparando:
            desenhar_comparativo(screen)
        else:
            desenhar_cabecalho(screen, agora)
            desenhar_tabuleiro(screen, agora)
            desenhar_legenda(screen)
            desenhar_sidebar(screen, agora)
            desenhar_rodape(screen)
            if manual and venceu_manual:
                desenhar_vitoria_manual(screen)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
