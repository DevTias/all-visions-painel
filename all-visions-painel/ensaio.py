"""Carga inicial do painel.

Fatos reais (vindos da memoria da marca): edicao 1.0, precos dos lotes, custos, capacidade,
datas e local da proxima edicao.

Dados de ensaio (inventados para o painel ter o que mostrar): quantidades por lote da 2.0,
compradores, promoters, vendas, comentarios e votos. No modo ensaio o calendario fica parado
em 17/04/2027, o 13o dia de venda. O modo real apaga tudo isso e usa o relogio de verdade.
"""
import json
import random
import secrets
from datetime import date, datetime, timedelta

from banco import ALFABETO, ESQUEMA, TABELAS, sem_acento

RELOGIO_ENSAIO = "2027-04-17"

DESIGN_INGRESSO = {
    "frase": "Amplie sua visão, expanda sua mente.",
    "rodape": "Apenas convidados",
    "clima": "nevoa",
    "mostrar_nome": True,
    "mostrar_lote": True,
    "mostrar_local": False,
}

CUSTOS_1_0 = [
    ("Decoração e cenografia", 1425.69),
    ("Marketing, designer e impulsionamento", 1447.98),
    ("Bebidas", 897.56),
    ("Pirotecnia", 860.00),
    ("Identidade e operação", 602.12),
    ("Fotógrafo", 200.00),
    ("Conserto de caixa de som", 190.00),
]

LOTES_1_0 = [
    ("Antecipado", "Com horário de entrada", 25),
    ("Sem horário", "Entrada padrão", 35),
    ("2º lote", "", 50),
    ("3º lote", "Esgotou rápido demais", 70),
    ("Porta", "Sob demanda, conforme a casa girava", 120),
]

# quantidades de ensaio para a escada da 2.0 (somam a capacidade da casa)
LOTES_2_0 = [
    ("Antecipado", "Com horário de entrada", 25, 20),
    ("Sem horário", "Entrada padrão", 35, 30),
    ("2º lote", "", 50, 40),
    ("3º lote", "", 70, 20),
    ("Porta", "Sob demanda na noite", 120, 10),
]

EQUIPE = [
    ("Mateus", "Direção, curadoria e comunicação"),
    ("Guilherme Barents", "Som, iluminação e estrutura"),
    ("Audiovisual", "Feed, gravações e aftermovie"),
    ("Bar", "Terceirizado"),
    ("Segurança", "Terceirizado"),
    ("Limpeza", "A contratar"),
]

FAIXAS = [
    (0, 8, 0, ""),
    (8, 10, 0, "Ingresso próprio garantido"),
    (15, 12, 0, "Ingresso + 1 e R$ 100 de consumação"),
    (25, 15, 50, "Nome na carta-convite da próxima edição"),
]

# ---------------------------------------------------------------- ensaio

PERFIL_DIARIO = [16, 11, 8, 7, 6, 5, 5, 4, 4, 3, 2, 2, 1]  # ingressos pagos por dia, 05/04 a 17/04

PRIMEIROS = [
    "Ana", "Bruno", "Clara", "Davi", "Elisa", "Felipe", "Giovana", "Heitor", "Isabela", "João", "Karen", "Lucas",
    "Marina", "Nicolas", "Olívia", "Pedro", "Rebeca", "Samuel", "Tainá", "Valentina", "Wesley", "Yasmin", "Igor",
    "Júlia", "Leandro", "Manuela", "Otávio", "Paula", "Renan", "Sofia", "Thiago", "Vitória", "André", "Bianca",
    "Diego", "Fernanda", "Gustavo", "Helena", "Larissa", "Murilo", "Natália", "Rodrigo", "Sabrina", "Vinícius",
    "Alice", "Bernardo", "Camila", "Eduardo", "Lívia", "Miguel", "Luana", "Enzo", "Maitê", "Raul", "Isis", "Tomás",
]
INICIAIS = "ABCDFGLMNOPRSTV"

PROMOTERS = [
    # nome, codigo, dia em que entrou, dias com story (indices a partir da abertura)
    ("Lia M.", "LIA27", 0, [0, 1, 2, 3, 5, 6, 7, 8, 9, 10, 11]),
    ("Rafa T.", "RAFA14", 0, [0, 1, 3, 4, 6, 8, 10]),
    ("Bia C.", "BIA08", 1, [1, 2, 5, 7, 9]),
    ("Théo S.", "THEO31", 0, [0, 2, 4]),
    ("Nina P.", "NINA05", 3, []),
]

# quem vendeu em cada dia (indice do promoter acima), um pedido por entrada.
# Lia, Rafa e Bia seguem vendendo; Théo parou no dia 10/04; Nina nunca vendeu.
VENDAS_POR_PROMOTER = [
    [0, 1, 3, 0, 1], [0, 1, 2, 3], [0, 2], [1, 3, 0], [0, 2], [1, 3], [0, 1], [2], [0], [2], [1], [0], [],
]


def _pesado(rng, pares):
    total = sum(p for _, p in pares)
    alvo = rng.uniform(0, total)
    acumulado = 0
    for valor, peso in pares:
        acumulado += peso
        if alvo <= acumulado:
            return valor
    return pares[-1][0]


def _codigo_ingresso(usados):
    while True:
        bloco = lambda: "".join(secrets.choice(ALFABETO) for _ in range(4))
        codigo = f"AV-{bloco()}-{bloco()}"
        if codigo not in usados:
            usados.add(codigo)
            return codigo


def _base(con, modo):
    con.execute(
        "INSERT INTO edicoes (id, nome, tema, data, local, capacidade, abertura_vendas, status, publico_final, notas) "
        "VALUES (1, 'ALL VISIONS 1.0', 'Jungle', '2026-05-16', 'Foccus Lounge', 120, NULL, 'encerrada', 120, ?)",
        ("Decoração foi o diferencial. Bar vendeu abaixo do esperado, faltou alguém nos banheiros e o 3º lote "
         "tinha pouca quantidade.",),
    )
    con.execute(
        "INSERT INTO edicoes (id, nome, tema, data, local, capacidade, abertura_vendas, status, notas) "
        "VALUES (2, 'ALL VISIONS 2.0', 'Infinito', '2027-05-01', 'Foccus Lounge', 120, '2027-04-05', 'em_venda', ?)",
        ("Tema espelhado. Peça central: betoneira espelhada no gramado. Nome da edição em aberto.",),
    )
    con.executemany("INSERT INTO custos (edicao_id, categoria, valor) VALUES (1, ?, ?)", CUSTOS_1_0)
    for i, (nome, desc, preco) in enumerate(LOTES_1_0):
        con.execute(
            "INSERT INTO lotes (edicao_id, nome, descricao, preco, quantidade, ordem, status) VALUES (1, ?, ?, ?, NULL, ?, 'encerrado')",
            (nome, desc, preco, i),
        )
    con.executemany("INSERT INTO equipe (nome, papel) VALUES (?, ?)", EQUIPE)
    con.executemany(
        "INSERT INTO comissao_faixas (edicao_id, min_vendas, percentual, bonus, mimo) VALUES (2, ?, ?, ?, ?)", FAIXAS
    )
    pares = {
        "modo": modo,
        "relogio": RELOGIO_ENSAIO,
        "ingresso_design": json.dumps(DESIGN_INGRESSO, ensure_ascii=False),
    }
    con.executemany("INSERT INTO config (chave, valor) VALUES (?, ?)", list(pares.items()))


def _ensaio(con):
    rng = random.Random(27)
    abertura = date(2027, 4, 5)

    # lotes da 2.0: dois esgotados, o 2o lote em venda
    status = ["esgotado", "esgotado", "ativo", "aguardando", "aguardando"]
    lotes = []
    for i, (nome, desc, preco, qtd) in enumerate(LOTES_2_0):
        cur = con.execute(
            "INSERT INTO lotes (edicao_id, nome, descricao, preco, quantidade, ordem, status) VALUES (2, ?, ?, ?, ?, ?, ?)",
            (nome, desc, preco, qtd, i, status[i]),
        )
        lotes.append({"id": cur.lastrowid, "preco": preco, "resta": qtd})

    # promoters e stories
    promoters = []
    for nome, codigo, d0, stories in PROMOTERS:
        cur = con.execute(
            "INSERT INTO promoters (edicao_id, nome, instagram, codigo, ativo, entrou_em) VALUES (2, ?, ?, ?, 1, ?)",
            (nome, "@" + sem_acento(nome).lower().replace(" ", "").replace(".", "") + "_", codigo,
             (abertura + timedelta(days=d0)).isoformat()),
        )
        pid = cur.lastrowid
        promoters.append({"id": pid})
        for d in stories:
            con.execute("INSERT INTO promoter_stories (promoter_id, data) VALUES (?, ?)",
                        (pid, (abertura + timedelta(days=d)).isoformat()))

    def novo_contato(quando, origem):
        primeiro = rng.choice(PRIMEIROS)
        inicial = rng.choice(INICIAIS)
        nome = f"{primeiro} {inicial}."
        cidade = _pesado(rng, [("Teresópolis", 82), ("Petrópolis", 6), ("Guapimirim", 5), ("Rio de Janeiro", 7)])
        bairro = rng.choice(["Alto", "Várzea", "Agriões", "Tijuca", "Fátima", "São Pedro", "Barra do Imbuí", "Araras"]) \
            if cidade == "Teresópolis" else ""
        cur = con.execute(
            "INSERT INTO contatos (nome, instagram, cidade, bairro, faixa_etaria, genero_favorito, bebida, origem, veterano, criado_em) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                nome,
                f"@{sem_acento(primeiro).lower()}.{inicial.lower()}{rng.randint(10, 99)}",
                cidade,
                bairro,
                _pesado(rng, [("18 a 21", 22), ("22 a 25", 38), ("26 a 30", 27), ("31 ou mais", 13)]),
                _pesado(rng, [("House", 24), ("Tech House", 27), ("Deep House", 15), ("Indie Dance", 14),
                              ("Melodic House", 15), ("Progressive House", 5)]),
                _pesado(rng, [("Gin", 36), ("Vodka", 22), ("Cerveja", 18), ("Whisky", 9), ("Tequila", 8),
                              ("Sem álcool", 7)]),
                origem,
                1 if rng.random() < 0.3 else 0,
                quando,
            ),
        )
        return cur.lastrowid, nome

    usados = set()

    def registrar(quando, lote, qtd, status_pedido, metodo, promoter_id):
        origem = "Promoter" if promoter_id else _pesado(rng, [("Story", 56), ("Feed", 20), ("Indicação", 24)])
        contato_id, nome = novo_contato(quando, origem)
        cur = con.execute(
            "INSERT INTO pedidos (edicao_id, lote_id, contato_id, promoter_id, quantidade, valor_unit, valor_total, metodo, status, criado_em) "
            "VALUES (2, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (lote["id"], contato_id, promoter_id, qtd, lote["preco"], lote["preco"] * qtd, metodo, status_pedido, quando),
        )
        if status_pedido == "pago":
            for n in range(qtd):
                titular = nome if n == 0 else f"Convidado de {nome}"
                con.execute("INSERT INTO ingressos (pedido_id, codigo, titular, status) VALUES (?, ?, ?, 'valido')",
                            (cur.lastrowid, _codigo_ingresso(usados), titular))
        lote["resta"] -= qtd

    for d, total in enumerate(PERFIL_DIARIO):
        dia = abertura + timedelta(days=d)
        ultimo = d == len(PERFIL_DIARIO) - 1
        falta = total
        fila = list(VENDAS_POR_PROMOTER[d])
        n_pedido = 0
        while falta > 0:
            lote = next(l for l in lotes if l["resta"] > 0)
            qtd = min(_pesado(rng, [(1, 50), (2, 38), (3, 12)]), falta, lote["resta"])
            if ultimo:
                hora, minuto = 0, 20  # o "hoje" do ensaio: so vale o que ja aconteceu
            else:
                hora = _pesado(rng, [(9, 4), (10, 5), (11, 6), (12, 12), (13, 10), (14, 5), (16, 4), (18, 7),
                                     (19, 12), (20, 14), (21, 13), (22, 8)])
                if d == 0:
                    hora = max(hora, 9)
                minuto = rng.randint(0, 59)
            quando = datetime(dia.year, dia.month, dia.day, hora, minuto, rng.randint(0, 59)).isoformat()
            # pedidos alternados: um por promoter, um direto, enquanto houver fila no dia
            promoter_id = promoters[fila.pop(0)]["id"] if fila and n_pedido % 2 == 0 else None
            n_pedido += 1
            registrar(quando, lote, qtd, "pago", _pesado(rng, [("pix", 78), ("cartao", 22)]), promoter_id)
            falta -= qtd

    # pagamentos que ficaram no meio do caminho (um deles ha mais de 24h)
    segundo = lotes[2]
    registrar("2027-04-15T13:05:00", segundo, 2, "pendente", "pix", promoters[1]["id"])
    registrar("2027-04-16T21:40:00", segundo, 1, "pendente", "pix", None)

    # central de automacao
    autos = [
        ("post", "Feed e stories do Instagram", "Abertura das vendas",
         "Dia 5. Uma porta se abre para quem já aprendeu a olhar. Responda e receba o caminho.",
         "Seguidores", "data", "2027-04-05T09:00:00", "enviada", "2027-04-05T09:00:00", None),
        ("mensagem", "Direct do Instagram", "Resposta com o link de venda",
         "Você olhou na hora certa. O acesso está aqui: {link}. Apenas convidados.",
         "Quem responde ao post", "resposta", None, "ativa", None, None),
        ("mensagem", "WhatsApp", "Ingresso entregue após a compra",
         "Seu acesso à {edicao} está confirmado. O ingresso segue neste link: {ingresso}. Guarde com você.",
         "Compradores", "compra", None, "ativa", None, None),
        ("post", "Stories do Instagram", "Virada para o 2º lote",
         "Um olhar se fecha, outro se abre. 2º lote disponível para quem ainda procura a entrada.",
         "Seguidores", "data", "2027-04-10T19:00:00", "enviada", "2027-04-10T19:00:00", None),
        ("post", "Reels do Instagram", "O reflexo: primeira revelação",
         "Dois espelhos, um de frente para o outro. No meio, você. 01.05.",
         "Seguidores", "data", "2027-04-20T19:30:00", "agendada", None, None),
        ("post", "TikTok", "Corte da 1.0: a casa por dentro",
         "O que foi visto não se desfaz.",
         "Seguidores", "data", "2027-04-22T18:00:00", "rascunho", None, None),
        ("mensagem", "WhatsApp", "Uma semana: lembrete para quem já está dentro",
         "Falta uma semana. Seu acesso já está com você. O resto, você vê lá.",
         "Compradores", "data", "2027-04-24T12:00:00", "agendada", None, None),
    ]
    con.executemany(
        "INSERT INTO automacoes (edicao_id, tipo, canal, titulo, conteudo, publico, gatilho, agendado_para, status, enviado_em, alcance) "
        "VALUES (2, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        autos,
    )

    tarefas = [
        ("Briefing do audiovisual para a edição", "Mateus", "2027-04-12", "feito", "manual", "media"),
        ("Fechar fornecedor dos espelhos da betoneira", "Mateus", "2027-04-20", "andamento", "manual", "alta"),
        ("Confirmar sistema de som e iluminação", "Guilherme Barents", "2027-04-22", "a_fazer", "manual", "alta"),
        ("Definir o drink autoral da edição", "Mateus", "2027-04-24", "a_fazer", "manual", "media"),
        ("Alinhar pirotecnia com a JR Pirotecnias", "Mateus", "2027-04-26", "a_fazer", "manual", "media"),
        ("Anunciar virada: 2º lote aberto", "Mateus", "2027-04-10", "feito", "automatica", "alta"),
    ]
    con.executemany(
        "INSERT INTO tarefas (edicao_id, titulo, responsavel, prazo, status, origem, prioridade) VALUES (2, ?, ?, ?, ?, ?, ?)",
        tarefas,
    )

    # comentarios de ensaio sobre a 1.0, escritos em cima dos aprendizados reais da edicao
    comentarios = [
        ("A decoração estava absurda, nunca vi nada assim aqui na cidade.", 5),
        ("Som impecável do início ao fim. Voltaria amanhã.", 5),
        ("Amei o clima, mas a fila do bar demorou demais.", 3),
        ("Banheiro ficou sujo depois da meia-noite, faltou alguém cuidando.", 2),
        ("O neon do olho virou o ponto de foto da noite. Lindo.", 5),
        ("Público muito bom, todo mundo na mesma energia.", 5),
        ("Queria ter comprado no 3º lote e acabou rápido demais. Fiquei na porta e achei caro.", 2),
        ("Drink da casa estava ótimo, pena que o cardápio era curto.", 4),
        ("Melhor festa de house que já fui em Teresópolis.", 5),
        ("Faltou papel no banheiro no fim da noite.", 2),
        ("A pirotecnia na hora do pico foi surreal.", 5),
        ("Bar fraco para o tamanho da festa, poucas opções.", 2),
        ("Lugar pequeno, mas isso deixou tudo mais íntimo. Gostei.", 4),
        ("As plantas e as luzes verdes deixaram tudo diferente de qualquer festa daqui.", 5),
    ]
    con.executemany(
        "INSERT INTO feedbacks (edicao_id, texto, nota, criado_em) VALUES (1, ?, ?, '2026-05-17T12:00:00')", comentarios
    )

    # rodada de votacao em andamento
    votos = [("Tech House", 19), ("House", 13), ("Indie Dance", 9), ("Melodic House", 7), ("Deep House", 4)]
    for opcao, n in votos:
        con.executemany("INSERT INTO votos (edicao_id, opcao, criado_em) VALUES (2, ?, '2027-04-17T00:00:00')",
                        [(opcao,)] * n)


def semear(con, modo="ensaio"):
    """Recria o banco inteiro. modo = 'ensaio' (com dados simulados) ou 'real' (so os fatos da marca)."""
    con.executescript(ESQUEMA)
    for tabela in TABELAS:
        con.execute(f"DELETE FROM {tabela}")
    _base(con, modo)
    if modo == "ensaio":
        _ensaio(con)
    con.commit()
