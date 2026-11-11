"""Visoes: as leituras do painel.

Tres frentes, todas calculadas em cima dos dados do banco e do historico da 1.0:
  - leitura de preco   (ritmo, projecao, escada de lotes)
  - leitura do publico (quem esta comprando e o que isso pede da noite)
  - pontos cegos       (riscos e o que fazer com cada um)

Nada aqui e caixa-preta: cada leitura devolve o campo "como_li" explicando a conta.
"""
from collections import Counter
from datetime import date, datetime, timedelta

from banco import agora, estoque, hoje, q, q1

PICO_FINAL = 1.8      # premissa: os ultimos 4 dias vendem 1,8x o ritmo medio
DIAS_DE_PICO = 4
GENEROS = ["Deep House", "Melodic House", "House", "Indie Dance", "Progressive House", "Tech House"]  # do mais calmo ao mais intenso


def arred5(valor):
    return int(round(valor / 5.0) * 5)


def reais(valor):
    inteiro = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return "R$ " + (inteiro[:-3] if inteiro.endswith(",00") else inteiro)


def pct(parte, todo):
    return round(100 * parte / todo) if todo else 0


def plural(n, um, varios):
    return f"{n} {um if n == 1 else varios}"


def fmt_num(valor, casas=1):
    return f"{valor:.{casas}f}".replace(".", ",")


def referencia_1_0():
    custo = q1("SELECT COALESCE(SUM(valor), 0) AS v FROM custos WHERE edicao_id = 1")["v"]
    ed = q1("SELECT * FROM edicoes WHERE id = 1")
    publico = (ed or {}).get("publico_final") or 0
    return {"custo": round(custo, 2), "publico": publico, "custo_por_pessoa": round(custo / publico, 2) if publico else 0}


# ---------------------------------------------------------------- metricas de venda

def serie_diaria(ed):
    linhas = {
        r["dia"]: r
        for r in q(
            "SELECT substr(criado_em, 1, 10) AS dia, SUM(quantidade) AS ingressos, SUM(valor_total) AS receita "
            "FROM pedidos WHERE edicao_id = ? AND status = 'pago' GROUP BY dia",
            (ed["id"],),
        )
    }
    if not ed.get("abertura_vendas"):
        return []
    inicio = date.fromisoformat(ed["abertura_vendas"])
    if linhas:
        inicio = min(inicio, date.fromisoformat(min(linhas)))
    fim = min(hoje(), date.fromisoformat(ed["data"]))
    serie, acumulado, dia = [], 0, inicio
    while dia <= fim:
        r = linhas.get(dia.isoformat())
        n = r["ingressos"] if r else 0
        acumulado += n
        serie.append({"dia": dia.isoformat(), "ingressos": n, "receita": r["receita"] if r else 0, "acumulado": acumulado})
        dia += timedelta(days=1)
    return serie


def metricas(ed, lotes=None):
    lotes = lotes if lotes is not None else estoque(ed["id"])
    h = hoje()
    festa = date.fromisoformat(ed["data"])
    abertura = date.fromisoformat(ed["abertura_vendas"]) if ed.get("abertura_vendas") else h
    serie = serie_diaria(ed)

    vendidos = sum(l["vendidos"] for l in lotes)
    reservados = sum(l["reservados"] for l in lotes)
    receita = sum(l["receita"] for l in lotes)
    capacidade = ed["capacidade"]
    restante = max(capacidade - vendidos, 0)
    dias_restantes = max((festa - h).days, 0)

    def ritmo(n):
        ultimos = serie[-n:]
        return sum(x["ingressos"] for x in ultimos) / len(ultimos) if ultimos else 0.0

    r3, r7 = ritmo(3), ritmo(7)
    base = 0.6 * r3 + 0.4 * r7
    necessario = (restante / dias_restantes) if dias_restantes else float(restante)
    indice = round(base / necessario, 2) if necessario > 0 else None

    def projetar(b, pico):
        total, pontos = float(vendidos), []
        for i in range(1, dias_restantes + 1):
            fator = pico if (dias_restantes - i) < DIAS_DE_PICO else 1.0
            total = min(capacidade, total + b * fator)
            pontos.append({"dia": (h + timedelta(days=i)).isoformat(), "acumulado": round(total, 1)})
        return pontos

    central = projetar(base, PICO_FINAL)
    baixa = projetar(r3, 1.0)
    alta = projetar(max(base, r7), 2.4)
    fim = lambda pontos: round(pontos[-1]["acumulado"]) if pontos else vendidos

    potencial = receita + sum((l["disponivel"] or 0) * l["preco"] + l["reservados"] * l["preco"] for l in lotes)
    ref = referencia_1_0()

    return {
        "hoje": h.isoformat(),
        "vendidos": vendidos,
        "reservados": reservados,
        "capacidade": capacidade,
        "restante": restante,
        "ocupacao": pct(vendidos, capacidade),
        "receita": round(receita, 2),
        "ticket_medio": round(receita / vendidos, 2) if vendidos else 0,
        "receita_potencial": round(potencial, 2),
        "dias_restantes": dias_restantes,
        "dias_ate_abertura": max((abertura - h).days, 0),
        "dia_de_venda": max((h - abertura).days + 1, 0) if h <= festa else None,
        "dias_de_venda": (festa - abertura).days,
        "ritmo_3d": round(r3, 2),
        "ritmo_7d": round(r7, 2),
        "ritmo_base": round(base, 2),
        "ritmo_necessario": round(necessario, 2),
        "indice": indice,
        "projecao": {"central": fim(central), "baixa": fim(baixa), "alta": fim(alta), "pontos": central},
        "serie": serie,
        "referencia": ref,
        "cobertura_custo": pct(receita, ref["custo"]),
    }


# ---------------------------------------------------------------- leitura de preco

def leitura_precos(ed, m, lotes):
    itens = []
    indice = m["indice"]
    em_venda = m["dia_de_venda"] and m["dia_de_venda"] > 0 and m["vendidos"] > 0
    ativos = [l for l in lotes if l["status"] == "ativo"]
    futuros = [l for l in lotes if l["status"] == "aguardando"]
    com_estoque = [l for l in lotes if l["quantidade"] is not None]
    ref = m["referencia"]

    # 1. quanto a escada inteira rende, comparado ao custo da 1.0
    if com_estoque:
        folga = m["receita_potencial"] - ref["custo"]
        itens.append({
            "id": "escada",
            "tom": "atencao" if folga < ref["custo"] * 0.2 else "ok",
            "titulo": "Quanto a escada inteira rende",
            "leitura": (
                f"Esgotando todos os lotes nos preços de hoje, a bilheteria fecha em {reais(m['receita_potencial'])}. "
                f"A 1.0 custou {reais(ref['custo'])} ({reais(ref['custo_por_pessoa'])} por pessoa). "
                + (f"Sobram {reais(folga)} de folga." if folga >= 0 else f"Faltam {reais(-folga)} para empatar só com ingresso.")
            ),
            "sugestao": (
                "A folga é curta: a edição depende do bar para fechar bem. Um degrau a mais antes da porta "
                "ou um drink autoral vendido antes da noite aliviam essa conta."
                if folga < ref["custo"] * 0.2 else
                "A escada cobre o custo de referência com folga. O bar entra como resultado, não como salvação."
            ),
            "como_li": "Receita já paga + (ingressos livres e reservados × preço de cada lote), contra o custo total da 1.0.",
        })

    # 2. o lote que esta aberto: em quantos dias esgota
    for l in ativos:
        if not em_venda or l["disponivel"] is None:
            continue
        ritmo = m["ritmo_base"]
        dias = (l["disponivel"] / ritmo) if ritmo > 0 else None
        depois = [x for x in futuros if x["ordem"] > l["ordem"]]
        em_risco = sum((x["quantidade"] or 0) * x["preco"] for x in depois)
        qtd_depois = sum(x["quantidade"] or 0 for x in depois)
        sobra = max(m["dias_restantes"] - dias, 0) if dias is not None else 0
        cabem = int(ritmo * sobra)
        if depois and (dias is None or cabem < qtd_depois):
            if dias is None or dias > m["dias_restantes"]:
                conta = f"o {l['nome']} não esgota antes da festa. Os {qtd_depois} ingressos seguintes, que valem {reais(em_risco)}, nem chegam a abrir."
            else:
                conta = (
                    f"o {l['nome']} leva cerca de {max(round(dias), 1)} dias para esgotar. Sobram {round(sobra)} dias para os "
                    f"{qtd_depois} ingressos seguintes, que valem {reais(em_risco)}: no mesmo ritmo, saem só {cabem}."
                )
            data_virada = (hoje() + timedelta(days=max(min(4, m["dias_restantes"] - 5), 1))).strftime("%d/%m")
            itens.append({
                "id": f"lote-lento-{l['id']}",
                "tom": "atencao",
                "titulo": f"{l['nome']} está segurando a escada",
                "leitura": f"No ritmo de {fmt_num(m['ritmo_base'])} ingressos por dia, {conta}",
                "sugestao": (
                    f"Não mexa no preço para baixo. Marque a virada por data: anuncie que o {l['nome']} fecha em "
                    f"{data_virada}, sobre ou não sobre ingresso. A escassez passa a ser de tempo, o que combina com a marca."
                ),
                "como_li": "Ingressos livres do lote ÷ ritmo base (60% dos últimos 3 dias + 40% dos últimos 7).",
            })
        elif dias <= 2 and depois:
            itens.append({
                "id": f"lote-virando-{l['id']}",
                "tom": "ok",
                "titulo": f"{l['nome']} vira em até {plural(max(round(dias), 1), 'dia', 'dias')}",
                "leitura": f"Restam {l['disponivel']} ingressos e o ritmo é de {fmt_num(m['ritmo_base'])} por dia.",
                "sugestao": f"Deixe arte e texto da virada para o {depois[0]['nome']} prontos hoje. A troca de lote é automática.",
                "como_li": "Ingressos livres do lote ÷ ritmo base.",
            })

    # 3. degraus que ainda nao abriram: subir, segurar ou manter
    if em_venda and indice is not None:
        for l in futuros:
            if "porta" in l["nome"].lower():
                continue
            if indice >= 1.25:
                novo = arred5(l["preco"] * (1.15 if indice >= 1.6 else 1.10))
                if novo > l["preco"]:
                    itens.append({
                        "id": f"subir-{l['id']}",
                        "tom": "oportunidade",
                        "titulo": f"{l['nome']}: há espaço para {reais(novo)}",
                        "leitura": (
                            f"A venda corre a {fmt_num(indice, 2)}× do ritmo necessário para lotar. Quando a procura passa de 1,25×, "
                            "o próximo degrau aguenta um preço maior sem travar."
                        ),
                        "sugestao": f"Suba de {reais(l['preco'])} para {reais(novo)} antes de abrir o lote. Quem já comprou não é afetado.",
                        "impacto": round((novo - l["preco"]) * (l["quantidade"] or 0), 2),
                        "acoes": [{"rotulo": f"Aplicar {reais(novo)}", "metodo": "PATCH", "url": f"/api/lotes/{l['id']}", "corpo": {"preco": novo}}],
                        "como_li": "Índice de demanda = ritmo base ÷ ritmo necessário. Acima de 1,25 sugiro +10%; acima de 1,6, +15%.",
                    })
            elif indice < 0.8:
                itens.append({
                    "id": f"segurar-{l['id']}",
                    "tom": "neutro",
                    "titulo": f"{l['nome']}: segure em {reais(l['preco'])}",
                    "leitura": f"A venda corre a {fmt_num(indice, 2)}× do ritmo necessário. Subir o próximo degrau agora só alonga o intervalo sem venda.",
                    "sugestao": "Mantenha o preço. O que destrava o ritmo aqui é revelação e promoter em movimento, não desconto.",
                    "como_li": "Índice de demanda abaixo de 0,8: preço fica como está.",
                })

    # 4. a licao da 1.0: o ultimo lote antes da porta esgotou rapido demais
    antes_da_porta = [l for l in com_estoque if "porta" not in l["nome"].lower()]
    if len(antes_da_porta) >= 2:
        ultimo, doador = antes_da_porta[-1], antes_da_porta[-2]
        fatia = ultimo["quantidade"] / ed["capacidade"]
        alvo = round(ed["capacidade"] * 0.25)
        delta = alvo - ultimo["quantidade"]
        if ultimo["status"] == "aguardando" and fatia < 0.22 and delta > 0:
            pode = doador["disponivel"] is not None and doador["disponivel"] >= delta and doador["status"] in ("ativo", "aguardando")
            item = {
                "id": "licao-terceiro-lote",
                "tom": "atencao",
                "titulo": f"{ultimo['nome']} está pequeno de novo",
                "leitura": (
                    f"Na 1.0 o 3º lote ({reais(70)}) esgotou rápido demais. Hoje o {ultimo['nome']} tem {ultimo['quantidade']} "
                    f"ingressos, {pct(ultimo['quantidade'], ed['capacidade'])}% da casa."
                ),
                "sugestao": (
                    f"Leve o {ultimo['nome']} para {alvo} ingressos (25% da casa), tirando {delta} do {doador['nome']}. "
                    + ("Com o ritmo abaixo do necessário, faça a troca junto com a virada por data, não antes."
                       if indice is not None and indice < 0.8 else "A capacidade total não muda.")
                ),
                "impacto": round(delta * (ultimo["preco"] - doador["preco"]), 2),
                "como_li": "Fatia do último lote antes da porta na capacidade. Abaixo de 22% eu aponto; o alvo é 25%.",
            }
            if pode:
                item["acoes"] = [
                    {"rotulo": f"Passar {delta} para o {ultimo['nome']}", "metodo": "PATCH", "url": f"/api/lotes/{doador['id']}",
                     "corpo": {"quantidade": doador["quantidade"] - delta}},
                    {"metodo": "PATCH", "url": f"/api/lotes/{ultimo['id']}", "corpo": {"quantidade": alvo}},
                ]
            itens.append(item)

    # 5. porta: precisa ficar bem acima do ultimo lote
    porta = next((l for l in lotes if "porta" in l["nome"].lower()), None)
    if porta and antes_da_porta:
        teto = antes_da_porta[-1]["preco"]
        if porta["preco"] < teto * 1.5:
            novo = arred5(teto * 1.7)
            itens.append({
                "id": "porta",
                "tom": "oportunidade",
                "titulo": f"Porta: leve para {reais(novo)}",
                "leitura": f"A porta está a {reais(porta['preco'])}, perto demais do último lote ({reais(teto)}). Na 1.0 ela ficou em {reais(120)} contra {reais(70)}.",
                "sugestao": "A porta cara protege quem comprou antes e reforça que o acesso se decide cedo.",
                "acoes": [{"rotulo": f"Aplicar {reais(novo)}", "metodo": "PATCH", "url": f"/api/lotes/{porta['id']}", "corpo": {"preco": novo}}],
                "como_li": "Porta ÷ último lote. A referência da 1.0 foi 1,7×; abaixo de 1,5× eu aponto.",
            })

    # 6. soma dos lotes contra a capacidade
    soma = sum(l["quantidade"] for l in com_estoque)
    if com_estoque and soma != ed["capacidade"]:
        mais = soma > ed["capacidade"]
        itens.append({
            "id": "soma-lotes",
            "tom": "atencao" if mais else "neutro",
            "titulo": "Lotes e capacidade não fecham",
            "leitura": f"Os lotes somam {soma} ingressos e a casa comporta {ed['capacidade']}.",
            "sugestao": "Reduza algum lote: vender acima do limite da casa quebra a experiência." if mais
            else f"Há {ed['capacidade'] - soma} lugares sem lote. Distribua ou deixe como reserva de convidados.",
            "como_li": "Soma das quantidades de todos os lotes da edição.",
        })

    if not com_estoque:
        itens.append({
            "id": "sem-lotes",
            "tom": "neutro",
            "titulo": "A escada ainda não existe",
            "leitura": "Nenhum lote criado para esta edição. A 1.0 usou cinco degraus: R$ 25, R$ 35, R$ 50, R$ 70 e porta a R$ 120.",
            "sugestao": "Comece repetindo os degraus da 1.0 e dê ao 3º lote pelo menos 25% da casa.",
            "como_li": "Histórico de preços da 1.0.",
        })
    return itens


# ---------------------------------------------------------------- leitura do publico

def _dist(valores):
    validos = [v for v in valores if v]
    total = len(validos)
    return [{"rotulo": k, "n": n, "pct": pct(n, total)} for k, n in Counter(validos).most_common()]


def leitura_publico(ed):
    pessoas = q(
        """
        SELECT c.*, SUM(p.quantidade) AS ingressos FROM contatos c
        JOIN pedidos p ON p.contato_id = c.id
        WHERE p.edicao_id = ? AND p.status = 'pago' GROUP BY c.id
        """,
        (ed["id"],),
    )
    pedidos = q("SELECT quantidade, criado_em FROM pedidos WHERE edicao_id = ? AND status = 'pago'", (ed["id"],))
    total = len(pessoas)
    saida = {
        "total": total,
        "faixas": _dist(p["faixa_etaria"] for p in pessoas),
        "cidades": _dist(p["cidade"] for p in pessoas),
        "bairros": _dist(p["bairro"] for p in pessoas)[:6],
        "origens": _dist(p["origem"] for p in pessoas),
        "generos": _dist(p["genero_favorito"] for p in pessoas),
        "bebidas": _dist(p["bebida"] for p in pessoas),
        "veteranos": pct(sum(1 for p in pessoas if p["veterano"]), total),
        "em_grupo": pct(sum(1 for p in pedidos if p["quantidade"] >= 2), len(pedidos)),
        "horas": [],
        "noite": [],
        "recomendacoes": [],
    }
    if not total:
        return saida

    horas = Counter(int(p["criado_em"][11:13]) for p in pedidos)
    saida["horas"] = [{"hora": h, "n": horas.get(h, 0)} for h in range(24)]
    pico = max(horas, key=horas.get)

    # divisao da noite (6 horas em blocos de 30 min) proporcional ao que a casa pede, na ordem de intensidade
    generos = {g["rotulo"]: g["n"] for g in saida["generos"]}
    soma = sum(generos.values()) or 1
    cotas = {g: generos.get(g, 0) * 12 / soma for g in GENEROS}
    blocos = {g: int(c) for g, c in cotas.items()}
    for g in sorted(GENEROS, key=lambda g: cotas[g] - blocos[g], reverse=True)[: 12 - sum(blocos.values())]:
        blocos[g] += 1
    saida["noite"] = [{"genero": g, "horas": blocos[g] / 2} for g in GENEROS if blocos[g]]

    rec = saida["recomendacoes"]
    gs = saida["generos"]
    if len(gs) >= 2:
        menor = gs[-1]
        rec.append({
            "frente": "Música",
            "titulo": f"A casa pede {gs[0]['rotulo']} e {gs[1]['rotulo']}",
            "texto": (
                f"{gs[0]['pct']}% e {gs[1]['pct']}% das respostas. Monte o pico da noite nesses dois e trate "
                f"{menor['rotulo']} ({menor['pct']}%) como respiro, não como bloco inteiro."
            ),
        })
    if saida["bebidas"]:
        b = saida["bebidas"][0]
        rec.append({
            "frente": "Bar",
            "titulo": f"Drink autoral com base de {b['rotulo'].lower()}",
            "texto": (
                f"{b['pct']}% apontam {b['rotulo'].lower()} como bebida da noite. Na 1.0 o bar vendeu abaixo do esperado: "
                "um autoral em cima do que a casa já pede reduz esse risco."
            ),
        })
    if saida["em_grupo"] >= 35:
        rec.append({
            "frente": "Cenografia",
            "titulo": "O público chega em dupla ou em grupo",
            "texto": (
                f"{saida['em_grupo']}% dos pedidos têm dois ingressos ou mais. A betoneira espelhada funciona como ponto "
                "de encontro: deixe espaço em volta para o grupo inteiro caber no reflexo."
            ),
        })
    if saida["veteranos"] >= 20:
        rec.append({
            "frente": "Ritual",
            "titulo": f"{saida['veteranos']}% já estiveram na 1.0",
            "texto": "Um sinal só para eles (pulseira de outra cor, um adesivo que só quem voltou recebe) reforça o pertencimento sem dizer uma palavra.",
        })
    fora = 100 - next((c["pct"] for c in saida["cidades"] if c["rotulo"] == "Teresópolis"), 0)
    if fora >= 10:
        rec.append({
            "frente": "Operação",
            "titulo": f"{fora}% vêm de fora de Teresópolis",
            "texto": "Inclua no lembrete da véspera como chegar e onde parar. Para esse público, a festa começa na estrada.",
        })
    rec.append({
        "frente": "Comunicação",
        "titulo": f"A janela de compra abre às {pico}h",
        "texto": f"É a hora com mais pedidos. Revelações e viradas publicadas entre {(pico - 1) % 24}h e {pico}h pegam o público já de olho.",
    })
    if saida["faixas"]:
        f = saida["faixas"][0]
        rec.append({
            "frente": "Público",
            "titulo": f"Faixa dominante: {f['rotulo']} anos",
            "texto": f"{f['pct']}% dos compradores. Use essa faixa como régua para linguagem, horário de abertura da casa e cardápio.",
        })
    return saida


# ---------------------------------------------------------------- pontos cegos

def _dias_desde(texto):
    if not texto:
        return None
    return (hoje() - date.fromisoformat(texto[:10])).days


def pontos_cegos(ed, m, lotes, promoters):
    riscos = []
    festa = date.fromisoformat(ed["data"])
    eid = ed["id"]
    em_venda = (m["dia_de_venda"] or 0) > 0 and m["dias_restantes"] > 0
    h = hoje()

    def tarefa(titulo, responsavel, dias, prioridade="alta"):
        return {"rotulo": "Criar tarefa", "metodo": "POST", "url": "/api/tarefas",
                "corpo": {"titulo": titulo, "responsavel": responsavel, "prazo": (h + timedelta(days=dias)).isoformat(),
                          "prioridade": prioridade, "origem": "automatica"}}

    # 1. ritmo de venda
    if em_venda and m["restante"] > 0 and m["ritmo_necessario"] > 0 and m["vendidos"] > 0:
        razao = m["ritmo_3d"] / m["ritmo_necessario"]
        if razao < 0.8:
            quando = datetime.combine(h + timedelta(days=1), datetime.min.time()).replace(hour=19, minute=30)
            riscos.append({
                "id": "ritmo",
                "nivel": "alto" if razao < 0.55 else "medio",
                "titulo": "A venda perdeu ritmo",
                "leitura": (
                    f"Nos últimos 3 dias saíram {fmt_num(m['ritmo_3d'])} ingressos por dia. Para lotar, é preciso {fmt_num(m['ritmo_necessario'])}. "
                    f"A projeção fecha em {m['projecao']['central']} de {m['capacidade']} (entre {m['projecao']['baixa']} e {m['projecao']['alta']})."
                ),
                "mitigacao": (
                    "Solte uma revelação do tema: um pedaço do espelho, sem explicar. Mistério dá assunto para os promoters "
                    "e traz de volta quem viu a abertura e não comprou."
                ),
                "acoes": [{
                    "rotulo": "Agendar revelação", "metodo": "POST", "url": "/api/automacoes",
                    "corpo": {"tipo": "post", "canal": "Stories do Instagram", "titulo": "Revelação: um pedaço do espelho",
                              "conteudo": "O que acontece quando o olhar não encontra fim?", "publico": "Seguidores",
                              "gatilho": "data", "agendado_para": quando.isoformat(), "status": "agendada"},
                }],
            })

    # 2. promoters parados
    parados = [p for p in promoters if p["ativo"] and p["situacao"] == "parado"]
    if parados and em_venda:
        nomes = ", ".join(p["nome"] for p in parados)
        riscos.append({
            "id": "promoters-parados",
            "nivel": "medio" if len(parados) < max(len(promoters) / 2, 1) else "alto",
            "titulo": f"{plural(len(parados), 'promoter', 'promoters')} sem movimento",
            "leitura": f"{nomes}: nenhuma venda nos últimos 5 dias. " + " ".join(
                f"{p['nome']} " + ("nunca vendeu." if p["dias_sem_venda"] is None else f"está há {p['dias_sem_venda']} dias sem vender.")
                for p in parados
            ),
            "mitigacao": (
                "Fale com cada um antes de trocar: mande a arte da próxima revelação em primeira mão e combine um story "
                "por dia até a virada. Se seguir parado, repasse o código para a lista de espera."
            ),
            "acoes": [tarefa(f"Falar com promoters parados: {nomes}", "Mateus", 1)],
        })

    # 3. concentracao em um promoter so
    vendas_prom = sum(p["vendas"] for p in promoters)
    if vendas_prom >= 10:
        topo = max(promoters, key=lambda p: p["vendas"])
        if topo["vendas"] / vendas_prom > 0.5:
            riscos.append({
                "id": "concentracao",
                "nivel": "baixo",
                "titulo": f"{topo['nome']} carrega mais da metade das vendas por código",
                "leitura": f"{topo['vendas']} de {vendas_prom} ingressos vendidos por promoter vieram de um código só.",
                "mitigacao": "Reconheça quem puxa e descubra o que essa pessoa faz diferente. Vire isso em roteiro para os outros.",
            })

    # 4. pagamentos pendentes ha mais de 24h
    limite = (agora() - timedelta(hours=24)).isoformat()
    pend = q1(
        "SELECT COUNT(*) AS n, COALESCE(SUM(valor_total), 0) AS v, COALESCE(SUM(quantidade), 0) AS ing FROM pedidos "
        "WHERE edicao_id = ? AND status = 'pendente' AND criado_em < ?", (eid, limite))
    if pend["n"]:
        riscos.append({
            "id": "pendentes",
            "nivel": "medio",
            "titulo": f"{plural(pend['n'], 'pedido pendente', 'pedidos pendentes')} há mais de 24h",
            "leitura": f"{plural(pend['ing'], 'ingresso reservado e não pago', 'ingressos reservados e não pagos')}, {reais(pend['v'])} parados. Enquanto isso, o lote fica com estoque preso.",
            "mitigacao": "Um lembrete curto resolve a maioria. Sem resposta em 24h, estorne e devolva o ingresso ao lote.",
            "acoes": [{
                "rotulo": "Agendar lembrete", "metodo": "POST", "url": "/api/automacoes",
                "corpo": {"tipo": "mensagem", "canal": "WhatsApp", "titulo": "Lembrete de pagamento pendente",
                          "conteudo": "Seu acesso ainda está reservado, mas não por muito tempo. O pagamento fecha a entrada.",
                          "publico": "Pagamento pendente", "gatilho": "data",
                          "agendado_para": (agora() + timedelta(hours=1)).replace(minute=0, second=0).isoformat(), "status": "agendada"},
            }],
        })

    # 5. o que a 1.0 ensinou: banheiros e bar
    tarefas = [t["titulo"].lower() for t in q("SELECT titulo FROM tarefas WHERE edicao_id = ?", (eid,))]
    if not any(("banheiro" in t or "limpeza" in t) for t in tarefas):
        riscos.append({
            "id": "banheiros",
            "nivel": "medio",
            "titulo": "Ninguém escalado para os banheiros",
            "leitura": "Na 1.0 faltou alguém cuidando dos banheiros durante a festa. Nesta edição ainda não existe tarefa nem responsável para isso.",
            "mitigacao": "Contrate uma pessoa só para isso, com ronda a cada 30 minutos, e deixe o nome dela na escala da noite.",
            "acoes": [tarefa("Contratar limpeza dos banheiros para a noite (ronda a cada 30 min)", "Mateus", 5)],
        })
    autos = q("SELECT titulo, conteudo, agendado_para, status, gatilho FROM automacoes WHERE edicao_id = ?", (eid,))
    fala_de_bar = any(("bar" in t.split() or "drink" in t or "consuma" in t) for t in tarefas)
    if not fala_de_bar:
        riscos.append({
            "id": "bar",
            "nivel": "baixo",
            "titulo": "O bar segue sem plano",
            "leitura": "O bar da 1.0 vendeu abaixo do esperado e, até aqui, nada no planejamento trata disso.",
            "mitigacao": "Defina o drink autoral cedo e apresente antes da noite. Quem chega já sabendo o que pedir compra na primeira hora.",
            "acoes": [tarefa("Definir drink autoral e plano do bar (cardápio, equipe, ponto de venda)", "Mateus", 7, "media")],
        })

    # 6. buracos na comunicacao: vespera e dia seguinte
    def tem_no_dia(d):
        return any(a["agendado_para"] and a["agendado_para"][:10] == d.isoformat() and a["status"] != "pausada" for a in autos)

    vespera, seguinte = festa - timedelta(days=1), festa + timedelta(days=1)
    if h <= vespera and not tem_no_dia(vespera):
        riscos.append({
            "id": "vespera",
            "nivel": "baixo",
            "titulo": "Sem lembrete na véspera",
            "leitura": f"Não há nada agendado para {vespera.strftime('%d/%m')}. O lembrete da véspera é o que mais reduz atraso e ausência.",
            "mitigacao": "Uma mensagem curta para quem comprou, com horário e o ingresso à mão.",
            "acoes": [{
                "rotulo": "Agendar lembrete", "metodo": "POST", "url": "/api/automacoes",
                "corpo": {"tipo": "mensagem", "canal": "WhatsApp", "titulo": "Véspera: amanhã os olhos se abrem",
                          "conteudo": "Amanhã os olhos se abrem. Seu acesso já está com você.", "publico": "Compradores",
                          "gatilho": "data", "agendado_para": f"{vespera.isoformat()}T18:00:00", "status": "agendada"},
            }],
        })
    if h <= seguinte and not tem_no_dia(seguinte):
        riscos.append({
            "id": "agradecimento",
            "nivel": "baixo",
            "titulo": "Sem agradecimento no dia seguinte",
            "leitura": f"Nada agendado para {seguinte.strftime('%d/%m')}. O pós-festa é quando a lembrança ainda está quente e o comentário vem fácil.",
            "mitigacao": "Agradeça e peça uma frase sobre a noite. Essas respostas alimentam a leitura pós-evento.",
            "acoes": [{
                "rotulo": "Agendar agradecimento", "metodo": "POST", "url": "/api/automacoes",
                "corpo": {"tipo": "mensagem", "canal": "WhatsApp", "titulo": "Dia seguinte: o que foi visto",
                          "conteudo": "O que foi visto não se desfaz. Obrigado por ampliar a visão com a gente. Em uma frase: o que ficou da noite?",
                          "publico": "Compradores", "gatilho": "data", "agendado_para": f"{seguinte.isoformat()}T14:00:00", "status": "agendada"},
            }],
        })

    # 7. tarefas vencidas
    vencidas = q("SELECT titulo, responsavel, prazo FROM tarefas WHERE edicao_id = ? AND status != 'feito' AND prazo < ?", (eid, h.isoformat()))
    if vencidas:
        riscos.append({
            "id": "tarefas-vencidas",
            "nivel": "medio",
            "titulo": f"{plural(len(vencidas), 'tarefa', 'tarefas')} fora do prazo",
            "leitura": "; ".join(f"{t['titulo']} ({t['responsavel'] or 'sem dono'})" for t in vencidas[:4]) + ".",
            "mitigacao": "Reagende com data nova ou passe para outra pessoa. Tarefa vencida sem dono é a que estoura na semana da festa.",
        })

    # acao ja tomada: o botao da lugar a um registro, para nao parecer que nada aconteceu
    na_central = {a["titulo"] for a in autos if a["status"] in ("agendada", "ativa", "enviada")}
    for r in riscos:
        for a in r.get("acoes") or []:
            pedido = a.get("corpo") or {}
            if a["url"] == "/api/tarefas" and pedido.get("titulo", "").lower() in tarefas:
                r["feito"], r["acoes"] = "Tarefa criada. Ela está em Automação, na lista da equipe.", []
                break
            if a["url"] == "/api/automacoes" and pedido.get("titulo") in na_central:
                r["feito"], r["acoes"] = "Já está na fila da central de automação.", []
                break

    ordem = {"alto": 0, "medio": 1, "baixo": 2}
    riscos.sort(key=lambda r: ordem[r["nivel"]])
    return riscos


def todas(ed, promoters):
    lotes = estoque(ed["id"])
    m = metricas(ed, lotes)
    return {
        "metricas": m,
        "precos": leitura_precos(ed, m, lotes),
        "publico": leitura_publico(ed),
        "riscos": pontos_cegos(ed, m, lotes, promoters),
        "premissas": [
            f"Ritmo base: 60% da média dos últimos 3 dias + 40% da média dos últimos 7.",
            f"Projeção: ritmo base até a festa, com os últimos {DIAS_DE_PICO} dias vendendo {PICO_FINAL}× (efeito de última semana).",
            "Faixa da projeção: piso sem pico final, teto com pico de 2,4×.",
            f"Custo de referência: tudo o que a 1.0 gastou, {reais(m['referencia']['custo'])} para {m['referencia']['publico']} pessoas.",
        ],
    }
