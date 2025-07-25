import threading
import time
import random
import serial
from PyQt5.QtMultimedia import QSoundEffect
from PyQt5.QtCore import QUrl
from .settings import SOUND_PATH

class SerialController:
    def __init__(self, porta, baud_rate, comunicador, logger):
        self.porta = porta
        self.baud_rate = baud_rate
        self.comunicador = comunicador
        self.logger = logger
        self.serial_conn = None
        self.thread_rodando = False

    def conectar(self):
        self.serial_conn = serial.Serial(port=self.porta, baudrate=self.baud_rate, timeout=1)
        self.thread_rodando = True
        thread = threading.Thread(target=self.ler_dados_serial)
        thread.start()

    def desconectar(self):
        self.thread_rodando = False
        if self.serial_conn:
            self.serial_conn.close()

    def ler_dados_serial(self):
        while self.thread_rodando and self.serial_conn.is_open:
            try:
                linha = self.serial_conn.readline().decode('ascii').strip()
                if linha:
                    try:
                        valor = float(linha)
                        self.comunicador.atualizar_valor.emit(valor)
                    except ValueError:
                        self.logger.warning(f"Dado inválido recebido: {linha}")
            except Exception as e:
                self.logger.error(f"Erro na leitura serial: {str(e)}")
                time.sleep(1)

class SimuladorController:
    def __init__(self, comunicador, intervalo):
        self.comunicador = comunicador
        self.intervalo = intervalo
        self.thread_rodando = False

    def iniciar(self):
        self.thread_rodando = True
        thread = threading.Thread(target=self.ler_dados_simulados)
        thread.start()

    def parar(self):
        self.thread_rodando = False

    def ler_dados_simulados(self):
        while self.thread_rodando:
            valor = round(random.uniform(5.0, 25.0), 2)
            valores_simulados = [random.uniform(0, 1400) for _ in range(4)]  # Simula 4 canais
            self.comunicador.atualizar_canais.emit(valores_simulados)
            time.sleep(self.intervalo)

def configurar_alerta_sonoro():
    alerta_sonoro = QSoundEffect()
    alerta_sonoro.setSource(QUrl.fromLocalFile(SOUND_PATH))
    return alerta_sonoro

def ler_key(self):
    """Implementação real para ler a key do dispositivo"""
    self.serial.write(b'READ_KEY\n')  # Comando específico do seu hardware
    response = self.serial.readline().decode().strip()
    return response

def gravar_key(self, new_key):
    """Implementação real para gravar nova key"""
    command = f"WRITE_KEY {new_key}\n".encode()
    self.serial.write(command)
    response = self.serial.readline().decode().strip()
    if response != "OK":
        raise ValueError("Falha ao gravar key")