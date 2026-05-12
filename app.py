from flask import Flask, request, jsonify
import sqlite3
import csv
import os
from datetime import datetime

from pubsub import AsyncConn

app = Flask(__name__)
pubnub = AsyncConn("Flask Application", "meu_canal")

DB_NAME = "data.db"
CSV_NAME = "relatorio_acessos.csv"

colaboradores = {
    "553307625663": {
        "nome": "Julia",
        "matricula": "001",
        "cargo": "Desenvolvedora",
        "acesso": True,
        "ativo": True
    },
    "771439528262": {
        "nome": "Visitante",
        "matricula": "002",
        "cargo": "Visitante",
        "acesso": False,
        "ativo": True
    }
}


def connect_db():
    return sqlite3.connect(DB_NAME)


def create_table():
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs_acesso (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                nome TEXT,
                matricula TEXT,
                tag_rfid TEXT,
                status TEXT NOT NULL,
                mensagem TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def salvar_csv(evento):
    arquivo_existe = os.path.isfile(CSV_NAME)

    with open(CSV_NAME, "a", newline="", encoding="utf-8") as arquivo:
        campos = ["tipo", "nome", "matricula", "tag_rfid", "status", "mensagem", "timestamp"]
        writer = csv.DictWriter(arquivo, fieldnames=campos)

        if not arquivo_existe:
            writer.writeheader()

        writer.writerow(evento)


def montar_logs(rows):
    logs = []

    for row in rows:
        logs.append({
            "id": row[0],
            "tipo": row[1],
            "nome": row[2],
            "matricula": row[3],
            "tag_rfid": row[4],
            "status": row[5],
            "mensagem": row[6],
            "timestamp": row[7]
        })

    return logs


def buscar_logs_por_tipo(tipo):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, tipo, nome, matricula, tag_rfid, status, mensagem, timestamp
            FROM logs_acesso
            WHERE tipo = ?
            ORDER BY id DESC
        """, (tipo,))
        rows = cursor.fetchall()

    return jsonify(montar_logs(rows)), 200


def criar_evento_por_tag(tag_rfid):
    colaborador = colaboradores.get(tag_rfid)

    if colaborador is None:
        return {
            "tipo": "TENTATIVA_INVASAO",
            "nome": "Desconhecido",
            "matricula": None,
            "tag_rfid": tag_rfid,
            "status": "TAG_NAO_CADASTRADA",
            "mensagem": "Tentativa de invasão com tag desconhecida"
        }

    if colaborador["acesso"] is True and colaborador["ativo"] is True:
        return {
            "tipo": "ENTRADA",
            "nome": colaborador["nome"],
            "matricula": colaborador["matricula"],
            "tag_rfid": tag_rfid,
            "status": "AUTORIZADO",
            "mensagem": f"Bem-vindo, {colaborador['nome']}"
        }

    return {
        "tipo": "TENTATIVA_NEGADA",
        "nome": colaborador["nome"],
        "matricula": colaborador["matricula"],
        "tag_rfid": tag_rfid,
        "status": "NAO_AUTORIZADO",
        "mensagem": f"Acesso negado para {colaborador['nome']}"
    }


create_table()


@app.route("/", methods=["POST", "GET"])
def raiz():
    if request.method == "POST":
        return criar_log()

    return listar_logs()


@app.route("/logs", methods=["GET"])
def listar_logs():
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, tipo, nome, matricula, tag_rfid, status, mensagem, timestamp
            FROM logs_acesso
            ORDER BY id DESC
        """)
        rows = cursor.fetchall()

    return jsonify(montar_logs(rows)), 200


@app.route("/logs/recentes", methods=["GET"])
def logs_recentes():
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, tipo, nome, matricula, tag_rfid, status, mensagem, timestamp
            FROM logs_acesso
            ORDER BY id DESC
            LIMIT 10
        """)
        rows = cursor.fetchall()

    return jsonify(montar_logs(rows)), 200


@app.route("/logs/entradas", methods=["GET"])
def logs_entradas():
    return buscar_logs_por_tipo("ENTRADA")


@app.route("/logs/negados", methods=["GET"])
def logs_negados():
    return buscar_logs_por_tipo("TENTATIVA_NEGADA")


@app.route("/logs/invasoes", methods=["GET"])
def logs_invasoes():
    return buscar_logs_por_tipo("TENTATIVA_INVASAO")


@app.route("/colaboradores", methods=["GET"])
def listar_colaboradores():
    return jsonify(colaboradores), 200


def criar_log():
    try:
        body = request.get_json()

        if not body:
            return jsonify({"error": "JSON não enviado"}), 400

        tag_rfid = body.get("tag_rfid")

        if not tag_rfid:
            return jsonify({"error": "Tag RFID não enviada"}), 400

        tag_rfid = str(tag_rfid)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        evento = criar_evento_por_tag(tag_rfid)
        evento["timestamp"] = timestamp

        with connect_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO logs_acesso 
                (tipo, nome, matricula, tag_rfid, status, mensagem, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                evento["tipo"],
                evento["nome"],
                evento["matricula"],
                evento["tag_rfid"],
                evento["status"],
                evento["mensagem"],
                evento["timestamp"]
            ))
            conn.commit()

        salvar_csv(evento)
        pubnub.publish(evento)

        return jsonify({
            "message": "Evento registrado com sucesso",
            "evento": evento
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)