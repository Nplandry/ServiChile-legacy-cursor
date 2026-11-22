

from __future__ import annotations

from datetime import date as date_cls

from app.dominio.antecedentes import ANTECEDENTES_MAX_BYTES, ResultadoAntecedentes
from app.dominio.aval import AVAL_MAX_BYTES, ResultadoAval
from app.dominio.biometria import BIOMETRIA_MAX_BYTES, retener_hasta as retener_biometria
from app.dominio.cedula import CEDULA_MAX_BYTES, ResultadoCedula
from app.dominio.entidades import Usuario
from app.dominio.errores import (
    AntecedentesInvalido,
    AntecedentesMuyGrande,
    AvalInvalido,
    AvalMuyGrande,
    BiometriaInvalida,
    BiometriaMuyGrande,
    CedulaInvalida,
    CedulaMuyGrande,
    RutEnUso,
)
from app.servicios.pades_anti_replay import registrar_hash_unico
from app.tiempo import ahora_utc

_FIRMAS_IMAGEN = (
    (b"\xff\xd8\xff", "jpeg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"RIFF", "webp"),
    (b"GIF87a", "gif"),
    (b"GIF89a", "gif"),
)

class MezclaReporteEvidencias:
    def procesar_biometria(self, usuario: Usuario, contenido: bytes) -> Usuario:
        if len(contenido) > BIOMETRIA_MAX_BYTES:
            raise BiometriaMuyGrande("La foto supera el tamaño máximo de 5 MB.")
        if not self._parece_imagen(contenido):
            raise BiometriaInvalida("Suba una foto (JPEG, PNG, WebP o GIF).")
        if self.biometria is None:
            raise BiometriaInvalida("Almacenamiento biométrico no disponible.")

        if usuario.biometria_ruta:
            self.biometria.eliminar(usuario.id, usuario.biometria_ruta)

        meta = self.biometria.guardar(usuario.id, contenido)
        ahora = ahora_utc()
        usuario.biometria_verificada = True
        usuario.biometria_verificada_en = ahora
        usuario.biometria_ruta = meta.ruta_relativa
        usuario.biometria_sha256 = meta.sha256
        usuario.biometria_bytes = meta.bytes_
        usuario.biometria_ancho = meta.ancho
        usuario.biometria_alto = meta.alto
        usuario.biometria_content_type = meta.content_type
        usuario.biometria_retener_hasta = retener_biometria(
            ahora, dias=self.biometria_retencion_dias
        )
        usuario = self.usuarios.guardar(usuario)
        if self.xp is not None:
            self.xp.por_biometria(usuario.id)
            usuario.xp = self.xp.total(usuario.id)
        return usuario

    def procesar_cedula(
        self, usuario: Usuario, contenido: bytes
    ) -> tuple[Usuario, ResultadoCedula]:

        if len(contenido) > CEDULA_MAX_BYTES:
            raise CedulaMuyGrande("La foto del carnet supera el tamaño máximo de 8 MB.")
        if not self._parece_imagen(contenido):
            raise CedulaInvalida("Suba una foto frontal del carnet (JPEG, PNG o WebP).")
        if self.cedula is None or self.analizador_cedula is None:
            raise CedulaInvalida("Validación de cédula no disponible.")
        if self.biometria is None:
            raise CedulaInvalida("Almacenamiento biométrico no disponible.")
        if not usuario.biometria_verificada or not usuario.biometria_ruta:
            raise CedulaInvalida(
                "Complete primero la verificación biométrica (selfie). "
                "Se usa para comparar el rostro del carnet."
            )

        try:
            selfie = self.biometria.leer(usuario.biometria_ruta)
        except BiometriaInvalida as error:
            raise CedulaInvalida(error.mensaje) from error

        if usuario.cedula_ruta:
            self.cedula.eliminar(usuario.id, usuario.cedula_ruta)

        jpeg, meta = self.cedula.preparar_en_memoria(contenido)
        resultado = self.analizador_cedula.analizar(
            jpeg,
            ancho=meta.ancho,
            alto=meta.alto,
            bytes_=meta.bytes_,
            rut_perfil=usuario.rut,
            nombre_perfil=usuario.nombre,
            rut_perfil_verificado=bool(usuario.rut_verificado),
            selfie_jpeg=selfie,
        )

        if not resultado.aceptado:
            raise CedulaInvalida(resultado.motivo)

        if resultado.rut and not usuario.rut_verificado:
            otro = self.usuarios.obtener_por_rut(resultado.rut)
            if otro is not None and otro.id != usuario.id:
                raise RutEnUso("Este RUT ya está registrado en otra cuenta.")
            usuario.rut = resultado.rut
            usuario.rut_verificado = True

        ahora = ahora_utc()
        usuario.cedula_verificada = True
        usuario.cedula_verificada_en = ahora
        usuario.cedula_ruta = None
        usuario.cedula_sha256 = meta.sha256
        usuario.cedula_bytes = meta.bytes_
        usuario.cedula_ancho = meta.ancho
        usuario.cedula_alto = meta.alto
        usuario.cedula_content_type = None
        usuario.cedula_retener_hasta = None
        usuario.cedula_score = resultado.score
        usuario.cedula_rut_ocr = resultado.rut
        resultado = ResultadoCedula(
            aceptado=resultado.aceptado,
            score=resultado.score,
            rut=resultado.rut,
            nombre_ocr=resultado.nombre_ocr,
            senales=resultado.senales,
            motivo=resultado.motivo.rstrip(".") + ".",
            texto_compacto_len=resultado.texto_compacto_len,
            face_score=resultado.face_score,
        )

        usuario = self.usuarios.guardar(usuario)
        if self.xp is not None and usuario.rut_verificado:
            self.xp.por_rut(usuario.id)
            usuario.xp = self.xp.total(usuario.id)
        return usuario, resultado

    def procesar_antecedentes(
        self, usuario: Usuario, contenido: bytes, nombre_archivo: str | None = None
    ) -> tuple[Usuario, ResultadoAntecedentes]:
        if self.analizador is None:
            raise AntecedentesInvalido("Analizador de antecedentes no disponible.")
        if len(contenido) > ANTECEDENTES_MAX_BYTES:
            raise AntecedentesMuyGrande("El PDF supera el tamaño máximo de 8 MB.")
        resultado = self.analizador.analizar(contenido, nombre_archivo)
        if not resultado.aceptado:
            raise AntecedentesInvalido(resultado.motivo)
        registrar_hash_unico(
            self.usuarios,
            resultado.sha256_hash,
            scope="antecedentes",
            tipo="antecedentes",
            usuario_id=usuario.id,
            al_rechazar=lambda: AntecedentesInvalido(
                "Este certificado (hash) ya fue utilizado. No se admite reutilizar el mismo PDF."
            ),
        )

        usuario.antecedentes_verificados = True
        usuario.antecedentes_verificados_en = ahora_utc()
        usuario.antecedentes_anotaciones = bool(resultado.anotaciones)
        usuario.antecedentes_score = resultado.score
        usuario.antecedentes_pades = bool(resultado.verificado_criptograficamente)
        usuario.antecedentes_entidad_emisora = resultado.entidad_emisora
        usuario.antecedentes_sha256 = resultado.sha256_hash
        usuario.antecedentes_glosa = resultado.glosa
        fecha_em = None
        if resultado.fecha_emision:
            try:
                fecha_em = date_cls.fromisoformat(resultado.fecha_emision)
            except ValueError:
                fecha_em = None
        usuario.antecedentes_fecha_emision = fecha_em
        usuario = self.usuarios.guardar(usuario)
        if self.xp is not None:
            self.xp.por_antecedentes(usuario.id)
            usuario.xp = self.xp.total(usuario.id)
        return (usuario, resultado)

    def procesar_aval(
        self, usuario: Usuario, contenido: bytes, nombre_archivo: str | None = None
    ) -> tuple[Usuario, ResultadoAval]:
        if self.analizador_aval is None:
            raise AvalInvalido("Analizador de aval/garantía no disponible.")
        if len(contenido) > AVAL_MAX_BYTES:
            raise AvalMuyGrande("El PDF supera el tamaño máximo de 8 MB.")
        if not contenido.startswith(b"%PDF"):
            raise AvalInvalido(
                "Solo se acepta PDF con texto real. No se admiten fotos ni imágenes."
            )
        resultado = self.analizador_aval.analizar(
            contenido,
            rut_perfil=usuario.rut,
            nombre_perfil=usuario.nombre,
            nombre_archivo=nombre_archivo,
        )
        if not resultado.aceptado:
            raise AvalInvalido(resultado.motivo)
        usuario.aval_verificado = True
        usuario.aval_verificado_en = ahora_utc()
        usuario.aval_score = resultado.score
        usuario.aval_tipo = resultado.tipo
        usuario = self.usuarios.guardar(usuario)
        if self.xp is not None:
            self.xp.por_aval(usuario.id)
            usuario.xp = self.xp.total(usuario.id)
        return usuario, resultado

    def _parece_imagen(self, contenido: bytes) -> bool:
        if not contenido or len(contenido) < 12:
            return False
        for firma, tipo in _FIRMAS_IMAGEN:
            if contenido.startswith(firma):
                if tipo == "webp":
                    return contenido[8:12] == b"WEBP"
                return True
        return False
