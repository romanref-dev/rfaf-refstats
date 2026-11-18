import argparse
import os
import sys

from supabase import create_client

import config
from guarda_division_honor import (
    SUPABASE_URL,
    SUPABASE_KEY,
    ejecutar_sincronizacion,
    sincronizar_arbitros_desde_partidos,
    sincronizar_competiciones_desde_partidos,
)


def obtener_catalogo(bloque: str):
    b = (bloque or "todas").strip().lower()
    if b in ("primera_andaluza", "1a", "1_andaluza"):
        return config.COMPETICIONES_PRIMERA_ANDALUZA
    if b in ("segunda_andaluza", "2a", "2_andaluza"):
        return config.COMPETICIONES_SEGUNDA_ANDALUZA
    if b in ("tercera_andaluza", "3a", "3_andaluza"):
        return config.COMPETICIONES_TERCERA_ANDALUZA
    if b in ("copas", "copas_aficionados"):
        return config.COMPETICIONES_COPAS_AFICIONADOS
    if b in ("otras", "otras_aficionados"):
        return config.COMPETICIONES_OTRAS_AFICIONADOS
    return config.COMPETICIONES_AFICIONADOS


def ejecutar_lote(competiciones, guardar_futuras=True):
    supabase_url = os.getenv("SUPABASE_URL", SUPABASE_URL)
    supabase_key = os.getenv("SUPABASE_KEY", SUPABASE_KEY)

    if not supabase_url or not supabase_key:
        raise RuntimeError(
            "Faltan SUPABASE_URL o SUPABASE_KEY en las variables de entorno."
        )

    fallidas = []

    for idx, comp in enumerate(competiciones, start=1):
        comp_id = str(comp["id"])
        nombre = comp["nombre"]
        print(f"\n{'*' * 100}")
        print(f"[{idx}/{len(competiciones)}] SINCRONIZANDO: {nombre} (ID: {comp_id})")
        print(f"{'*' * 100}")

        try:
            ejecutar_sincronizacion(
                competicion=nombre,
                competicion_id=comp_id,
                grupos_esperados=None,
                incluir_jugadores_tarjetas=True,
                omitir_sin_marcador=True,
                guardar_jornadas_futuras=guardar_futuras,
                sincronizar_tablas_resumen=False,
                titulo=f"RFAF - {nombre.upper()}",
            )
        except SystemExit as exc:
            if exc.code and exc.code != 0:
                print(f"AVISO: {nombre} terminó con código {exc.code}.")
                fallidas.append(nombre)
        except Exception as error:
            print(f"ERROR EN COMPETICIÓN {nombre} ({comp_id}): {error}")
            fallidas.append(nombre)

    supabase = create_client(supabase_url, supabase_key)
    try:
        sincronizar_arbitros_desde_partidos(supabase)
    except Exception as error:
        print("AVISO al sincronizar tabla arbitros:", error)

    try:
        sincronizar_competiciones_desde_partidos(supabase)
    except Exception as error:
        print("AVISO al sincronizar tabla competiciones:", error)

    print("\n" + "=" * 100)
    print(f"LOTE TERMINADO: {len(competiciones) - len(fallidas)}/{len(competiciones)} competiciones OK.")
    if fallidas:
        print("Competiciones con incidencias:", ", ".join(fallidas))
    print("=" * 100)


def main():
    parser = argparse.ArgumentParser(
        description="Sincronizador RFAF para todas las competiciones del bloque AFICIONADOS."
    )
    parser.add_argument(
        "--bloque",
        default="todas",
        help="Bloque a sincronizar: todas, primera_andaluza, segunda_andaluza, tercera_andaluza, copas, otras",
    )
    parser.add_argument(
        "--competicion-id",
        default=None,
        help="ID concreto de competición RFAF (opcional, si se quiere ejecutar solo una).",
    )
    parser.add_argument(
        "--sin-futuras",
        action="store_true",
        help="Si se indica, omite las jornadas futuras sin guardarlas como Pendiente.",
    )
    args = parser.parse_args()

    if args.competicion_id:
        encontrada = next(
            (c for c in config.COMPETICIONES_AFICIONADOS if c["id"] == str(args.competicion_id)),
            {"id": str(args.competicion_id), "nombre": f"Competición RFAF {args.competicion_id}"},
        )
        catalogo = [encontrada]
    else:
        catalogo = obtener_catalogo(args.bloque)

    ejecutar_lote(catalogo, guardar_futuras=not args.sin_futuras)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("\nERROR GENERAL:")
        print(error)
        sys.exit(1)
