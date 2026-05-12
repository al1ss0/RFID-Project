import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import time
import requests

leitorRfid = SimpleMFRC522()

LED_VERDE = 13
LED_VERMELHO = 16
BUZZER = 18

API_URL = "http://127.0.0.1:5000/"

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


def enviar_tag_para_api(tag):
    resposta = requests.post(API_URL, json={
        "tag_rfid": str(tag)
    })

    return resposta.json()


try:
    print("Sistema RFID iniciado. Aproxime uma tag...")

    while True:
        tag, text = leitorRfid.read()
        tag = str(tag)

        print(f"Tag lida: {tag}")

        try:
            resposta = enviar_tag_para_api(tag)
            evento = resposta.get("evento", {})

            print("Resposta da API:", evento)

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

        except Exception as erro:
            print("Erro ao enviar tag para API:", erro)

        print("Aguardando próxima tag...")
        time.sleep(2)

except KeyboardInterrupt:
    print("\nPrograma encerrado.")

finally:
    desligar_tudo()
    GPIO.cleanup()