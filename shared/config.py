
import os
from pathlib import Path

from dotenv import load_dotenv


# Directorio raíz de AI Software Factory
BASE_DIR = Path(__file__).resolve().parents[1]

# Cargar variables desde el archivo .env
load_dotenv(BASE_DIR / ".env")

# Modelo de IA
MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b"
)
