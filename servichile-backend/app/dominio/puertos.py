

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.dominio.antecedentes import ResultadoAntecedentes
from app.dominio.aval import ResultadoAval
from app.dominio.biometria import MetaBiometria
from app.dominio.cedula import MetaCedula, ResultadoCedula
from app.dominio.docs_empresa import ResultadoDocEmpresa, TipoDocEmpresa
from app.dominio.entidades import Negocio, TokenEmitido, Trabajo, Usuario
from app.dominio.oferta_negocio import FiltroListado
from app.dominio.transparencia.evaluador.motor import ResultadoEvaluador

class RegistroHashPades(Protocol):

    def registrar_hash_pades(
        self,
        sha256: str,
        *,
        scope: str,
        tipo: str | None = None,
        usuario_id: uuid.UUID | None = None,
        business_id: uuid.UUID | None = None,
    ) -> bool: ...

class RepositorioUsuarios(RegistroHashPades, Protocol):
    def obtener_por_email(self, email: str) -> Usuario | None: ...

    def obtener(self, usuario_id: uuid.UUID) -> Usuario | None: ...

    def obtener_por_rut(self, rut: str) -> Usuario | None: ...

    def crear(self, email: str, nombre: str, hash_contrasena: str) -> Usuario: ...

    def eliminar(self, usuario_id: uuid.UUID) -> None: ...

    def guardar(self, usuario: Usuario) -> Usuario: ...

class RepositorioNegocios(RegistroHashPades, Protocol):
    def obtener(self, negocio_id: uuid.UUID) -> Negocio | None: ...

    def listar(
        self, filtro: FiltroListado | None = None, limite: int = 100
    ) -> list[Negocio]: ...

    def listar_de(self, usuario_id: uuid.UUID) -> list[Negocio]: ...

    def listar_completos(self, limite: int = 500) -> list[Negocio]: ...

    def guardar(self, negocio: Negocio) -> Negocio: ...

    def eliminar(self, negocio_id: uuid.UUID) -> None: ...

    def eliminar_de(self, usuario_id: uuid.UUID) -> None: ...

class RepositorioTrabajos(Protocol):
    def crear(
        self, usuario_id: uuid.UUID, negocio_id: uuid.UUID, token_qr: str
    ) -> Trabajo: ...

    def obtener(self, trabajo_id: uuid.UUID) -> Trabajo | None: ...

    def obtener_por_qr(self, negocio_id: uuid.UUID, token_qr: str) -> Trabajo | None: ...

    def listar_por_usuario(self, usuario_id: uuid.UUID) -> list[Trabajo]: ...

    def listar_por_negocio(self, negocio_id: uuid.UUID) -> list[Trabajo]: ...

    def contar_por_estado(self, usuario_id: uuid.UUID) -> dict[str, int]: ...

    def contar_concretados_por_negocios(
        self, negocio_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, int]: ...

    def guardar(self, trabajo: Trabajo) -> Trabajo: ...

class RepositorioXp(Protocol):
    def otorgar(self, usuario_id: uuid.UUID, evento: str, puntos: int) -> int: ...

    def total(self, usuario_id: uuid.UUID) -> int: ...

class VerificadorIdentidad(Protocol):
    def existe_y_activo(self, rut: str) -> bool: ...

class HasheadorContrasena(Protocol):
    def hashear(self, contrasena: str) -> str: ...

    def verificar(self, hash_contrasena: str | None, contrasena: str) -> bool: ...

class EmisorSesion(Protocol):
    def emitir(self, usuario_id: uuid.UUID) -> TokenEmitido: ...

    def sujeto(self, token: str) -> uuid.UUID: ...

@dataclass(frozen=True)
class TokenReporteFirmado:
    token: str
    expires_in: int
    expires_at: datetime

@dataclass(frozen=True)
class TokenReporteLeido:
    usuario_id: uuid.UUID
    expires_at: datetime

class EmisorReporte(Protocol):
    def emitir(self, usuario_id: uuid.UUID) -> TokenReporteFirmado: ...

    def leer(self, token: str) -> TokenReporteLeido: ...

class AnalizadorAntecedentes(Protocol):
    def analizar(
        self, contenido: bytes, nombre_archivo: str | None = None
    ) -> ResultadoAntecedentes: ...

class AnalizadorAval(Protocol):
    def analizar(
        self,
        contenido: bytes,
        *,
        rut_perfil: str | None = None,
        nombre_perfil: str | None = None,
        nombre_archivo: str | None = None,
    ) -> ResultadoAval: ...

class AnalizadorDocEmpresa(Protocol):
    def analizar(
        self,
        contenido: bytes,
        *,
        tipo: TipoDocEmpresa,
        rut_empresa: str | None = None,
        nombre_empresa: str | None = None,
        nombre_archivo: str | None = None,
    ) -> ResultadoDocEmpresa: ...

class AlmacenamientoBiometria(Protocol):
    def guardar(self, usuario_id: uuid.UUID, contenido: bytes) -> MetaBiometria: ...

    def leer(self, ruta_relativa: str) -> bytes: ...

    def eliminar(
        self, usuario_id: uuid.UUID, ruta_relativa: str | None = None
    ) -> None: ...

class AlmacenamientoCedula(Protocol):
    def preparar_en_memoria(self, contenido: bytes) -> tuple[bytes, MetaCedula]: ...

    def guardar(self, usuario_id: uuid.UUID, contenido: bytes) -> MetaCedula: ...

    def leer(self, ruta_relativa: str) -> bytes: ...

    def eliminar(
        self, usuario_id: uuid.UUID, ruta_relativa: str | None = None
    ) -> None: ...

class LectorOcrCedula(Protocol):
    def extraer_texto(self, jpeg_bytes: bytes) -> str: ...

class AnalizadorCedula(Protocol):
    def analizar(
        self,
        jpeg_bytes: bytes,
        *,
        ancho: int,
        alto: int,
        bytes_: int,
        rut_perfil: str | None = None,
        nombre_perfil: str | None = None,
        rut_perfil_verificado: bool = False,
        selfie_jpeg: bytes | None = None,
    ) -> ResultadoCedula: ...

class PuertoEvaluador(Protocol):

    def evaluar(self, negocio: Negocio) -> ResultadoEvaluador: ...

@dataclass(frozen=True)
class MensajeSaliente:
    destino: str
    asunto: str
    cuerpo: str

class EnviadorPlataforma(Protocol):

    def disponible(self) -> bool: ...

    def enviar(self, mensaje: MensajeSaliente) -> None: ...

class RepositorioCorreo(Protocol):
    def registrar(
        self,
        usuario_id: uuid.UUID,
        business_id: uuid.UUID | None,
        tipo: str,
        destino: str,
        asunto: str,
        cuerpo: str,
        estado: str,
    ) -> None: ...

@dataclass(frozen=True)
class TransaccionWebpayCreada:
    token: str
    url: str

@dataclass(frozen=True)
class TransaccionWebpayConfirmada:
    response_code: int
    status: str
    authorization_code: str | None = None
    payment_type_code: str | None = None
    card_last4: str | None = None
    buy_order: str | None = None
    detalle: str | None = None

class PasarelaWebpay(Protocol):
    def crear(
        self, buy_order: str, session_id: str, amount: int, return_url: str
    ) -> TransaccionWebpayCreada: ...

    def confirmar(self, token: str) -> TransaccionWebpayConfirmada: ...

class RepositorioComprasInforme(Protocol):
    def crear(
        self,
        usuario_id: uuid.UUID,
        business_id: uuid.UUID,
        buy_order: str,
        monto: int,
    ): ...

    def guardar(self, compra): ...

    def obtener_por_token(self, token: str): ...

    def obtener_por_buy_order(self, buy_order: str): ...

    def reclamar_para_confirmar(self, token: str, usuario_id: uuid.UUID): ...

    def tiene_autorizada(
        self, usuario_id: uuid.UUID, business_id: uuid.UUID
    ) -> bool: ...

    def ultima_autorizada(
        self, usuario_id: uuid.UUID, business_id: uuid.UUID
    ): ...

    def listar_pendientes_reconciliar(
        self, *, min_edad_seg: int, max_edad_seg: int, limite: int
    ): ...

    def anular_pendientes_abiertos(
        self, usuario_id: uuid.UUID, business_id: uuid.UUID, *, excepto_id=None
    ) -> int: ...

    def resumen_mes(self, usuario_id: uuid.UUID, mes_clave: str) -> tuple[int, int]: ...

class RepositorioComprasPublicacion(Protocol):
    def crear(self, usuario_id: uuid.UUID, buy_order: str, monto: int): ...

    def guardar(self, compra): ...

    def obtener_por_token(self, token: str): ...

    def obtener_por_buy_order(self, buy_order: str): ...

    def cupon_libre(self, usuario_id: uuid.UUID): ...

    def cupon_listo_alta(self, usuario_id: uuid.UUID): ...

    def reservar_para_alta(
        self, usuario_id: uuid.UUID, buy_order: str, *, commit: bool = True
    ): ...

    def liberar_reserva(
        self, usuario_id: uuid.UUID, buy_order: str, *, commit: bool = True
    ): ...

    def liberar_reservas_stale(self, *, max_edad_seg: int = 180) -> int: ...

    def consumir_atomico(
        self,
        usuario_id: uuid.UUID,
        buy_order: str,
        business_id: uuid.UUID,
        *,
        commit: bool = True,
    ): ...

    def reclamar_para_confirmar(self, token: str, usuario_id: uuid.UUID): ...

    def anular_pendientes_abiertos(
        self, usuario_id: uuid.UUID, *, excepto_id=None
    ) -> int: ...

    def listar_pendientes_reconciliar(
        self, *, min_edad_seg: int, max_edad_seg: int, limite: int
    ): ...

