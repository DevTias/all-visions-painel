"""Banco de dados do painel: esquema, conexao, relogio e utilitarios comuns."""
import os
import re
import secrets
import sqlite3
import unicodedata
from datetime import date, datetime

from flask import g

BASE = os.path.dirname(os.path.abspath(__file__))
PASTA_DADOS = os.path.join(BASE, "dados")
CAMINHO_DB = os.environ.get("AV_DB", os.path.join(PASTA_DADOS, "painel.db"))

ESQUEMA = """
CREATE TABLE IF NOT EXISTS config (
    chave TEXT PRIMARY KEY,
    valor TEXT
);
CREATE TABLE IF NOT EXISTS edicoes (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    tema TEXT,
    data TEXT NOT NULL,
    local TEXT,
    capacidade INTEGER NOT NULL,
    abertura_vendas TEXT,
    status TEXT NOT NULL DEFAULT 'planejada',      -- planejada | em_venda | encerrada
    publico_final INTEGER,
    notas TEXT
);
CREATE TABLE IF NOT EXISTS custos (
    id INTEGER PRIMARY KEY,
    edicao_id INTEGER NOT NULL REFERENCES edicoes(id),
    categoria TEXT NOT NULL,
    valor REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS lotes (
    id INTEGER PRIMARY KEY,
    edicao_id INTEGER NOT NULL REFERENCES edicoes(id),
    nome TEXT NOT NULL,
    descricao TEXT,
    preco REAL NOT NULL,
    quantidade INTEGER,                            -- NULL = nao registrado (historico)
    ordem INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'aguardando'      -- aguardando | ativo | esgotado | pausado | encerrado
);
CREATE TABLE IF NOT EXISTS contatos (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    instagram TEXT,
    telefone TEXT,
    email TEXT,
    cidade TEXT,
    bairro TEXT,
    faixa_etaria TEXT,
    genero_favorito TEXT,
    bebida TEXT,
    origem TEXT,
    veterano INTEGER NOT NULL DEFAULT 0,
    tags TEXT,
    notas TEXT,
    criado_em TEXT
);
CREATE TABLE IF NOT EXISTS promoters (
    id INTEGER PRIMARY KEY,
    edicao_id INTEGER NOT NULL REFERENCES edicoes(id),
    nome TEXT NOT NULL,
    instagram TEXT,
    codigo TEXT NOT NULL UNIQUE,
    ativo INTEGER NOT NULL DEFAULT 1,
    entrou_em TEXT
);
CREATE TABLE IF NOT EXISTS promoter_stories (
    id INTEGER PRIMARY KEY,
    promoter_id INTEGER NOT NULL REFERENCES promoters(id) ON DELETE CASCADE,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS comissao_faixas (
    id INTEGER PRIMARY KEY,
    edicao_id INTEGER NOT NULL REFERENCES edicoes(id),
    min_vendas INTEGER NOT NULL,
    percentual REAL NOT NULL,
    bonus REAL NOT NULL DEFAULT 0,
    mimo TEXT
);
CREATE TABLE IF NOT EXISTS pedidos (
    id INTEGER PRIMARY KEY,
    edicao_id INTEGER NOT NULL REFERENCES edicoes(id),
    lote_id INTEGER NOT NULL REFERENCES lotes(id),
    contato_id INTEGER REFERENCES contatos(id),
    promoter_id INTEGER REFERENCES promoters(id),
    quantidade INTEGER NOT NULL,
    valor_unit REAL NOT NULL,
    valor_total REAL NOT NULL,
    metodo TEXT NOT NULL DEFAULT 'pix',            -- pix | cartao | dinheiro | cortesia
    status TEXT NOT NULL DEFAULT 'pago',           -- pago | pendente | estornado
    criado_em TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ingressos (
    id INTEGER PRIMARY KEY,
    pedido_id INTEGER NOT NULL REFERENCES pedidos(id),
    codigo TEXT NOT NULL UNIQUE,
    titular TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'valido',         -- valido | usado | cancelado
    checkin_em TEXT
);
CREATE TABLE IF NOT EXISTS automacoes (
    id INTEGER PRIMARY KEY,
    edicao_id INTEGER NOT NULL REFERENCES edicoes(id),
    tipo TEXT NOT NULL,                            -- mensagem | post | tarefa
    canal TEXT,
    titulo TEXT NOT NULL,
    conteudo TEXT,
    publico TEXT,                                  -- segmento, ou responsavel quando tipo = tarefa
    gatilho TEXT NOT NULL DEFAULT 'data',          -- data | compra | resposta
    agendado_para TEXT,
    status TEXT NOT NULL DEFAULT 'agendada',       -- rascunho | agendada | ativa | enviada | pausada
    enviado_em TEXT,
    alcance INTEGER
);
CREATE TABLE IF NOT EXISTS tarefas (
    id INTEGER PRIMARY KEY,
    edicao_id INTEGER NOT NULL REFERENCES edicoes(id),
    titulo TEXT NOT NULL,
    responsavel TEXT,
    prazo TEXT,
    status TEXT NOT NULL DEFAULT 'a_fazer',        -- a_fazer | andamento | feito
    origem TEXT NOT NULL DEFAULT 'manual',         -- manual | automatica
    prioridade TEXT NOT NULL DEFAULT 'media'       -- alta | media | baixa
);
CREATE TABLE IF NOT EXISTS equipe (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    papel TEXT
);
CREATE TABLE IF NOT EXISTS votos (
    id INTEGER PRIMARY KEY,
    edicao_id INTEGER NOT NULL REFERENCES edicoes(id),
    opcao TEXT NOT NULL,
    criado_em TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS feedbacks (
    id INTEGER PRIMARY KEY,
    edicao_id INTEGER NOT NULL REFERENCES edicoes(id),
    texto TEXT NOT NULL,
    nota INTEGER,
    criado_em TEXT
);
CREATE INDEX IF NOT EXISTS idx_pedidos_edicao ON pedidos(edicao_id, status);
CREATE INDEX IF NOT EXISTS idx_pedidos_promoter ON pedidos(promoter_id);
CREATE INDEX IF NOT EXISTS idx_ingressos_pedido ON ingressos(pedido_id);
"""

TABELAS = [
    "votos", "feedbacks", "tarefas", "automacoes", "ingressos", "pedidos", "comissao_faixas",
    "promoter_stories", "promoters", "contatos", "lotes", "custos", "equipe", "edicoes", "config",
]


# ---------------------------------------------------------------- conexao

def conectar():
    os.makedirs(os.path.dirname(CAMINHO_DB), exist_ok=True)
    con = sqlite3.connect(CAMINHO_DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def db():
    if "db" not in g:
        g.db = conectar()
    return g.db


def fechar(_erro=None):
    con = g.pop("db", None)
    if con is not None:
        con.close()


def q(sql, args=()):
    return [dict(r) for r in db().execute(sql, args).fetchall()]


def q1(sql, args=()):
    r = db().execute(sql, args).fetchone()
    return dict(r) if r else None


def run(sql, args=()):
    cur = db().execute(sql, args)
    db().commit()
    return cur.lastrowid


# ---------------------------------------------------------------- config e relogio

def cfg(chave, padrao=None):
    r = q1("SELECT valor FROM config WHERE chave = ?", (chave,))
    return r["valor"] if r else padrao


def set_cfg(chave, valor):
    run(
        "INSERT INTO config (chave, valor) VALUES (?, ?) "
        "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
        (chave, valor),
    )


def agora():
    """No modo ensaio o calendario fica parado na data simulada; a hora do dia e a real."""
    real = datetime.now().replace(microsecond=0)
    if cfg("modo") == "ensaio":
        dia = date.fromisoformat(cfg("relogio"))
        return datetime.combine(dia, real.time())
    return real


def hoje():
    return agora().date()


def carimbo():
    return agora().isoformat()


# ---------------------------------------------------------------- utilitarios

ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sem 0/O e 1/I


def sem_acento(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto or "") if unicodedata.category(c) != "Mn")


def novo_codigo_ingresso():
    while True:
        bloco = lambda: "".join(secrets.choice(ALFABETO) for _ in range(4))
        codigo = f"AV-{bloco()}-{bloco()}"
        if not q1("SELECT 1 FROM ingressos WHERE codigo = ?", (codigo,)):
            return codigo


def novo_codigo_promoter(nome):
    raiz = re.sub(r"[^A-Z]", "", sem_acento(nome).upper().split(" ")[0] if nome.strip() else "")[:6] or "OLHO"
    while True:
        codigo = f"{raiz}{secrets.randbelow(90) + 10}"
        if not q1("SELECT 1 FROM promoters WHERE codigo = ?", (codigo,)):
            return codigo


def arroba(valor):
    v = (valor or "").strip().lower().lstrip("@")
    return f"@{v}" if v else ""


def edicao_atual():
    return q1("SELECT * FROM edicoes WHERE status != 'encerrada' ORDER BY data LIMIT 1") or q1(
        "SELECT * FROM edicoes ORDER BY data DESC LIMIT 1"
    )


def estoque(edicao_id):
    """Lotes da edicao com vendidos (pagos), reservados (pendentes) e disponiveis."""
    lotes = q(
        """
        SELECT l.*,
            COALESCE((SELECT SUM(p.quantidade) FROM pedidos p WHERE p.lote_id = l.id AND p.status = 'pago'), 0) AS vendidos,
            COALESCE((SELECT SUM(p.quantidade) FROM pedidos p WHERE p.lote_id = l.id AND p.status = 'pendente'), 0) AS reservados,
            COALESCE((SELECT SUM(p.valor_total) FROM pedidos p WHERE p.lote_id = l.id AND p.status = 'pago'), 0) AS receita
        FROM lotes l WHERE l.edicao_id = ? ORDER BY l.ordem, l.id
        """,
        (edicao_id,),
    )
    for l in lotes:
        l["disponivel"] = None if l["quantidade"] is None else max(l["quantidade"] - l["vendidos"] - l["reservados"], 0)
    return lotes
