
const PerfilEmpresa = {
  modo: null,
  editandoId: null,
  PREFIJO_TEL: '+56 9 ',

  PRECIO_PUBLICACION: 8990,
  STORAGE_BORRADOR: 'servichile.publicacion.borrador',
  STORAGE_PAGO: 'servichile.publicacion.pago',

  esProveedor() {
    return typeof ProgresoCuenta !== 'undefined'
      ? ProgresoCuenta.esProveedor()
      : false;
  },

  esEmpresa() {
    return PerfilEmpresa.esProveedor();
  },

  formatoClp(n) {
    if (typeof MarketMonetizacion !== 'undefined' && MarketMonetizacion.formatoClp) {
      return MarketMonetizacion.formatoClp(n);
    }
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  },

  precioPublicacionTxt() {
    return (
      '$' + PerfilEmpresa.formatoClp(PerfilEmpresa.PRECIO_PUBLICACION) + ' CLP'
    );
  },

  guardarBorrador(datos) {
    try {
      sessionStorage.setItem(
        PerfilEmpresa.STORAGE_BORRADOR,
        JSON.stringify(datos || {})
      );
    } catch (_) {

    }
  },

  leerBorrador() {
    try {
      const raw = sessionStorage.getItem(PerfilEmpresa.STORAGE_BORRADOR);
      return raw ? JSON.parse(raw) : null;
    } catch (_) {
      return null;
    }
  },

  limpiarBorrador() {
    try {
      sessionStorage.removeItem(PerfilEmpresa.STORAGE_BORRADOR);
    } catch (_) {

    }
  },

  guardarPagoPendiente(data) {
    try {
      sessionStorage.setItem(
        PerfilEmpresa.STORAGE_PAGO,
        JSON.stringify(
          Object.assign({}, data || {}, { producto: 'publicacion' })
        )
      );
      if (typeof MarketMonetizacion !== 'undefined' && MarketMonetizacion.guardarPagoPendiente) {
        MarketMonetizacion.guardarPagoPendiente({
          buy_order: data && data.buy_order,
          token: data && data.token,
          producto: 'publicacion'
        });
      }
    } catch (_) {

    }
  },

  leerPagoPendiente() {
    try {
      const raw = sessionStorage.getItem(PerfilEmpresa.STORAGE_PAGO);
      if (raw) return JSON.parse(raw);
    } catch (_) {

    }
    if (typeof MarketMonetizacion !== 'undefined' && MarketMonetizacion.leerPagoPendiente) {
      const p = MarketMonetizacion.leerPagoPendiente() || {};
      if (p.producto === 'publicacion') return p;
    }
    return null;
  },

  limpiarPagoPendiente() {
    try {
      sessionStorage.removeItem(PerfilEmpresa.STORAGE_PAGO);
    } catch (_) {

    }
  },

  esRetornoPublicacion() {
    const p = PerfilEmpresa.leerPagoPendiente() || {};
    if (p.producto === 'publicacion') return true;
    try {
      return (
        new URLSearchParams(window.location.search || '').get('producto') ===
        'publicacion'
      );
    } catch (_) {
      return false;
    }
  },

  init() {
    try {
      localStorage.removeItem('servichile.rut_empresa_pendiente');
    } catch {}
    const host = document.getElementById('perfilEmpresaRaiz');
    if (!host) return;
    while (host.firstChild) host.removeChild(host.firstChild);
    if (!PerfilEmpresa.esProveedor()) {
      host.hidden = true;
      return;
    }
    host.hidden = false;
    host.appendChild(PerfilEmpresa.render());
    PerfilEmpresa.cargarMias();
    PerfilEmpresa.cargarCatalogoPublicacion();
  },

  async cargarCatalogoPublicacion() {
    try {
      const res = await Auth.request('/v1/pagos/publicacion/catalogo');
      if (res.ok && res.data && res.data.monto) {
        PerfilEmpresa.PRECIO_PUBLICACION = Number(res.data.monto) || 8990;
        PerfilEmpresa._aplicarTextosPrecio();
      }
    } catch (_) {

    }
  },

  _aplicarTextosPrecio() {
    const txt = PerfilEmpresa.precioPublicacionTxt();
    const btn = document.getElementById('peBtnPublicarPagar');
    if (btn) btn.textContent = 'Pagar y publicar ' + txt;
    const enviar = document.getElementById('peBtnEnviarPublicar');
    if (enviar && PerfilEmpresa.modo === 'crear') {
      enviar.textContent = 'Pagar ' + txt + ' y publicar';
    }
  },

  categorias() {
    if (typeof Market !== 'undefined' && Array.isArray(Market.CATEGORIAS)) {
      return Market.CATEGORIAS.filter((c) => c.id !== 'all');
    }
    return [
      { id: 'tecnologia', label: 'Tecnología y datos' },
      { id: 'industria', label: 'Minería e industria' },
      { id: 'construccion', label: 'Construcción' },
      { id: 'servicios-profesionales', label: 'Servicios profesionales' },
      { id: 'logistica', label: 'Transporte, Logística y Última Milla' }
    ];
  },

  render() {
    const wrap = document.createElement('div');
    wrap.className = 'perfil-empresa';

    const titulo = document.createElement('h3');
    titulo.className = 'section-heading';
    titulo.textContent = '¿Quiere crear una empresa?';

    const lead = document.createElement('p');
    lead.className = 'section-lead';
    lead.textContent =
      'Cree su ficha para aparecer ante compradores B2B que buscan proveedores verificables.';

    const valor = document.createElement('div');
    valor.className = 'perfil-empresa__valor';
    const valorTitulo = document.createElement('p');
    valorTitulo.className = 'perfil-empresa__valor-titulo';
    valorTitulo.textContent = 'Publicar tiene valor: sin ficha activa no lo encuentran en Explorar.';
    const valorLista = document.createElement('ul');
    valorLista.className = 'perfil-empresa__valor-lista';
    [
      'Publicar ficha cuesta ' +
        PerfilEmpresa.precioPublicacionTxt() +
        ' (Webpay). El informe de proveedor se vende aparte.',
      'La ficha queda a su nombre. No hay directorio previo para reclamar.',
      'Si la quita del perfil, se elimina del marketplace.'
    ].forEach((t) => {
      const li = document.createElement('li');
      li.textContent = t;
      valorLista.appendChild(li);
    });
    const acciones = document.createElement('div');
    acciones.className = 'perfil-empresa__acciones';

    const btnCrear = document.createElement('button');
    btnCrear.type = 'button';
    btnCrear.className = 'submit-btn';
    btnCrear.id = 'peBtnPublicarPagar';
    btnCrear.textContent =
      'Pagar y publicar ' + PerfilEmpresa.precioPublicacionTxt();
    btnCrear.addEventListener('click', () => PerfilEmpresa.mostrarModo('crear'));

    acciones.appendChild(btnCrear);
    valor.append(valorTitulo, valorLista, acciones);

    const panel = document.createElement('div');
    panel.id = 'perfilEmpresaPanel';
    panel.className = 'perfil-empresa__panel';
    panel.hidden = true;

    const miasTitulo = document.createElement('h4');
    miasTitulo.className = 'perfil-empresa__subtitulo';
    miasTitulo.textContent = 'Sus empresas';

    const mias = document.createElement('div');
    mias.id = 'perfilEmpresaMias';
    mias.className = 'perfil-empresa__mias';
    mias.setAttribute('aria-live', 'polite');

    const box = document.createElement('div');
    box.className = 'perfil-empresa__carga';
    box.setAttribute('role', 'status');
    const spin = document.createElement('span');
    spin.className = 'perfil-empresa__spinner';
    spin.setAttribute('aria-hidden', 'true');
    const msg = document.createElement('p');
    msg.className = 'perfil-empresa__carga-texto';
    msg.textContent = 'Cargando sus empresas…';
    box.append(spin, msg);
    mias.appendChild(box);

    const status = document.createElement('p');
    status.id = 'perfilEmpresaStatus';
    status.className = 'status-text';
    status.setAttribute('role', 'status');

    wrap.append(titulo, lead, valor, panel, miasTitulo, mias, status);
    return wrap;
  },

  mostrarModo(modo, negocio) {
    PerfilEmpresa.modo = modo;
    PerfilEmpresa.editandoId = modo === 'editar' && negocio ? negocio.id : null;
    const panel = document.getElementById('perfilEmpresaPanel');
    if (!panel) return;
    while (panel.firstChild) panel.removeChild(panel.firstChild);
    panel.hidden = false;
    panel.appendChild(PerfilEmpresa.formFicha(modo === 'editar' ? negocio : null));
    panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  },

  bindRutInput(input) {
    if (!input || typeof Security === 'undefined') return;
    input.addEventListener('input', () => {
      input.value = Security.formatRut(input.value);
    });
  },

  _cursorTrasPrefijoTel(input, forzarFinal) {
    if (!input) return;
    const min = PerfilEmpresa.PREFIJO_TEL.length;
    const colocar = () => {
      try {
        const len = input.value.length;
        if (forzarFinal || len <= min) {
          input.setSelectionRange(len, len);
          return;
        }
        const start = input.selectionStart == null ? min : input.selectionStart;
        const end = input.selectionEnd == null ? start : input.selectionEnd;
        if (start < min || end < min) {
          input.setSelectionRange(Math.max(min, start), Math.max(min, end));
        }
      } catch (_) {}
    };
    requestAnimationFrame(() => requestAnimationFrame(colocar));
    setTimeout(colocar, 0);
  },

  _aplicarFormatoInput(input, formateado, caretAntes, largoAntes) {
    if (formateado === input.value) return;
    input.value = formateado;
    const delta = formateado.length - largoAntes;
    const next = Math.max(0, (caretAntes || 0) + delta);
    try {
      input.setSelectionRange(next, next);
    } catch (_) {}
  },

  bindTelefonoInput(input) {
    if (!input) return;
    input.setAttribute('inputmode', 'tel');
    input.setAttribute('autocomplete', 'tel');
    input.placeholder = '+56 9 1234 5678';

    input.addEventListener('focus', () => {
      const vacio = !input.value.trim();
      if (vacio) input.value = PerfilEmpresa.PREFIJO_TEL;
      PerfilEmpresa._cursorTrasPrefijoTel(input, vacio);
    });

    input.addEventListener('click', () => {
      if (!input.value.startsWith('+56')) return;
      PerfilEmpresa._cursorTrasPrefijoTel(input, false);
    });

    input.addEventListener('keydown', (e) => {
      const min = PerfilEmpresa.PREFIJO_TEL.length;
      if (!input.value.startsWith(PerfilEmpresa.PREFIJO_TEL.slice(0, 3))) return;
      const start = input.selectionStart == null ? 0 : input.selectionStart;
      const end = input.selectionEnd == null ? start : input.selectionEnd;
      if (
        (e.key === 'Backspace' && start <= min && start === end) ||
        (e.key === 'ArrowLeft' && start <= min) ||
        e.key === 'Home'
      ) {
        e.preventDefault();
        try {
          input.setSelectionRange(min, min);
        } catch (_) {}
      }
    });

    input.addEventListener('input', () => {
      if (typeof Security === 'undefined') return;
      const valor = input.value;
      if (!valor.trim() || valor.trim() === '+56' || valor.trim() === '+56 9') {
        if (valor.trim() === '+56' || valor.trim() === '+56 9') {
          input.value = valor.trim() === '+56' ? '+56 ' : '+56 9 ';
        } else {
          input.setCustomValidity('');
          input.removeAttribute('aria-invalid');
        }
        return;
      }
      const caret = input.selectionStart;
      const formateado = Security.formatTelefono(valor);
      PerfilEmpresa._aplicarFormatoInput(input, formateado, caret, valor.length);
      input.setCustomValidity('');
      input.removeAttribute('aria-invalid');
    });

    input.addEventListener('blur', () => {
      let valor = input.value.trim();
      if (!valor || valor === '+56' || valor === '+56 9') {
        input.value = '';
        input.setCustomValidity('');
        input.removeAttribute('aria-invalid');
        return;
      }
      if (typeof Security !== 'undefined') {
        valor = Security.formatTelefono(valor);
        input.value = valor;
        if (!Security.validateTelefono(valor)) {
          input.setCustomValidity(
            'El teléfono debe comenzar con +56, p. ej. +56 9 1234 5678'
          );
          input.setAttribute('aria-invalid', 'true');
        } else {
          input.setCustomValidity('');
          input.removeAttribute('aria-invalid');
        }
      }
    });
  },

  formFicha(negocio) {
    const editando = !!(negocio && negocio.id);
    const form = document.createElement('form');
    form.className = 'form perfil-empresa__form';
    form.noValidate = true;

    const intro = document.createElement('p');
    intro.className = 'field__hint';
    intro.textContent = editando
      ? 'Actualice los datos de la ficha. Al guardar se refrescan las consultas de transparencia (ChileCompra, cabeceras, etc.).'
      : 'Al pagar y publicar (' +
        PerfilEmpresa.precioPublicacionTxt() +
        '), la ficha queda a su nombre y visible en Explorar. El informe de proveedor se vende aparte.';

    const campoRut = PerfilEmpresa.campoTexto(
      'peRut',
      'RUT de la empresa',
      true,
      12,
      'text',
      'Necesario para ChileCompra y consultas de estado del proveedor.'
    );
    form.append(
      intro,
      PerfilEmpresa.campoTexto('peNombre', 'Nombre de la empresa', true, 160),
      campoRut,
      PerfilEmpresa.campoCategoria('peCategoria'),
      PerfilEmpresa.campoTexto(
        'peDireccion',
        'Dirección de oficina',
        true,
        200,
        'text',
        'Calle, número, comuna o ciudad donde opera la empresa.'
      ),
      PerfilEmpresa.campoTexto('peTelefono', 'Teléfono', false, 30, 'tel'),
      PerfilEmpresa.campoTexto('peWeb', 'Sitio web', false, 200),
      PerfilEmpresa.campoRecurso(
        'peBanner',
        'peBannerPreview',
        'URL del banner',
        false
      ),
      PerfilEmpresa.campoRecurso(
        'peLogo',
        'peLogoPreview',
        'URL del logo',
        true
      ),
      PerfilEmpresa.campoTextoarea('peDesc', 'Descripción', 2000),
      PerfilEmpresa.bloqueOferta()
    );

    const peRut = campoRut.querySelector('#peRut');
    PerfilEmpresa.bindRutInput(peRut);
    const peTel = form.querySelector('#peTelefono');
    PerfilEmpresa.bindTelefonoInput(peTel);
    PerfilEmpresa.bindUrlPreview(form, 'peBanner', 'peBannerPreview', false);
    PerfilEmpresa.bindUrlPreview(form, 'peLogo', 'peLogoPreview', true);
    const peNombre = form.querySelector('#peNombre');
    if (peNombre) {
      peNombre.addEventListener('input', () => {
        const logoInput = form.querySelector('#peLogo');
        const url = PerfilEmpresa.normalizarUrlRecurso(
          (logoInput && logoInput.value) || ''
        );
        if (url) return;
        PerfilEmpresa.refrescarPreview(form, 'peLogo', 'peLogoPreview', true);
      });
    }

    if (editando) {
      PerfilEmpresa.rellenarForm(form, negocio);
    }
    PerfilEmpresa.refrescarPreview(form, 'peBanner', 'peBannerPreview', false);
    PerfilEmpresa.refrescarPreview(form, 'peLogo', 'peLogoPreview', true);

    const acciones = document.createElement('div');
    acciones.className = 'perfil-empresa__form-acciones';
    const enviar = document.createElement('button');
    enviar.type = 'submit';
    enviar.className = 'submit-btn';
    enviar.id = 'peBtnEnviarPublicar';
    enviar.textContent = editando
      ? 'Guardar cambios'
      : 'Pagar ' + PerfilEmpresa.precioPublicacionTxt() + ' y publicar';
    const cancelar = document.createElement('button');
    cancelar.type = 'button';
    cancelar.className = 'history__clear';
    cancelar.textContent = 'Cancelar';
    cancelar.addEventListener('click', () => PerfilEmpresa.cerrarPanel());
    acciones.append(enviar, cancelar);
    form.appendChild(acciones);

    const formStatus = document.createElement('p');
    formStatus.id = 'perfilEmpresaFormStatus';
    formStatus.className = 'status-text status-text--sm perfil-empresa__form-status';
    formStatus.setAttribute('role', 'status');
    formStatus.setAttribute('aria-live', 'polite');
    form.appendChild(formStatus);

    form.addEventListener('submit', (e) => {
      e.preventDefault();
      if (editando) PerfilEmpresa.enviarActualizar();
      else PerfilEmpresa.enviarCrear();
    });
    return form;
  },

  rellenarForm(raiz, n) {
    const set = (id, val) => {
      const el = (raiz && raiz.querySelector('#' + id)) || document.getElementById(id);
      if (el) el.value = val != null ? String(val) : '';
    };
    set('peNombre', n.nombre || '');
    let rut = (n.rut_empresa || '').trim();
    if (rut && typeof Security !== 'undefined') rut = Security.formatRut(rut);
    set('peRut', rut);
    set('peCategoria', n.categoria || '');
    set('peDireccion', n.direccion || '');
    let tel = (n.telefono || '').trim();
    if (tel && typeof Security !== 'undefined') tel = Security.formatTelefono(tel);
    set('peTelefono', tel);
    set('peWeb', n.sitio_web || '');
    set('peBanner', n.imagen_url || '');
    set('peLogo', n.logo_url || '');
    set('peDesc', n.descripcion || '');
    PerfilEmpresa.pintarTags('peServicios', n.servicios, raiz);
    PerfilEmpresa.pintarTags('peReferencias', n.referencias, raiz);
    PerfilEmpresa.marcarChecks('peIndustrias', n.industrias, raiz);
    PerfilEmpresa.marcarChecks('peContrataciones', n.contrataciones, raiz);
    set('peMonto', n.monto || '');
    set('pePlazo', n.plazo || '');
  },

  leerForm() {
    const nombre = ((document.getElementById('peNombre') || {}).value || '').trim();
    let rut_empresa = (
      (document.getElementById('peRut') || {}).value || ''
    ).trim();
    const categoria = (document.getElementById('peCategoria') || {}).value || '';
    const direccion = ((document.getElementById('peDireccion') || {}).value || '').trim();
    let telefono = ((document.getElementById('peTelefono') || {}).value || '').trim();
    const sitio_web = ((document.getElementById('peWeb') || {}).value || '').trim();
    const imagen_url = ((document.getElementById('peBanner') || {}).value || '').trim();
    const logo_url = ((document.getElementById('peLogo') || {}).value || '').trim();
    const descripcion = ((document.getElementById('peDesc') || {}).value || '').trim();
    const servicios = PerfilEmpresa.leerTags('peServicios');
    const referencias = PerfilEmpresa.leerTags('peReferencias');
    if (!Array.isArray(servicios) || !Array.isArray(referencias)) return null;
    return {
      nombre,
      rut_empresa,
      categoria,
      direccion,
      telefono,
      sitio_web,
      imagen_url,
      logo_url,
      descripcion,
      servicios,
      referencias,
      industrias: PerfilEmpresa.leerChecks('peIndustrias'),
      contrataciones: PerfilEmpresa.leerChecks('peContrataciones'),
      monto: ((document.getElementById('peMonto') || {}).value || '').trim(),
      plazo: ((document.getElementById('pePlazo') || {}).value || '').trim()
    };
  },

  validarForm(datos) {
    if (!datos) return null;
    if (datos.nombre.length < 2) {
      PerfilEmpresa.setStatus('Ingrese el nombre de la empresa.');
      const peNombre = document.getElementById('peNombre');
      if (peNombre) peNombre.focus();
      return null;
    }
    let rut_empresa = datos.rut_empresa;
    if (
      !rut_empresa ||
      (typeof Security !== 'undefined' && !Security.validateRut(rut_empresa))
    ) {
      PerfilEmpresa.setStatus('Ingrese un RUT de empresa válido, p. ej. 12.345.678-9.');
      const peRutBad = document.getElementById('peRut');
      if (peRutBad) {
        peRutBad.setAttribute('aria-invalid', 'true');
        peRutBad.focus();
      }
      return null;
    }
    if (typeof Security !== 'undefined') {
      rut_empresa = Security.formatRut(rut_empresa);
      const peRut = document.getElementById('peRut');
      if (peRut) {
        peRut.value = rut_empresa;
        peRut.removeAttribute('aria-invalid');
      }
    }
    if (datos.direccion.length < 3) {
      PerfilEmpresa.setStatus('Ingrese la dirección de oficina.');
      const peDir = document.getElementById('peDireccion');
      if (peDir) peDir.focus();
      return null;
    }
    let telefono = (datos.telefono || '').trim();
    if (!telefono || telefono === '+56' || telefono === '+56 9') {
      telefono = '';
      const peTelVacio = document.getElementById('peTelefono');
      if (peTelVacio) {
        peTelVacio.value = '';
        peTelVacio.setCustomValidity('');
        peTelVacio.removeAttribute('aria-invalid');
      }
    } else if (typeof Security !== 'undefined') {
      telefono = Security.formatTelefono(telefono);
      const peTel = document.getElementById('peTelefono');
      if (peTel) peTel.value = telefono;
      if (!Security.validateTelefono(telefono)) {
        PerfilEmpresa.setStatus(
          'Teléfono inválido. Debe comenzar con +56, p. ej. +56 9 1234 5678.'
        );
        if (peTel) {
          peTel.setCustomValidity(
            'El teléfono debe comenzar con +56, p. ej. +56 9 1234 5678'
          );
          peTel.setAttribute('aria-invalid', 'true');
          peTel.focus();
        }
        return null;
      }
      if (peTel) {
        peTel.setCustomValidity('');
        peTel.removeAttribute('aria-invalid');
      }
    } else if (!telefono.replace(/\s/g, '').startsWith('+56')) {
      PerfilEmpresa.setStatus('El teléfono debe comenzar con +56.');
      return null;
    }
    const banner = PerfilEmpresa.normalizarUrlRecurso(datos.imagen_url);
    if (datos.imagen_url && !banner) {
      PerfilEmpresa.setStatus(
        'La URL del banner debe ser https:// (sin espacios ni esquemas peligrosos).'
      );
      return null;
    }
    const logo = PerfilEmpresa.normalizarUrlRecurso(datos.logo_url);
    if (datos.logo_url && !logo) {
      PerfilEmpresa.setStatus(
        'La URL del logo debe ser https:// (sin espacios ni esquemas peligrosos).'
      );
      return null;
    }
    if (banner) {
      const peBanner = document.getElementById('peBanner');
      if (peBanner) peBanner.value = banner;
    }
    if (logo) {
      const peLogo = document.getElementById('peLogo');
      if (peLogo) peLogo.value = logo;
    }
    return Object.assign({}, datos, {
      rut_empresa,
      telefono: telefono || '',
      imagen_url: banner || '',
      logo_url: logo || ''
    });
  },

  normalizarUrlRecurso(valor) {
    if (!valor) return '';
    let url = String(valor).trim();
    if (!url || url.length > 500 || /\s/.test(url)) return '';
    const bajo = url.toLowerCase();
    if (
      /^(javascript|data|vbscript|file|blob):/.test(bajo)
    ) {
      return '';
    }
    if (bajo.startsWith('http://')) {
      url = 'https://' + url.slice(7);
    } else if (!bajo.startsWith('https://')) {
      return '';
    }
    const host = url.slice(8).split('/')[0] || '';
    if (!host || host.startsWith('.') || host.endsWith('.')) return '';
    if (host.toLowerCase() !== 'localhost' && host.indexOf('.') < 0) return '';
    return url;
  },

  iconoImagen() {
    const ns = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('aria-hidden', 'true');
    const rect = document.createElementNS(ns, 'rect');
    rect.setAttribute('x', '3');
    rect.setAttribute('y', '5');
    rect.setAttribute('width', '18');
    rect.setAttribute('height', '14');
    rect.setAttribute('rx', '2');
    rect.setAttribute('fill', 'none');
    rect.setAttribute('stroke', 'currentColor');
    rect.setAttribute('stroke-width', '1.6');
    const circ = document.createElementNS(ns, 'circle');
    circ.setAttribute('cx', '9');
    circ.setAttribute('cy', '10');
    circ.setAttribute('r', '1.4');
    circ.setAttribute('fill', 'currentColor');
    const path = document.createElementNS(ns, 'path');
    path.setAttribute('d', 'M3 16l5-4 3 2.5 3-2.5 7 5');
    path.setAttribute('fill', 'none');
    path.setAttribute('stroke', 'currentColor');
    path.setAttribute('stroke-width', '1.6');
    path.setAttribute('stroke-linejoin', 'round');
    svg.append(rect, circ, path);
    return svg;
  },

  inicialesPreview() {
    const nombre = ((document.getElementById('peNombre') || {}).value || '').trim();
    const partes = nombre.split(/\s+/).filter(Boolean);
    if (!partes.length) return 'Logo';
    return partes
      .slice(0, 2)
      .map((parte) => parte.charAt(0))
      .join('')
      .toUpperCase();
  },

  campoPreview(id, logo) {
    const wrap = document.createElement('div');
    wrap.className =
      'perfil-empresa__preview' + (logo ? ' perfil-empresa__preview--logo' : '');
    wrap.id = id;
    wrap.setAttribute('aria-live', 'polite');
    const marco = document.createElement('div');
    marco.className = 'perfil-empresa__marco';
    const ph = document.createElement('div');
    ph.className = 'perfil-empresa__ph';
    ph.setAttribute('aria-hidden', 'true');
    if (!logo) ph.append(PerfilEmpresa.iconoImagen());
    const caption = document.createElement('span');
    caption.className = 'perfil-empresa__ph-texto';
    caption.textContent = logo ? 'Logo' : 'Banner';
    const sub = document.createElement('span');
    sub.className = 'perfil-empresa__ph-sub';
    sub.textContent = logo ? 'Iniciales del nombre' : 'Imagen de la ficha';
    ph.append(caption, sub);
    const img = document.createElement('img');
    img.alt = '';
    img.decoding = 'async';
    marco.append(ph, img);
    wrap.append(marco);
    return wrap;
  },

  campoRecurso(inputId, previewId, label, logo) {
    const field = document.createElement('div');
    field.className = 'field perfil-empresa__recurso';
    const lab = document.createElement('label');
    lab.className = 'field__label';
    lab.htmlFor = inputId;
    lab.textContent = label;
    const input = document.createElement('input');
    input.id = inputId;
    input.className = 'field__input';
    input.type = 'url';
    input.maxLength = 500;
    input.placeholder = 'https://';
    field.append(lab, PerfilEmpresa.campoPreview(previewId, logo), input);
    return field;
  },

  bindUrlPreview(raiz, inputId, previewId, logo) {
    const input = raiz && raiz.querySelector('#' + inputId);
    if (!input) return;
    const pintar = () =>
      PerfilEmpresa.refrescarPreview(raiz, inputId, previewId, logo);
    input.addEventListener('input', pintar);
    input.addEventListener('change', pintar);
  },

  refrescarPreview(raiz, inputId, previewId, logo) {
    const scope = raiz || document;
    const input =
      (scope.querySelector && scope.querySelector('#' + inputId)) ||
      document.getElementById(inputId);
    const box =
      (scope.querySelector && scope.querySelector('#' + previewId)) ||
      document.getElementById(previewId);
    if (!input || !box) return;
    const img = box.querySelector('img');
    if (!img) return;
    const url = PerfilEmpresa.normalizarUrlRecurso(input.value || '');
    img.onload = null;
    img.onerror = null;
    if (!url) {
      PerfilEmpresa.pintarPlaceholder(box, logo);
      return;
    }
    box.classList.remove(
      'perfil-empresa__preview--lista',
      'perfil-empresa__preview--error'
    );
    img.onerror = () => {
      img.onerror = null;
      img.removeAttribute('src');
      box.classList.remove('perfil-empresa__preview--lista');
      box.classList.add('perfil-empresa__preview--error');
      const hint = box.querySelector('.field__hint');
      const sub = box.querySelector('.perfil-empresa__ph-sub');
      if (hint) {
        hint.textContent = logo
          ? 'No se pudo cargar el logo (revise la URL)'
          : 'No se pudo cargar el banner (revise la URL)';
      }
      if (sub) sub.textContent = 'Revisa el enlace https';
    };
    img.onload = () => {
      box.classList.remove('perfil-empresa__preview--error');
      box.classList.add('perfil-empresa__preview--lista');
      const hint = box.querySelector('.field__hint');
      if (hint) {
        hint.textContent = logo
          ? 'Vista previa del logo'
          : 'Vista previa del banner';
      }
    };
    img.src = url;
  },

  pintarPlaceholder(box, logo) {
    box.classList.remove(
      'perfil-empresa__preview--lista',
      'perfil-empresa__preview--error'
    );
    const img = box.querySelector('img');
    if (img) img.removeAttribute('src');
    const texto = box.querySelector('.perfil-empresa__ph-texto');
    const sub = box.querySelector('.perfil-empresa__ph-sub');
    const hint = box.querySelector('.field__hint');
    if (logo) {
      if (texto) texto.textContent = PerfilEmpresa.inicialesPreview();
      if (sub) sub.textContent = 'Iniciales del nombre';
      if (hint) hint.textContent = 'Vista previa del logo';
      return;
    }
    if (texto) texto.textContent = 'Banner';
    if (sub) sub.textContent = 'Imagen de la ficha';
    if (hint) hint.textContent = 'Vista previa del banner';
  },

  cerrarPanel() {
    PerfilEmpresa.modo = null;
    PerfilEmpresa.editandoId = null;
    const panel = document.getElementById('perfilEmpresaPanel');
    if (panel) {
      panel.hidden = true;
      while (panel.firstChild) panel.removeChild(panel.firstChild);
    }
  },

  catalogo() {
    if (typeof Oferta !== 'undefined') return Oferta;
    return {
      MAX_SERVICIOS: 6,
      MAX_REFERENCIAS: 8,
      MAX_LARGO_SERVICIO: 40,
      MAX_LARGO_REFERENCIA: 80,
      INDUSTRIAS: [],
      CONTRATACIONES: [],
      MONTOS: [],
      PLAZOS: []
    };
  },

  bloqueOferta() {
    const cat = PerfilEmpresa.catalogo();
    const bloque = document.createElement('fieldset');
    bloque.className = 'pe-oferta';
    const titulo = document.createElement('legend');
    titulo.className = 'pe-oferta__titulo';
    titulo.textContent = 'Oferta declarada';
    const nota = document.createElement('p');
    nota.className = 'field__hint';
    nota.textContent =
      'Estos datos los declara la empresa. No entran al índice de transparencia.';
    bloque.append(
      titulo,
      nota,
      PerfilEmpresa.campoTags(
        'peServicios',
        'Servicios que ofrece',
        'Hasta 6 etiquetas cortas. Por ejemplo: bodega, transporte, última milla.',
        cat.MAX_SERVICIOS,
        cat.MAX_LARGO_SERVICIO
      ),
      PerfilEmpresa.campoChecks(
        'peIndustrias',
        'Le vende a',
        cat.INDUSTRIAS,
        'Rubro de sus clientes. No es el tipo de proveedor.'
      ),
      PerfilEmpresa.campoChecks(
        'peContrataciones',
        'Cómo se contrata',
        cat.CONTRATACIONES
      ),
      PerfilEmpresa.campoSelect(
        'peMonto',
        'Monto que acepta',
        'El tramo de operación que toma.',
        cat.MONTOS
      ),
      PerfilEmpresa.campoSelect(
        'pePlazo',
        'Plazo para responder una cotización',
        '',
        cat.PLAZOS
      ),
      PerfilEmpresa.campoTags(
        'peReferencias',
        'Referencias',
        'Empresas a las que ha prestado servicios. Es un dato declarado, sin verificación.',
        cat.MAX_REFERENCIAS,
        cat.MAX_LARGO_REFERENCIA
      )
    );
    return bloque;
  },

  campoTags(id, label, hint, maxItems, maxLen) {
    const field = document.createElement('div');
    field.className = 'field';
    field.id = id;
    field.dataset.max = String(maxItems || 6);
    field.dataset.maxlen = String(maxLen || 40);
    const lab = document.createElement('label');
    lab.className = 'field__label';
    lab.htmlFor = id + 'Input';
    lab.textContent = label;
    const lista = document.createElement('ul');
    lista.className = 'pe-tags';
    const input = document.createElement('input');
    input.id = id + 'Input';
    input.className = 'field__input';
    input.type = 'text';
    input.maxLength = maxLen || 40;
    input.autocomplete = 'off';
    input.placeholder = 'Escriba y presione Enter';
    const agregar = (crudo) => {
      const error = PerfilEmpresa.agregarTag(field, crudo);
      if (error) PerfilEmpresa.setStatus(error);
      else PerfilEmpresa.setStatus('');
    };
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ',') {
        e.preventDefault();
        agregar(input.value);
        input.value = '';
      }
    });
    input.addEventListener('blur', () => {
      if (!input.value.trim()) return;
      agregar(input.value);
      input.value = '';
    });
    field.append(lab, lista, input);
    if (hint) {
      const hintEl = document.createElement('p');
      hintEl.className = 'field__hint';
      hintEl.textContent = hint;
      field.appendChild(hintEl);
    }
    return field;
  },

  agregarTag(field, crudo) {
    const texto = String(crudo || '').replace(/\s+/g, ' ').replace(/,+$/g, '').trim();
    if (!texto) return '';
    const max = Number(field.dataset.max || 6);
    const maxLen = Number(field.dataset.maxlen || 40);
    const lista = field.querySelector('.pe-tags');
    const actuales = lista ? lista.querySelectorAll('li').length : 0;
    if (texto.length < 2 || texto.length > maxLen) {
      return 'Cada etiqueta debe tener entre 2 y ' + maxLen + ' caracteres.';
    }
    if (!/^[0-9A-Za-zÁÉÍÓÚÜÑáéíóúüñ][0-9A-Za-zÁÉÍÓÚÜÑáéíóúüñ .,&'’/\-]*$/.test(texto)) {
      return "Use solo letras, números y los signos . , & ' / -";
    }
    const ya = Array.prototype.some.call(lista.querySelectorAll('li'), (li) => {
      return (li.dataset.valor || '').toLowerCase() === texto.toLowerCase();
    });
    if (ya) return '';
    if (actuales >= max) return 'Puede indicar hasta ' + max + ' etiquetas.';
    const li = document.createElement('li');
    li.className = 'pe-tag';
    li.dataset.valor = texto;
    const nombre = document.createElement('span');
    nombre.textContent = texto;
    const quitar = document.createElement('button');
    quitar.type = 'button';
    quitar.textContent = '×';
    quitar.setAttribute('aria-label', 'Quitar ' + texto);
    quitar.addEventListener('click', () => li.remove());
    li.append(nombre, quitar);
    lista.appendChild(li);
    return '';
  },

  pintarTags(id, valores, raiz) {
    const field = (raiz && raiz.querySelector('#' + id)) || document.getElementById(id);
    if (!field) return;
    const lista = field.querySelector('.pe-tags');
    if (lista) while (lista.firstChild) lista.removeChild(lista.firstChild);
    (Array.isArray(valores) ? valores : []).forEach((valor) => {
      PerfilEmpresa.agregarTag(field, valor);
    });
  },

  leerTags(id) {
    const field = document.getElementById(id);
    if (!field) return [];
    const input = field.querySelector('input');
    if (input && input.value.trim()) {
      const error = PerfilEmpresa.agregarTag(field, input.value);
      input.value = '';
      if (error) {
        PerfilEmpresa.setStatus(error);
        return null;
      }
    }
    return Array.prototype.map.call(field.querySelectorAll('li'), (li) => li.dataset.valor);
  },

  campoChecks(id, label, opciones, hint) {
    const field = document.createElement('fieldset');
    field.className = 'field pe-checks';
    field.id = id;
    const legend = document.createElement('legend');
    legend.className = 'field__label';
    legend.textContent = label;
    field.appendChild(legend);
    (opciones || []).forEach((opcion) => {
      const lab = document.createElement('label');
      lab.className = 'pe-check';
      const input = document.createElement('input');
      input.type = 'checkbox';
      input.value = opcion.id;
      const texto = document.createElement('span');
      texto.textContent = opcion.label;
      lab.append(input, texto);
      field.appendChild(lab);
    });
    if (hint) {
      const hintEl = document.createElement('p');
      hintEl.className = 'field__hint';
      hintEl.textContent = hint;
      field.appendChild(hintEl);
    }
    return field;
  },

  marcarChecks(id, valores, raiz) {
    const field = (raiz && raiz.querySelector('#' + id)) || document.getElementById(id);
    if (!field) return;
    const elegidos = new Set(Array.isArray(valores) ? valores : []);
    field.querySelectorAll('input[type="checkbox"]').forEach((input) => {
      input.checked = elegidos.has(input.value);
    });
  },

  leerChecks(id) {
    const field = document.getElementById(id);
    if (!field) return [];
    return Array.prototype.map
      .call(field.querySelectorAll('input[type="checkbox"]:checked'), (input) => input.value);
  },

  campoSelect(id, label, hint, opciones) {
    const field = document.createElement('div');
    field.className = 'field';
    const lab = document.createElement('label');
    lab.className = 'field__label';
    lab.htmlFor = id;
    lab.textContent = label;
    const select = document.createElement('select');
    select.id = id;
    select.className = 'ui-select';
    const vacio = document.createElement('option');
    vacio.value = '';
    vacio.textContent = 'Sin indicar';
    select.appendChild(vacio);
    (opciones || []).forEach((opcion) => {
      const opt = document.createElement('option');
      opt.value = opcion.id;
      opt.textContent = opcion.label;
      select.appendChild(opt);
    });
    field.append(lab, select);
    if (hint) {
      const hintEl = document.createElement('p');
      hintEl.className = 'field__hint';
      hintEl.textContent = hint;
      field.appendChild(hintEl);
    }
    return field;
  },

  campoTexto(id, label, required, max, type, hint) {
    const field = document.createElement('div');
    field.className = 'field';
    const lab = document.createElement('label');
    lab.className = 'field__label';
    lab.htmlFor = id;
    lab.textContent = label;
    const input = document.createElement('input');
    input.id = id;
    input.className = 'field__input';
    input.type = type || 'text';
    input.maxLength = max || 160;
    if (required) input.required = true;
    field.append(lab, input);
    if (hint) {
      const hintEl = document.createElement('p');
      hintEl.className = 'field__hint';
      hintEl.textContent = hint;
      field.appendChild(hintEl);
    }
    return field;
  },

  campoTextoarea(id, label, max) {
    const field = document.createElement('div');
    field.className = 'field';
    const lab = document.createElement('label');
    lab.className = 'field__label';
    lab.htmlFor = id;
    lab.textContent = label;
    const ta = document.createElement('textarea');
    ta.id = id;
    ta.className = 'field__input';
    ta.rows = 3;
    ta.maxLength = max || 2000;
    field.append(lab, ta);
    return field;
  },

  campoCategoria(id) {
    const field = document.createElement('div');
    field.className = 'field';
    const lab = document.createElement('label');
    lab.className = 'field__label';
    lab.htmlFor = id;
    lab.textContent = 'Tipo de proveedor';
    const select = document.createElement('select');
    select.id = id;
    select.className = 'ui-select';
    select.required = true;
    PerfilEmpresa.categorias().forEach((c) => {
      const opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = c.label;
      select.appendChild(opt);
    });
    field.append(lab, select);
    const hint = document.createElement('p');
    hint.className = 'field__hint';
    hint.textContent = 'Qué es la empresa. No es el rubro de sus clientes.';
    field.appendChild(hint);
    return field;
  },

  setStatus(msg) {
    const texto = msg || '';
    const formEl = document.getElementById('perfilEmpresaFormStatus');
    const globalEl = document.getElementById('perfilEmpresaStatus');
    const destino = formEl || globalEl;
    if (destino) destino.textContent = texto;
    if (formEl && globalEl) globalEl.textContent = '';
    if (formEl) {
      formEl.classList.toggle('perfil-empresa__form-status--error', !!texto);
    }
  },

  pintarCargaMias(host, texto) {
    while (host.firstChild) host.removeChild(host.firstChild);
    const box = document.createElement('div');
    box.className = 'perfil-empresa__carga';
    box.setAttribute('role', 'status');
    box.setAttribute('aria-live', 'polite');
    const spin = document.createElement('span');
    spin.className = 'perfil-empresa__spinner';
    spin.setAttribute('aria-hidden', 'true');
    const msg = document.createElement('p');
    msg.className = 'perfil-empresa__carga-texto';
    msg.textContent = texto || 'Cargando sus empresas…';
    box.append(spin, msg);
    host.appendChild(box);
  },

  etiquetaCategoria(id) {
    const cats = PerfilEmpresa.categorias();
    const hit = cats.find((c) => c.id === id);
    return (hit && hit.label) || id || '';
  },

  metaEmpresa(n) {
    const partes = [PerfilEmpresa.etiquetaCategoria(n.categoria || '')];
    if (n.rater_listo && n.indice_transparencia != null) {
      partes.push('★ ' + Number(n.indice_transparencia).toFixed(1));
    }
    const rutTxt = (n.rut_empresa || '').trim();
    partes.push(rutTxt ? 'RUT ' + rutTxt : 'Sin RUT');
    return partes.filter(Boolean).join(' ');
  },

  pintarListaMias(host, lista) {
    while (host.firstChild) host.removeChild(host.firstChild);
    if (!lista.length) {
      const vacio = document.createElement('p');
      vacio.className = 'field__hint';
      vacio.textContent = 'Aún no tiene empresas asociadas a esta cuenta.';
      host.appendChild(vacio);
      return;
    }
    const ul = document.createElement('ul');
    ul.className = 'perfil-empresa__lista';
    lista.forEach((n) => {
      const li = document.createElement('li');
      li.className = 'perfil-empresa__item';
      if (n.id) li.dataset.businessId = String(n.id);
      const texto = document.createElement('div');
      texto.className = 'perfil-empresa__item-texto';
      const nombre = document.createElement('strong');
      nombre.textContent = n.nombre;
      const meta = document.createElement('span');
      meta.className = 'perfil-empresa__item-meta';
      meta.textContent = PerfilEmpresa.metaEmpresa(n);
      texto.append(nombre, meta);
      const accionesItem = document.createElement('div');
      accionesItem.className = 'perfil-empresa__item-acciones';
      const actualizar = document.createElement('button');
      actualizar.type = 'button';
      actualizar.className = 'perfil-empresa__btn perfil-empresa__btn--editar';
      actualizar.textContent = 'Editar ficha';
      actualizar.addEventListener('click', () => PerfilEmpresa.mostrarModo('editar', n));
      const quitar = document.createElement('button');
      quitar.type = 'button';
      quitar.className = 'perfil-empresa__btn perfil-empresa__btn--eliminar';
      quitar.textContent = 'Eliminar';
      quitar.addEventListener('click', () => PerfilEmpresa.quitarEmpresa(n.id, n.nombre));
      accionesItem.append(actualizar, quitar);
      const superior = document.createElement('div');
      superior.className = 'perfil-empresa__item-superior';
      superior.append(texto, accionesItem);
      li.appendChild(superior);
      if (typeof Trabajos !== 'undefined' && n.id) {
        li.appendChild(Trabajos.panelConcretarTitular(n));
      }
      ul.appendChild(li);
    });
    host.appendChild(ul);
  },

  actualizarMetaEnLista(n) {
    const host = document.getElementById('perfilEmpresaMias');
    if (!host || !n || !n.id) return;
    const li = host.querySelector(
      '.perfil-empresa__item[data-business-id="' + String(n.id) + '"]'
    );
    if (!li) return;
    const meta = li.querySelector('.perfil-empresa__item-meta');
    if (meta) meta.textContent = PerfilEmpresa.metaEmpresa(n);
  },

  async completarIndicesMias(lista, intentos) {
    const max = intentos == null ? 8 : intentos;
    if (!lista || !lista.length || max <= 0) return;
    const pendientes = lista.filter((n) => n && n.id && !n.rater_listo);
    if (!pendientes.length) return;
    await Promise.all(
      pendientes.map((n) =>
        Auth.request('/v1/businesses/' + encodeURIComponent(n.id) + '/reputation', {
          token: Auth.sesion.token
        })
          .then((r) => {
            if (!r || !r.ok || !r.data) return;
            if (r.data.rater_listo) {
              n.rater_listo = true;
              n.indice_transparencia = r.data.indice_transparencia;
              n.indice_pct = r.data.indice_pct;
              PerfilEmpresa.actualizarMetaEnLista(n);
            }
          })
          .catch(() => null)
      )
    );
    if (lista.some((n) => n && n.id && !n.rater_listo)) {
      await new Promise((resolve) => setTimeout(resolve, 1200));
      return PerfilEmpresa.completarIndicesMias(lista, max - 1);
    }
  },

  async cargarMias() {
    const host = document.getElementById('perfilEmpresaMias');
    if (!host || !Auth.isAuthenticated()) return;
    PerfilEmpresa.pintarCargaMias(host, 'Cargando sus empresas…');
    const res = await Auth.request('/v1/businesses/mias', { token: Auth.sesion.token });
    if (!res.ok) {
      while (host.firstChild) host.removeChild(host.firstChild);
      const err = document.createElement('p');
      err.className = 'error-text';
      err.textContent = res.error || 'No se pudieron cargar sus empresas.';
      host.appendChild(err);
      return;
    }
    const lista = Array.isArray(res.data) ? res.data : [];
    PerfilEmpresa._mias = lista;
    PerfilEmpresa.pintarListaMias(host, lista);
    PerfilEmpresa.completarIndicesMias(lista);
  },

  async quitarEmpresa(id, nombre) {
    if (!Auth.isAuthenticated()) {
      PerfilEmpresa.setStatus('Inicie sesión para gestionar sus empresas.');
      return;
    }
    const ok = window.confirm(
      '¿Eliminar «' +
        (nombre || 'esta empresa') +
        '»? Deja de aparecer en Explorar y se borra de la base de datos.'
    );
    if (!ok) return;
    PerfilEmpresa.setStatus('Eliminando…');
    const res = await Auth.request(
      '/v1/businesses/' + encodeURIComponent(id),
      { method: 'DELETE', token: Auth.sesion.token }
    );
    if (!res.ok) {
      PerfilEmpresa.setStatus(res.error || 'No se pudo eliminar la empresa.');
      return;
    }
    if (typeof Market !== 'undefined') {
      Market._cache = null;
      Market._firma = '';
      if (Market._reps) delete Market._reps[String(id)];
      Market.negocios = (Market.negocios || []).filter((n) => String(n.id) !== String(id));
    }
    if (typeof SubirConfianza !== 'undefined') {
      SubirConfianza.empresas = null;
      SubirConfianza.reputacionMia = null;
    }
    PerfilEmpresa.setStatus('Empresa eliminada.');
    PerfilEmpresa.cargarMias();
  },

  urlRetornoPublicacion() {
    let base = window.location.origin + window.location.pathname;
    if (typeof MarketMonetizacion !== 'undefined' && MarketMonetizacion.urlRetornoPago) {
      base = MarketMonetizacion.urlRetornoPago();
    } else {
      base = base + (base.indexOf('?') >= 0 ? '&' : '?') + 'pago=retorno';
    }
    if (base.indexOf('producto=publicacion') < 0) {
      base += (base.indexOf('?') >= 0 ? '&' : '?') + 'producto=publicacion';
    }
    return base;
  },

  async enviarCrear() {
    if (!PerfilEmpresa.esProveedor()) {
      PerfilEmpresa.setStatus('Solo una cuenta proveedor puede crear fichas.');
      return;
    }
    if (!Auth.isAuthenticated()) {
      PerfilEmpresa.setStatus('Inicie sesión para crear una empresa.');
      return;
    }
    const datos = PerfilEmpresa.validarForm(PerfilEmpresa.leerForm());
    if (!datos) return;
    PerfilEmpresa.guardarBorrador(datos);
    PerfilEmpresa.setStatus(
      'Iniciando pago de publicación (' +
        PerfilEmpresa.precioPublicacionTxt() +
        ')…'
    );

    const acceso = await Auth.request('/v1/pagos/publicacion/acceso', {
      method: 'GET',
      token: Auth.sesion.token
    });
    if (acceso.ok && acceso.data && acceso.data.autorizado && !acceso.data.consumido) {
      await PerfilEmpresa.crearConBuyOrder(datos, acceso.data.buy_order);
      return;
    }

    const ini = await Auth.request('/v1/pagos/publicacion', {
      method: 'POST',
      token: Auth.sesion.token,
      body: { return_url: PerfilEmpresa.urlRetornoPublicacion() }
    });
    if (!ini.ok) {
      const detail = ini.data && ini.data.detail;
      const codigo = detail && detail.codigo;
      if (codigo === 'cupon_disponible' && detail.buy_order) {
        await PerfilEmpresa.crearConBuyOrder(datos, detail.buy_order);
        return;
      }
      PerfilEmpresa.setStatus(
        (detail && detail.mensaje) || ini.error || 'No se pudo iniciar el pago.'
      );
      return;
    }
    PerfilEmpresa.guardarPagoPendiente({
      buy_order: ini.data.buy_order,
      token: ini.data.token,
      reclamo: ini.data.reclamo
    });
    PerfilEmpresa.setStatus('Redirigiendo a Webpay…');
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = ini.data.url;
    form.style.display = 'none';
    const tokenField = document.createElement('input');
    tokenField.type = 'hidden';
    tokenField.name = 'token_ws';
    tokenField.value = ini.data.token;
    form.appendChild(tokenField);
    document.body.appendChild(form);
    form.submit();
  },

  async crearConBuyOrder(datos, buyOrder) {
    const host = document.getElementById('perfilEmpresaMias');
    const prev = Array.isArray(PerfilEmpresa._mias) ? PerfilEmpresa._mias.slice() : [];
    const provisional = {
      id: null,
      nombre: datos.nombre,
      categoria: datos.categoria,
      rut_empresa: datos.rut_empresa,
      telefono: datos.telefono || null,
      sitio_web: datos.sitio_web || null,
      direccion: datos.direccion,
      descripcion: datos.descripcion || null,
      servicios: datos.servicios,
      industrias: datos.industrias,
      contrataciones: datos.contrataciones,
      monto: datos.monto || null,
      plazo: datos.plazo || null,
      referencias: datos.referencias,
      rater_listo: false
    };
    const listaOptimistic = [provisional].concat(prev);
    PerfilEmpresa._mias = listaOptimistic;
    if (host) PerfilEmpresa.pintarListaMias(host, listaOptimistic);
    PerfilEmpresa.cerrarPanel();
    PerfilEmpresa.setStatus('Publicando ficha…');

    const res = await Auth.request('/v1/businesses', {
      method: 'POST',
      body: {
        nombre: datos.nombre,
        categoria: datos.categoria,
        direccion: datos.direccion,
        telefono: datos.telefono || null,
        sitio_web: datos.sitio_web || null,
        imagen_url: datos.imagen_url || null,
        logo_url: datos.logo_url || null,
        descripcion: datos.descripcion || null,
        rut_empresa: datos.rut_empresa,
        servicios: datos.servicios,
        industrias: datos.industrias,
        contrataciones: datos.contrataciones,
        monto: datos.monto || null,
        plazo: datos.plazo || null,
        referencias: datos.referencias,
        buy_order: buyOrder
      },
      token: Auth.sesion.token
    });
    if (!res.ok) {
      PerfilEmpresa._mias = prev;
      if (host) PerfilEmpresa.pintarListaMias(host, prev);
      const detail = res.data && res.data.detail;
      PerfilEmpresa.setStatus(
        (detail && detail.mensaje) || res.error || 'No se pudo crear la empresa.'
      );
      return false;
    }
    const creado = res.data || {};
    Object.assign(provisional, creado, { rater_listo: !!creado.rater_listo });
    if (host) PerfilEmpresa.pintarListaMias(host, PerfilEmpresa._mias);
    PerfilEmpresa.limpiarBorrador();
    PerfilEmpresa.limpiarPagoPendiente();
    if (typeof MarketMonetizacion !== 'undefined' && MarketMonetizacion.limpiarPagoPendiente) {
      MarketMonetizacion.limpiarPagoPendiente();
    }
    PerfilEmpresa.setStatus('Empresa publicada. Ya aparece en Explorar.');
    if (typeof SubirConfianza !== 'undefined') {
      SubirConfianza.empresas = null;
      SubirConfianza.reputacionMia = null;
    }
    if (typeof Market !== 'undefined') {
      Market._cache = null;
      Market._firma = '';
    }
    PerfilEmpresa.completarIndicesMias(PerfilEmpresa._mias);
    return true;
  },

  async procesarRetornoPublicacion() {
    if (PerfilEmpresa._confirmandoPublicacion) return true;
    if (typeof MarketMonetizacion !== 'undefined' && MarketMonetizacion.capturarRetornoDesdeUrl) {
      MarketMonetizacion.capturarRetornoDesdeUrl();
    }
    const sesion = typeof Auth !== 'undefined' ? Auth.getCurrentUser() : null;
    if (!sesion || !sesion.token) {
      const status = document.getElementById('loginStatus');
      if (status) {
        status.textContent =
          'Pago de publicación recibido. Inicie sesión para crear la ficha.';
      }
      return true;
    }
    PerfilEmpresa._confirmandoPublicacion = true;
    try {
      return await PerfilEmpresa._procesarRetornoPublicacionAutenticado(sesion);
    } finally {
      PerfilEmpresa._confirmandoPublicacion = false;
    }
  },

  async _procesarRetornoPublicacionAutenticado(sesion) {
    const params = new URLSearchParams(window.location.search || '');
    const guardado =
      (typeof MarketMonetizacion !== 'undefined' &&
        MarketMonetizacion.leerRetornoPago &&
        MarketMonetizacion.leerRetornoPago()) ||
      {};
    const tokenWs = params.get('token_ws') || guardado.token_ws || null;
    const tbkToken = params.get('TBK_TOKEN') || guardado.tbk_token || null;
    const pendiente = PerfilEmpresa.leerPagoPendiente() || {};
    const orden =
      pendiente.buy_order ||
      params.get('TBK_ORDEN_COMPRA') ||
      guardado.tbk_orden ||
      null;

    async function irAPerfil() {
      if (typeof App !== 'undefined' && App.openSection) {
        await App.openSection('perfil');
      } else if (typeof App !== 'undefined' && App.showView) {
        App.showView('perfilView');
        if (typeof PerfilEmpresa.init === 'function') PerfilEmpresa.init();
      }
    }

    if (tbkToken && !tokenWs) {
      if (orden) {
        await Auth.request('/v1/pagos/publicacion/anular', {
          method: 'POST',
          token: sesion.token,
          body: { buy_order: orden, motivo: 'Cancelado o abortado en Webpay' }
        });
      }
      PerfilEmpresa.limpiarPagoPendiente();
      await irAPerfil();
      PerfilEmpresa.setStatus('Pago de publicación cancelado en Webpay.');
      return true;
    }

    await irAPerfil();
    PerfilEmpresa.setStatus('Confirmando pago de publicación…');
    let conf;
    if (tokenWs) {
      conf = await Auth.request('/v1/pagos/publicacion/confirmar', {
        method: 'POST',
        token: sesion.token,
        body: { token: tokenWs }
      });
    } else if (orden) {
      conf = await Auth.request('/v1/pagos/publicacion/recuperar', {
        method: 'POST',
        token: sesion.token,
        body: { buy_order: orden }
      });
    } else {
      PerfilEmpresa.setStatus('No se pudo recuperar el pago de publicación.');
      return true;
    }

    if (!conf.ok || !conf.data || !conf.data.autorizado) {
      const detail = conf.data && conf.data.detail;
      PerfilEmpresa.setStatus(
        (detail && detail.mensaje) ||
          (conf.data && conf.data.error_detalle) ||
          conf.error ||
          'El pago de publicación no fue autorizado.'
      );
      return true;
    }

    if (typeof MarketMonetizacion !== 'undefined' && MarketMonetizacion.limpiarPagoPendiente) {
      try {
        sessionStorage.removeItem(MarketMonetizacion.STORAGE_PAGO_RETORNO);
      } catch (_) {
      }
    }

    const datos = PerfilEmpresa.leerBorrador();
    if (!datos) {
      PerfilEmpresa.setStatus(
        'Pago OK (orden ' +
          conf.data.buy_order +
          '). Complete el formulario y publique para usar el cupón.'
      );
      PerfilEmpresa.mostrarModo('crear');
      return true;
    }
    await PerfilEmpresa.crearConBuyOrder(datos, conf.data.buy_order);
    return true;
  },

  async enviarActualizar() {
    if (!PerfilEmpresa.esProveedor()) {
      PerfilEmpresa.setStatus('Solo una cuenta proveedor puede editar fichas.');
      return;
    }
    if (!Auth.isAuthenticated()) {
      PerfilEmpresa.setStatus('Inicie sesión para actualizar la empresa.');
      return;
    }
    const id = PerfilEmpresa.editandoId;
    if (!id) {
      PerfilEmpresa.setStatus('No hay empresa seleccionada para actualizar.');
      return;
    }
    const datos = PerfilEmpresa.validarForm(PerfilEmpresa.leerForm());
    if (!datos) return;
    PerfilEmpresa.setStatus('Guardando cambios y actualizando consultas…');
    const res = await Auth.request('/v1/businesses/' + encodeURIComponent(id), {
      method: 'PATCH',
      body: {
        nombre: datos.nombre,
        categoria: datos.categoria,
        direccion: datos.direccion,
        telefono: datos.telefono || null,
        sitio_web: datos.sitio_web || null,
        imagen_url: datos.imagen_url || null,
        logo_url: datos.logo_url || null,
        descripcion: datos.descripcion || null,
        rut_empresa: datos.rut_empresa,
        servicios: datos.servicios,
        industrias: datos.industrias,
        contrataciones: datos.contrataciones,
        monto: datos.monto || null,
        plazo: datos.plazo || null,
        referencias: datos.referencias
      },
      token: Auth.sesion.token
    });
    if (!res.ok) {
      PerfilEmpresa.setStatus(res.error || 'No se pudo actualizar la empresa.');
      return;
    }
    PerfilEmpresa.setStatus('Datos actualizados. Las consultas de transparencia se refrescaron.');
    PerfilEmpresa.cerrarPanel();
    if (typeof SubirConfianza !== 'undefined') {
      SubirConfianza.empresas = null;
      SubirConfianza.reputacionMia = null;
    }
    if (typeof Market !== 'undefined') {
      Market._cache = null;
      Market._firma = '';
      if (Market._reps) delete Market._reps[String(id)];
    }
    PerfilEmpresa.cargarMias();
  }
};
