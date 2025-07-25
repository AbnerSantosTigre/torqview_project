import sys
from PyQt5.QtWidgets import QApplication

from app.ui import TorqView

def main():
    
    app = QApplication(sys.argv)
    
    try:
        window = TorqView()
        window.show()
        
        # Conexão para garantir saída limpa
        app.aboutToQuit.connect(window.close)
        
        ret = app.exec_()
        
        # Limpeza pós-execution
        del window
        QApplication.processEvents()
        
        sys.exit(ret)
    except Exception as e:
        print(f"ERRO CRÍTICO: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()