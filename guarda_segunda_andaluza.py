import sys
import config
from guarda_aficionados_rfaf import ejecutar_lote

if __name__ == "__main__":
    try:
        ejecutar_lote(config.COMPETICIONES_SEGUNDA_ANDALUZA, guardar_futuras=True)
    except Exception as error:
        print("\nERROR GENERAL:")
        print(error)
        sys.exit(1)
