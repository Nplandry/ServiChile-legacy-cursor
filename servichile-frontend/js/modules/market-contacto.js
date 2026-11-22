
(function () {
  if (typeof MarketMonetizacion === 'undefined') {
    throw new Error('market-contacto requiere market-monetizacion.js');
  }
  Object.assign(MarketMonetizacion, {
  interceptarContacto(n, estadoEl) {
    MarketMonetizacion.abrirModalIntencion(n, estadoEl);
  },

  cerrarModal() {
    const el = document.getElementById('paywallModal');
    if (el) el.remove();
    document.body.classList.remove('paywall-modal-open');
  },

  abrirModalIntencion(n, estadoEl) {
    MarketMonetizacion.cerrarModal();
    const demo = MarketMonetizacion.datosDemo(n);
    const overlay = document.createElement('div');
    overlay.id = 'paywallModal';
    overlay.className = 'paywall-modal';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-labelledby', 'paywallModalTitulo');

    const dialog = document.createElement('div');
    dialog.className = 'paywall-modal__dialog';

    const head = document.createElement('div');
    head.className = 'paywall-modal__head';
    const h = document.createElement('h3');
    h.id = 'paywallModalTitulo';
    h.textContent = 'Antes de contactar a ' + n.nombre;
    const cerrar = document.createElement('button');
    cerrar.type = 'button';
    cerrar.className = 'paywall-modal__cerrar';
    cerrar.setAttribute('aria-label', 'Cerrar');
    cerrar.textContent = '×';
    cerrar.addEventListener('click', MarketMonetizacion.cerrarModal);
    head.append(h, cerrar);

    const body = document.createElement('div');
    body.className = 'paywall-modal__body';
    body.id = 'paywallModalBody';

    const respuestas = { proposito: null, monto: null, plazo: null };

    function pintarPreguntas() {
      MarketMonetizacion.limpiar(body);
      body.appendChild(
        MarketMonetizacion.pregunta(
          '¿Para qué necesita contactar a esta empresa?',
          [
            { id: 'cotizar', label: 'Cotizar un proyecto / servicio' },
            { id: 'proveedor', label: 'Evaluarla como proveedor fijo' },
            { id: 'licitacion', label: 'Licitación formal' }
          ],
          (id) => {
            respuestas.proposito = id;
            pintarMonto();
          }
        )
      );
    }

    function pintarMonto() {
      MarketMonetizacion.limpiar(body);
      body.appendChild(
        MarketMonetizacion.pregunta(
          '¿Cuál es el monto aproximado de la operación?',
          [
            { id: 'bajo', label: 'Menos de $1.000.000' },
            { id: 'medio', label: 'Entre $1.000.000 y $5.000.000' },
            { id: 'alto', label: 'Más de $5.000.000' }
          ],
          (id) => {
            respuestas.monto = id;
            pintarPlazo();
          }
        )
      );
    }

    function pintarPlazo() {
      MarketMonetizacion.limpiar(body);
      body.appendChild(
        MarketMonetizacion.pregunta(
          '¿Cuándo planea cerrar este trato?',
          [
            { id: 'semana', label: 'Esta semana (Presupuesto aprobado)' },
            { id: 'mes', label: 'Este mes (En evaluación)' },
            { id: 'cotizando', label: 'Solo cotizando' }
          ],
          (id) => {
            respuestas.plazo = id;
            const caliente =
              (respuestas.monto === 'medio' || respuestas.monto === 'alto') &&
              respuestas.plazo === 'semana';
            if (caliente) {
              MarketMonetizacion.pintarEscenarioA(body, n, demo, estadoEl, respuestas);
            } else {
              MarketMonetizacion.pintarEscenarioB(body, n, demo, estadoEl, respuestas);
            }
          }
        )
      );
    }

    pintarPreguntas();
    dialog.append(head, body);
    overlay.appendChild(dialog);
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) MarketMonetizacion.cerrarModal();
    });
    document.body.classList.add('paywall-modal-open');
    document.body.appendChild(overlay);
  },

  pregunta(titulo, opciones, onPick) {
    const wrap = document.createElement('div');
    wrap.className = 'paywall-q';
    const h = document.createElement('p');
    h.className = 'paywall-q__titulo';
    h.textContent = titulo;
    const lista = document.createElement('div');
    lista.className = 'paywall-q__opciones';
    opciones.forEach((op) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'paywall-q__btn';
      btn.textContent = op.label;
      btn.addEventListener('click', () => onPick(op.id));
      lista.appendChild(btn);
    });
    wrap.append(h, lista);
    return wrap;
  },

  etiquetaIntencion(clave, mapa) {
    const item = (mapa || []).find((op) => op.id === clave);
    return item ? item.label : clave || '';
  },

  mensajeContacto(n, demo, respuestas) {
    const firma = demo.indiceOk
      ? 'Nota en ServiChile: ★ ' + demo.nota
      : demo.casoIndice || 'Ficha en ServiChile';
    const proposito = MarketMonetizacion.etiquetaIntencion(respuestas && respuestas.proposito, [
      { id: 'cotizar', label: 'Cotizar un proyecto / servicio' },
      { id: 'proveedor', label: 'Evaluarla como proveedor fijo' },
      { id: 'licitacion', label: 'Licitación formal' }
    ]);
    const monto = MarketMonetizacion.etiquetaIntencion(respuestas && respuestas.monto, [
      { id: 'bajo', label: 'Menos de $1.000.000' },
      { id: 'medio', label: 'Entre $1.000.000 y $5.000.000' },
      { id: 'alto', label: 'Más de $5.000.000' }
    ]);
    const plazo = MarketMonetizacion.etiquetaIntencion(respuestas && respuestas.plazo, [
      { id: 'semana', label: 'Esta semana (Presupuesto aprobado)' },
      { id: 'mes', label: 'Este mes (En evaluación)' },
      { id: 'cotizando', label: 'Solo cotizando' }
    ]);
    return (
      'Hola ' +
      (n.nombre || '') +
      ',\n\n' +
      'Le contacto desde ServiChile (' +
      firma +
      ').\n' +
      'Motivo: ' +
      proposito +
      '\n' +
      'Monto aproximado: ' +
      monto +
      '\n' +
      'Plazo: ' +
      plazo +
      '\n\n' +
      'Quedo atento.'
    );
  },

  pintarEscenarioA(body, n, demo, estadoEl, respuestas) {
    MarketMonetizacion.pintarCierreContacto(body, n, demo, estadoEl, respuestas, {
      caliente: true
    });
  },

  pintarEscenarioB(body, n, demo, estadoEl, respuestas) {
    MarketMonetizacion.pintarCierreContacto(body, n, demo, estadoEl, respuestas, {
      caliente: false
    });
  },

  pintarCierreContacto(body, n, demo, estadoEl, respuestas, opts) {
    MarketMonetizacion.limpiar(body);
    const caliente = !!(opts && opts.caliente);
    const wrap = document.createElement('div');
    wrap.className =
      'paywall-cierre' + (caliente ? ' paywall-cierre--caliente' : ' paywall-cierre--frio');

    const aviso = document.createElement('p');
    aviso.className = 'paywall-cierre__aviso';
    aviso.textContent = caliente
      ? 'Operación relevante con ' +
        n.nombre +
        '. Elija WhatsApp o correo. Si necesita el informe de proveedor, cómprelo desde la ficha.'
      : 'Elija cómo contactar a ' +
        n.nombre +
        '. El informe de proveedor se compra aparte desde la ficha.';

    const whatsapp = document.createElement('button');
    whatsapp.type = 'button';
    whatsapp.className = 'paywall-cierre__principal';
    whatsapp.textContent = 'Contactar por WhatsApp';
    whatsapp.addEventListener('click', () => {
      MarketMonetizacion.abrirWhatsApp(n, demo, estadoEl, respuestas);
    });

    const correo = document.createElement('button');
    correo.type = 'button';
    correo.className = 'paywall-cierre__secundario';
    correo.textContent = 'Contactar por correo';
    correo.addEventListener('click', () => {
      MarketMonetizacion.abrirCorreo(n, demo, estadoEl, respuestas);
    });

    wrap.append(aviso, whatsapp, correo);

    if (caliente) {
      const especialista = document.createElement('button');
      especialista.type = 'button';
      especialista.className = 'paywall-cierre__secundario';
      especialista.textContent =
        'Que un especialista gestione esta contratación (gratis para usted - comisión al proveedor)';
      especialista.addEventListener('click', () => {
        MarketMonetizacion.mostrarRebote(n, demo);
        MarketMonetizacion.toast(
          'Solicitud registrada. Un especialista puede contactarlo; la comisión la asume el proveedor.'
        );
        if (estadoEl) estadoEl.textContent = 'Solicitud de gestión enviada.';
        MarketMonetizacion.cerrarModal();
      });
      wrap.appendChild(especialista);
    }

    body.appendChild(wrap);
  },

  abrirWhatsApp(n, demo, estadoEl, respuestas) {
    MarketMonetizacion.mostrarRebote(n, demo);
    const msg = MarketMonetizacion.mensajeContacto(n, demo, respuestas || {});
    const url = 'https://wa.me/?text=' + encodeURIComponent(msg);
    window.open(url, '_blank', 'noopener,noreferrer');
    if (estadoEl) estadoEl.textContent = 'WhatsApp abierto con su mensaje.';
    MarketMonetizacion.cerrarModal();
  },

  abrirCorreo(n, demo, estadoEl, respuestas) {
    MarketMonetizacion.mostrarRebote(n, demo);
    const cuerpo = MarketMonetizacion.mensajeContacto(n, demo, respuestas || {});
    const asunto = 'Consulta desde ServiChile: ' + (n.nombre || 'empresa');
    const url =
      'mailto:?subject=' +
      encodeURIComponent(asunto) +
      '&body=' +
      encodeURIComponent(cuerpo);
    window.location.href = url;
    if (estadoEl) estadoEl.textContent = 'Correo abierto con el borrador de contacto.';
    MarketMonetizacion.cerrarModal();
  }
  });
})();
