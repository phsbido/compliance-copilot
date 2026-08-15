"""
Configurações centrais do protótipo.

Camada: transversal — usada pela Camada 2 (Núcleo de Raciocínio) e por
qualquer outra camada que precise saber qual provedor de LLM está ativo.

Decisão de projeto (ver docs/decisoes_arquitetura.md): as configurações são
lidas de variáveis de ambiente (.env), não hardcoded, para permitir trocar de
modelo/provedor sem alterar código-fonte.
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1")
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")


settings = Settings()
