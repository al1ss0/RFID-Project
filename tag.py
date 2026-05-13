import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import time
import requests
import json
import os

leitorRfid = SimpleMFRC522()

LED_VERDE = 13
LED_VERMELHO = 16
BUZZER = 18

API_URL = "http://127.0.0.1:5000/"
COLABORADORES_URL = "http://127.0.0.1:5000/colaboradores"

CACHE_FILE = "colaboradores_cache.json"
EVENTOS_OFFLINE = "eventos_offline.json"

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)

GPIO.setup(LED_VERDE, GPIO.OUT)
GPIO.setup(LED_VERMELHO, GPIO.OUT)
GPIO.setup(BUZZER, GPIO.OUT)


def desligar_tudo():
    GPIO.output(LED_VERDE, GPIO.LOW)
    GPIO.output(LED_VERMELHO, GPIO.LOW)
    GPIO.output(BUZZER, GPIO.LOW)


def som_autorizado():
    GPIO.output(BUZZER, GPIO.HIGH)
    time.sleep(0.2)
    GPIO.output(BUZZER, GPIO.LOW)


def som_negado():
    for _ in range(2):
        GPIO.output(BUZZER, GPIO.HIGH)
        time.sleep(0.2)
        GPIO.output(BUZZER, GPIO.LOW)
        time.sleep(0.2)


def som_invasao():
    for _ in range(5):
        GPIO.output(BUZZER, GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(BUZZER, GPIO.LOW)
        time.sleep(0.1)


def baixar_colaboradores():
    try:
        resposta = requests.get(COLABORADORES_URL, timeout=3)

        if resposta.status_code == 200:
            colaboradores = resposta.json()

            with open(CACHE_FILE, "w") as arquivo:
                json.dump(colaboradores, arquivo)

            print("Cache de colaboradores atualizado.")

    except Exception as erro:
        print("Sem conexão com API. Usando cache local.")


def carregar_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as arquivo:
            return json.load(arquivo)

    return []


def salvar_evento_offline(tag):
    eventos = []

    if os.path.exists(EVENTOS_OFFLINE):
        with open(EVENTOS_OFFLINE, "r") as arquivo:
            eventos = json.load(arquivo)

    eventos.append({
        "tag_rfid": str(tag)
    })

    with open(EVENTOS_OFFLINE, "w") as arquivo:
        json.dump(eventos, arquivo)

    print("Evento salvo offline.")


def sincronizar_eventos():
    if not os.path.exists(EVENTOS_OFFLINE):
        return

    try:
        with open(EVENTOS_OFFLINE, "r") as arquivo:
            eventos = json.load(arquivo)

        if len(eventos) == 0:
            return

        print(f"Sincronizando {len(eventos)} eventos offline...")

        for evento in eventos:
            requests.post(API_URL, json=evento, timeout=3)

        os.remove(EVENTOS_OFFLINE)

        print("Eventos offline sincronizados.")

    except Exception as erro:
        print("Falha ao sincronizar eventos offline.")


def validar_localmente(tag):
    colaboradores = carregar_cache()

    for colaborador in colaboradores:

        if colaborador["tag_rfid"] == str(tag):

            if colaborador["acesso"]:

                return {
                    "status": "AUTORIZADO",
                    "mensagem": f"Bem-vindo, {colaborador['nome']}"
                }

            else:

                return {
                    "status": "NAO_AUTORIZADO",
                    "mensagem": f"Acesso negado para {colaborador['nome']}"
                }

    return {
        "status": "TAG_NAO_CADASTRADA",
        "mensagem": "Tentativa de invasão com tag desconhecida"
    }


def enviar_tag_para_api(tag):
    resposta = requests.post(API_URL, json={
        "tag_rfid": str(tag)
    }, timeout=3)

    return resposta.json()


try:
    print("Sistema RFID iniciado.")

    baixar_colaboradores()
    sincronizar_eventos()

    while True:

        print("\nAproxime a tag...")
        tag, text = leitorRfid.read()
        tag = str(tag)

        print(f"Tag lida: {tag}")

        try:
            resposta = enviar_tag_para_api(tag)

            evento = resposta.get("evento", {})

            print("ONLINE")

        except Exception as erro:

            print("OFFLINE - usando cache local")

            evento = validar_localmente(tag)

            salvar_evento_offline(tag)

        status = evento.get("status")
        mensagem = evento.get("mensagem")

        print(mensagem)

        if status == "AUTORIZADO":

            GPIO.output(LED_VERDE, GPIO.HIGH)

            som_autorizado()

            time.sleep(2)

            GPIO.output(LED_VERDE, GPIO.LOW)

        elif status == "NAO_AUTORIZADO":

            GPIO.output(LED_VERMELHO, GPIO.HIGH)

            som_negado()

            time.sleep(2)

            GPIO.output(LED_VERMELHO, GPIO.LOW)

        elif status == "TAG_NAO_CADASTRADA":

            GPIO.output(LED_VERMELHO, GPIO.HIGH)

            som_invasao()

            time.sleep(2)

            GPIO.output(LED_VERMELHO, GPIO.LOW)

        time.sleep(2)

except KeyboardInterrupt:
    print("\nPrograma encerrado.")

finally:
    desligar_tudo()
    GPIO.cleanup()