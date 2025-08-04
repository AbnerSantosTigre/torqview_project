from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QComboBox, QLCDNumber, QFrame, QFileDialog, QStackedLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QSpinBox, QDialog, QGroupBox, QRadioButton, QTabWidget, QLineEdit, QGraphicsOpacityEffect,
    QDateTimeEdit, QSplitter, QCheckBox, QFormLayout, QDoubleSpinBox, QApplication, QMainWindow
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap, QFont
from datetime import datetime
import random

import pyqtgraph as pg
from pyqtgraph import PlotWidget

from .widgets import BotaoArredondado
from app.logger import configurar_logs
from app.controller import ModbusController,  SimuladorController, configurar_alerta_sonoro
from ..pdf import gerar_pdf
from ..settings import *
from ..database import init_db, salvar_leitura, buscar_leituras, buscar_leituras_por_data

class Comunicador(QObject):
    atualizar_canais = pyqtSignal(list)  # Sinal para atualizar múltiplos canais

class TorqView(QWidget):
    def __init__(self):
        super().__init__()
        self.inicializar_recursos()
        self.setWindowTitle("TorqView - Leitor de Torquímetro")
        self.setGeometry(100, 100, 1200, 800)
        self.setFont(QFont("Segoe UI", 12))

        self.logger = configurar_logs()
        self.comunicador = Comunicador()
        self.comunicador.atualizar_canais.connect(self.atualizar_canais)

        self.conexao_serial_ativa = False
        self.thread_rodando = False
        self.intervalo_leitura = 1.0
        self.dados_coletados = []
        self.dados_eixo_x = []
        self.dados_eixo_y = []
        self.limite_registros = 10
        self.modo_admin = False
        self.dados_canais = {1: [], 2: [], 3: [], 4: []}
        self.picos_canais = {1: None, 2: None, 3: None, 4: None}
        self.limites = {1: 1400, 2: 140, 3: 14, 4: 4}

        self.alerta_sonoro = configurar_alerta_sonoro()
        self.serial_controller = None

        self.iniciar_interface()
        self.configurar_estilos()

        self.criar_tela_filtros()

        init_db()

        self.picos_registrados = []  # Lista para armazenar os picos (valor, porta, sentido, tempo)
        self.limite_picos = 25  # Limite de registros na tabela

        self.current_key = "Não lida"  # Armazena a key atual
        self.new_key = ""  # Armazena a nova key para gravação

        self._timers = []  # Para armazenar referências a timers
        self._shutting_down = False  # Flag de encerramento

    def __del__(self):
        if not self._shutting_down:
            self.close()

    def iniciar_interface(self):
        self.pilha_telas = QStackedLayout()
        self.criar_tela_inicial()
        self.criar_tela_monitoramento()
        self.setLayout(self.pilha_telas)

    def configurar_estilos(self):
        self.setStyleSheet("""
            QWidget { background-color: #1e1e1e; color: white; font-size: 14px; }
            QPushButton.primary_button {
                background-color: #d32f2f; color: white;
                padding: 10px 20px; border-radius: 6px;
                font-weight: bold; min-width: 120px; font-size: 20px;
            }
            QPushButton.primary_button:hover { background-color: #ff4c4c; }
            QLCDNumber { background-color: #212121; color: #d32f2f; }
            QTableWidget { background-color: #333; border-radius: 8px; }
            QHeaderView::section { background-color: #d32f2f; }
            QWidget#graph_widget { background-color: #252525; border-radius: 8px; }
            QLabel.stat_card {
                font-size: 20px; background-color: #333;
                padding: 10px 20px; border-radius: 8px;
            }
            QDateTimeEdit {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
            }
            pg.setConfigOption('background', '#1e1e1e')
            pg.setConfigOption('foreground', 'white')
        """)

    def criar_tela_inicial(self):
        pagina = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        titulo = QLabel("\u2699\ufe0f TorqView")
        titulo.setStyleSheet("font-size: 32px; font-weight: bold; color: #d32f2f;")

        logo = QLabel()
        try:
            # Tenta vários caminhos possíveis
            logo_paths = [
                "resources/images/logo.png",
                "logo.png",
                os.path.join(os.path.dirname(__file__), "..", "resources", "images", "logo.png")
            ]
            
            logo_encontrado = False
            for path in logo_paths:
                if os.path.exists(path) and not QPixmap(path).isNull():
                    logo.setPixmap(QPixmap(path).scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    logo_encontrado = True
                    break
            
            if not logo_encontrado:
                # Cria um placeholder gráfico profissional
                logo.setText("TORQVIEW")
                logo.setStyleSheet("""
                    font-size: 16px;
                    font-weight: bold;
                    color: white;
                    background-color: #d32f2f;
                    border-radius: 10px;
                    padding: 15px;
                    qproperty-alignment: AlignCenter;
                """)
                logo.setFixedSize(120, 100)
        except Exception as e:
            print(f"AVISO: Erro ao carregar logo: {str(e)}")
            # Fallback extremo
            logo.setText("LOGO")
            logo.setMinimumSize(100, 100)

        cabecalho = QHBoxLayout()
        cabecalho.addWidget(titulo)
        cabecalho.addStretch()
        cabecalho.addWidget(logo)

        botoes = QVBoxLayout()
        self.botao_monitoramento = BotaoArredondado("Monitoramento")
        self.botao_configuracoes = BotaoArredondado("Configura\u00e7\u00f5es")
        botoes.addWidget(self.botao_monitoramento)
        botoes.addWidget(self.botao_configuracoes)

        self.botao_monitoramento.clicked.connect(lambda: self.pilha_telas.setCurrentIndex(1))
        self.botao_configuracoes.clicked.connect(self.abrir_configuracoes_gerais)

        layout.addLayout(cabecalho)
        layout.addLayout(botoes)
        pagina.setLayout(layout)
        self.pilha_telas.addWidget(pagina)

        botao_filtrar = QPushButton("Filtrar Leituras")
        botao_filtrar.clicked.connect(lambda: self.pilha_telas.setCurrentIndex(2))
        layout.addWidget(botao_filtrar)

    def configurar_alerta_sonoro():
        try:
            from PyQt5.QtMultimedia import QSoundEffect
            from PyQt5.QtCore import QUrl
            import os
            
            # Caminhos possíveis para o arquivo de som
            possible_paths = [
                os.path.join("resources", "sounds", "alert.wav"),
                os.path.join("sounds", "alert.wav"),
                "alert.wav",
                os.path.join(os.path.dirname(__file__), "..", "resources", "sounds", "alert.wav")
            ]
            
            effect = QSoundEffect()
            
            for path in possible_paths:
                if os.path.exists(path):
                    absolute_path = os.path.abspath(path)
                    print(f"Carregando som de alerta de: {absolute_path}")
                    effect.setSource(QUrl.fromLocalFile(absolute_path))
                    effect.setVolume(0.5)  # Volume moderado
                    return effect
            
            print("AVISO: Arquivo alert.wav não encontrado em:")
            print("\n".join([os.path.abspath(p) for p in possible_paths]))
            return None
        
        except Exception as e:
            print(f"AVISO: Erro ao configurar alerta sonoro - {str(e)}")
            return None
        
    def inicializar_recursos(self):
        """Garante que todos os recursos necessários existam"""
        import os
        from urllib.request import urlretrieve
        
        # Criar estrutura de diretórios
        os.makedirs("resources/images", exist_ok=True)
        os.makedirs("resources/sounds", exist_ok=True)
        
        # URLs de recursos padrão
        recursos = {
            "logo.png": "https://via.placeholder.com/200x100.png?text=TORQVIEW",
            "alert.wav": "https://www.soundjay.com/buttons/sounds/button-09.wav"
        }
        
        # Verificar e baixar recursos faltantes
        for arquivo, url in recursos.items():
            path = os.path.join("resources", "images" if arquivo.endswith(".png") else "sounds", arquivo)
            if not os.path.exists(path):
                try:
                    print(f"Baixando recurso padrão: {arquivo}")
                    urlretrieve(url, path)
                except Exception as e:
                    print(f"AVISO: Não foi possível baixar {arquivo}: {str(e)}")

    def criar_aba_key(self):
        aba = QWidget()
        layout = QVBoxLayout()

        # Grupo de leitrua da Key
        grupo_leitura = QGroupBox("Identificação do Dispositivo")
        layout_leitura = QFormLayout()

        self.label_key_atual = QLabel("Key Atual: Não lida")
        self.line_edit_nova_key = QLineEdit()
        self.line_edit_nova_key.setPlaceholderText("Insira a nova Key")

        btn_ler_key = QPushButton("Ler Key")
        btn_ler_key.clicked.connect(self.ler_key_dispositivo)

        btn_gravar_key = QPushButton("Gravar Noa Key")
        btn_gravar_key.clicked.connect(self.gravar_nova_key)

        layout_leitura.addRow(self.label_key_atual)
        layout_leitura.addRow("NOva Key:", self.line_edit_nova_key)
        layout_leitura.addRow(btn_ler_key)
        layout_leitura.addRow(btn_gravar_key)
        grupo_leitura.setLayout(layout_leitura)

        # Grupo de informações
        grupo_info = QGroupBox("Informações da Key")
        layout_info = QVBoxLayout()
        self.label_info_key = QLabel(
            "Formaro esperado: XXXX_XXXX_XXXX_XXXX\n"
            "Exemplo: 38F6_0156_3053_13C4"
        )
        self.label_info_key.setWordWrap(True)
        layout_info.addWidget(self.label_info_key)
        grupo_info.setLayout(layout_info)

        layout.addWidget(grupo_leitura)
        layout.addWidget(grupo_info)
        aba.setLayout(layout)

        return aba
    
    def ler_key_dispositivo(self):
        """Simula a leitura da key do dispositivo"""
        try:
            # Simulação - na prática, você faria a leitura serial aqui
            if self.conexao_serial_ativa and hasattr(self, 'serial_controller'):
                # Se estiver usando comunicação serial real:
                # self.current_key = self.serial_controller.ler_key()
                
                # Modo simulado:
                self.current_key = "38F6_0156_3053_13C4"  # Exemplo fixo
                self.label_key_atual.setText(f"Key Atual: {self.current_key}")
                QMessageBox.information(self, "Sucesso", "Key lida com sucesso!")
            else:
                QMessageBox.warning(self, "Aviso", "Conecte-se ao dispositivo primeiro")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao ler key:\n{str(e)}")

    def gravar_nova_key(self):
        """Grava uma nova key no dispositivo"""
        nova_key = self.line_edit_nova_key.text().strip()
        
        if not nova_key:
            QMessageBox.warning(self, "Aviso", "Insira uma nova key antes de gravar")
            return
        
        try:
            # Validação básica do formato (ajuste conforme seu padrão)
            if len(nova_key) != 19 or nova_key.count('_') != 3:
                raise ValueError("Formato inválido. Use XXXX_XXXX_XXXX_XXXX")
            
            if self.conexao_serial_ativa and hasattr(self, 'serial_controller'):
                # Se estiver usando comunicação serial real:
                # self.serial_controller.gravar_key(nova_key)
                
                # Modo simulado:
                self.current_key = nova_key
                self.label_key_atual.setText(f"Key Atual: {self.current_key}")
                QMessageBox.information(self, "Sucesso", "Nova key gravada com sucesso!")
            else:
                QMessageBox.warning(self, "Aviso", "Conecte-se ao dispositivo primeiro")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao gravar key:\n{str(e)}")

    def criar_tela_monitoramento(self):
        pagina = QWidget()
        layout_principal = QVBoxLayout()
        
        # Cria o gráfico
        self.grafico = PlotWidget()
        self.grafico.setBackground('#252525')
        self.grafico.showGrid(x=True, y=True, alpha=0.3)
        self.grafico.setLabel('left', 'Torque (Nm)')
        self.grafico.setLabel('bottom', 'Tempo (segundos)')
        self.curva = self.grafico.plot(pen=pg.mkPen(color='#d32f2f', width=2))
        
        # Container para os controles (LCD, botões, etc.)
        container_controles = QWidget()
        layout_controles = QVBoxLayout()
        
        # LCD Display
        self.display_lcd = QLCDNumber()
        self.display_lcd.setDigitCount(6)
        self.display_lcd.display(0.00)
        
        # Status e conexão
        self.rotulo_status = QLabel("Status: Aguardando conex\u00e3o...")
        
        # Botões de conexão
        self.botao_conectar = QPushButton("Conectar")
        self.botao_conectar.setObjectName("primary_button")
        self.botao_conectar.clicked.connect(self.conectar_serial)
        
        self.botao_desconectar = QPushButton("Desconectar")
        self.botao_desconectar.setObjectName("primary_button")
        self.botao_desconectar.setEnabled(False)
        self.botao_desconectar.clicked.connect(self.desconectar_serial)
        
        self.seletor_porta = QComboBox()
        self.seletor_porta.addItems(["COM1", "COM2", "COM3", "COM4", "Simulado"])
        
        # Layout dos botões de conexão
        layout_conexao = QHBoxLayout()
        layout_conexao.addWidget(self.botao_conectar)
        layout_conexao.addWidget(self.botao_desconectar)
        layout_conexao.addWidget(self.seletor_porta)
        
        # Botão de PDF
        self.botao_pdf = QPushButton("Gerar PDF")
        self.botao_pdf.clicked.connect(self.salvar_pdf)
        
        # Adiciona todos os controles ao layout
        layout_controles.addWidget(self.display_lcd)
        layout_controles.addWidget(self.rotulo_status)
        layout_controles.addLayout(layout_conexao)
        layout_controles.addWidget(self.botao_pdf)
        container_controles.setLayout(layout_controles)
        
        # Divide a tela entre gráfico e controles
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.grafico)
        splitter.addWidget(container_controles)
        splitter.setSizes([500, 300])  # Ajuste estas proporções conforme necessário
        
        layout_principal.addWidget(splitter)
        pagina.setLayout(layout_principal)
        self.pilha_telas.addWidget(pagina)
        
        # Inicializa as listas de dados do gráfico
        self.dados_eixo_x = []
        self.dados_eixo_y = []

        # Cria a tabela de picos (abaixo do gráfico)
        self.tabela_picos = QTableWidget()
        self.tabela_picos.setColumnCount(4)
        self.tabela_picos.setHorizontalHeaderLabels(["Pico (Nm)", "Porta", "Sentido", "Tempo"])
        self.tabela_picos.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabela_picos.setMaximumHeight(200)  # Altura fixa para não ocupar muito espaço

        # Adiciona a tabela ao layout principal (antes do container_controles)
        layout_principal.addWidget(self.tabela_picos)
        layout_principal.addWidget(container_controles)  # Mantém os controles abaixo

        layout_canais = QHBoxLayout()
        self.displays = {
            1: QLCDNumber(),
            2: QLCDNumber(),
            3: QLCDNumber(),
            4: QLCDNumber()
        }
        for canal, display in self.displays.items():
            display.setDigitCount(6)
            display.display(0.00)
            layout_canais.addWidget(QLabel(f"Canal {canal}"))
            layout_canais.addWidget(display)

        layout_controles.addLayout(layout_canais)

         # Crie um QTabWidget para organizar as abas
        tabs = QTabWidget()
        
        # Aba de monitoramento principal
        tab_monitor = QWidget()
        layout_monitor = QVBoxLayout()
        # ... (adicione os widgets de monitoramento aqui)
        tab_monitor.setLayout(layout_monitor)
        
        # Aba de Key
        tab_key = self.criar_aba_key()
        
        # Adicione as abas
        tabs.addTab(tab_monitor, "Monitoramento")
        tabs.addTab(tab_key, "Identificação")
        
        # Adicione o QTabWidget ao layout principal
        layout_principal.addWidget(tabs)

    def conectar_serial(self):
        porta = self.seletor_porta.currentText()
        if porta == "Simulado":
            self.simulador = SimuladorController(self.comunicador, self.intervalo_leitura)
            self.simulador.iniciar()
        else:
            self.serial_controller = ModbusController(
                porta = porta,
                baud_rate = 19200,
                comunicador = self.comunicador,
                logger = self.logger
            )
            try:
                self.serial_controller.conectar()
                self.rotulo_status.setText(f"Conectado - {porta}")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha na conexão Modbus:\n{str(e)}")
                return

        self.botao_conectar.setEnabled(False)
        self.botao_desconectar.setEnabled(True)
        self.conexao_serial_ativa = True

    def desconectar_serial(self):
        if hasattr(self, 'serial_controller') and self.serial_controller:
            self.serial_controller.desconectar()
        if hasattr(self, 'simulador') and self.simulador:
            self.simulador.parar()
        self.botao_conectar.setEnabled(True)
        self.botao_desconectar.setEnabled(False)
        self.rotulo_status.setText("Status: Desconectado")
        self.conexao_serial_ativa = False

    def atualizar_canais(self, valores):
        """Atualiza os valores dos 4 canais."""
        for canal, valor in enumerate(valores, start=1):
            if canal in self.displays:
                self.displays[canal].display(valor)
            
            # Salva no banco de dados
            salvar_leitura(valor, f"Canal {canal}")
            
            # Atualiza dados do gráfico (usando Canal 1 como principal)
            if canal == 1:
                self.dados_eixo_y.append(valor)
                self.dados_eixo_x.append(len(self.dados_eixo_y) * self.intervalo_leitura)
                self.curva.setData(self.dados_eixo_x, self.dados_eixo_y)
                
                # Auto-ajuste dos eixos
                if len(self.dados_eixo_y) > 0:
                    self.grafico.setXRange(0, len(self.dados_eixo_y) * self.intervalo_leitura, padding=0.1)
                    margem = 0.1
                    valor_min = min(self.dados_eixo_y) * (1 - margem)
                    valor_max = max(self.dados_eixo_y) * (1 + margem)
                    self.grafico.setYRange(valor_min, valor_max)

            # Detecção de picos por canal
            if self.picos_canais[canal] is None or valor > self.picos_canais[canal]:
                self.picos_canais[canal] = valor
                tempo_atual = datetime.now().strftime("%M:%S")
                sentido = "Horário" if valor >= 0 else "Anti-horário"
                novo_pico = (valor, f"Canal {canal}", sentido, tempo_atual)
                
                self.picos_registrados.append(novo_pico)
                self.picos_registrados.sort(reverse=True, key=lambda x: x[0])
                
                if len(self.picos_registrados) > self.limite_picos:
                    self.picos_registrados = self.picos_registrados[:self.limite_picos]
                
                self.atualizar_tabela_picos()

    def criar_aba_controles(self):
        aba = QWidget()
        layout = QVBoxLayout()

        # Seção Pico
        grupo_pico = QGroupBox("Configuração de Picos")
        layout_pico = QVBoxLayout()
        self.checkbox_pico = QCheckBox("Habilitar Detecção de Picos")
        self.label_ultimo_pico = QLabel("Último Pico: -- Nm")
        layout_pico.addWidget(self.checkbox_pico)
        layout_pico.addWidget(self.label_ultimo_pico)
        grupo_pico.setLayout(layout_pico)

        # Seção Key
        grupo_key = QGroupBox("Identificação de Dispositivo")
        layout_key = QVBoxLayout()
        self.label_key = QLabel("Key: Não lida")
        self.botao_ler_key = QPushButton("Ler Key")
        layout_key.addWidget(self.label_key)
        layout_key.addWidget(self.botao_ler_key)
        grupo_key.setLayout(layout_key)

        layout.addWidget(grupo_pico)
        layout.addWidget(grupo_key)
        aba.setLayout(layout)
        return aba

    def salvar_pdf(self):
        if not buscar_leituras():
            QMessageBox.warning(self, "Aviso", "Nenhum dado para gerar PDF.")
            return

        caminho, _ = QFileDialog.getSaveFileName(self, "Salvar PDF", "", "PDF Files (*.pdf)")
        if caminho:
            # Busca os picos do banco em vez de usar valores aleatórios
            picos_db = buscar_leituras(limite=5)  # Pega os 5 maiores picos
            picos_formatados = [
                [f"{valor:.2f}", porta, "Horário", timestamp]
                for valor, porta, timestamp in picos_db
            ]
            
            gerar_pdf(
                caminho, 
                self, 
                [leitura[0] for leitura in buscar_leituras(limite=100)],  # Últimas 100 leituras
                self.seletor_porta.currentText(), 
                self.intervalo_leitura, 
                picos_formatados  # Usa os picos reais
            )

    def criar_tela_filtros(self):
        pagina = QWidget()
        layout = QVBoxLayout()
        
        # Widgets para seleção de data
        grupo_data = QGroupBox("Filtrar por Data")
        layout_data = QHBoxLayout()
        
        self.data_inicio = QDateTimeEdit()
        self.data_inicio.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.data_inicio.setDateTime(self.data_inicio.minimumDateTime())
        
        self.data_fim = QDateTimeEdit()
        self.data_fim.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.data_fim.setDateTime(self.data_fim.maximumDateTime())
        
        layout_data.addWidget(QLabel("De:"))
        layout_data.addWidget(self.data_inicio)
        layout_data.addWidget(QLabel("Até:"))
        layout_data.addWidget(self.data_fim)
        grupo_data.setLayout(layout_data)
        
        # Botão de busca
        botao_buscar = QPushButton("Buscar Leituras")
        botao_buscar.setStyleSheet("background-color: #4CAF50; color: white;")
        botao_buscar.clicked.connect(self.buscar_leituras_filtradas)
        
        # Tabela de resultados
        self.tabela_resultados = QTableWidget()
        self.tabela_resultados.setColumnCount(3)
        self.tabela_resultados.setHorizontalHeaderLabels(["Valor", "Porta", "Data/Hora"])
        self.tabela_resultados.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Layout principal
        layout.addWidget(grupo_data)
        layout.addWidget(botao_buscar)
        layout.addWidget(self.tabela_resultados)
        pagina.setLayout(layout)
        
        self.pilha_telas.addWidget(pagina)  # Adiciona à pilha de telas

    def buscar_leituras_filtradas(self):
        # Obtém as datas selecionadas
        data_inicio = self.data_inicio.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        data_fim = self.data_fim.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        
        # Busca no banco de dados
        leituras = buscar_leituras_por_data(
            data_inicio=data_inicio,
            data_fim=data_fim,
            porta=self.seletor_porta.currentText() if self.seletor_porta.currentText() != "Simulado" else None
        )
        
        # Preenche a tabela
        self.tabela_resultados.setRowCount(len(leituras))
        for row, (valor, porta, timestamp) in enumerate(leituras):
            self.tabela_resultados.setItem(row, 0, QTableWidgetItem(f"{valor:.2f}"))
            self.tabela_resultados.setItem(row, 1, QTableWidgetItem(porta))
            self.tabela_resultados.setItem(row, 2, QTableWidgetItem(timestamp))

    def criar_tela_historico(self):
        pagina = QWidget()
        layout = QVBoxLayout()
        
        tabela = QTableWidget()
        tabela.setColumnCount(3)
        tabela.setHorizontalHeaderLabels(["Valor", "Porta", "Data/Hora"])
        tabela.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Busca as últimas 50 leituras
        leituras = buscar_leituras(limite=50)
        tabela.setRowCount(len(leituras))
        
        for row, (valor, porta, timestamp) in enumerate(leituras):
            tabela.setItem(row, 0, QTableWidgetItem(f"{valor:.2f}"))
            tabela.setItem(row, 1, QTableWidgetItem(porta))
            tabela.setItem(row, 2, QTableWidgetItem(timestamp))
        
        layout.addWidget(tabela)
        pagina.setLayout(layout)
        self.pilha_telas.addWidget(pagina)  # Adiciona à pilha de telas
    
    def abrir_configuracoes_gerais(self):
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Configurações Avançadas")
            dialog.setFixedSize(600, 400)
            
            # Layout principal
            main_layout = QVBoxLayout(dialog)
            
            # Abas
            tabs = QTabWidget()
            
            # Aba Conexão
            tab_conexao = QWidget()
            layout_conexao = QFormLayout(tab_conexao)
            
            self.combo_baud = QComboBox()
            self.combo_baud.addItems(["9600", "19200", "38400", "57600", "115200"])
            layout_conexao.addRow("Baud Rate:", self.combo_baud)
            
            # Aba Canais
            tab_canais = QWidget()
            layout_canais = QFormLayout(tab_canais)
            
            self.spinboxes_limites = {}
            for canal in range(1, 5):
                spinbox = QDoubleSpinBox()
                spinbox.setRange(0, 2000)
                spinbox.setValue(self.limites.get(canal, 0))
                self.spinboxes_limites[canal] = spinbox
                layout_canais.addRow(f"Limite Canal {canal} (Nm):", spinbox)
            
            tabs.addTab(tab_conexao, "Conexão")
            tabs.addTab(tab_canais, "Canais")
            main_layout.addWidget(tabs)
            
            # Botões de ação
            btn_layout = QHBoxLayout()
            btn_salvar = QPushButton("Salvar")
            btn_cancelar = QPushButton("Cancelar")
            
            # Conexão segura
            if hasattr(self, 'salvar_configuracoes'):
                btn_salvar.clicked.connect(lambda: self.salvar_configuracoes(dialog))
            else:
                btn_salvar.clicked.connect(dialog.accept)
            
            btn_cancelar.clicked.connect(dialog.reject)
            btn_layout.addWidget(btn_salvar)
            btn_layout.addWidget(btn_cancelar)
            main_layout.addLayout(btn_layout)
            
            dialog.exec_()
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao abrir configurações:\n{str(e)}")

    def salvar_configuracoes(self, dialog):
        """Salva as configurações alteradas na dialog"""
        try:
            # Salvar baud rate
            novo_baud = int(self.combo_baud.currentText())
            if hasattr(self, 'serial_controller') and self.serial_controller:
                self.serial_controller.baudrate = novo_baud
            
            # Salvar limites dos canais
            for canal, spinbox in self.spinboxes_limites.items():
                self.limites[canal] = spinbox.value()
            
            QMessageBox.information(self, "Sucesso", "Configurações salvas com sucesso!")
            dialog.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao salvar configurações:\n{str(e)}")

    def verificar_admin(self):
        if verificar_admin(self.campo_senha.text()):
            self.modo_admin = True
            QMessageBox.information(self, "Sucesso", "Modo Admin ativado!")
        else:
            QMessageBox.warning(self, "Erro", "Senha incorreta!")

    def atualizar_tabela_picos(self):
        self.tabela_picos.setRowCount(len(self.picos_registrados))
        for row, (valor, porta, sentido, tempo) in enumerate(self.picos_registrados):
            self.tabela_picos.setItem(row, 0, QTableWidgetItem(f"{valor:.2f}"))
            self.tabela_picos.setItem(row, 1, QTableWidgetItem(porta))
            self.tabela_picos.setItem(row, 2, QTableWidgetItem(sentido))
            self.tabela_picos.setItem(row, 3, QTableWidgetItem(tempo))

    def configurar_estilos(self):
        # ... (estilos existentes)
        self.setStyleSheet("""
            QTableWidget#tabela_picos {
                background-color: #333;
                border-radius: 8px;
            }
            QHeaderView::section {
                background-color: #d32f2f;
                padding: 5px;
            }
        """)
        self.tabela_picos.setObjectName("tabela_picos")  # Aplica o estilo

    def verificar_recursos(self):
        recursos_ok = True
        required = [
            "resources/images/logo.png",
            "resources/sounds/alert.wav"
        ]
        
        for recurso in required:
            if not os.path.exists(recurso):
                print(f"AVISO CRÍTICO: Recurso faltando - {recurso}")
                recursos_ok = False
        
        if not recursos_ok:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText("Alguns recursos estão faltando!")
            msg.setInformativeText("O aplicativo pode não funcionar completamente.")
            msg.exec_()
        
        return recursos_ok
    
    def verificar_admin(self, senha):
        """Verifica se a senha corresponde ao hash admin"""
        salt = os.getenv("TORQVIEW_SALT", "default_salt_altere_em_producao")
        input_hash = sha256((salt + senha).encode()).hexdigest()
        return input_hash == ADMIN_HASH

    def closeEvent(self, event):
        # Parar todas as threads primeiro
        self.thread_rodando = False
        
        # Desconectar serial de forma segura
        if hasattr(self, 'serial_controller') and self.serial_controller is not None:
            try:
                if hasattr(self.serial_controller, 'desconectar'):
                    self.serial_controller.desconectar()
                elif hasattr(self.serial_controller, 'close'):
                    self.serial_controller.close()
            except Exception as e:
                print(f"AVISO: Falha ao desconectar serial - {str(e)}")
        
        # Parar simulador
        if hasattr(self, 'simulador') and self.simulador is not None:
            try:
                self.simulador.parar()
            except Exception as e:
                print(f"AVISO: Falha ao parar simulador - {str(e)}")
        
        # Encerrar todos os timers
        for timer in getattr(self, '_timers', []):
            timer.stop()
        
        # Forçar processamento de eventos pendentes
        QApplication.processEvents()
        
        # Aceitar o evento de fechamento
        event.accept()
