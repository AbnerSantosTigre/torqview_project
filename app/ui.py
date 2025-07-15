from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QComboBox, QLCDNumber, QFrame, QFileDialog, QStackedLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QSpinBox, QDialog, QGroupBox, QRadioButton, QTabWidget, QLineEdit, QGraphicsOpacityEffect,
    QDateTimeEdit, QSplitter
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap, QFont
from datetime import datetime
import random

import pyqtgraph as pg
from pyqtgraph import PlotWidget

from .widgets import BotaoArredondado
from .logger import configurar_logs
from .auth import verificar_admin
from .controller import SerialController, SimuladorController, configurar_alerta_sonoro
from .pdf import gerar_pdf
from .settings import *
from .database import init_db, salvar_leitura, buscar_leituras, buscar_leituras_por_data

class Comunicador(QObject):
    atualizar_valor = pyqtSignal(float)

class TorqView(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TorqView - Leitor de Torquímetro")
        self.setGeometry(100, 100, 1200, 800)
        self.setFont(QFont("Segoe UI", 12))

        self.logger = configurar_logs()
        self.comunicador = Comunicador()
        self.comunicador.atualizar_valor.connect(self.atualizar_valor)

        self.conexao_serial_ativa = False
        self.thread_rodando = False
        self.intervalo_leitura = 1.0
        self.dados_coletados = []
        self.dados_eixo_x = []
        self.dados_eixo_y = []
        self.limite_registros = 10
        self.modo_admin = False

        self.alerta_sonoro = configurar_alerta_sonoro()
        self.serial_controller = None

        self.iniciar_interface()
        self.configurar_estilos()

        self.criar_tela_filtros()

        init_db()

        self.picos_registrados = []  # Lista para armazenar os picos (valor, porta, sentido, tempo)
        self.limite_picos = 25  # Limite de registros na tabela

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
        if QPixmap("logo.png").isNull():
            print("AVISO: logo.png não encontrado ou inválido!")
        else:
            logo.setPixmap(QPixmap("logo.png").scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo.setGraphicsEffect(QGraphicsOpacityEffect())
        logo.graphicsEffect().setOpacity(0.2)

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

    def conectar_serial(self):
        porta = self.seletor_porta.currentText()
        if porta == "Simulado":
            self.simulador = SimuladorController(self.comunicador, self.intervalo_leitura)
            self.simulador.iniciar()
        else:
            self.serial_controller = SerialController(porta, 9600, self.comunicador, self.logger)
            try:
                self.serial_controller.conectar()
                self.rotulo_status.setText(f"Conectado - {porta}")
            except Exception as e:
                QMessageBox.critical(self, "Erro", str(e))

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

    def atualizar_valor(self, valor):
        # Atualiza o display LCD
        self.display_lcd.display(valor)
        
        # Salva a leitura no banco de dados
        salvar_leitura(valor, self.seletor_porta.currentText())
        
        # Atualiza os dados do gráfico
        self.dados_eixo_y.append(valor)
        self.dados_eixo_x.append(len(self.dados_eixo_y) * self.intervalo_leitura)
        
        # --- TRAVA O EIXO X PARA MOSTRAR TODAS AS LEITURAS ---
        # Define o limite mínimo e máximo do eixo X
        x_min = 0  # Começa em 0
        x_max = len(self.dados_eixo_y) * self.intervalo_leitura  # Até a última leitura
        
        # Atualiza a curva do gráfico com todos os dados (não apenas os últimos 100 pontos)
        self.curva.setData(self.dados_eixo_x, self.dados_eixo_y)
        
        # Trava o eixo X para mostrar todo o intervalo
        self.grafico.setXRange(x_min, x_max, padding=0.1)  # padding=0.1 adiciona 10% de margem
        
        # Auto-ajuste do eixo Y (opcional)
        if len(self.dados_eixo_y) > 0:
            margem = 0.1  # 10% de margem
            valor_min = min(self.dados_eixo_y) * (1 - margem)
            valor_max = max(self.dados_eixo_y) * (1 + margem)
            self.grafico.setYRange(valor_min, valor_max)
        
        # Verifica se deve disparar alerta (opcional)
        if hasattr(self, 'limite_alerta') and valor > self.limite_alerta:
            if self.alerta_sonoro:
                self.alerta_sonoro.play()

        # Registra picos (apenas valores maiores que o último pico registrado)
        if not self.picos_registrados or valor > self.picos_registrados[-1][0]:
            tempo_atual = datetime.now().strftime("%M:%S")  # Formato minuto:segundo
            sentido = "Horário" if valor >= 0 else "Anti-horário"  # Define o sentido
            novo_pico = (valor, self.seletor_porta.currentText(), sentido, tempo_atual)
            
            self.picos_registrados.append(novo_pico)
            self.picos_registrados.sort(reverse=True, key=lambda x: x[0])  # Ordena por pico (Nm)
            
            # Mantém apenas os 25 maiores picos
            if len(self.picos_registrados) > self.limite_picos:
                self.picos_registrados = self.picos_registrados[:self.limite_picos]
            
            self.atualizar_tabela_picos()  # Atualiza a tabela

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
        dialog = QDialog(self)
        dialog.setWindowTitle("Configura\u00e7\u00f5es")
        dialog.setFixedSize(400, 300)

        tabs = QTabWidget()

        aba_admin = QWidget()
        layout_admin = QVBoxLayout()
        self.campo_senha = QLineEdit()
        self.campo_senha.setEchoMode(QLineEdit.Password)
        botao_login = QPushButton("Acessar como Admin")
        botao_login.clicked.connect(self.verificar_admin)
        layout_admin.addWidget(QLabel("Senha Admin:"))
        layout_admin.addWidget(self.campo_senha)
        layout_admin.addWidget(botao_login)
        aba_admin.setLayout(layout_admin)

        tabs.addTab(aba_admin, "Admin")

        layout_dialog = QVBoxLayout()
        layout_dialog.addWidget(tabs)
        dialog.setLayout(layout_dialog)
        dialog.exec_()

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

    def closeEvent(self, event):
        self.thread_rodando = False
        if hasattr(self, 'serial_controller')and self.serial_controller is not None:
            try:
                self.self_controller.desconcetar()
            except Exception as e:
                print(f"AVISO: Falha ao desconectar serial: {e}")
        if hasattr(self, 'simulador')and self.simulador is not None:
            self.simulador.parar()
        event.accept()
