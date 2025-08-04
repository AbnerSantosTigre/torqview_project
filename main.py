import sys
import traceback
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer

from app.settings import RESOURCES_DIR
if not RESOURCES_DIR.exists():
    RESOURCES_DIR.mkdir(parents=True)

from app.ui import TorqView

def excepthook(exctype, value, tb):
    """Captura exceções não tratadas e exibe em uma messagebox"""
    error_msg = ''.join(traceback.format_exception(exctype, value, tb))
    print(f"ERRO CRÍTICO: {error_msg}")
    
    # Cria uma QApplication se não existir
    if not QApplication.instance():
        app = QApplication(sys.argv)
    
    QMessageBox.critical(
        None,
        "Erro Fatal",
        f"Ocorreu um erro inesperado:\n\n{str(value)}\n\nDetalhes:\n{error_msg}"
    )
    sys.exit(1)

def main():
    # Configura handler global de exceções
    sys.excepthook = excepthook
    
    # Cria a aplicação
    app = QApplication(sys.argv)
    
    try:
        # Cria a janela principal
        window = TorqView()
        window.show()
        
        # Configura um timer para garantir inicialização
        QTimer.singleShot(100, lambda: None)
        
        # Executa o loop de eventos
        ret = app.exec_()
        
        # Encerramento limpo
        if hasattr(window, 'close'):
            window.close()
        
        sys.exit(ret)
        
    except Exception as e:
        excepthook(type(e), e, e.__traceback__)

if __name__ == "__main__":
    main()