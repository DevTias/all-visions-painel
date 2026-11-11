"""ALL VISIONS · painel da festa.

Flask + SQLite. Rode com:  python app.py   (ou de dois cliques em iniciar.bat)
Abre em http://127.0.0.1:5000
"""
import json
import random
from datetime import date, timedelta

from flask import Flask, jsonify, render_template, request

import laboratorio as lab
import visoes
from banco import (ESQUEMA, agora, arroba, carimbo, cfg, conectar, edicao_atual, estoque, fechar, hoje,
                   novo_codigo_ingresso, novo_codigo_promoter, q, q1, run, set_cfg)
from ensaio import INICIAIS, PRIMEIROS, semear

app = Flask(__name__)
app.json.ensure_ascii = False
app.json.sort_keys = False
app.teardown_appcontext(fechar)

METODOS = ("pix", "cartao", "dinheiro", "cortesia")
SEGMENTOS = ["Compradores", "Pagamento pendente", "Veteranos da 1.0", "Estreantes", "Vieram por promoter",
             "Sem check-in", "Todos os contatos"]
PUBLICOS_ABERTOS = ["Seguidores", "Quem responde ao post", "Promoters"]


def iniciar_banco():
    con = conectar()
    con.executescript(ESQUEMA)
    if not con.execute("SELECT 1 FROM config LIMIT 1").fetchone():
        semear(con, "ensaio")
    con.close()


def erro(mensagem, status=400):
    return jsonify({"erro": mensagem}), status


def corpo():
    return request.get_json(silent=True) or {}


def inteiro(valor, padrao=None):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return padrao


def numero(valor, padrao=None):
    try:
        return float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return padrao


# ================================================================ regras de dominio

def promoters_metricas(edicao_id):
    faixas = q("SELECT * FROM comissao_faixas WHERE edicao_id = ? ORDER BY min_vendas", (edicao_id,))
    lista = q(
        """
        SELECT pr.*,
            COALESCE((SELECT SUM(quantidade) FROM pedidos WHERE promoter_id = pr.id AND status = 'pago'), 0) AS vendas,
            COALESCE((SELECT SUM(valor_total) FROM pedidos WHERE promoter_id = pr.id AND status = 'pago'), 0) AS receita,
            (SELECT MAX(criado_em) FROM pedidos WHERE promoter_id = pr.id AND status = 'pago') AS ultima_venda,
            (SELECT COUNT(*) FROM promoter_stories WHERE promoter_id = pr.id) AS stories,
            (SELECT MAX(data) FROM promoter_stories WHERE promoter_id = pr.id) AS ultimo_story
        FROM promoters pr WHERE pr.edicao_id = ?
        """,
        (edicao_id,),
    )
    h = hoje()
    for p in lista:
        faixa = None
        for f in faixas:
            if p["vendas"] >= f["min_vendas"]:
                faixa = f
        proxima = next((f for f in faixas if f["min_vendas"] > p["vendas"]), None)
        p["faixa"] = faixa
        p["proxima_faixa"] = proxima
        p["faltam"] = proxima["min_vendas"] - p["vendas"] if proxima else 0
        p["comissao"] = round(p["receita"] * faixa["percentual"] / 100 + (faixa["bonus"] or 0), 2) if faixa and p["vendas"] else 0
        p["dias_sem_venda"] = (h - date.fromisoformat(p["ultima_venda"][:10])).days if p["ultima_venda"] else None
        p["dias_sem_story"] = (h - date.fromisoformat(p["ultimo_story"][:10])).days if p["ultimo_story"] else None
        if not p["ativo"]:
            p["situacao"] = "desligado"
        elif p["dias_sem_venda"] is not None and p["dias_sem_venda"] <= 4:
            p["situacao"] = "em movimento"
        elif p["dias_sem_venda"] is None and (h - date.fromisoformat(p["entrou_em"][:10])).days < 3:
            p["situacao"] = "recém-chegado"
        else:
            p["situacao"] = "parado"
    lista.sort(key=lambda p: (-p["vendas"], p["nome"]))
    for i, p in enumerate(lista):
        p["posicao"] = i + 1
    return lista


def tarefa_auto(ed, titulo, responsavel, dias, prioridade="media"):
    if q1("SELECT 1 FROM tarefas WHERE edicao_id = ? AND titulo = ?", (ed["id"], titulo)):
        return
    run(
        "INSERT INTO tarefas (edicao_id, titulo, responsavel, prazo, status, origem, prioridade) VALUES (?, ?, ?, ?, 'a_fazer', 'automatica', ?)",
        (ed["id"], titulo, responsavel, (hoje() + timedelta(days=dias)).isoformat(), prioridade),
    )


def regras_automaticas(ed):
    """Escada de lotes: esgotou, abre o proximo. E delega as tarefas de virada."""
    lotes = estoque(ed["id"])
    for i, l in enumerate(lotes):
        if l["status"] != "ativo" or not l["quantidade"]:
            continue
        proximo = next((x for x in lotes[i + 1:] if x["status"] == "aguardando"), None)
        ocupado = (l["vendidos"] + l["reservados"]) / l["quantidade"]
        if l["disponivel"] <= 0:
            run("UPDATE lotes SET status = 'esgotado' WHERE id = ?", (l["id"],))
            if proximo:
                run("UPDATE lotes SET status = 'ativo' WHERE id = ?", (proximo["id"],))
                proximo["status"] = "ativo"
                tarefa_auto(ed, f"Anunciar virada: {proximo['nome']} aberto", "Mateus", 0, "alta")
        elif ocupado >= 0.8 and proximo:
            tarefa_auto(ed, f"Preparar virada para {proximo['nome']} (arte e texto)", "Mateus", 1)


def emitir_ingressos(pedido_id, titular, quantidade):
    for n in range(quantidade):
        nome = titular if n == 0 else f"Convidado de {titular}"
        run("INSERT INTO ingressos (pedido_id, codigo, titular, status) VALUES (?, ?, ?, 'valido')",
            (pedido_id, novo_codigo_ingresso(), nome))


def achar_ou_criar_contato(d):
    nome = (d.get("nome") or "").strip()
    insta = arroba(d.get("instagram"))
    achado = q1("SELECT id FROM contatos WHERE instagram = ? AND instagram != ''", (insta,)) if insta else None
    if not achado and not insta:
        achado = q1("SELECT id FROM contatos WHERE nome = ? AND (instagram IS NULL OR instagram = '')", (nome,))
    if achado:
        for campo in ("genero_favorito", "bebida", "faixa_etaria", "cidade", "telefone", "email"):
            if d.get(campo):
                run(f"UPDATE contatos SET {campo} = ? WHERE id = ?", (str(d[campo]).strip(), achado["id"]))
        return achado["id"]
    return run(
        "INSERT INTO contatos (nome, instagram, telefone, email, cidade, bairro, faixa_etaria, genero_favorito, bebida, origem, veterano, criado_em) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (nome, insta, d.get("telefone") or "", d.get("email") or "", d.get("cidade") or "", d.get("bairro") or "",
         d.get("faixa_etaria") or "", d.get("genero_favorito") or "", d.get("bebida") or "",
         d.get("origem") or "", 1 if d.get("veterano") else 0, carimbo()),
    )


def pedido_completo(pedido_id):
    p = q1(
        """
        SELECT p.*, c.nome AS comprador, c.instagram, l.nome AS lote, pr.nome AS promoter, pr.codigo AS codigo_promoter
        FROM pedidos p LEFT JOIN contatos c ON c.id = p.contato_id JOIN lotes l ON l.id = p.lote_id
        LEFT JOIN promoters pr ON pr.id = p.promoter_id WHERE p.id = ?
        """,
        (pedido_id,),
    )
    if p:
        p["ingressos"] = q("SELECT codigo, titular, status, checkin_em FROM ingressos WHERE pedido_id = ? ORDER BY id", (pedido_id,))
    return p


def criar_pedido(ed, d, publico=False):
    """Registra uma venda. Devolve (pedido, None) ou (None, mensagem de erro)."""
    lote = q1("SELECT * FROM lotes WHERE id = ? AND edicao_id = ?", (inteiro(d.get("lote_id")), ed["id"]))
    if not lote:
        return None, "Lote não encontrado."
    if publico and lote["status"] != "ativo":
        return None, "Este lote não está aberto."
    if lote["status"] in ("encerrado", "esgotado"):
        return None, f"O {lote['nome']} está {lote['status']}."
    nome = (d.get("nome") or "").strip()
    if not nome:
        return None, "Informe o nome de quem compra."
    qtd = inteiro(d.get("quantidade"), 1)
    if qtd < 1 or qtd > (4 if publico else 10):
        return None, f"Quantidade entre 1 e {4 if publico else 10}."
    atual = next(l for l in estoque(ed["id"]) if l["id"] == lote["id"])
    if atual["disponivel"] is not None and qtd > atual["disponivel"]:
        return None, (f"Só resta 1 ingresso no {lote['nome']}." if atual['disponivel'] == 1 else f"Só restam {atual['disponivel']} ingressos no {lote['nome']}.")

    promoter_id, origem = None, d.get("origem") or ""
    codigo = (d.get("codigo") or d.get("ref") or "").strip().upper()
    if codigo:
        promoter = q1("SELECT * FROM promoters WHERE codigo = ? AND edicao_id = ? AND ativo = 1", (codigo, ed["id"]))
        if promoter:
            promoter_id, origem = promoter["id"], "Promoter"
        elif not publico:
            return None, "Código de promoter não reconhecido."

    metodo = d.get("metodo") if d.get("metodo") in METODOS else "pix"
    status = "pendente" if d.get("status") == "pendente" else "pago"
    unitario = 0 if metodo == "cortesia" else lote["preco"]
    contato_id = achar_ou_criar_contato({**d, "nome": nome, "origem": origem})
    pedido_id = run(
        "INSERT INTO pedidos (edicao_id, lote_id, contato_id, promoter_id, quantidade, valor_unit, valor_total, metodo, status, criado_em) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (ed["id"], lote["id"], contato_id, promoter_id, qtd, unitario, unitario * qtd, metodo, status, carimbo()),
    )
    if status == "pago":
        emitir_ingressos(pedido_id, nome, qtd)
    regras_automaticas(ed)
    return pedido_completo(pedido_id), None


def condicao_segmento(segmento):
    """Devolve (trecho SQL sobre contatos c, parametros) para o segmento. Usa :e como id da edicao."""
    comprou = "c.id IN (SELECT contato_id FROM pedidos WHERE edicao_id = :e AND status = 'pago')"
    return {
        "Compradores": comprou,
        "Pagamento pendente": "c.id IN (SELECT contato_id FROM pedidos WHERE edicao_id = :e AND status = 'pendente')",
        "Veteranos da 1.0": "c.veterano = 1",
        "Estreantes": f"c.veterano = 0 AND {comprou}",
        "Vieram por promoter": "c.id IN (SELECT contato_id FROM pedidos WHERE edicao_id = :e AND status = 'pago' AND promoter_id IS NOT NULL)",
        "Sem check-in": f"{comprou} AND c.id NOT IN (SELECT p.contato_id FROM pedidos p JOIN ingressos i ON i.pedido_id = p.id "
                        "WHERE p.edicao_id = :e AND i.status = 'usado')",
        "Todos os contatos": "1 = 1",
    }.get(segmento)


def tamanho_publico(ed, publico):
    cond = condicao_segmento(publico)
    if cond:
        return q1(f"SELECT COUNT(*) AS n FROM contatos c WHERE {cond}", {"e": ed["id"]})["n"]
    if publico == "Promoters":
        return q1("SELECT COUNT(*) AS n FROM promoters WHERE edicao_id = ? AND ativo = 1", (ed["id"],))["n"]
    return None


# ================================================================ paginas

@app.get("/")
def pagina_painel():
    return render_template("painel.html")


@app.get("/convite")
def pagina_convite():
    return render_template("publico.html", visao="convite", chave=request.args.get("ref", ""))


@app.get("/ingresso/<codigo>")
def pagina_ingresso(codigo):
    return render_template("publico.html", visao="ingresso", chave=codigo)


@app.get("/p/<codigo>")
def pagina_promoter(codigo):
    return render_template("publico.html", visao="promoter", chave=codigo)


@app.get("/pista")
def pagina_pista():
    return render_template("publico.html", visao="pista", chave="")


# ================================================================ painel e configuracao

@app.get("/api/painel")
def api_painel():
    ed = edicao_atual()
    lotes = estoque(ed["id"])
    m = visoes.metricas(ed, lotes)
    proms = promoters_metricas(ed["id"])
    riscos = visoes.pontos_cegos(ed, m, lotes, proms)
    ultimas = q(
        """
        SELECT p.id, p.quantidade, p.valor_total, p.status, p.criado_em, c.nome AS comprador, l.nome AS lote, pr.nome AS promoter
        FROM pedidos p LEFT JOIN contatos c ON c.id = p.contato_id JOIN lotes l ON l.id = p.lote_id
        LEFT JOIN promoters pr ON pr.id = p.promoter_id
        WHERE p.edicao_id = ? ORDER BY p.criado_em DESC, p.id DESC LIMIT 7
        """,
        (ed["id"],),
    )
    proximas = q(
        "SELECT id, tipo, canal, titulo, agendado_para FROM automacoes WHERE edicao_id = ? AND status = 'agendada' AND gatilho = 'data' "
        "ORDER BY agendado_para LIMIT 4", (ed["id"],))
    abertas = q(
        "SELECT id, titulo, responsavel, prazo, prioridade FROM tarefas WHERE edicao_id = ? AND status != 'feito' ORDER BY prazo LIMIT 4",
        (ed["id"],))
    entradas = q1(
        "SELECT COUNT(*) AS n FROM ingressos i JOIN pedidos p ON p.id = i.pedido_id WHERE p.edicao_id = ? AND i.status = 'usado'",
        (ed["id"],))["n"]
    return jsonify({
        "edicao": ed, "modo": cfg("modo"), "agora": carimbo(), "metricas": m, "lotes": lotes, "ultimas": ultimas,
        "proximas": proximas, "tarefas": abertas, "entradas": entradas,
        "riscos": [{"id": r["id"], "nivel": r["nivel"], "titulo": r["titulo"], "leitura": r["leitura"]} for r in riscos],
        "promoters": [{"nome": p["nome"], "vendas": p["vendas"], "situacao": p["situacao"]} for p in proms[:4]],
    })


@app.get("/api/config")
def api_config():
    ed = edicao_atual()
    historico = q("SELECT * FROM edicoes WHERE status = 'encerrada' ORDER BY data DESC")
    for h in historico:
        h["custos"] = q("SELECT categoria, valor FROM custos WHERE edicao_id = ? ORDER BY valor DESC", (h["id"],))
        h["lotes"] = q("SELECT nome, descricao, preco FROM lotes WHERE edicao_id = ? ORDER BY ordem", (h["id"],))
    return jsonify({
        "modo": cfg("modo"), "agora": carimbo(), "edicao": ed, "historico": historico,
        "ingresso_design": json.loads(cfg("ingresso_design") or "{}"),
        "equipe": q("SELECT * FROM equipe ORDER BY id"),
        "segmentos": SEGMENTOS, "publicos": PUBLICOS_ABERTOS + SEGMENTOS, "generos": lab.GENEROS,
        "objetivos": lab.OBJETIVOS, "base_url": request.host_url.rstrip("/"),
    })


@app.post("/api/config/modo")
def api_modo():
    modo = corpo().get("modo")
    if modo not in ("ensaio", "real"):
        return erro("Modo deve ser 'ensaio' ou 'real'.")
    fechar()
    con = conectar()
    semear(con, modo)
    con.close()
    return jsonify({"modo": modo})


@app.put("/api/config/ingresso")
def api_design_ingresso():
    d = corpo()
    atual = json.loads(cfg("ingresso_design") or "{}")
    for chave in ("frase", "rodape", "clima"):
        if chave in d:
            atual[chave] = str(d[chave])[:120]
    for chave in ("mostrar_nome", "mostrar_lote", "mostrar_local"):
        if chave in d:
            atual[chave] = bool(d[chave])
    set_cfg("ingresso_design", json.dumps(atual, ensure_ascii=False))
    return jsonify(atual)


@app.patch("/api/edicao")
def api_edicao():
    ed, d = edicao_atual(), corpo()
    campos = {}
    for chave in ("nome", "tema", "local", "notas"):
        if chave in d:
            campos[chave] = str(d[chave]).strip()
    for chave in ("data", "abertura_vendas"):
        if d.get(chave):
            try:
                campos[chave] = date.fromisoformat(d[chave]).isoformat()
            except ValueError:
                return erro("Data inválida. Use AAAA-MM-DD.")
    if "capacidade" in d:
        cap = inteiro(d["capacidade"])
        if not cap or cap < 1:
            return erro("Capacidade inválida.")
        campos["capacidade"] = cap
    if campos:
        run(f"UPDATE edicoes SET {', '.join(f'{k} = ?' for k in campos)} WHERE id = ?", (*campos.values(), ed["id"]))
    return jsonify(edicao_atual())


# ================================================================ ingressos: lotes, pedidos, e-tickets, portaria

@app.get("/api/lotes")
def api_lotes():
    return jsonify(estoque(edicao_atual()["id"]))


@app.post("/api/lotes")
def api_lote_novo():
    ed, d = edicao_atual(), corpo()
    nome, preco, qtd = (d.get("nome") or "").strip(), numero(d.get("preco")), inteiro(d.get("quantidade"))
    if not nome or preco is None or preco < 0 or qtd is None or qtd < 1:
        return erro("Informe nome, preço e quantidade do lote.")
    ordem = q1("SELECT COALESCE(MAX(ordem), -1) + 1 AS o FROM lotes WHERE edicao_id = ?", (ed["id"],))["o"]
    status = d.get("status") if d.get("status") in ("aguardando", "ativo", "pausado") else "aguardando"
    lote_id = run(
        "INSERT INTO lotes (edicao_id, nome, descricao, preco, quantidade, ordem, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (ed["id"], nome, (d.get("descricao") or "").strip(), preco, qtd, ordem, status),
    )
    return jsonify(next(l for l in estoque(ed["id"]) if l["id"] == lote_id)), 201


@app.patch("/api/lotes/<int:lote_id>")
def api_lote_editar(lote_id):
    ed, d = edicao_atual(), corpo()
    lote = next((l for l in estoque(ed["id"]) if l["id"] == lote_id), None)
    if not lote:
        return erro("Lote não encontrado.", 404)
    campos = {}
    if "nome" in d and str(d["nome"]).strip():
        campos["nome"] = str(d["nome"]).strip()
    if "descricao" in d:
        campos["descricao"] = str(d["descricao"]).strip()
    if "preco" in d:
        preco = numero(d["preco"])
        if preco is None or preco < 0:
            return erro("Preço inválido.")
        campos["preco"] = preco
    if "quantidade" in d:
        qtd = inteiro(d["quantidade"])
        saidos = lote["vendidos"] + lote["reservados"]
        if qtd is None or qtd < max(saidos, 1):
            return erro(f"A quantidade não pode ficar abaixo do que já saiu ({saidos}).")
        campos["quantidade"] = qtd
    if "ordem" in d and inteiro(d["ordem"]) is not None:
        campos["ordem"] = inteiro(d["ordem"])
    if d.get("status") in ("aguardando", "ativo", "pausado", "esgotado"):
        campos["status"] = d["status"]
    if campos:
        run(f"UPDATE lotes SET {', '.join(f'{k} = ?' for k in campos)} WHERE id = ?", (*campos.values(), lote_id))
        if "quantidade" in campos and lote["status"] == "esgotado" and campos["quantidade"] > lote["vendidos"] + lote["reservados"] \
                and "status" not in campos:
            run("UPDATE lotes SET status = 'ativo' WHERE id = ?", (lote_id,))
    return jsonify(next(l for l in estoque(ed["id"]) if l["id"] == lote_id))


@app.delete("/api/lotes/<int:lote_id>")
def api_lote_apagar(lote_id):
    if q1("SELECT 1 FROM pedidos WHERE lote_id = ?", (lote_id,)):
        return erro("Este lote já tem pedidos. Pause em vez de apagar.", 409)
    run("DELETE FROM lotes WHERE id = ? AND edicao_id = ?", (lote_id, edicao_atual()["id"]))
    return jsonify({"ok": True})


@app.get("/api/pedidos")
def api_pedidos():
    ed = edicao_atual()
    filtros, args = ["p.edicao_id = ?"], [ed["id"]]
    if request.args.get("status") in ("pago", "pendente", "estornado"):
        filtros.append("p.status = ?")
        args.append(request.args["status"])
    busca = (request.args.get("busca") or "").strip()
    if busca:
        filtros.append("(c.nome LIKE ? OR c.instagram LIKE ? OR pr.codigo LIKE ? OR EXISTS "
                       "(SELECT 1 FROM ingressos i WHERE i.pedido_id = p.id AND i.codigo LIKE ?))")
        args += [f"%{busca}%"] * 4
    linhas = q(
        f"""
        SELECT p.id, p.quantidade, p.valor_total, p.metodo, p.status, p.criado_em, c.nome AS comprador, c.instagram,
               l.nome AS lote, pr.nome AS promoter, pr.codigo AS codigo_promoter,
               (SELECT GROUP_CONCAT(i.codigo, ' ') FROM ingressos i WHERE i.pedido_id = p.id) AS codigos
        FROM pedidos p LEFT JOIN contatos c ON c.id = p.contato_id JOIN lotes l ON l.id = p.lote_id
        LEFT JOIN promoters pr ON pr.id = p.promoter_id
        WHERE {' AND '.join(filtros)} ORDER BY p.criado_em DESC, p.id DESC LIMIT 400
        """,
        args,
    )
    return jsonify(linhas)


@app.post("/api/pedidos")
def api_pedido_novo():
    pedido, problema = criar_pedido(edicao_atual(), corpo())
    if problema:
        return erro(problema)
    return jsonify(pedido), 201


@app.patch("/api/pedidos/<int:pedido_id>")
def api_pedido_status(pedido_id):
    ed = edicao_atual()
    pedido = pedido_completo(pedido_id)
    if not pedido:
        return erro("Pedido não encontrado.", 404)
    novo = corpo().get("status")
    if novo == "pago" and pedido["status"] == "pendente":
        run("UPDATE pedidos SET status = 'pago' WHERE id = ?", (pedido_id,))
        emitir_ingressos(pedido_id, pedido["comprador"] or "Convidado", pedido["quantidade"])
    elif novo == "estornado" and pedido["status"] in ("pago", "pendente"):
        run("UPDATE pedidos SET status = 'estornado' WHERE id = ?", (pedido_id,))
        run("UPDATE ingressos SET status = 'cancelado' WHERE pedido_id = ? AND status = 'valido'", (pedido_id,))
    else:
        return erro("Mudança de status não permitida.")
    regras_automaticas(ed)
    return jsonify(pedido_completo(pedido_id))


def ingresso_detalhe(codigo):
    return q1(
        """
        SELECT i.codigo, i.titular, i.status, i.checkin_em, l.nome AS lote, p.criado_em AS comprado_em, p.metodo,
               e.nome AS edicao, e.tema, e.data, e.local
        FROM ingressos i JOIN pedidos p ON p.id = i.pedido_id JOIN lotes l ON l.id = p.lote_id
        JOIN edicoes e ON e.id = p.edicao_id WHERE i.codigo = ?
        """,
        ((codigo or "").strip().upper(),),
    )


@app.get("/api/ingressos/<codigo>")
def api_ingresso(codigo):
    ing = ingresso_detalhe(codigo)
    if not ing:
        return erro("Ingresso não encontrado.", 404)
    ing["design"] = json.loads(cfg("ingresso_design") or "{}")
    return jsonify(ing)


@app.get("/api/ingressos/<codigo>/qr")
def api_ingresso_qr(codigo):
    try:
        import segno
    except ImportError:
        return erro("QR indisponível: instale o pacote segno.", 501)
    matriz = segno.make(codigo.strip().upper(), error="m", micro=False).matrix
    return jsonify({"linhas": ["".join("1" if celula else "0" for celula in linha) for linha in matriz]})


@app.get("/api/checkin")
def api_checkin_resumo():
    ed = edicao_atual()
    r = q1(
        "SELECT COALESCE(SUM(i.status = 'usado'), 0) AS dentro, COALESCE(SUM(i.status IN ('usado', 'valido')), 0) AS emitidos "
        "FROM ingressos i JOIN pedidos p ON p.id = i.pedido_id WHERE p.edicao_id = ?", (ed["id"],))
    ultimos = q(
        "SELECT i.codigo, i.titular, i.checkin_em, l.nome AS lote FROM ingressos i JOIN pedidos p ON p.id = i.pedido_id "
        "JOIN lotes l ON l.id = p.lote_id WHERE p.edicao_id = ? AND i.status = 'usado' ORDER BY i.checkin_em DESC LIMIT 6", (ed["id"],))
    return jsonify({"dentro": r["dentro"], "emitidos": r["emitidos"], "ultimos": ultimos})


@app.post("/api/checkin")
def api_checkin():
    ing = ingresso_detalhe(corpo().get("codigo"))
    if not ing:
        return jsonify({"ok": False, "mensagem": "Código não reconhecido."}), 404
    if ing["status"] == "usado":
        return jsonify({"ok": False, "mensagem": f"Este ingresso já entrou às {ing['checkin_em'][11:16]}.", "ingresso": ing}), 409
    if ing["status"] == "cancelado":
        return jsonify({"ok": False, "mensagem": "Ingresso cancelado.", "ingresso": ing}), 409
    run("UPDATE ingressos SET status = 'usado', checkin_em = ? WHERE codigo = ?", (carimbo(), ing["codigo"]))
    return jsonify({"ok": True, "mensagem": f"{ing['titular']}, {ing['lote']}. Entrada liberada.", "ingresso": ingresso_detalhe(ing["codigo"])})


@app.post("/api/ensaio/venda")
def api_ensaio_venda():
    """So no modo ensaio: registra uma venda inventada para ver o painel reagir."""
    if cfg("modo") != "ensaio":
        return erro("Disponível apenas no modo ensaio.", 403)
    ed = edicao_atual()
    lote = next((l for l in estoque(ed["id"]) if l["status"] == "ativo" and l["disponivel"]), None)
    if not lote:
        return erro("Nenhum lote aberto com ingresso disponível.")
    proms = [p for p in promoters_metricas(ed["id"]) if p["ativo"]]
    usar_promoter = proms and random.random() < 0.45
    primeiro, inicial = random.choice(PRIMEIROS), random.choice(INICIAIS)
    pedido, problema = criar_pedido(ed, {
        "lote_id": lote["id"],
        "nome": f"{primeiro} {inicial}.",
        "instagram": f"{primeiro.lower()}.{inicial.lower()}{random.randint(100, 999)}",
        "quantidade": min(random.choice([1, 1, 1, 2, 2, 3]), lote["disponivel"]),
        "codigo": random.choice(proms)["codigo"] if usar_promoter else "",
        "origem": random.choice(["Story", "Story", "Feed", "Indicação"]),
        "cidade": random.choice(["Teresópolis"] * 8 + ["Petrópolis", "Rio de Janeiro"]),
        "faixa_etaria": random.choice(["18 a 21", "22 a 25", "22 a 25", "26 a 30", "31 ou mais"]),
        "genero_favorito": random.choice(lab.GENEROS),
        "bebida": random.choice(["Gin", "Gin", "Vodka", "Cerveja", "Whisky", "Tequila", "Sem álcool"]),
        "metodo": random.choice(["pix", "pix", "pix", "cartao"]),
    })
    if problema:
        return erro(problema)
    return jsonify(pedido), 201


# ================================================================ promoters

@app.get("/api/promoters")
def api_promoters():
    ed = edicao_atual()
    lista = promoters_metricas(ed["id"])
    return jsonify({
        "promoters": lista,
        "faixas": q("SELECT * FROM comissao_faixas WHERE edicao_id = ? ORDER BY min_vendas", (ed["id"],)),
        "totais": {
            "vendas": sum(p["vendas"] for p in lista),
            "receita": round(sum(p["receita"] for p in lista), 2),
            "comissao": round(sum(p["comissao"] for p in lista), 2),
            "parados": sum(1 for p in lista if p["situacao"] == "parado"),
        },
        "base_url": request.host_url.rstrip("/"),
    })


@app.post("/api/promoters")
def api_promoter_novo():
    ed, d = edicao_atual(), corpo()
    nome = (d.get("nome") or "").strip()
    if not nome:
        return erro("Informe o nome do promoter.")
    codigo = "".join(c for c in (d.get("codigo") or "").upper() if c.isalnum())[:12]
    if codigo and q1("SELECT 1 FROM promoters WHERE codigo = ?", (codigo,)):
        return erro("Este código já está em uso.")
    codigo = codigo or novo_codigo_promoter(nome)
    pid = run("INSERT INTO promoters (edicao_id, nome, instagram, codigo, ativo, entrou_em) VALUES (?, ?, ?, ?, 1, ?)",
              (ed["id"], nome, arroba(d.get("instagram")), codigo, hoje().isoformat()))
    return jsonify(next(p for p in promoters_metricas(ed["id"]) if p["id"] == pid)), 201


@app.patch("/api/promoters/<int:pid>")
def api_promoter_editar(pid):
    d = corpo()
    if not q1("SELECT 1 FROM promoters WHERE id = ?", (pid,)):
        return erro("Promoter não encontrado.", 404)
    if "nome" in d and str(d["nome"]).strip():
        run("UPDATE promoters SET nome = ? WHERE id = ?", (str(d["nome"]).strip(), pid))
    if "instagram" in d:
        run("UPDATE promoters SET instagram = ? WHERE id = ?", (arroba(d["instagram"]), pid))
    if "ativo" in d:
        run("UPDATE promoters SET ativo = ? WHERE id = ?", (1 if d["ativo"] else 0, pid))
    return jsonify(next(p for p in promoters_metricas(edicao_atual()["id"]) if p["id"] == pid))


@app.delete("/api/promoters/<int:pid>")
def api_promoter_apagar(pid):
    if q1("SELECT 1 FROM pedidos WHERE promoter_id = ?", (pid,)):
        return erro("Este promoter tem vendas registradas. Desligue em vez de apagar.", 409)
    run("DELETE FROM promoters WHERE id = ?", (pid,))
    return jsonify({"ok": True})


@app.post("/api/promoters/<int:pid>/stories")
def api_promoter_story(pid):
    if not q1("SELECT 1 FROM promoters WHERE id = ?", (pid,)):
        return erro("Promoter não encontrado.", 404)
    run("INSERT INTO promoter_stories (promoter_id, data) VALUES (?, ?)", (pid, hoje().isoformat()))
    return jsonify(next(p for p in promoters_metricas(edicao_atual()["id"]) if p["id"] == pid))


@app.put("/api/comissoes")
def api_comissoes():
    ed = edicao_atual()
    faixas = []
    for f in corpo().get("faixas") or []:
        minimo, perc = inteiro(f.get("min_vendas")), numero(f.get("percentual"))
        if minimo is None or minimo < 0 or perc is None or not 0 <= perc <= 100:
            return erro("Cada faixa precisa de vendas mínimas e de um percentual entre 0 e 100.")
        faixas.append((ed["id"], minimo, perc, numero(f.get("bonus"), 0) or 0, (f.get("mimo") or "").strip()))
    if not faixas:
        return erro("Mantenha pelo menos uma faixa.")
    if len({f[1] for f in faixas}) != len(faixas):
        return erro("Duas faixas começam no mesmo número de vendas.")
    run("DELETE FROM comissao_faixas WHERE edicao_id = ?", (ed["id"],))
    for f in sorted(faixas, key=lambda f: f[1]):
        run("INSERT INTO comissao_faixas (edicao_id, min_vendas, percentual, bonus, mimo) VALUES (?, ?, ?, ?, ?)", f)
    return jsonify(q("SELECT * FROM comissao_faixas WHERE edicao_id = ? ORDER BY min_vendas", (ed["id"],)))


@app.get("/api/promoters/codigo/<codigo>")
def api_promoter_visao(codigo):
    """Visao simplificada que o proprio promoter abre no celular."""
    ed = edicao_atual()
    lista = promoters_metricas(ed["id"])
    p = next((x for x in lista if x["codigo"] == codigo.strip().upper()), None)
    if not p:
        return erro("Código não encontrado.", 404)
    vendas = q(
        "SELECT substr(p.criado_em, 1, 10) AS dia, p.quantidade, l.nome AS lote FROM pedidos p JOIN lotes l ON l.id = p.lote_id "
        "WHERE p.promoter_id = ? AND p.status = 'pago' ORDER BY p.criado_em DESC LIMIT 6", (p["id"],))
    jogo = next((r for r in lab.ranking(lista)["ranking"] if r["id"] == p["id"]), None)
    return jsonify({
        "nome": p["nome"], "codigo": p["codigo"], "edicao": ed["nome"], "data": ed["data"],
        "vendas": p["vendas"], "receita": p["receita"], "comissao": p["comissao"], "stories": p["stories"],
        "posicao": p["posicao"], "de": len([x for x in lista if x["ativo"]]),
        "faixa": p["faixa"], "proxima_faixa": p["proxima_faixa"], "faltam": p["faltam"],
        "link": f"{request.host_url.rstrip('/')}/convite?ref={p['codigo']}",
        "ultimas": vendas, "jogo": jogo,
    })


# ================================================================ central de automacao

def _validar_automacao(d, parcial=False):
    campos = {}
    if "tipo" in d or not parcial:
        if d.get("tipo") not in ("mensagem", "post", "tarefa"):
            return None, "Tipo deve ser mensagem, post ou tarefa."
        campos["tipo"] = d["tipo"]
    if "titulo" in d or not parcial:
        if not (d.get("titulo") or "").strip():
            return None, "Dê um título à automação."
        campos["titulo"] = d["titulo"].strip()
    for chave in ("canal", "conteudo", "publico"):
        if chave in d:
            campos[chave] = (d[chave] or "").strip()
    if "gatilho" in d:
        campos["gatilho"] = d["gatilho"] if d["gatilho"] in ("data", "compra", "resposta") else "data"
    if "agendado_para" in d:
        campos["agendado_para"] = (d["agendado_para"] or "")[:19] or None
        if campos["agendado_para"] and len(campos["agendado_para"]) == 16:
            campos["agendado_para"] += ":00"
    if "status" in d:
        if d["status"] not in ("rascunho", "agendada", "ativa", "enviada", "pausada"):
            return None, "Status inválido."
        campos["status"] = d["status"]
    return campos, None


@app.get("/api/automacoes")
def api_automacoes():
    ed = edicao_atual()
    linhas = q(
        "SELECT * FROM automacoes WHERE edicao_id = ? ORDER BY (agendado_para IS NULL) DESC, agendado_para, id", (ed["id"],))
    for a in linhas:
        a["alcance_previsto"] = None if a["tipo"] == "tarefa" else tamanho_publico(ed, a["publico"])
        a["checagem"] = lab.checagem(a["conteudo"]) if a["tipo"] != "tarefa" and a["conteudo"] else None
    vencidas = sum(1 for a in linhas if a["status"] == "agendada" and a["gatilho"] == "data" and a["agendado_para"]
                   and a["agendado_para"] <= carimbo())
    return jsonify({"automacoes": linhas, "vencidas": vencidas, "agora": carimbo(), "festa": ed["data"]})


@app.post("/api/automacoes")
def api_automacao_nova():
    ed = edicao_atual()
    campos, problema = _validar_automacao(corpo())
    if problema:
        return erro(problema)
    campos.setdefault("gatilho", "data")
    if campos["gatilho"] == "data" and not campos.get("agendado_para"):
        return erro("Escolha data e hora do disparo.")
    campos.setdefault("status", "agendada" if campos["gatilho"] == "data" else "ativa")
    campos["edicao_id"] = ed["id"]
    aid = run(f"INSERT INTO automacoes ({', '.join(campos)}) VALUES ({', '.join('?' for _ in campos)})", tuple(campos.values()))
    return jsonify(q1("SELECT * FROM automacoes WHERE id = ?", (aid,))), 201


@app.patch("/api/automacoes/<int:aid>")
def api_automacao_editar(aid):
    if not q1("SELECT 1 FROM automacoes WHERE id = ?", (aid,)):
        return erro("Automação não encontrada.", 404)
    campos, problema = _validar_automacao(corpo(), parcial=True)
    if problema:
        return erro(problema)
    if campos:
        run(f"UPDATE automacoes SET {', '.join(f'{k} = ?' for k in campos)} WHERE id = ?", (*campos.values(), aid))
    return jsonify(q1("SELECT * FROM automacoes WHERE id = ?", (aid,)))


@app.delete("/api/automacoes/<int:aid>")
def api_automacao_apagar(aid):
    run("DELETE FROM automacoes WHERE id = ?", (aid,))
    return jsonify({"ok": True})


@app.post("/api/automacoes/executar")
def api_automacoes_executar():
    """Dispara o que venceu. O disparo e registrado, nao enviado: nenhum canal real esta ligado."""
    ed = edicao_atual()
    vencidas = q(
        "SELECT * FROM automacoes WHERE edicao_id = ? AND status = 'agendada' AND gatilho = 'data' AND agendado_para <= ? ORDER BY agendado_para",
        (ed["id"], carimbo()))
    feitas = []
    for a in vencidas:
        if a["tipo"] == "tarefa":
            tarefa_auto(ed, a["titulo"], a["publico"] or "Mateus", 1, "media")
            alcance = None
        else:
            alcance = tamanho_publico(ed, a["publico"])
        run("UPDATE automacoes SET status = 'enviada', enviado_em = ?, alcance = ? WHERE id = ?", (carimbo(), alcance, a["id"]))
        feitas.append({"id": a["id"], "titulo": a["titulo"], "tipo": a["tipo"], "alcance": alcance})
    regras_automaticas(ed)
    return jsonify({"disparadas": feitas})


@app.get("/api/contatos")
def api_contatos():
    ed = edicao_atual()
    cond = condicao_segmento(request.args.get("segmento") or "Todos os contatos") or "1 = 1"
    args = {"e": ed["id"]}
    busca = (request.args.get("busca") or "").strip()
    if busca:
        cond += " AND (c.nome LIKE :b OR c.instagram LIKE :b OR c.tags LIKE :b OR c.cidade LIKE :b)"
        args["b"] = f"%{busca}%"
    linhas = q(
        f"""
        SELECT c.*,
            COALESCE((SELECT SUM(quantidade) FROM pedidos WHERE contato_id = c.id AND edicao_id = :e AND status = 'pago'), 0) AS ingressos,
            COALESCE((SELECT SUM(valor_total) FROM pedidos WHERE contato_id = c.id AND edicao_id = :e AND status = 'pago'), 0) AS gasto,
            (SELECT MAX(criado_em) FROM pedidos WHERE contato_id = c.id) AS ultima_compra,
            (SELECT status FROM pedidos WHERE contato_id = c.id ORDER BY criado_em DESC LIMIT 1) AS ultimo_status
        FROM contatos c WHERE {cond} ORDER BY ultima_compra DESC, c.id DESC LIMIT 400
        """,
        args,
    )
    contagem = {s: q1(f"SELECT COUNT(*) AS n FROM contatos c WHERE {condicao_segmento(s)}", {"e": ed["id"]})["n"] for s in SEGMENTOS}
    return jsonify({"contatos": linhas, "segmentos": contagem})


@app.post("/api/contatos")
def api_contato_novo():
    d = corpo()
    if not (d.get("nome") or "").strip():
        return erro("Informe o nome.")
    cid = achar_ou_criar_contato(d)
    if d.get("tags") or d.get("notas"):
        run("UPDATE contatos SET tags = ?, notas = ? WHERE id = ?", (d.get("tags") or "", d.get("notas") or "", cid))
    return jsonify(q1("SELECT * FROM contatos WHERE id = ?", (cid,))), 201


@app.patch("/api/contatos/<int:cid>")
def api_contato_editar(cid):
    d = corpo()
    if not q1("SELECT 1 FROM contatos WHERE id = ?", (cid,)):
        return erro("Contato não encontrado.", 404)
    permitidos = ("nome", "instagram", "telefone", "email", "cidade", "bairro", "faixa_etaria", "genero_favorito",
                  "bebida", "tags", "notas")
    campos = {k: str(d[k]).strip() for k in permitidos if k in d}
    if "veterano" in d:
        campos["veterano"] = 1 if d["veterano"] else 0
    if campos:
        run(f"UPDATE contatos SET {', '.join(f'{k} = ?' for k in campos)} WHERE id = ?", (*campos.values(), cid))
    return jsonify(q1("SELECT * FROM contatos WHERE id = ?", (cid,)))


@app.get("/api/tarefas")
def api_tarefas():
    ed = edicao_atual()
    return jsonify({
        "tarefas": q("SELECT * FROM tarefas WHERE edicao_id = ? ORDER BY (status = 'feito'), prazo, id", (ed["id"],)),
        "equipe": q("SELECT * FROM equipe ORDER BY id"),
        "hoje": hoje().isoformat(),
    })


@app.post("/api/tarefas")
def api_tarefa_nova():
    ed, d = edicao_atual(), corpo()
    titulo = (d.get("titulo") or "").strip()
    if not titulo:
        return erro("Descreva a tarefa.")
    existente = q1("SELECT * FROM tarefas WHERE edicao_id = ? AND titulo = ?", (ed["id"], titulo))
    if existente:
        return jsonify(existente)
    tid = run(
        "INSERT INTO tarefas (edicao_id, titulo, responsavel, prazo, status, origem, prioridade) VALUES (?, ?, ?, ?, 'a_fazer', ?, ?)",
        (ed["id"], titulo, (d.get("responsavel") or "").strip(), d.get("prazo") or None,
         "automatica" if d.get("origem") == "automatica" else "manual",
         d.get("prioridade") if d.get("prioridade") in ("alta", "media", "baixa") else "media"),
    )
    return jsonify(q1("SELECT * FROM tarefas WHERE id = ?", (tid,))), 201


@app.patch("/api/tarefas/<int:tid>")
def api_tarefa_editar(tid):
    d = corpo()
    if not q1("SELECT 1 FROM tarefas WHERE id = ?", (tid,)):
        return erro("Tarefa não encontrada.", 404)
    campos = {k: str(d[k]).strip() for k in ("titulo", "responsavel", "prazo") if k in d}
    if d.get("status") in ("a_fazer", "andamento", "feito"):
        campos["status"] = d["status"]
    if d.get("prioridade") in ("alta", "media", "baixa"):
        campos["prioridade"] = d["prioridade"]
    if campos:
        run(f"UPDATE tarefas SET {', '.join(f'{k} = ?' for k in campos)} WHERE id = ?", (*campos.values(), tid))
    return jsonify(q1("SELECT * FROM tarefas WHERE id = ?", (tid,)))


@app.delete("/api/tarefas/<int:tid>")
def api_tarefa_apagar(tid):
    run("DELETE FROM tarefas WHERE id = ?", (tid,))
    return jsonify({"ok": True})


# ================================================================ visoes (leituras)

@app.get("/api/visoes")
def api_visoes():
    ed = edicao_atual()
    return jsonify(visoes.todas(ed, promoters_metricas(ed["id"])))


# ================================================================ laboratorio

@app.get("/api/lab/ranking")
def api_lab_ranking():
    return jsonify(lab.ranking(promoters_metricas(edicao_atual()["id"])))


@app.route("/api/lab/votacao", methods=["GET", "POST", "DELETE"])
def api_lab_votacao():
    ed = edicao_atual()
    if request.method == "POST":
        opcao = corpo().get("opcao")
        if opcao not in lab.GENEROS:
            return erro("Opção fora da curadoria da casa.")
        run("INSERT INTO votos (edicao_id, opcao, criado_em) VALUES (?, ?, ?)", (ed["id"], opcao, carimbo()))
    elif request.method == "DELETE":
        run("DELETE FROM votos WHERE edicao_id = ?", (ed["id"],))
    return jsonify(lab.votacao(ed["id"]))


@app.post("/api/lab/texto")
def api_lab_texto():
    return jsonify(lab.textos(edicao_atual(), corpo().get("objetivo")))


@app.post("/api/lab/checagem")
def api_lab_checagem():
    return jsonify(lab.checagem(corpo().get("texto") or ""))


@app.get("/api/lab/roteiro")
def api_lab_roteiro():
    ed = edicao_atual()
    lotacao = max(0, min(100, inteiro(request.args.get("lotacao"), 50)))
    energia = max(1, min(5, inteiro(request.args.get("energia"), 3)))
    hora = request.args.get("hora") or "00:00"
    if len(hora) != 5 or hora[2] != ":" or not hora.replace(":", "").isdigit():
        hora = "00:00"
    lider = lab.votacao(ed["id"])["lider"] if request.args.get("votos") == "1" else None
    return jsonify(lab.roteiro(lotacao, energia, hora, lider))


@app.route("/api/lab/sentimento", methods=["GET", "POST"])
def api_lab_sentimento():
    encerrada = q1("SELECT id, nome FROM edicoes WHERE status = 'encerrada' ORDER BY data DESC LIMIT 1") or edicao_atual()
    if request.method == "POST":
        texto = (corpo().get("texto") or "").strip()
        if len(texto) < 3:
            return erro("Escreva o comentário.")
        run("INSERT INTO feedbacks (edicao_id, texto, nota, criado_em) VALUES (?, ?, ?, ?)",
            (encerrada["id"], texto[:500], inteiro(corpo().get("nota")), carimbo()))
    saida = lab.sentimento(encerrada["id"])
    saida["edicao"] = encerrada["nome"]
    return jsonify(saida)


# ================================================================ lado publico (convite e compra em modo conceito)

@app.get("/api/publico/convite")
def api_publico_convite():
    ed = edicao_atual()
    codigo = (request.args.get("ref") or "").strip().upper()
    promoter = q1("SELECT nome FROM promoters WHERE codigo = ? AND edicao_id = ? AND ativo = 1", (codigo, ed["id"])) if codigo else None
    lote = next((l for l in estoque(ed["id"]) if l["status"] == "ativo" and l["disponivel"]), None)
    abertura = ed.get("abertura_vendas")
    return jsonify({
        "edicao": ed["nome"], "data": ed["data"], "abertura": abertura,
        "aberto": bool(lote) and (not abertura or hoje().isoformat() >= abertura),
        "lote": {"id": lote["id"], "nome": lote["nome"], "preco": lote["preco"],
                 "ultimos": lote["disponivel"] <= 5} if lote else None,
        "por": promoter["nome"] if promoter else None, "ref": codigo if promoter else "",
        "generos": lab.GENEROS,
    })


@app.post("/api/publico/pedido")
def api_publico_pedido():
    d = corpo()
    dados = {k: d.get(k) for k in ("lote_id", "nome", "instagram", "quantidade", "genero_favorito", "bebida", "faixa_etaria", "cidade", "ref")}
    dados["metodo"], dados["status"] = "pix", "pago"
    if not dados.get("ref"):
        dados["origem"] = "Story"
    pedido, problema = criar_pedido(edicao_atual(), dados, publico=True)
    if problema:
        return erro(problema)
    return jsonify({"ingressos": [i["codigo"] for i in pedido["ingressos"]], "total": pedido["valor_total"]}), 201


iniciar_banco()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
