import threading
import time
import random
import struct
from PyQt5.QtMultimedia import QSoundEffect
from PyQt5.QtCore import QUrl
from pymodbus.client import ModbusSerialClient
from app.settings import SOUND_PATH

class ModbusController:
    def __init__(self, porta, baud_rate, comunicador, logger):
        self.porta = porta
        self.baud_rate = baud_rate
        self.comunicador = comunicador
        self.logger = logger
        self.client = None
        self.thread_rodando = False

        self.slave_id = 1
        self.registros = {
            'torque' : 0x0606,
            'pico' : 0x0608,
            'vale' : 0x060A,
            'calibracao' : 0x0FB8
        }

    def conectar(self):
        """Estabelece conexão Modbus RTU"""
        try:
            self.client = ModbusSerialClient(
                port = self.porta,
                baudrate = self.baud_rate,
                parity = 'N',
                stopbits = 1,
                timeout = 1,
            )
            if not self.client.connect():
                raise Exception("Falha ao conectar o dispositivo")
            
            self.thread_rodando = True
            thread = threading.Thread(target=self.ler_dados_modbus, daemon=True)
            thread.start()

        except Exception as e:
            self.logger.error(f"Erro na conexão: {str(e)}")
            raise

    def desconectar(self):
        """Encerra a conexão Modbus"""
        self.thread_rodando = False
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                self.logger.error(f"Erro ao desconectar: {str(e)}")

    def ler_dados_modbus(self):
        while self.thread_rodando:
            try:
                if not self.client.connected:
                    self.client.connect()
                    
                response = self.client.read_holding_registers(
                    address=self.registros['torque'],
                    count=2,
                    slave=self.slave_id
                )
                
                if response.isError():
                    self.logger.error(f"Erro Modbus: {response}")
                    time.sleep(1)
                    continue
                    
                torque = struct.unpack('>f', struct.pack('>HH', *response.registers))[0]
                self.comunicador.atualizar_canais.emit([torque, 0, 0, 0])
                
            except Exception as e:
                self.logger.error(f"Erro na leitura: {str(e)}")
            finally:
                time.sleep(1)

    def ler_key(self):
        """Lê a chave do dispositivo via Modbus"""
        try:
            # Lê 8 registros (16 caracteres ASCII)
            response = self.client.read_holding_registers(
                address=self.registros['calibracao'],
                count=8,
                slave=self.slave_id
            )
            
            if response.isError():
                raise Exception("Erro na leitura da chave")
                
            # Converte registros para string ASCII
            key_bytes = b''.join([reg.to_bytes(2, 'big') for reg in response.registers])
            return key_bytes.decode('ascii').strip('\x00')
            
        except Exception as e:
            self.logger.error(f"Erro ao ler chave: {str(e)}")
            raise

    def gravar_key(self, new_key):
        """Grava nova chave no dispositivo via Modbus"""
        try:
            # Converte a string para bytes (16 caracteres máximo)
            if len(new_key) > 16:
                raise ValueError("Chave deve ter no máximo 16 caracteres")
                
            key_bytes = new_key.ljust(16).encode('ascii')
            
            # Divide em 8 registros de 16 bits
            registers = [
                int.from_bytes(key_bytes[i:i+2], 'big')
                for i in range(0, 16, 2)
            ]
            
            # Escreve nos registros
            response = self.client.write_registers(
                address=self.registros['calibracao'],
                values=registers,
                slave=self.slave_id
            )
            
            if response.isError():
                raise Exception("Erro ao gravar chave")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao gravar chave: {str(e)}")
            raise

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