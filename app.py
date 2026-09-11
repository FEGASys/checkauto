# -*- coding: utf-8 -*-
"""CheckAuto — checklist de revisão de veículos.

Roda atrás do nginx em /checklist/ (o prefixo é removido pelo proxy),
então todas as rotas aqui são relativas à raiz.
"""

import json
import os
import sqlite3
import time

from flask import Flask, g, jsonify, render_template, request, send_from_directory

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("CHECKAUTO_DB", os.path.join(BASE, "dados.db"))

app = Flask(__name__, template_folder=BASE, static_folder=None)

# O logotipo fica na raiz do projeto; aceita os dois nomes possíveis.
LOGOS = ("logo.png", "logo_preview.png")


# ---------------------------------------------------------------- banco
def conectar():
    con = getattr(g, "_con", None)
    if con is None:
        con = g._con = sqlite3.connect(DB_PATH, timeout=10)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
    return con


@app.teardown_appcontext
def fechar(_exc):
    con = getattr(g, "_con", None)
    if con is not None:
        con.close()


def criar_tabelas():
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.execute("""
        CREATE TABLE IF NOT EXISTS revisoes (
            id            TEXT PRIMARY KEY,
            placa         TEXT NOT NULL DEFAULT '',
            modelo        TEXT NOT NULL DEFAULT '',
            ano           TEXT NOT NULL DEFAULT '',
            km            TEXT NOT NULL DEFAULT '',
            data          TEXT NOT NULL DEFAULT '',
            responsavel   TEXT NOT NULL DEFAULT '',
            conferente    TEXT NOT NULL DEFAULT '',
            os            TEXT NOT NULL DEFAULT '',
            total         TEXT NOT NULL DEFAULT '',
            itens         TEXT NOT NULL DEFAULT '{}',
            atualizado_em INTEGER NOT NULL DEFAULT 0
        )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS ix_revisoes_placa ON revisoes(placa)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_revisoes_quando ON revisoes(atualizado_em DESC)")
    con.commit()
    con.close()


criar_tabelas()

CAMPOS = ("placa", "modelo", "ano", "km", "data", "responsavel", "conferente", "os", "total")


def como_dict(linha):
    reg = {c: linha[c] for c in CAMPOS}
    reg["id"] = linha["id"]
    reg["atualizadoEm"] = linha["atualizado_em"]
    try:
        reg["itens"] = json.loads(linha["itens"] or "{}")
    except ValueError:
        reg["itens"] = {}
    return reg


# ---------------------------------------------------------------- páginas
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/logo.png")
def logo():
    for nome in LOGOS:
        if os.path.exists(os.path.join(BASE, nome)):
            return send_from_directory(BASE, nome, max_age=60 * 60 * 24 * 7)
    return ("", 404)


@app.route("/saude")
def saude():
    return jsonify(ok=True, agora=int(time.time()))


# ---------------------------------------------------------------- API
@app.route("/api/revisoes", methods=["GET"])
def listar():
    busca = (request.args.get("q") or "").strip().upper()
    sql = "SELECT * FROM revisoes"
    args = []
    if busca:
        sql += " WHERE UPPER(placa) LIKE ? OR UPPER(modelo) LIKE ?"
        args = ["%" + busca + "%", "%" + busca + "%"]
    sql += " ORDER BY atualizado_em DESC LIMIT 500"
    linhas = conectar().execute(sql, args).fetchall()
    return jsonify([como_dict(l) for l in linhas])


@app.route("/api/revisoes", methods=["POST"])
def salvar():
    dados = request.get_json(silent=True) or {}
    placa = (dados.get("placa") or "").strip().upper()
    if not placa:
        return jsonify(erro="Informe a placa do veículo."), 400

    agora = int(time.time() * 1000)
    ident = (dados.get("id") or "").strip()
    if not ident:
        ident = "".join(ch for ch in placa if ch.isalnum()) + "-" + str(agora)

    valores = [ident, placa]
    for campo in CAMPOS[1:]:
        valores.append(str(dados.get(campo) or "")[:200])
    valores.append(json.dumps(dados.get("itens") or {}, ensure_ascii=False))
    valores.append(agora)

    con = conectar()
    con.execute("""
        INSERT INTO revisoes (id, placa, modelo, ano, km, data, responsavel,
                              conferente, os, total, itens, atualizado_em)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
            placa=excluded.placa, modelo=excluded.modelo, ano=excluded.ano,
            km=excluded.km, data=excluded.data, responsavel=excluded.responsavel,
            conferente=excluded.conferente, os=excluded.os, total=excluded.total,
            itens=excluded.itens, atualizado_em=excluded.atualizado_em
    """, valores)
    con.commit()
    linha = con.execute("SELECT * FROM revisoes WHERE id=?", (ident,)).fetchone()
    return jsonify(como_dict(linha))


@app.route("/api/revisoes/<ident>", methods=["DELETE"])
def excluir(ident):
    con = conectar()
    con.execute("DELETE FROM revisoes WHERE id=?", (ident,))
    con.commit()
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8010, debug=True)
