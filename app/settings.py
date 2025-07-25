import os
from pathlib import Path
from hashlib import sha256
from dotenv import load_dotenv  # Nova importação

# Carrega variáveis do .env antes de qualquer acesso
load_dotenv()

# Configuração de caminhos
BASE_DIR = Path(__file__).resolve().parent.parent

# Diretórios de recursos
RESOURCES_DIR = BASE_DIR / "resources"
DB_DIR = BASE_DIR / "db"
LOGS_DIR = BASE_DIR / "logs"

# Cria os diretórios se não existirem
for directory in [RESOURCES_DIR, DB_DIR, LOGS_DIR]:
    directory.mkdir(exist_ok=True)

# Paths absolutos
SOUND_PATH = str(RESOURCES_DIR / "sounds" / "alert.wav")
LOG_FILE = LOGS_DIR / "torqview.log"
PDF_DIR = BASE_DIR.parent / "PDF"
DB_PATH = DB_DIR / "torqview.db"

# Configurações de segurança
def get_admin_hash():
    """Gera hash seguro da senha admin com salt."""
    salt = os.getenv("TORQVIEW_SALT", "default_salt_altere_em_producao")  # 👈 Salt no .env
    raw_pass = os.getenv("TORQVIEW_ADMIN_PASS")  # 👈 Obrigatório no .env
    
    if not raw_pass:
        raise ValueError("Variável TORQVIEW_ADMIN_PASS não configurada no .env!")
    
    return sha256((salt + raw_pass).encode()).hexdigest()

ADMIN_HASH = get_admin_hash()

# Configurações adicionais (opcional)
DEBUG_MODE = os.getenv("TORQVIEW_DEBUG", "False").lower() == "true"
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "3"))