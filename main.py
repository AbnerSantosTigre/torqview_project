import sys
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtGui import QFont

def main():
    try:
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        
        fonte = QFont()
        fonte.setPointSize(12)
        app.setFont(fonte)
        
        from app.ui import TorqView
        janela = TorqView()
        janela.show()
        sys.exit(app.exec_())
    except Exception as e:
        QMessageBox.critical(None, "Erro", f"Não foi possível iniciar o aplicativo:\n{str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()