"""
Ponto de entrada da interface web — Camada 1 (Interação), ao lado da CLI.

Uso:
    python main_web.py                  # abre http://127.0.0.1:8000 no navegador
    python main_web.py --porta 8080
    python main_web.py --sem-navegador
"""
import argparse

from src.layer1_interaction.web import main

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interface web do copiloto de compliance.")
    parser.add_argument("--porta", type=int, default=8000, help="porta local (padrão: 8000)")
    parser.add_argument("--sem-navegador", action="store_true", help="não abre o navegador automaticamente")
    args = parser.parse_args()
    main(porta=args.porta, abrir_navegador=not args.sem_navegador)
