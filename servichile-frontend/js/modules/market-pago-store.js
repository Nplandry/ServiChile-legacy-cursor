
(function () {
  if (typeof MarketMonetizacion === 'undefined') {
    throw new Error('market-pago-store requiere market-monetizacion.js');
  }
  Object.assign(MarketMonetizacion, {
  guardarPagoPendiente(data, n) {
    const negocio = n || {};
    const bid = data.business_id || negocio.id;
    const payload = {
      buy_order: data.buy_order,
      business_id: bid != null && bid !== '' ? String(bid) : null,
      nombre: negocio.nombre || data.nombre || '',
      monto: data.monto,
      reclamo: data.reclamo || null,
      producto: data.producto || null,
      token: data.token || null,
      ts: Date.now()
    };
    try {
      sessionStorage.setItem(
        MarketMonetizacion.STORAGE_PAGO,
        JSON.stringify(payload)
      );
    } catch (_) {

    }
    try {
      localStorage.removeItem(MarketMonetizacion.STORAGE_PAGO);
    } catch (_) {

    }
  },

  leerPagoPendiente() {
    try {
      const ses = sessionStorage.getItem(MarketMonetizacion.STORAGE_PAGO);
      if (ses) return JSON.parse(ses);
    } catch (_) {

    }

    try {
      const legacy = localStorage.getItem(MarketMonetizacion.STORAGE_PAGO);
      if (legacy) {
        localStorage.removeItem(MarketMonetizacion.STORAGE_PAGO);
        sessionStorage.setItem(MarketMonetizacion.STORAGE_PAGO, legacy);
        return JSON.parse(legacy);
      }
    } catch (_) {

    }
    return null;
  },

  guardarRetornoPago(params) {
    const payload = {
      token_ws: params.token_ws || null,
      tbk_token: params.tbk_token || null,
      tbk_orden: params.tbk_orden || null,
      producto: params.producto || null,
      ts: Date.now()
    };

    try {
      sessionStorage.setItem(
        MarketMonetizacion.STORAGE_PAGO_RETORNO,
        JSON.stringify(payload)
      );
    } catch (_) {

    }
    try {
      localStorage.removeItem(MarketMonetizacion.STORAGE_PAGO_RETORNO);
    } catch (_) {

    }
  },

  leerRetornoPago() {
    try {
      const ses = sessionStorage.getItem(MarketMonetizacion.STORAGE_PAGO_RETORNO);
      if (ses) return JSON.parse(ses);
    } catch (_) {

    }

    try {
      const legacy = localStorage.getItem(MarketMonetizacion.STORAGE_PAGO_RETORNO);
      if (legacy) {
        localStorage.removeItem(MarketMonetizacion.STORAGE_PAGO_RETORNO);
        sessionStorage.setItem(MarketMonetizacion.STORAGE_PAGO_RETORNO, legacy);
        return JSON.parse(legacy);
      }
    } catch (_) {

    }
    return null;
  },

  guardarPrintToken(businessId, printToken, buyOrder) {
    if (!businessId || !printToken) return;
    let mapa = {};
    try {
      mapa =
        JSON.parse(
          sessionStorage.getItem(MarketMonetizacion.STORAGE_PRINT) || '{}'
        ) || {};
    } catch (_) {
      mapa = {};
    }
    mapa[String(businessId)] = {
      print_token: printToken,
      buy_order: buyOrder || null,
      ts: Date.now()
    };
    try {
      sessionStorage.setItem(
        MarketMonetizacion.STORAGE_PRINT,
        JSON.stringify(mapa)
      );
    } catch (_) {

    }
  },

  leerPrintToken(businessId) {
    if (!businessId) return null;
    try {
      const mapa = JSON.parse(
        sessionStorage.getItem(MarketMonetizacion.STORAGE_PRINT) || '{}'
      );
      const row = mapa && mapa[String(businessId)];
      return row && row.print_token ? row : null;
    } catch (_) {
      return null;
    }
  },

  limpiarPagoPendiente() {
    try {
      localStorage.removeItem(MarketMonetizacion.STORAGE_PAGO);
      localStorage.removeItem(MarketMonetizacion.STORAGE_PAGO_RETORNO);
    } catch (_) {

    }
    try {
      sessionStorage.removeItem(MarketMonetizacion.STORAGE_PAGO);
      sessionStorage.removeItem(MarketMonetizacion.STORAGE_PAGO_RETORNO);
      sessionStorage.removeItem(MarketMonetizacion.STORAGE_PRINT);
    } catch (_) {

    }
  }
  });
})();
