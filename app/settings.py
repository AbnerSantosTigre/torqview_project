from pathlib import Path

# Configuração de caminhos
BASE_DIR = Path(__file__).resolve().parent.parent
SOUND_PATH = str(BASE_DIR / "resources" / "sounds" / "alert.wav")
LOG_FILE = BASE_DIR / "logs" / "torqview.log"
PDF_DIR = BASE_DIR.parent / "PDF"
DB_PATH = BASE_DIR / "db" / "torqview.db"
SENHA_ADMIN = 'admin123'