class NegocioNoEncontrado(Exception):
    pass

class NoEsTitularDelNegocio(Exception):
    pass

class TrabajoNoEncontrado(Exception):
    pass

class TrabajoYaCerrado(Exception):
    pass

class NivelInsuficiente(Exception):
    def __init__(self, requiere: int) -> None:
        self.requiere = requiere

class ContrasenaIncorrecta(Exception):
    pass

class EmailYaRegistrado(Exception):
    pass

class RutEmpresaEnUso(Exception):
    pass

class CredencialesInvalidas(Exception):
    pass

class ReporteInvalido(Exception):
    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje

class ReporteError(Exception):
    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje

class RutRechazado(ReporteError):
    pass

class RutEnUso(ReporteError):
    pass

class RutYaVerificado(ReporteError):
    pass

class BiometriaInvalida(ReporteError):
    pass

class BiometriaMuyGrande(ReporteError):
    pass

class AntecedentesInvalido(ReporteError):
    pass

class AntecedentesMuyGrande(ReporteError):
    pass

class CedulaInvalida(ReporteError):
    pass

class CedulaMuyGrande(ReporteError):
    pass

class AvalInvalido(ReporteError):
    pass

class AvalMuyGrande(ReporteError):
    pass

class DocEmpresaInvalido(ReporteError):
    pass

class DocEmpresaMuyGrande(ReporteError):
    pass

class EvaluadorIndisponible(Exception):
    def __init__(
        self, mensaje: str = "No se pudo refrescar el índice de señales."
    ) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje

class RadarInvalido(Exception):
    def __init__(self, mensaje: str) -> None:
        self.mensaje = mensaje
        super().__init__(mensaje)

class CorreoRechazado(Exception):
    def __init__(self, mensaje: str) -> None:
        self.mensaje = mensaje
        super().__init__(mensaje)

class PagoInformeError(Exception):
    def __init__(
        self,
        mensaje: str,
        *,
        codigo: str = "pago_error",
        buy_order: str | None = None,
    ) -> None:
        self.mensaje = mensaje
        self.codigo = codigo
        self.buy_order = buy_order
        super().__init__(mensaje)

class InformeSinCompra(Exception):

    def __init__(
        self,
        mensaje: str = "Debe comprar el informe para acceder.",
        *,
        codigo: str = "informe_sin_compra",
    ) -> None:
        self.mensaje = mensaje
        self.codigo = codigo
        super().__init__(mensaje)

class PublicacionSinPago(Exception):

    def __init__(
        self,
        mensaje: str = "Debe pagar la publicación de la ficha antes de crearla.",
        *,
        codigo: str = "publicacion_sin_pago",
    ) -> None:
        self.mensaje = mensaje
        self.codigo = codigo
        super().__init__(mensaje)

class PagoPublicacionError(Exception):
    def __init__(
        self,
        mensaje: str,
        *,
        codigo: str = "pago_publicacion_error",
        buy_order: str | None = None,
    ) -> None:
        self.mensaje = mensaje
        self.codigo = codigo
        self.buy_order = buy_order
        super().__init__(mensaje)
