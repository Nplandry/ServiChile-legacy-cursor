

XP_REGISTRO = 10

XP_PERFIL_BASICO = 20

XP_RUT = 50

XP_BIOMETRIA = 80

XP_ANTECEDENTES = 60

XP_AVAL = 50

XP_TRABAJO_CONCRETADO = 25

EVENTO_REGISTRO = "registro"

EVENTO_PERFIL_BASICO = "perfil_basico"

EVENTO_RUT = "rut_verificado"

EVENTO_BIOMETRIA = "biometria"

EVENTO_ANTECEDENTES = "antecedentes"

EVENTO_AVAL = "aval"

def evento_trabajo_concretado(trabajo_id: str) -> str:

    return f"trabajo:{trabajo_id}"

def nivel_por_xp(xp: int) -> int:

    if xp >= 250:

        return 3

    if xp >= 100:

        return 2

    return 1
