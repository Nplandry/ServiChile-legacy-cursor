
const MarketMonetizacion = {
  STORAGE_REBOTE: 'servichile.rebote.vistas',
  STORAGE_PAGO: 'servichile.pago.informe',
  STORAGE_PAGO_RETORNO: 'servichile.pago.informe.retorno',
  STORAGE_PRINT: 'servichile.pago.informe.print',
  _confirmandoPago: false,

  PRECIO_INFORME: 9990,
  PRECIO_PLAN: 89990,
  _catalogoCargado: false,

  indiceDe(n) {
    if (n == null || n.indice_transparencia == null || n.indice_transparencia === '') {
      return {
        ok: false,
        nota: null,
        caso: 'Sin índice de transparencia (la ficha aún no tiene score).'
      };
    }
    const v = Number(n.indice_transparencia);
    if (!Number.isFinite(v)) {
      return {
        ok: false,
        nota: null,
        caso: 'Índice de transparencia inválido.'
      };
    }
    if (v === 0) {
      return {
        ok: false,
        nota: '0.0',
        caso: 'Índice 0 - sin señales o sin puntaje acumulado.'
      };
    }
    return { ok: true, nota: v.toFixed(1), caso: null };
  },

  datosCatalogo(n) {
    const indice = MarketMonetizacion.indiceDe(n);
    return {
      nota: indice.nota,
      casoIndice: indice.caso,
      indiceOk: indice.ok,
      precio: MarketMonetizacion.PRECIO_INFORME,
      precioTxt:
        '$' + MarketMonetizacion.formatoClp(MarketMonetizacion.PRECIO_INFORME) + ' CLP'
    };
  },

  datosDemo(n) {
    return MarketMonetizacion.datosCatalogo(n);
  },

  async cargarCatalogo() {
    if (MarketMonetizacion._catalogoCargado) return MarketMonetizacion.PRECIO_INFORME;
    try {
      const res = await Auth.request('/v1/pagos/informe/catalogo');
      if (res.ok && res.data && res.data.monto) {
        MarketMonetizacion.PRECIO_INFORME = Number(res.data.monto) || MarketMonetizacion.PRECIO_INFORME;
        MarketMonetizacion._catalogoCargado = true;
      }
    } catch (_) {

    }
    return MarketMonetizacion.PRECIO_INFORME;
  },

  async cargarResumenCompras() {
    const sesion = typeof Auth !== 'undefined' ? Auth.getCurrentUser() : null;
    if (!sesion || !sesion.token) return null;
    const res = await Auth.request('/v1/pagos/informe/resumen', {
      token: sesion.token
    });
    if (!res.ok) return null;
    return res.data || null;
  },

  registrarVistaRebote(n) {
    let mapa = {};
    try {
      mapa = JSON.parse(localStorage.getItem(MarketMonetizacion.STORAGE_REBOTE) || '{}') || {};
    } catch {
      mapa = {};
    }
    const id = String(n.id);
    const prev = mapa[id] || { vistas: 0, nombre: n.nombre };
    const indice = MarketMonetizacion.indiceDe(n);
    prev.vistas += 1;
    prev.nombre = n.nombre;
    prev.nota = indice.nota;
    prev.casoIndice = indice.caso;
    mapa[id] = prev;
    localStorage.setItem(MarketMonetizacion.STORAGE_REBOTE, JSON.stringify(mapa));
    return prev;
  },

  panel(n) {
    const cat = MarketMonetizacion.datosCatalogo(n);
    const wrap = document.createElement('aside');
    wrap.className = 'paywall';
    wrap.setAttribute('aria-label', 'Informe de proveedor');

    const titulo = document.createElement('h3');
    titulo.className = 'paywall__titulo';
    titulo.textContent = 'Informe de proveedor';

    const lead = document.createElement('p');
    lead.className = 'paywall__lead';
    lead.textContent =
      'Reporte de transparencia de ' +
      (n.nombre || 'esta empresa') +
      ', con QR de verificación y PDF. Entrega al confirmar el pago.';

    const precio = document.createElement('p');
    precio.className = 'paywall__precio';
    precio.innerHTML =
      '<strong>' +
      cat.precioTxt +
      '</strong> <span>pago único</span>';

    if (cat.casoIndice) {
      const aviso = document.createElement('p');
      aviso.className = 'paywall__lead paywall__lead--aviso';
      aviso.textContent = cat.casoIndice;
      wrap._avisoIndice = aviso;
    }

    const unlock = document.createElement('button');
    unlock.type = 'button';
    unlock.className = 'paywall__unlock';
    unlock.textContent = 'Comprar informe ' + cat.precioTxt;
    unlock.addEventListener('click', async () => {
      const reabierto = await MarketMonetizacion.reabrirInformeSiComprado(n);
      if (!reabierto) MarketMonetizacion.abrirCheckout(n, { fase: 'resumen' });
    });

    wrap.append(titulo, lead, precio);
    if (wrap._avisoIndice) wrap.appendChild(wrap._avisoIndice);
    wrap.append(unlock);
    wrap._demo = cat;
    wrap._negocio = n;
    MarketMonetizacion.cargarCatalogo().then(() => {
      const actual = MarketMonetizacion.datosCatalogo(n);
      precio.innerHTML =
        '<strong>' + actual.precioTxt + '</strong> <span>pago único</span>';
      if (!unlock.disabled && unlock.textContent.indexOf('Ver informe') < 0) {
        unlock.textContent = 'Comprar informe ' + actual.precioTxt;
      }
    });
    MarketMonetizacion.consultarAcceso(n).then((data) => {
      if (!data || !data.autorizado || !unlock.isConnected) return;
      unlock.disabled = false;
      unlock.textContent = 'Ver informe comprado';
    });
    return wrap;
  },

  formatoClp(n) {
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  },

  urlRetornoPago() {
    const base =
      window.location.origin +
      (window.location.pathname || '/index.html');
    return base + (base.indexOf('?') >= 0 ? '&' : '?') + 'pago=retorno';
  },

  mensajeErrorPago(err, fallback, reclamo) {
    const partes = [];
    if (err && err.mensaje) partes.push(err.mensaje);
    else if (typeof err === 'string' && err) partes.push(err);
    else if (fallback) partes.push(fallback);
    const buy = err && err.buy_order;
    if (buy) partes.push('Orden: ' + buy);
    const codigo = err && err.codigo;
    if (codigo) partes.push('Código: ' + codigo);
    const canal = reclamo || (err && err.reclamo) || null;
    if (canal && canal.instruccion) partes.push(canal.instruccion);
    else if (canal && canal.email) {
      partes.push(
        'Reclame en ' +
          canal.email +
          (canal.whatsapp ? ' o WhatsApp ' + canal.whatsapp : '') +
          (buy ? ' con la orden ' + buy : '')
      );
    }
    return partes.join(' ') || 'No se pudo completar el pago.';
  },

  mensajeCortoPago(err, fallback) {
    if (err && err.mensaje) return err.mensaje;
    if (typeof err === 'string' && err) return err;
    return fallback || 'No se pudo completar el pago.';
  },

  redirigirWebpay(url, token) {
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = url;
    form.acceptCharset = 'UTF-8';
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = 'token_ws';
    input.value = token;
    form.appendChild(input);
    document.body.appendChild(form);
    form.submit();
  },

  negocioDesdePendiente(pendiente, fallbackId) {
    const id = (pendiente && pendiente.business_id) || fallbackId;
    const lista =
      typeof Market !== 'undefined' && Market.negocios ? Market.negocios : [];
    const hallado = lista.find((x) => String(x.id) === String(id));
    if (hallado) return hallado;
    return {
      id: id,
      nombre: (pendiente && pendiente.nombre) || 'Proveedor'
    };
  },

  cerrarCheckout() {
    const el = document.getElementById('checkoutSheet');
    if (el) el.remove();
    document.body.classList.remove('checkout-sheet-open');
    MarketMonetizacion._checkout = null;
  },

  async abrirCheckout(n, opts) {
    opts = opts || {};
    await MarketMonetizacion.cargarCatalogo();
    const demo = MarketMonetizacion.datosCatalogo(n);
    MarketMonetizacion.cerrarCheckout();
    MarketMonetizacion.cerrarModal();

    const overlay = document.createElement('div');
    overlay.id = 'checkoutSheet';
    overlay.className = 'checkout-sheet';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-labelledby', 'checkoutSheetTitulo');

    const sheet = document.createElement('div');
    sheet.className = 'checkout-sheet__panel';

    const grab = document.createElement('div');
    grab.className = 'checkout-sheet__grab';
    grab.setAttribute('aria-hidden', 'true');

    const head = document.createElement('div');
    head.className = 'checkout-sheet__head';
    const h = document.createElement('h3');
    h.id = 'checkoutSheetTitulo';
    h.textContent = 'Compra';
    const sub = document.createElement('p');
    sub.className = 'checkout-sheet__sub';
    sub.textContent = n.nombre || 'Informe de proveedor';
    const cerrar = document.createElement('button');
    cerrar.type = 'button';
    cerrar.className = 'checkout-sheet__cerrar';
    cerrar.setAttribute('aria-label', 'Cerrar');
    cerrar.textContent = '×';
    cerrar.addEventListener('click', MarketMonetizacion.cerrarCheckout);
    head.append(h, sub, cerrar);

    const body = document.createElement('div');
    body.className = 'checkout-sheet__body';
    body.id = 'checkoutSheetBody';

    sheet.append(grab, head, body);
    overlay.appendChild(sheet);
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) MarketMonetizacion.cerrarCheckout();
    });
    document.body.classList.add('checkout-sheet-open');
    document.body.appendChild(overlay);

    MarketMonetizacion._checkout = { n: n, demo: demo, body: body, overlay: overlay };
    MarketMonetizacion.pintarCheckout(opts.fase || 'resumen', opts);
  },

  pintarCheckout(fase, opts) {
    opts = opts || {};
    const ctx = MarketMonetizacion._checkout;
    if (!ctx || !ctx.body) return;
    const n = ctx.n;
    const demo = ctx.demo || MarketMonetizacion.datosDemo(n);
    const body = ctx.body;
    MarketMonetizacion.limpiar(body);

    if (fase === 'resumen') {
      const resumen = document.createElement('div');
      resumen.className = 'checkout-sheet__resumen';

      const item = document.createElement('div');
      item.className = 'checkout-sheet__item';
      const nombre = document.createElement('p');
      nombre.className = 'checkout-sheet__item-nombre';
      nombre.textContent = 'Informe de proveedor';
      const detalle = document.createElement('p');
      detalle.className = 'checkout-sheet__item-detalle';
      detalle.textContent =
        'Ficha de ' +
        (n.nombre || 'la empresa') +
        ' PDF QR de verificación comprobante al correo de su cuenta';
      const monto = document.createElement('p');
      monto.className = 'checkout-sheet__item-precio';
      monto.textContent = demo.precioTxt;
      item.append(nombre, detalle, monto);

      const incluye = document.createElement('ul');
      incluye.className = 'checkout-sheet__incluye';
      [
        'Reporte de transparencia (índice, documentos y señales públicas).',
        'QR para verificar identidad en terreno o reuniones.',
        'Entrega inmediata tras autorizar el pago.'
      ].forEach((t) => {
        const li = document.createElement('li');
        li.textContent = t;
        incluye.appendChild(li);
      });

      const metodo = document.createElement('p');
      metodo.className = 'checkout-sheet__metodo';
      metodo.textContent = 'Pago seguro con Webpay';

      const pagar = document.createElement('button');
      pagar.type = 'button';
      pagar.className = 'checkout-sheet__cta';
      pagar.textContent = 'Pagar ' + demo.precioTxt;
      pagar.addEventListener('click', () => MarketMonetizacion.iniciarPagoDesdeCheckout());

      resumen.append(item, incluye, metodo, pagar);
      body.appendChild(resumen);
      return;
    }

    if (fase === 'redirigiendo') {
      body.appendChild(
        MarketMonetizacion.checkoutEstado({
          titulo: 'Abriendo Webpay…',
          texto:
            'Orden ' +
            (opts.orden || '-') +
            '. Complete el pago y volverá a ServiChile automáticamente.',
          spinner: true
        })
      );
      return;
    }

    if (fase === 'login') {
      body.appendChild(
        MarketMonetizacion.checkoutEstado({
          titulo: 'Inicie sesión para entregar el informe',
          texto:
            'El pago quedó registrado' +
            (opts.orden ? ' (orden ' + opts.orden + ')' : '') +
            '. Entre con la misma cuenta y se confirma la compra aquí.',
          orden: opts.orden
        })
      );
      return;
    }

    if (fase === 'confirmando') {
      body.appendChild(
        MarketMonetizacion.checkoutEstado({
          titulo: 'Confirmando pago…',
          texto: 'Estamos validando la autorización con Webpay.',
          spinner: true,
          orden: opts.orden
        })
      );
      return;
    }

    if (fase === 'exito') {
      const wrap = MarketMonetizacion.checkoutEstado({
        titulo: 'Pago autorizado',
        texto:
          'Orden ' +
          (opts.orden || '-') +
          '. Su informe está listo.',
        ok: true,
        orden: opts.orden
      });
      const abrir = document.createElement('button');
      abrir.type = 'button';
      abrir.className = 'checkout-sheet__cta';
      abrir.textContent = 'Ver informe';
      abrir.addEventListener('click', async () => {
        abrir.disabled = true;
        await MarketMonetizacion.entregarInformePagado(n, opts.pago || {});
        MarketMonetizacion.cerrarCheckout();
      });
      const listo = document.createElement('button');
      listo.type = 'button';
      listo.className = 'checkout-sheet__secundario';
      listo.textContent = 'Cerrar';
      listo.addEventListener('click', MarketMonetizacion.cerrarCheckout);
      wrap.append(abrir, listo);
      body.appendChild(wrap);
      return;
    }

    if (fase === 'cancelado') {
      body.appendChild(
        MarketMonetizacion.checkoutEstado({
          titulo: 'Pago cancelado',
          texto:
            'No se realizó el cobro' +
            (opts.orden ? '. Orden ' + opts.orden : '') +
            '. Puede intentarlo de nuevo cuando quiera.',
          orden: opts.orden
        })
      );
      const reintentar = document.createElement('button');
      reintentar.type = 'button';
      reintentar.className = 'checkout-sheet__cta';
      reintentar.textContent = 'Volver a intentar';
      reintentar.addEventListener('click', () =>
        MarketMonetizacion.pintarCheckout('resumen')
      );
      body.firstChild.appendChild(reintentar);
      return;
    }

    const errWrap = MarketMonetizacion.checkoutEstado({
      titulo: 'No se pudo completar la compra',
      texto: opts.mensaje || 'Intente de nuevo o contacte soporte con su orden.',
      orden: opts.orden,
      reclamo: opts.reclamo,
      error: true
    });
    const retry = document.createElement('button');
    retry.type = 'button';
    retry.className = 'checkout-sheet__cta';
    retry.textContent = 'Reintentar pago';
    retry.addEventListener('click', () => MarketMonetizacion.pintarCheckout('resumen'));
    const cerrar = document.createElement('button');
    cerrar.type = 'button';
    cerrar.className = 'checkout-sheet__secundario';
    cerrar.textContent = 'Cerrar';
    cerrar.addEventListener('click', MarketMonetizacion.cerrarCheckout);
    errWrap.append(retry, cerrar);
    body.appendChild(errWrap);
  },

  checkoutEstado(cfg) {
    const wrap = document.createElement('div');
    wrap.className =
      'checkout-sheet__estado' +
      (cfg.error ? ' checkout-sheet__estado--error' : '') +
      (cfg.ok ? ' checkout-sheet__estado--ok' : '');
    if (cfg.spinner) {
      const spin = document.createElement('div');
      spin.className = 'checkout-sheet__spinner';
      spin.setAttribute('aria-hidden', 'true');
      wrap.appendChild(spin);
    }
    const h = document.createElement('h4');
    h.textContent = cfg.titulo || '';
    const p = document.createElement('p');
    p.textContent = cfg.texto || '';
    wrap.append(h, p);
    if (cfg.orden) {
      const ord = document.createElement('p');
      ord.className = 'checkout-sheet__orden';
      ord.textContent = 'Orden ' + cfg.orden;
      wrap.appendChild(ord);
    }
    if (cfg.reclamo) {
      const r = document.createElement('p');
      r.className = 'checkout-sheet__reclamo';
      r.textContent =
        cfg.reclamo.instruccion ||
        ('Soporte: ' +
          (cfg.reclamo.email || '') +
          (cfg.reclamo.whatsapp ? ' WhatsApp ' + cfg.reclamo.whatsapp : ''));
      wrap.appendChild(r);
    }
    return wrap;
  },

  async iniciarPagoDesdeCheckout() {
    const ctx = MarketMonetizacion._checkout;
    if (!ctx || !ctx.n) return;
    const n = ctx.n;
    const sesion = typeof Auth !== 'undefined' ? Auth.getCurrentUser() : null;
    if (!sesion || !sesion.token) {
      MarketMonetizacion.pintarCheckout('login', {
        orden: null,
        mensaje: 'Debe iniciar sesión para pagar.'
      });
      return;
    }
    MarketMonetizacion.pintarCheckout('redirigiendo', { orden: '…' });
    const res = await Auth.request('/v1/pagos/informe', {
      method: 'POST',
      token: sesion.token,
      body: {
        business_id: n.id,
        return_url: MarketMonetizacion.urlRetornoPago()
      }
    });
    if (!res.ok) {
      const detail =
        res.data && res.data.detail && typeof res.data.detail === 'object'
          ? res.data.detail
          : null;
      if (detail && detail.codigo === 'ya_comprado') {
        const ok = await MarketMonetizacion.reabrirInformeSiComprado(n);
        if (ok) return;
      }
      MarketMonetizacion.pintarCheckout('error', {
        mensaje: MarketMonetizacion.mensajeCortoPago(
          detail || { mensaje: res.error },
          res.error || 'No se pudo iniciar el pago.'
        ),
        orden: detail && detail.buy_order,
        reclamo: detail && detail.reclamo
      });
      return;
    }
    const data = res.data || {};
    MarketMonetizacion.guardarPagoPendiente(data, n);
    MarketMonetizacion.pintarCheckout('redirigiendo', { orden: data.buy_order });
    MarketMonetizacion.redirigirWebpay(data.url, data.token);
  },

  comprarInforme(n) {
    MarketMonetizacion.abrirCheckout(n, { fase: 'resumen' });
  },

  limpiarUrlRetornoPago() {
    try {
      const u = new URL(window.location.href);
      [
        'pago',
        'token_ws',
        'TBK_TOKEN',
        'TBK_ORDEN_COMPRA',
        'TBK_ID_SESION',
        'producto'
      ].forEach((k) => u.searchParams.delete(k));
      window.history.replaceState({}, '', u.pathname + u.search + u.hash);
    } catch (_) {

    }
  },

  capturarRetornoDesdeUrl() {
    const params = new URLSearchParams(window.location.search || '');
    if (params.get('pago') !== 'retorno') return false;
    const pendiente = MarketMonetizacion.leerPagoPendiente() || {};
    MarketMonetizacion.guardarRetornoPago({
      token_ws: params.get('token_ws'),
      tbk_token: params.get('TBK_TOKEN'),
      tbk_orden: params.get('TBK_ORDEN_COMPRA') || pendiente.buy_order || null,
      producto:
        params.get('producto') || pendiente.producto || null
    });

    MarketMonetizacion.limpiarUrlRetornoPago();
    return true;
  },

  esRetornoPublicacion() {
    const pendiente = MarketMonetizacion.leerPagoPendiente() || {};
    const retorno = MarketMonetizacion.leerRetornoPago() || {};
    try {
      if (
        new URLSearchParams(window.location.search || '').get('producto') ===
        'publicacion'
      ) {
        return true;
      }
    } catch (_) {

    }
    return (
      pendiente.producto === 'publicacion' ||
      retorno.producto === 'publicacion'
    );
  },

  hayRetornoPendiente() {
    const g = MarketMonetizacion.leerRetornoPago() || {};
    return !!(g.token_ws || g.tbk_token);
  },

  async procesarRetornoPago() {
    MarketMonetizacion.capturarRetornoDesdeUrl();
    const params = new URLSearchParams(window.location.search || '');
    const guardado = MarketMonetizacion.leerRetornoPago() || {};
    const desdeUrl = params.get('pago') === 'retorno';
    if (!desdeUrl && !guardado.token_ws && !guardado.tbk_token) return false;

    if (MarketMonetizacion.esRetornoPublicacion()) {
      const asegurarPerfil = async () => {
        if (typeof PerfilEmpresa === 'undefined' && typeof Carga !== 'undefined') {
          const v =
            (typeof Auth !== 'undefined' && Auth.APP_VERSION) ||
            (typeof window !== 'undefined' && window.SERVICHILE_APP_VERSION) ||
            '219';
          await Carga.script('js/modules/perfil-empresa.js?v=' + v);
        }
        if (
          typeof PerfilEmpresa !== 'undefined' &&
          PerfilEmpresa.procesarRetornoPublicacion
        ) {
          return PerfilEmpresa.procesarRetornoPublicacion();
        }
        return false;
      };
      return asegurarPerfil();
    }

    const tokenWs = params.get('token_ws') || guardado.token_ws || null;
    const tbkToken = params.get('TBK_TOKEN') || guardado.tbk_token || null;
    const tbkOrden = params.get('TBK_ORDEN_COMPRA') || guardado.tbk_orden || null;
    const pendiente = MarketMonetizacion.leerPagoPendiente() || {};
    const sesion = typeof Auth !== 'undefined' ? Auth.getCurrentUser() : null;
    const negocio = MarketMonetizacion.negocioDesdePendiente(pendiente);
    const orden = pendiente.buy_order || tbkOrden || null;

    function limpiarUrl() {
      MarketMonetizacion.limpiarUrlRetornoPago();
    }

    if (!sesion || !sesion.token) {
      limpiarUrl();
      const status = document.getElementById('loginStatus');
      if (status) {
        status.textContent =
          'Pago recibido' +
          (orden ? ' (orden ' + orden + ')' : '') +
          '. Inicie sesión para entregar el informe.';
      }
      return true;
    }

    MarketMonetizacion.abrirCheckout(negocio, {
      fase: 'confirmando',
      orden: orden
    });

    if (tbkToken && !tokenWs) {
      const buy = orden || '';
      if (buy) {
        await Auth.request('/v1/pagos/informe/anular', {
          method: 'POST',
          token: sesion.token,
          body: { buy_order: buy, motivo: 'Cancelado o abortado en Webpay' }
        });
      }
      MarketMonetizacion.limpiarPagoPendiente();
      limpiarUrl();
      MarketMonetizacion.pintarCheckout('cancelado', {
        orden: buy || null,
        reclamo: pendiente.reclamo
      });
      return true;
    }

    if (MarketMonetizacion._confirmandoPago) return true;
    MarketMonetizacion._confirmandoPago = true;
    try {
      let res;
      if (tokenWs) {
        res = await Auth.request('/v1/pagos/informe/confirmar', {
          method: 'POST',
          token: sesion.token,
          body: { token: tokenWs }
        });
      } else if (orden) {

        res = await Auth.request('/v1/pagos/informe/recuperar', {
          method: 'POST',
          token: sesion.token,
          body: { buy_order: orden }
        });
      } else {
        MarketMonetizacion.limpiarPagoPendiente();
        limpiarUrl();
        MarketMonetizacion.pintarCheckout('error', {
          mensaje: 'No recibimos la autorización del pago. Intente de nuevo.',
          orden: orden,
          reclamo: pendiente.reclamo
        });
        return true;
      }
      limpiarUrl();
      if (!res.ok) {
        const detail =
          res.data && res.data.detail && typeof res.data.detail === 'object'
            ? res.data.detail
            : null;
        MarketMonetizacion.pintarCheckout('error', {
          mensaje: MarketMonetizacion.mensajeCortoPago(
            detail || { mensaje: res.error },
            res.error || 'No se pudo confirmar el pago.'
          ),
          orden: (detail && detail.buy_order) || orden,
          reclamo: (detail && detail.reclamo) || pendiente.reclamo
        });
        return true;
      }
      const data = res.data || {};
      if (!data.autorizado) {
        MarketMonetizacion.limpiarPagoPendiente();
        MarketMonetizacion.pintarCheckout('error', {
          mensaje: data.error_detalle || 'El pago no fue autorizado.',
          orden: data.buy_order || orden,
          reclamo: data.reclamo || pendiente.reclamo
        });
        return true;
      }

      const negocioOk = MarketMonetizacion.negocioDesdePendiente(
        pendiente,
        data.business_id
      );
      if (MarketMonetizacion._checkout) MarketMonetizacion._checkout.n = negocioOk;
      if (!data.print_token) {
        const acceso = await MarketMonetizacion.consultarAcceso(negocioOk);
        if (acceso && acceso.print_token) {
          data = Object.assign({}, data, acceso);
        }
      }
      if (!data.print_token) {
        MarketMonetizacion.pintarCheckout('error', {
          mensaje:
            'Pago autorizado, pero falta el sello de impresión. Reabra el informe comprado o contacte soporte.',
          orden: data.buy_order || orden,
          reclamo: data.reclamo || pendiente.reclamo
        });
        return true;
      }
      MarketMonetizacion.guardarPrintToken(
        data.business_id,
        data.print_token,
        data.buy_order
      );
      MarketMonetizacion.limpiarPagoPendiente();
      MarketMonetizacion.revelarPaywallSiVisible();
      await MarketMonetizacion.precargarReputacion(data.business_id);
      MarketMonetizacion.pintarCheckout('exito', {
        orden: data.buy_order,
        pago: data
      });
      const resumen = await MarketMonetizacion.cargarResumenCompras();
      if (resumen && resumen.autorizadas_mes >= 2) {
        MarketMonetizacion.mostrarPlanRecurrente(resumen);
      }
      return true;
    } finally {
      MarketMonetizacion._confirmandoPago = false;
    }
  },

  async precargarReputacion(businessId) {
    const sesion = typeof Auth !== 'undefined' ? Auth.getCurrentUser() : null;
    if (!sesion || !sesion.token || !businessId) return null;
    const res = await Auth.request(
      '/v1/businesses/' + encodeURIComponent(businessId) + '/reputation',
      { token: sesion.token }
    );
    if (!res.ok || !res.data) return null;
    if (typeof Market !== 'undefined') {
      if (!Market._reps) Market._reps = {};
      Market._reps[String(businessId)] = res.data;
    }
    return res.data;
  },

  async entregarInformePagado(n, pago) {
    if (!(await MarketMonetizacion.asegurarReporteEmpresa())) {
      MarketMonetizacion.pintarCheckout('error', {
        mensaje:
          'El pago está ok, pero no se pudo abrir el PDF. Guarde la orden y contacte soporte.',
        orden: pago && pago.buy_order,
        reclamo: pago && pago.reclamo
      });
      return false;
    }
    const sesion = typeof Auth !== 'undefined' ? Auth.getCurrentUser() : null;
    if (!sesion || !sesion.token || !n || !n.id) {
      MarketMonetizacion.toast('Inicie sesión para abrir el informe comprado.');
      return false;
    }
    let pagoOk = pago || null;
    const guardado = MarketMonetizacion.leerPrintToken(n.id);
    let printToken =
      (pagoOk && pagoOk.print_token) ||
      (guardado && guardado.print_token) ||
      null;
    if (!printToken) {
      const acceso = await MarketMonetizacion.consultarAcceso(n);
      if (acceso && acceso.print_token) {
        pagoOk = acceso;
        printToken = acceso.print_token;
        MarketMonetizacion.guardarPrintToken(
          n.id,
          acceso.print_token,
          acceso.buy_order
        );
      }
    }
    if (!printToken) {
      MarketMonetizacion.toast(
        'Falta el sello de impresión. Reabra el informe desde «Ver informe comprado».'
      );
      return false;
    }
    const ver = await Auth.request('/v1/pagos/informe/verificar-print', {
      method: 'POST',
      token: sesion.token,
      body: { business_id: n.id, print_token: printToken }
    });
    if (!ver.ok || !ver.data || !ver.data.autorizado || !ver.data.print_token) {
      MarketMonetizacion.pintarCheckout('error', {
        mensaje:
          (ver.data && ver.data.detail && ver.data.detail.mensaje) ||
          ver.error ||
          'No se pudo validar el sello de impresión. Reabra el informe comprado.',
        orden: (pagoOk && pagoOk.buy_order) || (guardado && guardado.buy_order),
        reclamo: pagoOk && pagoOk.reclamo
      });
      return false;
    }
    pagoOk = ver.data;
    MarketMonetizacion.guardarPrintToken(
      n.id,
      pagoOk.print_token,
      pagoOk.buy_order
    );
    let rep =
      (typeof Market !== 'undefined' && Market._reps && Market._reps[String(n.id)]) ||
      null;
    if (!rep) rep = await MarketMonetizacion.precargarReputacion(n.id);
    const ok = await ReporteEmpresa.imprimirFicha(n, rep, {
      autorizado: true,
      buy_order: pagoOk.buy_order,
      payload: pagoOk.qr_payload || null,
      expires_at: pagoOk.expires_at || null,
      print_token: pagoOk.print_token
    });
    if (!ok) return false;
    MarketMonetizacion.toast(
      pagoOk.enviado
        ? 'Informe abierto. Comprobante enviado a ' +
            (pagoOk.destino || 'su correo') +
            '.'
        : 'Informe abierto. Si no llega el comprobante al correo, revise spam o contacte soporte.'
    );
    return true;
  },

  async consultarAcceso(n) {
    const sesion = typeof Auth !== 'undefined' ? Auth.getCurrentUser() : null;
    if (!sesion || !sesion.token || !n || !n.id) return null;
    const res = await Auth.request(
      '/v1/pagos/informe/acceso/' + encodeURIComponent(n.id),
      { token: sesion.token }
    );
    if (!res.ok || !res.data || !res.data.autorizado) return null;
    return res.data;
  },

  async reabrirInformeSiComprado(n) {
    const data = await MarketMonetizacion.consultarAcceso(n);
    if (!data) return false;
    if (data.print_token) {
      MarketMonetizacion.guardarPrintToken(
        data.business_id || n.id,
        data.print_token,
        data.buy_order
      );
    }
    await MarketMonetizacion.abrirCheckout(n, {
      fase: 'exito',
      orden: data.buy_order,
      pago: data
    });
    return true;
  },

  revelarPaywallSiVisible() {
    const panel = document.querySelector('.paywall');
    if (!panel) return;
    const unlock = panel.querySelector('.paywall__unlock');
    if (unlock) {
      unlock.disabled = true;
      unlock.textContent = 'Informe comprado';
    }
  },

  mostrarRebote(n, demo) {
    const vista = MarketMonetizacion.registrarVistaRebote(n);
    const total = Math.max(3, vista.vistas);
    const notaTxt =
      vista.nota != null
        ? 'Nota actual: ' + vista.nota + ' ⭐'
        : vista.casoIndice || demo.casoIndice || 'Sin índice de transparencia';
    MarketMonetizacion.toast(
      'Aviso al titular de ' +
        n.nombre +
        ': «' +
        total +
        ' empresas revisaron el perfil esta semana (' +
        notaTxt +
        ').»'
    );
  },

  mostrarPlanRecurrente(resumen) {
    const gastado =
      (resumen && resumen.gastado_mes) ||
      MarketMonetizacion.PRECIO_INFORME * 2;
    MarketMonetizacion.abrirBanner(
      'Este mes lleva $' +
        MarketMonetizacion.formatoClp(gastado) +
        ' en informes. El Plan Empresas (próximamente, $' +
        MarketMonetizacion.formatoClp(MarketMonetizacion.PRECIO_PLAN) +
        '/mes) incluirá informes ilimitados y alertas.',
      'Avisarme cuando esté listo'
    );
  },

  abrirBanner(texto, ctaLabel) {
    let banner = document.getElementById('paywallBanner');
    if (banner) banner.remove();
    banner = document.createElement('div');
    banner.id = 'paywallBanner';
    banner.className = 'paywall-banner';
    banner.setAttribute('role', 'status');
    const p = document.createElement('p');
    p.textContent = texto;
    const acciones = document.createElement('div');
    acciones.className = 'paywall-banner__acciones';
    const cta = document.createElement('button');
    cta.type = 'button';
    cta.className = 'paywall-banner__cta';
    cta.textContent = ctaLabel;
    cta.addEventListener('click', () => {
      MarketMonetizacion.toast(
        'Plan Empresas: próximamente. Escríbanos a pagos@servichile.cl si quiere prioridad.'
      );
      banner.remove();
    });
    const cerrar = document.createElement('button');
    cerrar.type = 'button';
    cerrar.className = 'paywall-banner__cerrar';
    cerrar.textContent = 'Ahora no';
    cerrar.addEventListener('click', () => banner.remove());
    acciones.append(cta, cerrar);
    banner.append(p, acciones);
    document.body.appendChild(banner);
  },

  toast(msg) {
    let el = document.getElementById('paywallToast');
    if (!el) {
      el = document.createElement('div');
      el.id = 'paywallToast';
      el.className = 'paywall-toast';
      el.setAttribute('role', 'status');
      document.body.appendChild(el);
    }
    el.textContent = msg;
    el.hidden = false;
    clearTimeout(MarketMonetizacion._toastTimer);
    MarketMonetizacion._toastTimer = setTimeout(() => {
      el.hidden = true;
    }, 7000);
  },

  async asegurarReporteEmpresa() {
    if (typeof ReporteEmpresa !== 'undefined' && ReporteEmpresa.imprimirFicha) return true;
    if (typeof Carga === 'undefined' || !Carga.script) return false;
    const v =
      (typeof Auth !== 'undefined' && Auth.APP_VERSION) ||
      (typeof window !== 'undefined' && window.SERVICHILE_APP_VERSION) ||
      '219';
    await Carga.script('js/modules/reporte-empresa.js?v=' + v);
    await Carga.script('js/modules/reporte-qr.js?v=' + v);
    return typeof ReporteEmpresa !== 'undefined' && !!ReporteEmpresa.imprimirFicha;
  },

  async entregarInforme(n, statusEl) {

    MarketMonetizacion.abrirCheckout(n, { fase: 'resumen' });
    if (statusEl) statusEl.textContent = 'Complete el pago para obtener el informe.';
    return false;
  },

  async descargarInforme(n, statusEl) {
    return MarketMonetizacion.entregarInforme(n, statusEl);
  },

  limpiar(el) {
    while (el.firstChild) el.removeChild(el.firstChild);
  }
};
