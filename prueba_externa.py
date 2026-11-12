import time
from playwright.sync_api import sync_playwright
import testacta as rfaf


# Actas que vamos a comprobar.
ACTAS_PRUEBA = {
    1: ["2733990", "2733994"],
    2: ["2733996", "2734000", "2734001"],
}

# Referencia facilitada para el acta 2733990.
DATOS_ESPERADOS = {
    "2733990": {
        "local": "CADIZ C.F., S.A.D.",
        "visitante": "RAYO SANLUQUEÑO C.D.",
        "resultado": "2-0",
        "arbitro": "MONTARAZ ROJO, LEON",
        "amarillas_local": 4,
        "amarillas_visitante": 2,
        "rojas_local": 0,
        "rojas_visitante": 0,
        "total_tarjetas": 6,
    }
}


def comprobar_referencia(datos):
    acta = datos["acta"]
    if acta not in DATOS_ESPERADOS:
        return []

    esperado = DATOS_ESPERADOS[acta]
    errores = []

    for campo in ("local", "visitante", "resultado", "arbitro"):
        obtenido = datos.get(campo)
        if obtenido != esperado[campo]:
            errores.append(
                f"{campo}: esperado={esperado[campo]} | obtenido={obtenido}"
            )

    tarjetas = datos["tarjetas"]
    for campo in (
        "amarillas_local",
        "amarillas_visitante",
        "rojas_local",
        "rojas_visitante",
    ):
        if tarjetas.get(campo) != esperado[campo]:
            errores.append(
                f"{campo}: esperado={esperado[campo]} | "
                f"obtenido={tarjetas.get(campo)}"
            )

    total = len(datos["tarjetas_individuales"])
    if total != esperado["total_tarjetas"]:
        errores.append(
            f"Tarjetas individuales: esperado={esperado['total_tarjetas']} | "
            f"obtenido={total}"
        )

    return errores


def comprobar_acta(datos):
    errores = []

    if datos.get("estado") != "OK":
        errores.append(f"Estado: {datos.get('estado')}")

    tarjetas = datos.get("tarjetas", {})
    campos = (
        "amarillas_local",
        "amarillas_visitante",
        "rojas_local",
        "rojas_visitante",
    )

    for campo in campos:
        if tarjetas.get(campo) == "?":
            errores.append(f"Total sin verificar: {campo}")

    errores.extend(datos.get("errores_individuales", []))
    errores.extend(datos.get("errores_tarjetas", []))
    errores.extend(comprobar_referencia(datos))

    # Evita que la misma acta aparezca validada con un total desconocido.
    if any(tarjetas.get(campo) == "?" for campo in campos):
        return list(dict.fromkeys(errores))

    return list(dict.fromkeys(errores))


def main():
    resultados = []
    actas_no_encontradas = []

    print("\nPRUEBA EXTERNA DE ACTAS RFAF")
    print("=" * 90)
    print("Actas seleccionadas: 5")
    print("No se conecta a Supabase.")
    print("=" * 90)

    with sync_playwright() as playwright:
        navegador = playwright.chromium.launch(headless=True)
        page = navegador.new_page(
            viewport={"width": 1366, "height": 900}
        )

        try:
            for jornada, ids in ACTAS_PRUEBA.items():
                print(f"\nJORNADA {jornada}")
                print("-" * 90)

                actas_disponibles = rfaf.cargar_jornada(page, jornada)
                equipos_calendario = page.evaluate(rfaf.JS_CALENDARIO)

                for acta_id in ids:
                    if acta_id not in actas_disponibles:
                        actas_no_encontradas.append(acta_id)
                        print(f"NO ENCONTRADA | ACTA {acta_id}")
                        continue

                    datos = rfaf.procesar_acta(
                        page,
                        jornada,
                        acta_id,
                        equipos_calendario
                    )

                    errores = comprobar_acta(datos)
                    resultados.append({
                        "datos": datos,
                        "errores": errores
                    })

                    tarjetas = datos["tarjetas"]
                    estado = "VALIDADO" if not errores else "NO VALIDADO"

                    print(
                        f"{estado} | ACTA {acta_id} | "
                        f"{datos.get('local')} - {datos.get('visitante')} | "
                        f"{datos.get('resultado')} | "
                        f"AM {tarjetas.get('amarillas_local')}-"
                        f"{tarjetas.get('amarillas_visitante')} | "
                        f"RO {tarjetas.get('rojas_local')}-"
                        f"{tarjetas.get('rojas_visitante')} | "
                        f"Tarjetas: {len(datos.get('tarjetas_individuales', []))}"
                    )

                    for error in errores:
                        print(f"  ERROR: {error}")

                    time.sleep(1)

        finally:
            navegador.close()

    validas = sum(1 for r in resultados if not r["errores"])
    fallidas = len(resultados) - validas

    print("\n" + "=" * 90)
    print("RESULTADO DE LA PRUEBA")
    print("=" * 90)
    print(f"Actas procesadas: {len(resultados)}")
    print(f"Actas validadas: {validas}")
    print(f"Actas con errores: {fallidas}")
    print(f"Actas no encontradas: {len(actas_no_encontradas)}")

    if actas_no_encontradas:
        print("No encontradas: " + ", ".join(actas_no_encontradas))

    if validas == 5 and fallidas == 0 and not actas_no_encontradas:
        print("\nPRUEBA COMPLETADA: LAS 5 ACTAS ESTAN VALIDADAS.")
    else:
        print("\nPRUEBA NO SUPERADA: HAY ACTAS PENDIENTES DE REVISION.")

    print("\nNo se ha conectado ni escrito nada en Supabase.")


if __name__ == "__main__":
    main()
