# Bóveda de confianza Chile (`ca_chile.pem`)

Archivo maestro con certificados **públicos** (raíz e intermedios) de entidades
acreditadas para Firma Electrónica Avanzada en Chile.

- No contiene llaves privadas.
- Se carga una vez al iniciar el backend en un `ValidationContext` offline.
- Regenerar con `python -m scripts.construir_ca_chile <carpetas...> -o app/infraestructura/certs/ca_chile.pem`.
