"""Laboratorio: prototipos das cinco ideias de expansao do painel.

1. ranking()     jogo dos promoters (pontos, niveis, missoes)
2. votacao()     a pista decide (votacao ao vivo de genero)
3. textos()      estudio de texto no tom da marca + checagem()
4. roteiro()     roteiro vivo da noite, que se ajusta a lotacao, energia e votos
5. sentimento()  leitura pos-evento dos comentarios, por tema

Os prototipos usam regras e lexicos simples, de proposito: mostram o comportamento sem depender
de servico externo. O README explica onde entra um modelo de linguagem em cada um.
"""
import re
from datetime import date, timedelta

from banco import estoque, hoje, q, sem_acento

GENEROS = ["House", "Deep House", "Indie Dance", "Melodic House", "Tech House", "Progressive House"]

# ---------------------------------------------------------------- 1. jogo dos promoters

NIVEIS = [(0, "Vislumbre"), (60, "Foco"), (180, "Visão"), (400, "Infinito")]


def _sequencia(datas):
    """Dias seguidos com story, contando de hoje (ou ontem) para tras."""
    dias = {date.fromisoformat(d) for d in datas}
    cursor = hoje()
    if cursor not in dias:
        cursor -= timedelta(days=1)
    n = 0
    while cursor in dias:
        n += 1
        cursor -= timedelta(days=1)
    return n


def ranking(promoters):
    corte = (hoje() - timedelta(days=2)).isoformat()
    saida = []
    for p in promoters:
        if not p["ativo"]:
            continue
        stories = [r["data"] for r in q("SELECT data FROM promoter_stories WHERE promoter_id = ?", (p["id"],))]
        recentes = q(
            "SELECT COALESCE(SUM(quantidade), 0) AS n FROM pedidos WHERE promoter_id = ? AND status = 'pago' AND substr(criado_em, 1, 10) >= ?",
            (p["id"], corte),
        )[0]["n"]
        seq = _sequencia(stories)
        missoes = [
            {"nome": "Três em três", "regra": "3 ingressos em 3 dias", "feito": min(recentes, 3), "alvo": 3, "pontos": 30},
            {"nome": "Olho aberto", "regra": "story 3 dias seguidos", "feito": min(seq, 3), "alvo": 3, "pontos": 20},
        ]
        if p.get("proxima_faixa"):
            alvo = p["proxima_faixa"]["min_vendas"]
            missoes.append({"nome": "Próximo degrau", "regra": f"chegar a {alvo} vendas", "feito": min(p["vendas"], alvo), "alvo": alvo, "pontos": 40})
        pontos = p["vendas"] * 10 + len(stories) * 4 + seq * 5 + sum(m["pontos"] for m in missoes if m["feito"] >= m["alvo"])
        nivel = max((n for n in NIVEIS if pontos >= n[0]), key=lambda n: n[0])
        proximo = next((n for n in NIVEIS if n[0] > pontos), None)
        saida.append({
            "id": p["id"], "nome": p["nome"], "codigo": p["codigo"], "vendas": p["vendas"], "stories": len(stories),
            "sequencia": seq, "pontos": pontos, "nivel": nivel[1],
            "proximo_nivel": {"nome": proximo[1], "faltam": proximo[0] - pontos} if proximo else None,
            "missoes": missoes,
        })
    saida.sort(key=lambda r: -r["pontos"])
    for i, r in enumerate(saida):
        r["posicao"] = i + 1
    return {
        "regras": "10 pontos por ingresso, 4 por story, 5 por dia de sequência e o bônus de cada missão cumprida.",
        "niveis": [{"nome": n, "a_partir_de": p} for p, n in NIVEIS],
        "ranking": saida,
    }


# ---------------------------------------------------------------- 2. a pista decide

def votacao(edicao_id):
    contagem = {r["opcao"]: r["n"] for r in q("SELECT opcao, COUNT(*) AS n FROM votos WHERE edicao_id = ? GROUP BY opcao", (edicao_id,))}
    total = sum(contagem.values())
    opcoes = [{"opcao": g, "votos": contagem.get(g, 0), "pct": round(100 * contagem.get(g, 0) / total) if total else 0} for g in GENEROS]
    opcoes.sort(key=lambda o: -o["votos"])
    return {"pergunta": "O que a pista quer ver no próximo bloco?", "total": total, "opcoes": opcoes,
            "lider": opcoes[0]["opcao"] if total else None}


# ---------------------------------------------------------------- 3. estudio de texto

OBJETIVOS = {
    "abertura": "Abertura das vendas",
    "virada": "Virada de lote",
    "revelacao": "Revelação do tema",
    "lembrete": "Lembrete da véspera",
    "agradecimento": "Agradecimento pós-festa",
}

NIVEIS_MISTERIO = ["Claro", "Velado", "Enigma"]

FRASES = {
    "abertura": [
        "As vendas da {edicao} abrem em {abertura}. Responda a este post e o acesso chega até você. Apenas convidados.",
        "{abertura}. Uma porta se abre para quem já aprendeu a olhar. Responda e receba o caminho.",
        "Olhe de novo. Algo está prestes a se abrir.",
    ],
    "virada": [
        "{lote_anterior}: fechado. A partir de agora, o acesso é pelo {lote}, a R$ {preco}. Quem viu primeiro já está dentro.",
        "Um olhar se fecha, outro se abre. {Lote} disponível para quem ainda procura a entrada.",
        "Quem viu, viu. O próximo olhar já começou.",
    ],
    "revelacao": [
        "{edicao}. {data}, {local}. O tema desta vez devolve o seu olhar: tudo o que você vê também vê você.",
        "Dois espelhos, um de frente para o outro. No meio, você. {data}.",
        "O que acontece quando o olhar não encontra fim?",
    ],
    "lembrete": [
        "É amanhã. {data}, {local}. Leve o ingresso no celular e chegue cedo: a primeira hora é de quem quer ver tudo.",
        "Amanhã os olhos se abrem. Seu acesso já está com você.",
        "Falta um piscar.",
    ],
    "agradecimento": [
        "Obrigado por ter visto com a gente. A {edicao} só existiu porque cada um de vocês esteve lá. As imagens chegam em breve.",
        "O que foi visto não se desfaz. Obrigado por ampliar a visão com a gente.",
        "Você viu. Guarde.",
    ],
}


def textos(ed, objetivo):
    if objetivo not in FRASES:
        objetivo = "abertura"
    lotes = estoque(ed["id"])
    com_estoque = [l for l in lotes if l["quantidade"]]
    ativo = (next((l for l in com_estoque if l["status"] == "ativo"), None)
             or next((l for l in com_estoque if l["status"] == "aguardando"), None)
             or (com_estoque[-1] if com_estoque else None))
    anterior = None
    if ativo:
        antes = [l for l in com_estoque if l["ordem"] < ativo["ordem"]]
        anterior = antes[-1] if antes else None
    dm = lambda iso: date.fromisoformat(iso).strftime("%d.%m") if iso else "em breve"
    campos = {
        "edicao": ed["nome"], "data": dm(ed["data"]), "abertura": dm(ed.get("abertura_vendas")), "local": ed.get("local") or "",
        "lote": ativo["nome"] if ativo else "novo lote",
        "Lote": ativo["nome"] if ativo else "Novo lote",
        "lote_anterior": anterior["nome"] if anterior else "Primeiro lote",
        "preco": f"{ativo['preco']:.0f}" if ativo else "a definir",
    }
    versoes = []
    for nivel, modelo in zip(NIVEIS_MISTERIO, FRASES[objetivo]):
        texto = modelo.format(**campos)
        versoes.append({"nivel": nivel, "texto": texto, "checagem": checagem(texto)})
    return {"objetivo": objetivo, "rotulo": OBJETIVOS[objetivo], "versoes": versoes}


PROIBIDAS = [
    "imperdivel", "bombando", "promocao", "desconto", "garanta", "nao perca", "ultimas vagas", "ultimas unidades",
    "melhor festa", "open bar", "aproveite", "oferta", "corre", "so hoje", "arrasta pra cima", "vem com tudo",
]
VISAO = ["olh", "vis", "enxerg", "percep", "reflex", "foco", "iris", "pisc", "espelh", " ver", "viu", "vê"]
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿️]")


def checagem(texto):
    """Confere um texto contra as regras de voz da marca."""
    bruto = texto or ""
    plano = sem_acento(bruto).lower()
    alertas, acertos = [], []

    achadas = [p for p in PROIBIDAS if re.search(rf"\b{re.escape(p)}\b", plano)]
    if achadas:
        alertas.append("Soa comercial: " + ", ".join(f"“{p}”" for p in achadas) + ". A marca não vende, convida.")
    if EMOJI.search(bruto):
        alertas.append("Tem emoji. Em arte e texto da marca não entra; em legenda, só pontual.")
    if re.search(r"!{2,}", bruto) or bruto.count("!") > 1:
        alertas.append("Exclamação demais. O tom é contido.")
    gritos = [w for w in re.findall(r"\b[A-ZÀ-Ú]{4,}\b", bruto) if w not in ("VISIONS", "HOUSE")]
    if len(gritos) >= 2:
        alertas.append("Muitas palavras em caixa alta. Só o nome da marca pede isso.")
    if len(bruto) > 240:
        alertas.append(f"{len(bruto)} caracteres. Revele menos: acima de 240 o mistério se perde.")
    if bruto.count("#") > 2:
        alertas.append("Hashtags em excesso tiram a sofisticação.")

    if any(v in plano or v in bruto.lower() for v in VISAO):
        acertos.append("Conversa com visão, olhar ou percepção.")
    else:
        alertas.append("Não toca em visão, olhar ou percepção. Falta o fio da marca.")
    if "apenas convidados" in bruto.lower() or "convid" in plano or "acesso" in plano:
        acertos.append("Passa exclusividade pelo acesso, não pelo estoque.")
    if bruto and len(bruto) <= 120 and not achadas:
        acertos.append("Curto: revela só o necessário.")
    return {"ok": not alertas, "alertas": alertas, "acertos": acertos}


# ---------------------------------------------------------------- 4. roteiro vivo

BLOCOS = [
    ("23:00", "Deep House", "Aquecimento"),
    ("00:00", "House", "Subida"),
    ("01:00", "Indie Dance", "Virada"),
    ("02:00", "Tech House", "Pico"),
    ("03:00", "Melodic House", "Respiro"),
    ("04:00", "House", "Fechamento"),
]


def _minutos(hhmm):
    h, m = (int(x) for x in hhmm.split(":"))
    return ((h - 23) % 24) * 60 + m  # minutos desde as 23:00


def roteiro(lotacao, energia, hora, lider=None):
    """Ajusta o roteiro da noite. lotacao 0-100 (% da casa dentro), energia 1-5, hora 'HH:MM'."""
    blocos = [{"hora": h, "genero": g, "fase": f, "mudou": False} for h, g, f in BLOCOS]
    agora_min = _minutos(hora)
    atual = max(0, min(len(blocos) - 1, agora_min // 60))
    pico = next(i for i, b in enumerate(blocos) if b["fase"] == "Pico")
    ajustes = []

    # casa ainda vazia com o pico chegando: segura o pico uma hora
    if lotacao < 60 and atual < pico and pico - atual <= 2:
        blocos[pico], blocos[pico + 1] = blocos[pico + 1], blocos[pico]
        for i in (pico, pico + 1):
            blocos[i]["mudou"] = True
        blocos[pico]["hora"], blocos[pico + 1]["hora"] = BLOCOS[pico][0], BLOCOS[pico + 1][0]
        ajustes.append(f"Só {lotacao}% da casa entrou. O pico foi para as {BLOCOS[pico + 1][0]}: melhor lotar a pista antes de gastar o ponto alto.")
        pico += 1

    # casa cheia e energia caindo antes do pico: antecipa
    elif lotacao >= 80 and energia <= 2 and atual + 1 < pico:
        alvo = atual + 1
        blocos[alvo], blocos[pico] = blocos[pico], blocos[alvo]
        for i in (alvo, pico):
            blocos[i]["mudou"] = True
        blocos[alvo]["hora"], blocos[pico]["hora"] = BLOCOS[alvo][0], BLOCOS[pico][0]
        ajustes.append(f"Casa cheia ({lotacao}%) e pista morna. O pico sobe para as {BLOCOS[alvo][0]}.")
        pico = alvo

    # depois do pico com energia no teto: encurta o respiro
    if atual >= pico and energia >= 4:
        respiro = next((b for b in blocos if b["fase"] == "Respiro"), None)
        if respiro and _minutos(respiro["hora"]) > agora_min:
            respiro["mudou"] = True
            respiro["fase"] = "Respiro curto (30 min)"
            ajustes.append("A pista segue no teto depois do pico. O respiro cai para 30 minutos para não esfriar.")

    # voto da pista: so mexe em bloco flexivel (subida e virada). Pico, respiro e fechamento sao da curadoria.
    if lider:
        prox = atual + 1
        bloco_pico = blocos[pico]
        if lider == bloco_pico["genero"] and pico > atual:
            ajustes.append(f"A pista pede {lider}, que já é o pico da noite. Ele fica guardado para as {bloco_pico['hora']}.")
        elif prox < len(blocos) and blocos[prox]["fase"] in ("Subida", "Virada"):
            if blocos[prox]["genero"] != lider:
                ajustes.append(f"A pista pede {lider}. Ele entra no bloco das {blocos[prox]['hora']} no lugar de {blocos[prox]['genero']}.")
                blocos[prox]["genero"] = lider
                blocos[prox]["mudou"] = True
        elif prox < len(blocos):
            ajustes.append(f"A pista pede {lider}, mas o próximo bloco é de {blocos[prox]['fase'].lower()}. O voto vale para a próxima janela livre.")

    # banheiros: a licao da 1.0 vira lembrete operacional
    avisos = []
    if lotacao >= 70:
        avisos.append("Casa acima de 70%: ronda dos banheiros a cada 20 minutos.")
    if lotacao >= 85 and energia >= 4:
        avisos.append("Pico de movimento: reforce o bar com mais uma pessoa no caixa.")

    for i, b in enumerate(blocos):
        b["agora"] = i == atual
    if not ajustes:
        ajustes.append("Roteiro mantido. Lotação e energia estão dentro do esperado para a hora.")
    return {"hora": hora, "lotacao": lotacao, "energia": energia, "blocos": blocos, "ajustes": ajustes, "avisos": avisos}


# ---------------------------------------------------------------- 5. leitura pos-evento

POSITIVAS = [
    "absurd", "impecavel", "amei", "lind", "otim", "melhor", "surreal", "perfeit", "incrivel", "gostei", "voltaria",
    "bom", "boa", "intim", "energia", "diferente", "nunca vi",
]
NEGATIVAS = [
    "demor", "fila", "suj", "faltou", "fraco", "caro", "poucas", "pouco", "curto", "acabou", "ruim", "lotado",
    "quente", "pena", "pequeno", "rapido demais",
]
TEMAS = {
    "Decoração": ["decora", "neon", "planta", "luz", "luzes", "cenograf", "espelh", "foto"],
    "Som e música": ["som", "music", "dj", "set", "house", "pista"],
    "Bar": ["bar", "drink", "bebida", "cardapio"],
    "Banheiros": ["banheiro", "papel", "limpeza"],
    "Público": ["publico", "galera", "pessoas", "todo mundo", "energia"],
    "Ingressos": ["ingresso", "lote", "porta", "preco", "caro"],
    "Estrutura": ["lugar", "espaco", "pirotecnia", "pequeno"],
}


def _classificar(texto):
    plano = sem_acento(texto).lower()
    pos = sum(1 for p in POSITIVAS if re.search(rf"\b{p}", plano))
    neg = sum(1 for p in NEGATIVAS if re.search(rf"\b{p}", plano))
    saldo = pos - neg
    tom = "positivo" if saldo > 0 else "critico" if saldo < 0 else "misto" if pos and neg else "neutro"
    temas = [t for t, chaves in TEMAS.items() if any(re.search(rf"\b{c}", plano) for c in chaves)]
    return {"tom": tom, "saldo": saldo, "temas": temas or ["Geral"]}


def sentimento(edicao_id):
    linhas = q("SELECT id, texto, nota, criado_em FROM feedbacks WHERE edicao_id = ? ORDER BY id DESC", (edicao_id,))
    temas = {}
    for l in linhas:
        l.update(_classificar(l["texto"]))
        for t in l["temas"]:
            alvo = temas.setdefault(t, {"tema": t, "mencoes": 0, "positivo": 0, "critico": 0, "saldo": 0})
            alvo["mencoes"] += 1
            alvo["saldo"] += l["saldo"]
            if l["tom"] == "positivo":
                alvo["positivo"] += 1
            elif l["tom"] in ("critico", "misto"):
                alvo["critico"] += 1
    lista = sorted(temas.values(), key=lambda t: -t["mencoes"])
    total = len(linhas)
    positivos = sum(1 for l in linhas if l["tom"] == "positivo")
    notas = [l["nota"] for l in linhas if l["nota"]]
    repetir = [t["tema"] for t in lista if t["saldo"] > 0 and t["positivo"] >= t["critico"]]
    corrigir = [t["tema"] for t in sorted(lista, key=lambda t: t["saldo"]) if t["critico"] > t["positivo"]]
    return {
        "total": total,
        "positivos_pct": round(100 * positivos / total) if total else 0,
        "nota_media": round(sum(notas) / len(notas), 1) if notas else None,
        "temas": lista,
        "repetir": repetir[:3],
        "corrigir": corrigir[:3],
        "comentarios": linhas,
    }
