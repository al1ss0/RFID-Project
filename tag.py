import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import time
import csv
from datetime import datetime

leitorRfid = SimpleMFRC522()

LED_VERDE = 13       # pino físico 13
LED_VERMELHO = 16    # pino físico 16
BUZZER = 18          # pino físico 18

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)

GPIO.setup(LED_VERDE, GPIO.OUT)
GPIO.setup(LED_VERMELHO, GPIO.OUT)
GPIO.setup(BUZZER, GPIO.OUT)


colaboradores = {
    553307625663: {"nome": "Julia", "autorizado": True},
    771439528262: {"nome": "Visitante", "autorizado": False}
}

dentro_sala = {}
relatorio = {}
eventos = []
tentativas_invasao = 0

def registrar_evento(tag, nome, tipo, status):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    eventos.append({
        "data_hora": agora,
        "tag": tag,
        "nome": nome,
        "tipo": tipo,
        "status": status
    })

def desligar_tudo():
    GPIO.output(LED_VERDE, GPIO.LOW)
    GPIO.output(LED_VERMELHO, GPIO.LOW)
    GPIO.output(BUZZER, GPIO.LOW)

def som_autorizado():
    GPIO.output(BUZZER, GPIO.HIGH)
    time.sleep(0.2)
    GPIO.output(BUZZER, GPIO.LOW)

def som_negado():
    for i in range(2):
        GPIO.output(BUZZER, GPIO.HIGH)
        time.sleep(0.2)
        GPIO.output(BUZZER, GPIO.LOW)
        time.sleep(0.2)

def som_invasao():
    for i in range(5):
        GPIO.output(BUZZER, GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(BUZZER, GPIO.LOW)
        time.sleep(0.1)

def criar_relatorio_csv():
    with open("relatorio_acessos.csv", "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)

        escritor.writerow(["Data/Hora", "Tag", "Nome", "Tipo de evento", "Status"])

        for evento in eventos:
            escritor.writerow([
                evento["data_hora"],
                evento["tag"],
                evento["nome"],
                evento["tipo"],
                evento["status"]
            ])

        escritor.writerow([])
        escritor.writerow(["Resumo final"])
        escritor.writerow(["Nome", "Tempo total (min)", "Entradas", "Tentativas negadas"])

        for nome, dados in relatorio.items():
            minutos = dados["tempo_total"] / 60
            escritor.writerow([
                nome,
                f"{minutos:.2f}",
                dados["entradas"],
                dados["tentativas_negadas"]
            ])

        escritor.writerow([])
        escritor.writerow(["Tentativas de invasao", tentativas_invasao])

try:
    print("Sistema iniciado. Aproxime uma tag RFID...")

    while True:
        tag, text = leitorRfid.read()
        tag = int(tag)

        if tag in colaboradores:
            nome = colaboradores[tag]["nome"]
            autorizado = colaboradores[tag]["autorizado"]

            if nome not in relatorio:
                relatorio[nome] = {
                    "tempo_total": 0,
                    "entradas": 0,
                    "tentativas_negadas": 0
                }

            if autorizado:
                GPIO.output(LED_VERDE, GPIO.HIGH)
                som_autorizado()

                if tag not in dentro_sala:
                    print(f"Bem-vindo, {nome}")
                    registrar_evento(tag, nome, "ENTRADA", "AUTORIZADO")

                    dentro_sala[tag] = time.time()
                    relatorio[nome]["entradas"] += 1
                else:
                    print(f"Bem-vindo de volta, {nome}")
                    registrar_evento(tag, nome, "SAIDA", "AUTORIZADO")

                    tempo_permanencia = time.time() - dentro_sala[tag]
                    relatorio[nome]["tempo_total"] += tempo_permanencia
                    del dentro_sala[tag]

                time.sleep(5)
                GPIO.output(LED_VERDE, GPIO.LOW)

            else:
                print(f"Você não tem acesso a este projeto, {nome}")
                registrar_evento(tag, nome, "TENTATIVA_NEGADA", "NAO_AUTORIZADO")

                relatorio[nome]["tentativas_negadas"] += 1

                GPIO.output(LED_VERMELHO, GPIO.HIGH)
                som_negado()
                time.sleep(5)
                GPIO.output(LED_VERMELHO, GPIO.LOW)

        else:
            print("Identificação não encontrada!")
            registrar_evento(tag, "Desconhecido", "TENTATIVA_INVASAO", "TAG_NAO_CADASTRADA")

            tentativas_invasao += 1
            som_invasao()

            for i in range(10):
                GPIO.output(LED_VERMELHO, GPIO.HIGH)
                time.sleep(0.2)
                GPIO.output(LED_VERMELHO, GPIO.LOW)
                time.sleep(0.2)

        print("Aguardando próxima tag...")

except KeyboardInterrupt:
    print("\nPrograma encerrado.")
    print("\n===== RELATÓRIO FINAL =====")

    for nome, dados in relatorio.items():
        minutos = dados["tempo_total"] / 60

        print(f"\nColaborador: {nome}")
        print(f"Tempo total na sala: {minutos:.2f} minutos")
        print(f"Entradas autorizadas: {dados['entradas']}")
        print(f"Tentativas negadas: {dados['tentativas_negadas']}")

    print(f"\nTentativas de invasão: {tentativas_invasao}")

    criar_relatorio_csv()
    print("\nArquivo relatorio_acessos.csv criado com sucesso.")

finally:
    desligar_tudo()
    GPIO.cleanup()