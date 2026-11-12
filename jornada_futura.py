
from playwright.sync_api import sync_playwright

import guarda_division_honor as app


# ============================================================
# CONFIGURACION
# ============================================================

JORNADAS_PRUEBA = [10, 11, 12, 13]

GRUPOS_PRUEBA = {
    "49641343": "Grupo 1",
    "48933162": "Grupo 2",
}

print("\nPRUEBA COMPLETA DE JORNADAS RFAF")
print("=" * 100)
print("Grupos: Grupo 1 y Grupo 2")
print("Jornada 10: debe procesarse normalmente.")
print("Jornadas 11, 12 y 13: deben omitirse por ser futuras.")
print("No se conecta a Supabase.")
print("No guarda partidos ni tarjetas.")
print("=" * 100)


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def obtener_identificador_grupo(grupo):
    return str(
        grupo.get("value")
        or grupo.get("id")
        or grupo.get("codigo")
        or ""
    )


def obtener_nombre_grupo(grupo):
    return str(
        grupo.get("label")
        or grupo.get("nombre")
        or grupo.get("text")
        or grupo.get("texto")
        or ""
    )


def comprobar_resultado(numero, partidos, errores, omitidos):

    if numero == 10:

        correcto = (
            len(partidos) > 0
            and errores == 0
            and omitidos == 0
        )

        if correcto:
            print(
                f"PRUEBA CORRECTA | JORNADA 10 | "
                f"{len(partidos)} PARTIDOS"
            )
        else:
            print(
                "PRUEBA INCORRECTA | "
                "La jornada 10 no se ha procesado correctamente."
            )

        return correcto

    correcto = (
        len(partidos) == 0
        and errores == 0
        and omitidos == 1
    )

    if correcto:
        print(
            f"PRUEBA CORRECTA | "
            f"JORNADA {numero} OMITIDA"
        )
    else:
        print(
            f"PRUEBA INCORRECTA | "
            f"JORNADA {numero}"
        )

    return correcto


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():

    resultados = []
    errores_generales = []
    grupos_encontrados = []

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:

            # ------------------------------------------------
            # DESCUBRIR GRUPOS
            # ------------------------------------------------

            print("\nDESCUBRIENDO GRUPOS")
            print("=" * 100)

            grupos = app.descubrir_grupos(page)

            if not grupos:
                raise RuntimeError(
                    "No se han encontrado grupos."
                )

            for grupo in grupos:

                grupo_id = obtener_identificador_grupo(grupo)
                nombre = obtener_nombre_grupo(grupo)

                print(
                    f"Grupo detectado: "
                    f"{nombre or grupo_id} | ID: {grupo_id}"
                )

                if grupo_id in GRUPOS_PRUEBA:
                    grupos_encontrados.append(grupo)

            if len(grupos_encontrados) != 2:
                raise RuntimeError(
                    "No se han encontrado los dos grupos esperados. "
                    f"Encontrados: "
                    f"{[obtener_identificador_grupo(g) for g in grupos]}"
                )

            # ------------------------------------------------
            # PROBAR CADA GRUPO
            # ------------------------------------------------

            for grupo in grupos_encontrados:

                grupo_id = obtener_identificador_grupo(grupo)
                nombre_grupo = GRUPOS_PRUEBA[grupo_id]

                print("\n\n")
                print("#" * 100)
                print(f"INICIANDO PRUEBA: {nombre_grupo}")
                print(f"ID: {grupo_id}")
                print("#" * 100)

                # --------------------------------------------
                # DESCUBRIR JORNADAS
                # --------------------------------------------

                try:

                    jornadas = app.descubrir_jornadas(
                        page,
                        grupo
                    )

                    jornadas_seleccionadas = []

                    for numero in JORNADAS_PRUEBA:

                        jornada = next(
                            (
                                j for j in jornadas
                                if int(j["numero"]) == numero
                            ),
                            None
                        )

                        if jornada is None:
                            raise RuntimeError(
                                f"No se ha encontrado la jornada "
                                f"{numero} en {nombre_grupo}."
                            )

                        jornadas_seleccionadas.append(jornada)

                    print("\nJORNADAS QUE SE VAN A PROBAR:")

                    for jornada in jornadas_seleccionadas:
                        print(
                            f"Jornada {jornada['numero']} | "
                            f"{jornada['texto']}"
                        )

                except Exception as e:

                    errores_generales.append(
                        f"{nombre_grupo}: {e}"
                    )

                    print(
                        f"ERROR DESCUBRIENDO JORNADAS "
                        f"EN {nombre_grupo}: {e}"
                    )

                    continue

                # --------------------------------------------
                # PROCESAR JORNADAS
                # --------------------------------------------

                for jornada in jornadas_seleccionadas:

                    numero = int(jornada["numero"])

                    print("\n" + "-" * 100)

                    try:

                        partidos, errores, omitidos = (
                            app.extraer_jornada(
                                page,
                                grupo,
                                jornada
                            )
                        )

                        correcto = comprobar_resultado(
                            numero,
                            partidos,
                            errores,
                            omitidos
                        )

                        resultados.append({
                            "grupo": nombre_grupo,
                            "jornada": numero,
                            "partidos": len(partidos),
                            "errores": errores,
                            "omitidos": omitidos,
                            "correcto": correcto,
                        })

                    except Exception as e:

                        errores_generales.append(
                            f"{nombre_grupo} Jornada {numero}: {e}"
                        )

                        resultados.append({
                            "grupo": nombre_grupo,
                            "jornada": numero,
                            "partidos": 0,
                            "errores": 1,
                            "omitidos": 0,
                            "correcto": False,
                        })

                        print(
                            f"ERROR EN {nombre_grupo} "
                            f"JORNADA {numero}: {e}"
                        )

            # ------------------------------------------------
            # RESUMEN FINAL
            # ------------------------------------------------

            print("\n\n")
            print("=" * 100)
            print("RESUMEN GENERAL DE LA PRUEBA")
            print("=" * 100)

            for nombre_grupo in GRUPOS_PRUEBA.values():

                print(f"\n{nombre_grupo}")
                print("-" * 100)

                resultados_grupo = [
                    r for r in resultados
                    if r["grupo"] == nombre_grupo
                ]

                for r in resultados_grupo:

                    print(
                        f"Jornada {r['jornada']} | "
                        f"Partidos: {r['partidos']} | "
                        f"Errores: {r['errores']} | "
                        f"Omitidas: {r['omitidos']} | "
                        f"{'CORRECTO' if r['correcto'] else 'INCORRECTO'}"
                    )

            total_correctas = sum(
                1 for r in resultados if r["correcto"]
            )

            total_pruebas = len(GRUPOS_PRUEBA) * len(JORNADAS_PRUEBA)

            total_errores = len(errores_generales) + sum(
                r["errores"] for r in resultados
            )

            prueba_superada = (
                total_correctas == total_pruebas
                and total_errores == 0
                and len(resultados) == total_pruebas
            )

            print("\n" + "=" * 100)
            print("RESULTADO FINAL")
            print("=" * 100)

            print(f"Grupos examinados: {len(grupos_encontrados)}")
            print(f"Jornadas examinadas: {len(resultados)}")
            print(f"Comprobaciones correctas: {total_correctas}")
            print(f"Errores: {total_errores}")

            if prueba_superada:

                print("\nPRUEBA SUPERADA")
                print(
                    "Los dos grupos han procesado correctamente "
                    "la jornada 10 y han omitido las jornadas "
                    "11, 12 y 13."
                )

            else:

                print("\nPRUEBA NO SUPERADA")

                for error in errores_generales:
                    print(error)

            print("=" * 100)

        finally:
            browser.close()


if __name__ == "__main__":
    main()
