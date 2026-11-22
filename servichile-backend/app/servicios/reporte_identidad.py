from app.dominio.entidades import EstadoReporte, Usuario
from app.dominio import progreso_cliente as reglas_xp
from app.dominio.errores import (
    RutEnUso,
    RutRechazado,
    RutYaVerificado,
)
from app.dominio.reporte_estado import estado_reporte, nivel_reporte, score_confiabilidad
from app.dominio.rut import RutInvalido, normalizar_rut
from app.dominio.puertos import (
    AlmacenamientoBiometria,
    AlmacenamientoCedula,
    AnalizadorAntecedentes,
    AnalizadorAval,
    AnalizadorCedula,
    RepositorioTrabajos,
    RepositorioUsuarios,
    VerificadorIdentidad,
)
from app.servicios.reporte_evidencias import MezclaReporteEvidencias
from app.servicios.perfil import aplicar_perfil
from app.servicios.progreso_cliente import ServicioProgresoCliente
from app.tiempo import ahora_utc

class ServicioReporteIdentidad(MezclaReporteEvidencias):
    def __init__(
        self,
        usuarios: RepositorioUsuarios,
        trabajos: RepositorioTrabajos,
        verificador: VerificadorIdentidad,
        xp: ServicioProgresoCliente | None = None,
        analizador: AnalizadorAntecedentes | None = None,
        biometria: AlmacenamientoBiometria | None = None,
        biometria_retencion_dias: int = 180,
        cedula: AlmacenamientoCedula | None = None,
        analizador_cedula: AnalizadorCedula | None = None,
        cedula_retencion_dias: int = 180,
        analizador_aval: AnalizadorAval | None = None,
    ) -> None:
        self.usuarios = usuarios
        self.trabajos = trabajos
        self.verificador = verificador
        self.xp = xp
        self.analizador = analizador
        self.biometria = biometria
        self.biometria_retencion_dias = biometria_retencion_dias
        self.cedula = cedula
        self.analizador_cedula = analizador_cedula
        self.cedula_retencion_dias = cedula_retencion_dias
        self.analizador_aval = analizador_aval

    def estado(self, usuario: Usuario) -> EstadoReporte:
        usuario = self._aplicar_retencion_biometria(usuario)
        usuario = self._aplicar_retencion_cedula(usuario)
        conteo = self.trabajos.contar_por_estado(usuario.id)
        xp = self.xp.total(usuario.id) if self.xp is not None else int(usuario.xp or 0)
        return EstadoReporte(
            rut_verificado=usuario.rut_verificado,
            telefono=usuario.telefono,
            nivel_reporte=nivel_reporte(),
            estado_reporte=estado_reporte(usuario.rut_verificado),
            score_confiabilidad=score_confiabilidad(
                conteo.get("concretado", 0), conteo.get("no_concretado", 0)
            ),
            edad=usuario.perfil.edad if usuario.perfil else None,
            tipo_cuenta=usuario.perfil.tipo_cuenta if usuario.perfil else None,
            biometria_verificada=usuario.biometria_verificada,
            biometria_verificada_en=usuario.biometria_verificada_en,
            biometria_retener_hasta=usuario.biometria_retener_hasta,
            biometria_bytes=usuario.biometria_bytes,
            cedula_verificada=bool(usuario.cedula_verificada),
            cedula_verificada_en=usuario.cedula_verificada_en,
            cedula_retener_hasta=usuario.cedula_retener_hasta,
            cedula_bytes=usuario.cedula_bytes,
            cedula_score=usuario.cedula_score,
            antecedentes_verificados=bool(usuario.antecedentes_verificados),
            antecedentes_verificados_en=usuario.antecedentes_verificados_en,
            antecedentes_anotaciones=usuario.antecedentes_anotaciones,
            antecedentes_score=usuario.antecedentes_score,
            aval_verificado=bool(usuario.aval_verificado),
            aval_verificado_en=usuario.aval_verificado_en,
            aval_score=usuario.aval_score,
            aval_tipo=usuario.aval_tipo,
            xp=xp,
            nivel_xp=reglas_xp.nivel_por_xp(xp),
        )

    def actualizar_perfil(self, usuario: Usuario, cambios: dict) -> Usuario:
        if "rut" in cambios:
            if cambios["rut"] is None:
                raise RutRechazado("El RUT no se puede borrar una vez enviado.")
            self._verificar_rut(usuario, cambios["rut"])
        if "telefono" in cambios:
            usuario.telefono = cambios["telefono"]
        aplicar_perfil(usuario, cambios)
        usuario = self.usuarios.guardar(usuario)
        if self.xp is not None:
            if usuario.rut_verificado:
                self.xp.por_rut(usuario.id)
            self.xp.por_perfil_basico(usuario)
            usuario.xp = self.xp.total(usuario.id)
        return usuario

    def _verificar_rut(self, usuario: Usuario, texto: str) -> None:
        try:
            rut = normalizar_rut(texto)
        except RutInvalido as error:
            raise RutRechazado(str(error)) from None
        if usuario.rut_verificado:
            if usuario.rut == rut:
                return
            raise RutYaVerificado("El RUT ya fue verificado y no se puede cambiar.")
        otro = self.usuarios.obtener_por_rut(rut)
        if otro is not None and otro.id != usuario.id:
            raise RutEnUso("Este RUT ya está registrado en otra cuenta.")
        if not self.verificador.existe_y_activo(rut):
            raise RutRechazado(
                "No se pudo verificar el RUT ante una fuente oficial. "
                "Complete la verificación con cédula en Verificación, "
                "o configure CHILECOMPRA_TICKET para cruzar Mercado Público."
            )
        usuario.rut = rut
        usuario.rut_verificado = True

    def _aplicar_retencion_biometria(self, usuario: Usuario) -> Usuario:
        hasta = usuario.biometria_retener_hasta
        if not hasta or not usuario.biometria_verificada:
            return usuario
        ahora = ahora_utc()
        fin = hasta if hasta.tzinfo else hasta.replace(tzinfo=ahora.tzinfo)
        if fin >= ahora:
            return usuario
        if self.biometria is not None:
            self.biometria.eliminar(usuario.id, usuario.biometria_ruta)
        usuario.biometria_verificada = False
        usuario.biometria_verificada_en = None
        usuario.biometria_ruta = None
        usuario.biometria_sha256 = None
        usuario.biometria_bytes = None
        usuario.biometria_ancho = None
        usuario.biometria_alto = None
        usuario.biometria_content_type = None
        usuario.biometria_retener_hasta = None
        return self.usuarios.guardar(usuario)

    def _aplicar_retencion_cedula(self, usuario: Usuario) -> Usuario:
        hasta = usuario.cedula_retener_hasta
        if not hasta or not usuario.cedula_verificada:
            return usuario
        ahora = ahora_utc()
        fin = hasta if hasta.tzinfo else hasta.replace(tzinfo=ahora.tzinfo)
        if fin >= ahora:
            return usuario
        if self.cedula is not None:
            self.cedula.eliminar(usuario.id, usuario.cedula_ruta)
        usuario.cedula_verificada = False
        usuario.cedula_verificada_en = None
        usuario.cedula_ruta = None
        usuario.cedula_sha256 = None
        usuario.cedula_bytes = None
        usuario.cedula_ancho = None
        usuario.cedula_alto = None
        usuario.cedula_content_type = None
        usuario.cedula_retener_hasta = None
        usuario.cedula_score = None
        usuario.cedula_rut_ocr = None
        return self.usuarios.guardar(usuario)

