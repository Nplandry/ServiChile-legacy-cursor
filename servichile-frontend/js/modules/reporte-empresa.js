
const ReporteEmpresa = {
  STORAGE_EMPRESA: 'servichile.empresa.seleccionada',

  storageQuien() {
    const user = typeof Auth !== 'undefined' ? Auth.getCurrentUser() : null;
    return user && user.email ? String(user.email).toLowerCase() : 'anon';
  },

  claveSeleccion() {
    return ReporteEmpresa.STORAGE_EMPRESA + ':' + ReporteEmpresa.storageQuien();
  },

  leerSeleccionId() {
    try {
      return localStorage.getItem(ReporteEmpresa.claveSeleccion()) || '';
    } catch (_) {
      return '';
    }
  },

  guardarSeleccionId(id) {
    try {
      if (id) localStorage.setItem(ReporteEmpresa.claveSeleccion(), String(id));
      else localStorage.removeItem(ReporteEmpresa.claveSeleccion());
    } catch (_) {

    }
  },

  elegirNegocio(lista, preferidoId) {
    if (!Array.isArray(lista) || !lista.length) return null;
    const want = preferidoId != null && preferidoId !== ''
      ? String(preferidoId)
      : ReporteEmpresa.leerSeleccionId();
    if (want) {
      const hit = lista.find((n) => String(n.id) === want);
      if (hit) return hit;
    }
    return lista[0];
  },

  async init(opts) {
    const raiz = document.getElementById('reporteRaiz');
    if (!raiz) return;
    if (typeof ReporteQr !== 'undefined') {
      if (ReporteQr.cerrarModalValidador) ReporteQr.cerrarModalValidador();
      if (ReporteQr.detenerCamara) ReporteQr.detenerCamara();
    }
    if (typeof SubirConfianza !== 'undefined' && SubirConfianza.cargar) {
      SubirConfianza.cargar();
    }
    const estado = await ReporteEmpresa.cargarEstadoNegocio(
      opts && opts.businessId != null ? opts.businessId : null
    );
    while (raiz.firstChild) raiz.removeChild(raiz.firstChild);
    raiz.appendChild(ReporteEmpresa.render(estado));
  },

  async cargarEstadoNegocio(preferidoId) {
    if (typeof Auth === 'undefined' || !Auth.isAuthenticated() || !Auth.request) {
      return { sinFicha: true, rep: null, lista: [] };
    }
    try {
      const mias = await Auth.request('/v1/businesses/mias', { token: Auth.sesion.token });
      const lista = mias && Array.isArray(mias.data) ? mias.data : [];
      if (!lista.length) return { sinFicha: true, rep: null, lista: [] };
      const negocio = ReporteEmpresa.elegirNegocio(lista, preferidoId);
      if (negocio && negocio.id) ReporteEmpresa.guardarSeleccionId(negocio.id);
      const res = await Auth.request(
        '/v1/businesses/' + encodeURIComponent(negocio.id) + '/reputation',
        { token: Auth.sesion.token }
      );
      if (typeof SubirConfianza !== 'undefined') {
        SubirConfianza.empresas = lista;
        if (SubirConfianza.guardarSeleccionId) {
          SubirConfianza.guardarSeleccionId(negocio.id);
        }
        if (res && res.ok && res.data) SubirConfianza.reputacionMia = res.data;
      }
      return {
        sinFicha: false,
        rep: res && res.data ? res.data : null,
        negocio: negocio,
        lista: lista
      };
    } catch (_e) {
      return { sinFicha: true, rep: null, negocio: null, lista: [] };
    }
  },

  etiquetaCategoria(id) {
    if (typeof Market !== 'undefined' && Array.isArray(Market.CATEGORIAS)) {
      const hit = Market.CATEGORIAS.find((c) => c.id === id);
      if (hit && hit.label) return hit.label;
    }
    return id || '-';
  },

  textoOpcional(valor, vacio) {
    const t = valor != null ? String(valor).trim() : '';
    return t || vacio || 'Sin registrar';
  },

  irAComprarFicha() {
    if (typeof App !== 'undefined' && App.openSection) {
      App.openSection('perfil');
    } else if (typeof App !== 'undefined' && App.showView) {
      if (typeof PerfilEmpresa !== 'undefined') PerfilEmpresa.init();
      App.showView('perfilView');
    }
    setTimeout(() => {
      const el = document.getElementById('perfilEmpresaRaiz');
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 80);
  },

  usuario() {
    return typeof Auth !== 'undefined' ? Auth.getCurrentUser() : null;
  },

  perfil() {
    const u = ReporteEmpresa.usuario();
    return (u && u.perfil) || {};
  },

  ficha() {
    if (typeof ProgresoCuenta !== 'undefined') {
      return ProgresoCuenta.de('proveedor').calcularFicha();
    }
    return {
      id: null,
      nombre: 'Sin empresa',
      indice_transparencia: null,
      indice_pct: null,
      _docsCargados: 0,
      _docsTotal: 0,
      _sinFicha: true
    };
  },

  render(estado) {
    const info = estado && typeof estado === 'object' ? estado : { sinFicha: !estado, rep: estado || null };
    const wrap = document.createElement('div');
    wrap.className = 'reporte';

    if (info.sinFicha) {
      wrap.append(
        ReporteEmpresa.renderAvisoSinFicha(),
        ReporteEmpresa.renderAccionesBasicas(),
        typeof ReporteQr !== 'undefined'
          ? ReporteQr.renderModalValidador()
          : document.createComment('sin-modal-qr')
      );
      return wrap;
    }

    const lead = document.createElement('p');
    lead.className = 'section-lead reporte__lead no-print';
    lead.textContent =
      'Consulte su índice de transparencia, muestre su QR y valide el de otra parte. Puede imprimir o guardar el informe en PDF.';

    const selector = ReporteEmpresa.renderSelectorEmpresas(
      info.lista || [],
      info.negocio || null
    );

    const acciones = document.createElement('div');
    acciones.className = 'reporte__acciones no-print';

    const btnPdf = document.createElement('button');
    btnPdf.type = 'button';
    btnPdf.className = 'submit-btn';
    btnPdf.textContent = 'Imprimir o guardar PDF';
    btnPdf.addEventListener('click', () => ReporteEmpresa.imprimir());

    const btnQr = document.createElement('button');
    btnQr.type = 'button';
    btnQr.className = 'submit-btn submit-btn--secondary';
    if (typeof ReporteQr !== 'undefined' && ReporteQr.montarBotonQr) {
      ReporteQr.montarBotonQr(btnQr, 'Validar QR');
    } else {
      btnQr.textContent = 'Validar QR';
    }
    btnQr.addEventListener('click', () => {
      if (typeof ReporteQr !== 'undefined') ReporteQr.abrirModalValidador();
    });

    acciones.append(btnPdf, btnQr);

    const doc = ReporteEmpresa.renderDocumento(info.rep || null, info.negocio || null);

    const pieAcciones = document.createElement('div');
    pieAcciones.className = 'reporte__acciones reporte__acciones--pie no-print';
    const btnAct = document.createElement('button');
    btnAct.type = 'button';
    btnAct.className = 'history__clear';
    btnAct.textContent = 'Actualizar datos';
    btnAct.addEventListener('click', () =>
      ReporteEmpresa.init({
        businessId: info.negocio && info.negocio.id
      })
    );
    pieAcciones.appendChild(btnAct);

    const modal =
      typeof ReporteQr !== 'undefined'
        ? ReporteQr.renderModalValidador()
        : document.createComment('sin-modal-qr');

    wrap.append(lead);
    if (selector) wrap.appendChild(selector);
    wrap.append(acciones, doc, pieAcciones, modal);
    setTimeout(() => ReporteEmpresa.cargarQrInforme(), 0);
    return wrap;
  },

  renderSelectorEmpresas(lista, actual) {
    if (!Array.isArray(lista) || lista.length < 2) return null;

    const box = document.createElement('div');
    box.className = 'reporte__selector no-print';
    box.setAttribute('aria-label', 'Seleccionar empresa');

    const label = document.createElement('label');
    label.className = 'reporte__selector-label';
    label.htmlFor = 'reporteEmpresaSelect';
    label.textContent = 'Empresa';

    const select = document.createElement('select');
    select.id = 'reporteEmpresaSelect';
    select.className = 'ui-select';
    select.setAttribute('aria-label', 'Elija qué empresa ver en el reporte');

    lista.forEach((n) => {
      const opt = document.createElement('option');
      opt.value = String(n.id);
      opt.textContent = n.nombre || 'Empresa';
      if (actual && String(actual.id) === String(n.id)) opt.selected = true;
      select.appendChild(opt);
    });

    select.addEventListener('change', () => {
      const id = select.value;
      ReporteEmpresa.guardarSeleccionId(id);
      select.disabled = true;
      ReporteEmpresa.init({ businessId: id });
    });

    box.append(label, select);
    return box;
  },

  renderAvisoSinFicha() {
    const box = document.createElement('section');
    box.className = 'reporte-sin-ficha no-print';
    box.setAttribute('aria-label', 'Sin ficha de empresa');

    const titulo = document.createElement('h2');
    titulo.className = 'section-heading';
    titulo.textContent = 'Aún no tiene una ficha de empresa';

    const lead = document.createElement('p');
    lead.className = 'section-lead';
    lead.textContent =
      'Para generar su reporte de transparencia debe crear su empresa. En Perfil puede publicar una ficha nueva (pago Webpay).';

    const lista = document.createElement('ul');
    lista.className = 'reporte-sin-ficha__lista';
    [
      'Pagar y publicar ficha de empresa (Webpay)',
      'La ficha queda a nombre de quien la crea',
      'Sin ficha activa no aparece ante compradores en Explorar'
    ].forEach((t) => {
      const li = document.createElement('li');
      li.textContent = t;
      lista.appendChild(li);
    });

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'submit-btn';
    btn.textContent = 'Ir a Perfil a crear la empresa';
    btn.addEventListener('click', () => ReporteEmpresa.irAComprarFicha());

    box.append(titulo, lead, lista, btn);
    return box;
  },

  renderAccionesBasicas() {
    const acciones = document.createElement('div');
    acciones.className = 'reporte__acciones no-print';
    const btnQr = document.createElement('button');
    btnQr.type = 'button';
    btnQr.className = 'submit-btn submit-btn--secondary';
    if (typeof ReporteQr !== 'undefined' && ReporteQr.montarBotonQr) {
      ReporteQr.montarBotonQr(btnQr, 'Validar QR de otra parte');
    } else {
      btnQr.textContent = 'Validar QR de otra parte';
    }
    btnQr.addEventListener('click', () => {
      if (typeof ReporteQr !== 'undefined') ReporteQr.abrirModalValidador();
    });
    acciones.appendChild(btnQr);
    return acciones;
  },

  renderDocumento(rep, negocio) {
    const user = ReporteEmpresa.usuario() || {};
    const ficha = ReporteEmpresa.ficha();
    const emp =
      negocio ||
      (typeof SubirConfianza !== 'undefined' && SubirConfianza.empresaActual
        ? SubirConfianza.empresaActual()
        : null) ||
      {};
    const indice =
      rep && rep.indice_transparencia != null
        ? Number(rep.indice_transparencia)
        : Number(ficha.indice_transparencia) || 0;

    const doc = document.createElement('article');
    doc.className = 'reporte-doc reporte-doc--empresa';
    doc.id = 'reporteDocumento';
    doc.setAttribute('aria-label', 'Reporte de transparencia ServiChile');

    const cabezal = document.createElement('header');
    cabezal.className = 'reporte-doc__cabezal';

    const marca = document.createElement('div');
    marca.className = 'reporte-doc__marca';
    const logo = document.createElement('span');
    logo.className = 'reporte-doc__logo';
    logo.textContent = 'S';
    const marcaTxt = document.createElement('div');
    const marcaNombre = document.createElement('p');
    marcaNombre.className = 'reporte-doc__brand';
    marcaNombre.textContent = 'ServiChile';
    const marcaSub = document.createElement('p');
    marcaSub.className = 'reporte-doc__brand-sub';
    marcaSub.textContent = 'Reporte de transparencia empresarial';
    marcaTxt.append(marcaNombre, marcaSub);
    marca.append(logo, marcaTxt);

    const meta = document.createElement('div');
    meta.className = 'reporte-doc__meta';
    const emitido = document.createElement('p');
    emitido.textContent = 'Emitido: ' + ReporteEmpresa.hoy();
    const tipo = document.createElement('p');
    tipo.textContent = 'Informe de empresa';
    meta.append(emitido, tipo);
    cabezal.append(marca, meta);

    const titular = document.createElement('section');
    titular.className = 'reporte-doc__titular';
    const nombre = document.createElement('h3');
    nombre.className = 'reporte-doc__nombre';
    nombre.textContent =
      emp.nombre || ficha.nombre || (rep && rep.nombre) || 'Empresa sin nombre';
    const rubro = document.createElement('p');
    rubro.className = 'reporte-doc__correo';
    rubro.textContent = ReporteEmpresa.etiquetaCategoria(
      emp.categoria || (rep && rep.categoria)
    );
    titular.append(nombre, rubro);

    const qrBloque = document.createElement('section');
    qrBloque.className = 'reporte-doc__qr';
    qrBloque.setAttribute('aria-label', 'Código QR de identidad');
    const qrTitulo = document.createElement('h3');
    qrTitulo.className = 'reporte-doc__h';
    qrTitulo.textContent = 'Código QR de identidad';
    const qrAyuda = document.createElement('p');
    qrAyuda.className = 'reporte-doc__qr-ayuda';
    qrAyuda.textContent =
      'Escanee este código para validar la identidad de la empresa en ServiChile.';
    const qrStatus = document.createElement('p');
    qrStatus.className = 'status-text reporte-doc__qr-status';
    qrStatus.id = 'reporteQrStatus';
    qrStatus.setAttribute('role', 'status');
    qrStatus.textContent = 'Cargando código QR…';
    const qrHost = document.createElement('div');
    qrHost.className = 'reporte-doc__qr-host';
    qrHost.id = 'reporteQrHost';
    qrBloque.append(qrTitulo, qrAyuda, qrStatus, qrHost);

    const resumen = document.createElement('section');
    resumen.className = 'reporte-doc__resumen';
    resumen.setAttribute('aria-label', 'Resumen de transparencia');

    const docs =
      (rep && rep.docs_total != null
        ? Number(rep.docs_total)
        : ficha._docsTotal != null
          ? Number(ficha._docsTotal)
          : typeof ProgresoCuenta !== 'undefined'
            ? ProgresoCuenta.de('proveedor').idsDocumento().length
            : 11) || 11;
    const cargados =
      rep && rep.docs_verificados != null
        ? Number(rep.docs_verificados)
        : ficha._docsCargados != null
          ? ficha._docsCargados
          : 0;
    const pct =
      rep && rep.indice_pct != null
        ? Math.round(Number(rep.indice_pct))
        : ficha.indice_pct != null
          ? Math.round(Number(ficha.indice_pct))
          : Math.round((indice / 10) * 100);

    const resumenTitulo = document.createElement('h3');
    resumenTitulo.className = 'reporte-doc__h';
    resumenTitulo.textContent = 'Resumen de transparencia';
    resumen.appendChild(resumenTitulo);

    const metricas = document.createElement('div');
    metricas.className = 'reporte-doc__metricas';
    [
      ['Índice global', '★ ' + indice.toFixed(1) + ' / 10'],
      ['Señales', pct + '%'],
      ['Documentos legales', cargados + ' de ' + docs]
    ].forEach(([k, v]) => {
      const chip = document.createElement('div');
      chip.className = 'reporte-doc__chip';
      const dt = document.createElement('span');
      dt.className = 'reporte-doc__chip-k';
      dt.textContent = k;
      const dd = document.createElement('strong');
      dd.className = 'reporte-doc__chip-v';
      dd.textContent = v;
      chip.append(dt, dd);
      metricas.appendChild(chip);
    });
    [
      [
        'Razón social / nombre',
        emp.nombre || ficha.nombre || (rep && rep.nombre) || '-'
      ],
      [
        'RUT empresa',
        ReporteEmpresa.textoOpcional(
          emp.rut_empresa || ficha.rut_empresa || (rep && rep.rut_empresa)
        )
      ],
      [
        'Categoría',
        ReporteEmpresa.etiquetaCategoria(emp.categoria || (rep && rep.categoria))
      ],
      ['Dirección', ReporteEmpresa.textoOpcional(emp.direccion || ficha.direccion)],
      ['Teléfono', ReporteEmpresa.textoOpcional(emp.telefono || ficha.telefono)],
      ['Sitio web', ReporteEmpresa.textoOpcional(emp.sitio_web || ficha.sitio_web)],
      ['Descripción', ReporteEmpresa.textoOpcional(emp.descripcion, 'Sin descripción')]
    ].forEach(([k, v]) => {
      const chip = document.createElement('div');
      chip.className = 'reporte-doc__chip';
      const dt = document.createElement('span');
      dt.className = 'reporte-doc__chip-k';
      dt.textContent = k;
      const dd = document.createElement('strong');
      dd.className = 'reporte-doc__chip-v';
      dd.textContent = v;
      chip.append(dt, dd);
      metricas.appendChild(chip);
    });
    resumen.appendChild(metricas);

    const oferta = ReporteEmpresa.renderOferta(emp);

    const desgloseWrap = document.createElement('section');
    desgloseWrap.className = 'reporte-doc__desglose';
    desgloseWrap.setAttribute('aria-label', 'Desglose del índice global');
    if (typeof Market !== 'undefined' && Market.bloqueDesgloseIndice) {
      const n = Object.assign(
        {
          id: emp.id || (rep && rep.business_id) || ficha.id,
          nombre:
            emp.nombre ||
            (rep && rep.nombre) ||
            ficha.nombre ||
            'Mi empresa',
          indice_pct: pct,
          docs_empresa: emp.docs_empresa || ficha.docs_empresa || null
        },
        emp
      );
      const desglose = Market.bloqueDesgloseIndice(n, rep || null, indice, false);
      if (desglose) {
        desglose.classList.add('reporte-doc__indice');
        desgloseWrap.appendChild(desglose);
      }
    }

    const pie = document.createElement('footer');
    pie.className = 'reporte-doc__pie';
    const aviso = document.createElement('p');
    aviso.textContent =
      'Documento informativo generado por ServiChile a solicitud de la empresa titular. El índice refleja la verificación documental del perfil y no sustituye auditorías oficiales.';
    const ref = document.createElement('p');
    ref.className = 'reporte-doc__ref';
    ref.textContent =
      'Referencia: ' +
      ReporteEmpresa.refId(user) +
      ' ' +
      ReporteEmpresa.hoy();
    pie.append(aviso, ref);

    doc.append(cabezal, titular, qrBloque, resumen);
    if (oferta) doc.appendChild(oferta);
    doc.append(desgloseWrap, pie);
    return doc;
  },

  etiquetaOferta(lista, id) {
    if (typeof Oferta !== 'undefined' && Oferta.etiqueta) {
      return Oferta.etiqueta(lista, id) || id;
    }
    return id;
  },

  renderOferta(emp) {
    const servicios = Array.isArray(emp.servicios) ? emp.servicios : [];
    const industrias = Array.isArray(emp.industrias) ? emp.industrias : [];
    const contrataciones = Array.isArray(emp.contrataciones) ? emp.contrataciones : [];
    const referencias = Array.isArray(emp.referencias) ? emp.referencias : [];
    const catalogo = typeof Oferta !== 'undefined' ? Oferta : {};
    const filas = [];
    if (servicios.length) filas.push(['Servicios', servicios.join(', ')]);
    if (industrias.length) {
      filas.push([
        'Le vende a',
        industrias.map((id) => ReporteEmpresa.etiquetaOferta(catalogo.INDUSTRIAS, id)).join(', ')
      ]);
    }
    if (contrataciones.length) {
      filas.push([
        'Cómo se contrata',
        contrataciones
          .map((id) => ReporteEmpresa.etiquetaOferta(catalogo.CONTRATACIONES, id))
          .join(', ')
      ]);
    }
    if (emp.monto) {
      filas.push(['Monto que acepta', ReporteEmpresa.etiquetaOferta(catalogo.MONTOS, emp.monto)]);
    }
    if (emp.plazo) {
      filas.push([
        'Plazo de cotización',
        ReporteEmpresa.etiquetaOferta(catalogo.PLAZOS, emp.plazo)
      ]);
    }
    if (referencias.length) filas.push(['Referencias', referencias.join(', ')]);
    if (!filas.length) return null;

    const sec = document.createElement('section');
    sec.className = 'reporte-doc__oferta';
    sec.setAttribute('aria-label', 'Oferta declarada');
    const titulo = document.createElement('h3');
    titulo.className = 'reporte-doc__h';
    titulo.textContent = 'Oferta declarada';
    const metricas = document.createElement('div');
    metricas.className = 'reporte-doc__metricas';
    filas.forEach(([k, v]) => {
      const chip = document.createElement('div');
      chip.className = 'reporte-doc__chip';
      const dt = document.createElement('span');
      dt.className = 'reporte-doc__chip-k';
      dt.textContent = k;
      const dd = document.createElement('strong');
      dd.className = 'reporte-doc__chip-v';
      dd.textContent = v;
      chip.append(dt, dd);
      metricas.appendChild(chip);
    });
    sec.append(titulo, metricas);
    return sec;
  },

  async cargarQrInforme() {
    const status = document.getElementById('reporteQrStatus');
    const host = document.getElementById('reporteQrHost');
    if (!host) return;
    if (typeof Auth === 'undefined' || !Auth.isAuthenticated()) {
      if (status) status.textContent = 'Inicie sesión para incluir el QR en el informe.';
      return;
    }
    if (typeof ReporteQr === 'undefined') {
      if (status) status.textContent = 'No se pudo generar el código QR.';
      return;
    }
    const res = await ReporteQr.emitir();
    if (!res.ok) {
      if (status) status.textContent = res.error || 'No se pudo cargar el QR.';
      return;
    }
    if (status) status.textContent = '';
    while (host.firstChild) host.removeChild(host.firstChild);

    const frame = document.createElement('div');
    frame.className = 'reporte-doc__qr-frame';
    frame.id = 'reporteQrFrame';
    ReporteQr.dibujarQr(frame, res.data.payload);

    const expira = document.createElement('p');
    expira.className = 'reporte-doc__qr-expira';
    expira.textContent =
      'Válido hasta ' + ReporteQr.formatoFecha(res.data.expires_at);

    host.append(frame, expira);
    if (ReporteQr.programarRenovacion) {
      ReporteQr.programarRenovacion(res.data.expires_in);
    }
  },

  imprimir() {
    const doc = document.getElementById('reporteDocumento');
    if (!doc) return;
    const todos = doc.querySelector('.indice-desglose__filtro--todos');
    if (todos && todos.getAttribute('aria-pressed') !== 'true') todos.click();
    ReporteEmpresa.imprimirDocumento(doc);
  },

  async imprimirFicha(negocio, rep, opts) {
    const compra = opts && typeof opts === 'object' ? opts : null;
    if (
      !compra ||
      !compra.autorizado ||
      !compra.buy_order ||
      !String(compra.buy_order).trim() ||
      !compra.print_token ||
      !String(compra.print_token).trim()
    ) {
      if (typeof MarketMonetizacion !== 'undefined' && MarketMonetizacion.toast) {
        MarketMonetizacion.toast(
          'El PDF del informe solo se entrega tras validar la compra en el servidor.'
        );
      }
      return false;
    }
    const doc = ReporteEmpresa.renderDocumento(rep || null, negocio || null);
    const sello = document.createElement('p');
    sello.className = 'reporte-doc__compra';
    sello.textContent =
      'Informe comprado en ServiChile Orden ' + String(compra.buy_order).trim();
    const cabezal = doc.querySelector('.reporte-doc__cabezal');
    if (cabezal && cabezal.parentNode) {
      cabezal.parentNode.insertBefore(sello, cabezal.nextSibling);
    } else {
      doc.insertBefore(sello, doc.firstChild);
    }

    if (compra.payload && typeof ReporteQr !== 'undefined') {
      const status = doc.querySelector('#reporteQrStatus');
      const host = doc.querySelector('#reporteQrHost');
      if (status) status.textContent = '';
      if (host) {
        while (host.firstChild) host.removeChild(host.firstChild);
        const frame = document.createElement('div');
        frame.className = 'reporte-doc__qr-frame';
        ReporteQr.dibujarQr(frame, compra.payload);
        host.appendChild(frame);
        if (compra.expires_at) {
          const expira = document.createElement('p');
          expira.className = 'reporte-doc__qr-expira';
          expira.textContent =
            'Válido hasta ' +
            (ReporteQr.formatoFecha
              ? ReporteQr.formatoFecha(compra.expires_at)
              : String(compra.expires_at));
          host.appendChild(expira);
        }
      }
    } else {
      const status = doc.querySelector('#reporteQrStatus');
      if (status) {
        status.textContent =
          'Informe autorizado (orden ' +
          compra.buy_order +
          '). QR de identidad no disponible para esta ficha.';
      }
    }
    const filtros = doc.querySelectorAll('.indice-desglose__filtros');
    filtros.forEach((el) => el.remove());
    await ReporteEmpresa.imprimirDocumento(doc);
    return true;
  },

  imprimirDocumento(nodo) {
    return new Promise((resolve) => {
      const portal = document.getElementById('reportePrintPortal');
      if (!portal || !nodo) {
        resolve();
        return;
      }
      const pieza = nodo.parentNode ? nodo.cloneNode(true) : nodo;
      while (portal.firstChild) portal.removeChild(portal.firstChild);
      portal.appendChild(pieza);
      portal.hidden = false;
      portal.setAttribute('aria-hidden', 'false');

      requestAnimationFrame(() => {
        const todos = pieza.querySelector('.indice-desglose__filtro--todos');
        if (todos && todos.getAttribute('aria-pressed') !== 'true') todos.click();
        document.body.classList.add('reporte-print');
        const limpiar = () => {
          document.body.classList.remove('reporte-print');
          window.removeEventListener('afterprint', limpiar);
          while (portal.firstChild) portal.removeChild(portal.firstChild);
          portal.hidden = true;
          portal.setAttribute('aria-hidden', 'true');
          resolve();
        };
        window.addEventListener('afterprint', limpiar);
        window.print();
        setTimeout(limpiar, 1500);
      });
    });
  },

  hoy() {
    try {
      return new Date().toLocaleString('es-CL', {
        day: '2-digit',
        month: 'long',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return new Date().toISOString();
    }
  },

  refId(user) {
    const base = (user && (user.id || user.email)) || 'local';
    let h = 0;
    const s = String(base);
    for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
    return 'SC-E-' + h.toString(16).toUpperCase().padStart(8, '0');
  }
};
