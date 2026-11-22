

def score_confiabilidad(concretados: int, no_concretados: int) -> float | None:

    cerrados = concretados + no_concretados
    if cerrados == 0:
        return None
    return round(concretados / cerrados * 100, 1)

def nivel_reporte() -> int:
    return 1

def estado_reporte(rut_verificado: bool) -> str:
    return "verificado" if rut_verificado else "basico"
