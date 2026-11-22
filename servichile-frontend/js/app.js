const Carga = {
  _jobs: Object.create(null),

  script(src) {
    if (!Carga._jobs[src]) {
      Carga._jobs[src] = new Promise(function (resolve, reject) {
        const el = document.createElement('script');
        el.src = src;
        el.onload = function () { resolve(); };
        el.onerror = function () { reject(new Error(src)); };
        document.body.appendChild(el);
      });
    }
    return Carga._jobs[src];
  },

  async serie(srcs) {
    for (let i = 0; i < srcs.length; i++) await Carga.script(srcs[i]);
  },

  vistas() {
    const v =
      (typeof Auth !== 'undefined' && Auth.APP_VERSION) ||
      (typeof window !== 'undefined' && window.SERVICHILE_APP_VERSION) ||
      '219';
    return Carga.serie([
      'js/vendor/qrcode.min.js?v=' + v,
      'js/modules/reporte-persona.js?v=' + v,
      'js/modules/reporte-empresa.js?v=' + v,
      'js/modules/reporte-qr.js?v=' + v,
      'js/modules/subir-confianza.js?v=' + v,
      'js/modules/perfil-empresa.js?v=' + v
    ]);
  }
};

const App = {
  state: { rutVerificado: false, perfilGuardado: null },
  elements: {},

  async init() {

    try {
      if (
        window.location.hostname === '127.0.0.1' &&
        !window.SERVICHILE_ALLOW_127
      ) {
        const u = new URL(window.location.href);
        u.hostname = 'localhost';
        window.location.replace(u.toString());
        return;
      }
    } catch (_) {

    }
    Auth.init();
    App.cacheElements();
    App.bindAuthEvents();

    if (
      typeof MarketMonetizacion !== 'undefined' &&
      MarketMonetizacion.capturarRetornoDesdeUrl
    ) {
      MarketMonetizacion.capturarRetornoDesdeUrl();

      if (
        MarketMonetizacion.esRetornoPublicacion &&
        MarketMonetizacion.esRetornoPublicacion()
      ) {
        const v =
          (typeof Auth !== 'undefined' && Auth.APP_VERSION) ||
          (typeof window !== 'undefined' && window.SERVICHILE_APP_VERSION) ||
          '219';
        Carga.script('js/modules/perfil-empresa.js?v=' + v).catch(function () {});
      }
      if (
        !Auth.isAuthenticated() &&
        MarketMonetizacion.hayRetornoPendiente &&
        MarketMonetizacion.hayRetornoPendiente()
      ) {
        const pendiente = MarketMonetizacion.leerPagoPendiente
          ? MarketMonetizacion.leerPagoPendiente() || {}
          : {};
        const retorno = MarketMonetizacion.leerRetornoPago
          ? MarketMonetizacion.leerRetornoPago() || {}
          : {};
        const orden = pendiente.buy_order || retorno.tbk_orden || '';
        const esPub =
          pendiente.producto === 'publicacion' ||
          retorno.producto === 'publicacion';
        if (App.elements.loginStatus) {
          App.elements.loginStatus.classList.remove('is-error');
          App.elements.loginStatus.textContent =
            'Pago recibido' +
            (orden ? ' (orden ' + orden + ')' : '') +
            (esPub
              ? '. Inicie sesión para publicar la ficha.'
              : '. Inicie sesión para entregar el informe.');
        }
      }
    }

    if (Auth.isAuthenticated()) {
      await Auth.verificarSesion();
    }
    App.applyAuthState();
    if (typeof Compliance !== 'undefined') Compliance.initCookieBanner();
  },

  async verifySession() {
    const vigente = await Auth.verificarSesion();
    if (!vigente) App.applyAuthState();
  },

  cacheElements() {
    const ids = [
      'logoutBtn', 'authGate', 'loginForm', 'loginStatus',
      'historyBtn', 'historyPanel', 'historyOverlay',
      'historyClose', 'historyMenu', 'mapView', 'perfilView', 'perfilStatus',
      'perfilReporte', 'perfilForm', 'perfilNombre', 'perfilCorreo', 'perfilEdad',
      'perfilTelefono', 'perfilRut', 'perfilGuardar', 'perfilFormStatus',
      'perfilLogout', 'perfilEliminar',
      'perfilEliminarForm', 'perfilEliminarPass', 'perfilEliminarCancelar',
      'perfilEliminarStatus', 'verifyView', 'subirConfianzaView'
    ];
    ids.forEach(id => App.elements[id] = document.getElementById(id));
    App.elements.appHeader = document.querySelector('.app-header');
    App.elements.appMain = document.getElementById('main');
    App.elements.appFooter = document.querySelector('.app-footer');
  },

  bindAuthEvents() {
    App.elements.loginForm.addEventListener('submit', App.handleLogin);
    App.elements.logoutBtn.addEventListener('click', App.handleLogout);
    App.elements.historyBtn.addEventListener('click', App.openHistory);
    App.elements.historyClose.addEventListener('click', App.closeHistory);
    App.elements.historyOverlay.addEventListener('click', App.closeHistory);
    App.elements.historyMenu.addEventListener('click', App.handleMenuClick);
    App.elements.perfilForm.addEventListener('submit', App.handlePerfilGuardar);
    App.elements.perfilEdad.addEventListener('input', App.actualizarBotonGuardarPerfil);
    App.elements.perfilTelefono.addEventListener('focus', App.prefijoTelefonoPerfil);
    App.elements.perfilTelefono.addEventListener('click', App.protegerPrefijoTelefono);
    App.elements.perfilTelefono.addEventListener('keydown', App.protegerPrefijoTelefonoTecla);
    App.elements.perfilTelefono.addEventListener('input', App.formatearTelefonoPerfil);
    App.elements.perfilTelefono.addEventListener('blur', App.corregirTelefonoPerfil);
    App.elements.perfilEdad.addEventListener('blur', App.corregirEdadPerfil);
    App.elements.perfilRut.addEventListener('input', App.formatearRutPerfil);
    App.elements.perfilRut.addEventListener('blur', App.corregirRutPerfil);
    App.elements.perfilLogout.addEventListener('click', App.handleLogout);
    App.elements.perfilEliminar.addEventListener('click', App.mostrarEliminarCuenta);
    App.elements.perfilEliminarCancelar.addEventListener('click', App.ocultarEliminarCuenta);
    App.elements.perfilEliminarForm.addEventListener('submit', App.handleEliminarCuenta);
  },

  handleMenuClick(e) {
    const btn = e.target.closest('[data-view]');
    if (!btn) return;
    App.openSection(btn.dataset.view);
  },

  async openSection(name) {
    App.closeHistory();
    const v =
      (typeof Auth !== 'undefined' && Auth.APP_VERSION) ||
      (typeof window !== 'undefined' && window.SERVICHILE_APP_VERSION) ||
      '219';
    if (name === 'mapa') { App.showView('mapView'); return Market.init(); }
    if (name === 'perfil') {
      await Carga.script('js/modules/perfil-empresa.js?v=' + v);
      App.renderPerfil();
      if (typeof PerfilEmpresa !== 'undefined') PerfilEmpresa.init();
      return App.showView('perfilView');
    }
    if (name === 'reportes') {
      await Carga.serie([
        'js/vendor/qrcode.min.js?v=' + v,
        'js/modules/reporte-persona.js?v=' + v,
        'js/modules/reporte-empresa.js?v=' + v,
        'js/modules/reporte-qr.js?v=' + v,
        'js/modules/subir-confianza.js?v=' + v
      ]);
      ReporteQr.init();
      return App.showView('verifyView');
    }
    if (name === 'subir-confianza') {
      await Carga.script('js/modules/subir-confianza.js?v=' + v);
      App.actualizarEtiquetasConfianza();
      App.showView('subirConfianzaView');
      await SubirConfianza.init();
      return;
    }
  },

  esProveedor() {
    return typeof ProgresoCuenta !== 'undefined'
      ? ProgresoCuenta.esProveedor()
      : false;
  },

  esEmpresa() {
    return App.esProveedor();
  },

  actualizarEtiquetasConfianza() {
    const prog =
      typeof ProgresoCuenta !== 'undefined' ? ProgresoCuenta.actual() : null;
    const menuBtn = App.elements.historyMenu
      ? App.elements.historyMenu.querySelector('[data-view="subir-confianza"] span')
      : null;
    if (menuBtn) {
      menuBtn.textContent = prog ? prog.etiquetaMenu() : 'Subir Confianza';
    }
    const tituloVista = document.querySelector('#subirConfianzaView > .section-heading');
    if (tituloVista) {
      tituloVista.textContent = prog ? prog.etiquetaVista() : 'Subir Confianza';
    }
  },

  setMenuActive(name) {
    App.elements.historyMenu.querySelectorAll('[data-view]').forEach(btn => {
      const active = btn.dataset.view === name;
      btn.classList.toggle('history-menu__item--active', active);
      if (active) btn.setAttribute('aria-current', 'page');
      else btn.removeAttribute('aria-current');
    });
  },

  renderPerfil() {
    const user = Auth.getCurrentUser();
    if (!user) {
      App.elements.perfilStatus.textContent = 'Inicie sesión para ver su perfil.';
      return;
    }
    App.elements.perfilStatus.textContent = '';
    const perfil = user.perfil || {};

    App.elements.perfilNombre.value = user.nombre || '';
    App.elements.perfilCorreo.value = user.email || '';
    App.elements.perfilEdad.value = perfil.edad != null ? perfil.edad : '';
    const telRaw = perfil.telefono || '';
    App.elements.perfilTelefono.value =
      telRaw && typeof Security !== 'undefined' ? Security.formatTelefono(telRaw) : telRaw;
    const prog =
      typeof ProgresoCuenta !== 'undefined' ? ProgresoCuenta.para(perfil) : null;
    const campoEdad = App.elements.perfilEdad.closest('.field');
    if (campoEdad) campoEdad.hidden = prog ? !prog.soporta('edad') : false;
    App.state.rutVerificado = !!perfil.rut_verificado;
    App.elements.perfilRut.value = App.state.rutVerificado ? 'Verificado' : '';
    App.elements.perfilRut.placeholder = App.state.rutVerificado ? 'Verificado' : '12.345.678-5';
    App.elements.perfilRut.disabled = App.state.rutVerificado;
    App.state.perfilGuardado = {
      edad: App.elements.perfilEdad.value,
      telefono: App.elements.perfilTelefono.value
    };

    const filas = prog
      ? prog.filasEstado({ origen: 'perfil', perfil })
      : [['Tipo de cuenta', perfil.tipo_cuenta || 'Sin indicar']];
    App.renderDefinitionList(App.elements.perfilReporte, filas);
    App.actualizarEtiquetasConfianza();
    App.actualizarBotonGuardarPerfil();
  },

  actualizarBotonGuardarPerfil() {
    const cambios = App.cambiosPerfil();
    App.elements.perfilGuardar.disabled = Object.keys(cambios).length === 0;
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

  PREFIJO_TEL: '+56 9 ',

  _cursorTrasPrefijoTel(input, forzarFinal) {
    if (!input) return;
    const min = App.PREFIJO_TEL.length;
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

  prefijoTelefonoPerfil() {
    const input = App.elements.perfilTelefono;
    if (!input || input.disabled) return;
    const vacio = !input.value.trim();
    if (vacio) input.value = App.PREFIJO_TEL;
    App._cursorTrasPrefijoTel(input, vacio);
  },

  protegerPrefijoTelefono() {
    const input = App.elements.perfilTelefono;
    if (!input || input.disabled) return;
    if (!input.value.startsWith('+56')) return;
    App._cursorTrasPrefijoTel(input, false);
  },

  protegerPrefijoTelefonoTecla(e) {
    const input = App.elements.perfilTelefono;
    if (!input || input.disabled) return;
    const min = App.PREFIJO_TEL.length;
    if (!input.value.startsWith(App.PREFIJO_TEL.slice(0, 3))) return;
    const start = input.selectionStart == null ? 0 : input.selectionStart;
    const end = input.selectionEnd == null ? start : input.selectionEnd;
    if (
      (e.key === 'Backspace' && start <= min && start === end) ||
      (e.key === 'ArrowLeft' && start <= min) ||
      (e.key === 'Home')
    ) {
      e.preventDefault();
      try {
        input.setSelectionRange(min, min);
      } catch (_) {}
    }
  },

  formatearTelefonoPerfil() {
    const input = App.elements.perfilTelefono;
    if (!input || input.disabled) return;
    if (typeof Security === 'undefined') return;
    const valor = input.value;
    if (!valor.trim() || valor.trim() === '+56' || valor.trim() === '+56 9') {
      if (valor.trim() === '+56' || valor.trim() === '+56 9') {
        input.value = valor.trim() === '+56' ? '+56 ' : '+56 9 ';
      } else {
        input.setCustomValidity('');
        input.removeAttribute('aria-invalid');
      }
      App.actualizarBotonGuardarPerfil();
      return;
    }
    const caret = input.selectionStart;
    const formateado = Security.formatTelefono(valor);
    App._aplicarFormatoInput(input, formateado, caret, valor.length);
    if (Security.validateTelefono(formateado)) {
      input.setCustomValidity('');
      input.removeAttribute('aria-invalid');
    } else {
      input.removeAttribute('aria-invalid');
      input.setCustomValidity('');
    }
    App.actualizarBotonGuardarPerfil();
  },

  corregirTelefonoPerfil() {
    App.formatearTelefonoPerfil();
    const input = App.elements.perfilTelefono;
    if (!input || input.disabled) return;
    let valor = input.value.trim();
    if (!valor || valor === '+56' || valor === '+56 9') {
      input.value = '';
      input.setCustomValidity('');
      input.removeAttribute('aria-invalid');
      App.actualizarBotonGuardarPerfil();
      return;
    }
    if (typeof Security !== 'undefined' && !Security.validateTelefono(valor)) {
      input.setCustomValidity('El teléfono debe comenzar con +56, p. ej. +56 9 1234 5678');
      input.setAttribute('aria-invalid', 'true');
    }
  },

  corregirEdadPerfil() {
    const input = App.elements.perfilEdad;
    if (!input || input.disabled) return;
    const valor = input.value.trim();
    if (!valor) {
      input.setCustomValidity('');
      input.removeAttribute('aria-invalid');
      return;
    }
    if (typeof Security !== 'undefined' && !Security.validateEdad(valor)) {
      input.setCustomValidity('Ingrese una edad entre 14 y 120 años.');
      input.setAttribute('aria-invalid', 'true');
    } else {
      input.setCustomValidity('');
      input.removeAttribute('aria-invalid');
    }
  },

  formatearRutPerfil() {
    const input = App.elements.perfilRut;
    if (!input || input.disabled || App.state.rutVerificado) return;
    if (typeof Security === 'undefined') return;
    const valor = input.value;
    if (!valor.trim()) {
      input.setCustomValidity('');
      input.removeAttribute('aria-invalid');
      App.actualizarBotonGuardarPerfil();
      return;
    }
    const caret = input.selectionStart;
    const formateado = Security.formatRut(valor);
    App._aplicarFormatoInput(input, formateado, caret, valor.length);
    if (Security.validateRut(formateado)) {
      input.setCustomValidity('');
      input.removeAttribute('aria-invalid');
    } else {
      input.removeAttribute('aria-invalid');
      input.setCustomValidity('');
    }
    App.actualizarBotonGuardarPerfil();
  },

  corregirRutPerfil() {
    const input = App.elements.perfilRut;
    if (!input || input.disabled || App.state.rutVerificado) return;
    const valor = input.value.trim();
    if (!valor) {
      input.setCustomValidity('');
      input.removeAttribute('aria-invalid');
      App.actualizarBotonGuardarPerfil();
      return;
    }
    if (typeof Security === 'undefined') return;
    const formateado = Security.formatRut(valor);
    if (formateado !== input.value) input.value = formateado;
    if (Security.validateRut(formateado)) {
      input.setCustomValidity('');
      input.removeAttribute('aria-invalid');
    } else {
      input.setCustomValidity('RUT inválido. Revise el dígito verificador.');
      input.setAttribute('aria-invalid', 'true');
    }
    App.actualizarBotonGuardarPerfil();
  },

  cambiosPerfil() {
    const guardado = App.state.perfilGuardado || {};
    const cambios = {};
    const edad = App.elements.perfilEdad.value.trim();
    const telefono = App.elements.perfilTelefono.value.trim();
    const rut = App.elements.perfilRut.value.trim();
    if (edad !== '' && edad !== guardado.edad) cambios.edad = Number(edad);
    if (edad === '' && guardado.edad !== '') cambios.edad = null;
    if (telefono !== guardado.telefono) cambios.telefono = telefono === '' ? null : telefono;
    if (!App.state.rutVerificado && rut !== '') cambios.rut = rut;
    return cambios;
  },

  etiquetaEstadoReporte(estado) {
    const mapa = { basico: 'Básico', pendiente: 'En revisión', verificado: 'Verificado', rechazado: 'Rechazado' };
    return mapa[estado] || 'Básico';
  },

  renderDefinitionList(dl, filas) {
    while (dl.firstChild) dl.removeChild(dl.firstChild);
    filas.forEach(([k, v]) => {
      const dt = document.createElement('dt');
      dt.textContent = k;
      const dd = document.createElement('dd');
      dd.textContent = v;
      dl.append(dt, dd);
    });
  },

  async handlePerfilGuardar(e) {
    e.preventDefault();
    App.corregirTelefonoPerfil();
    App.corregirRutPerfil();
    App.corregirEdadPerfil();

    const edad = App.elements.perfilEdad.value.trim();
    const telefono = App.elements.perfilTelefono.value.trim();
    const rut = App.elements.perfilRut.value.trim();
    if (edad && typeof Security !== 'undefined' && !Security.validateEdad(edad)) {
      App.elements.perfilFormStatus.textContent =
        'Edad inválida. Ingrese un valor entre 14 y 120 años.';
      App.elements.perfilEdad.focus();
      return;
    }
    if (telefono && typeof Security !== 'undefined' && !Security.validateTelefono(telefono)) {
      App.elements.perfilFormStatus.textContent =
        'Teléfono inválido. Debe comenzar con +56, p. ej. +56 9 1234 5678.';
      App.elements.perfilTelefono.focus();
      return;
    }
    if (!App.state.rutVerificado && rut && typeof Security !== 'undefined' && !Security.validateRut(rut)) {
      App.elements.perfilFormStatus.textContent =
        'RUT inválido. Se corrigió el formato; revise el dígito verificador.';
      App.elements.perfilRut.focus();
      return;
    }

    const cambios = App.cambiosPerfil();
    if (Object.keys(cambios).length === 0) {
      App.actualizarBotonGuardarPerfil();
      return;
    }
    App.elements.perfilGuardar.disabled = true;
    App.elements.perfilFormStatus.textContent = '';
    const res = await Auth.actualizarPerfil(cambios);
    App.elements.perfilGuardar.disabled = false;
    if (!res.ok) {
      App.elements.perfilFormStatus.textContent = res.error;
      return;
    }
    App.renderPerfil();
    App.elements.perfilFormStatus.textContent = 'Perfil actualizado.';
  },

  mostrarEliminarCuenta() {
    App.elements.perfilEliminarForm.hidden = false;
    App.elements.perfilEliminarPass.value = '';
    App.elements.perfilEliminarStatus.textContent = '';
    App.elements.perfilEliminarForm.scrollIntoView({ behavior: 'smooth', block: 'center' });
    App.elements.perfilEliminarPass.focus({ preventScroll: true });
  },

  ocultarEliminarCuenta() {
    App.elements.perfilEliminarForm.hidden = true;
    App.elements.perfilEliminarPass.value = '';
    App.elements.perfilEliminarStatus.textContent = '';
  },

  async handleEliminarCuenta(e) {
    e.preventDefault();
    const boton = App.elements.perfilEliminarForm.querySelector('button[type="submit"]');
    boton.disabled = true;
    const res = await Auth.eliminarCuenta(App.elements.perfilEliminarPass.value);
    boton.disabled = false;
    if (!res.ok) {
      App.elements.perfilEliminarStatus.textContent = res.error;
      return;
    }
    App.ocultarEliminarCuenta();
    App.handleLogout();
  },

  applyAuthState() {
    const authed = Auth.isAuthenticated();
    document.documentElement.classList.toggle('boot-authed', authed);
    App.elements.authGate.hidden = authed;
    App.elements.appHeader.hidden = !authed;
    App.elements.appMain.hidden = !authed;
    App.elements.logoutBtn.hidden = !authed;
    App.elements.historyBtn.hidden = !authed;

    if (authed) {
      App.actualizarEtiquetasConfianza();
      App.openSection('mapa');
      const precargar = function () { Carga.vistas().catch(function () {}); };
      if (window.requestIdleCallback) requestIdleCallback(precargar, { timeout: 1200 });
      else setTimeout(precargar, 300);
    } else {
      App.closeHistory();
    }
  },

  openHistory() {
    App.elements.historyPanel.classList.add('history--open');
    App.elements.historyPanel.setAttribute('aria-hidden', 'false');
    App.elements.historyOverlay.hidden = false;
    App.elements.historyBtn.setAttribute('aria-expanded', 'true');
  },

  closeHistory() {
    App.elements.historyPanel.classList.remove('history--open');
    App.elements.historyPanel.setAttribute('aria-hidden', 'true');
    App.elements.historyOverlay.hidden = true;
    App.elements.historyBtn.setAttribute('aria-expanded', 'false');
  },

  async handleLogin(e) {
    e.preventDefault();
    const fd = new FormData(App.elements.loginForm);
    const submit = App.elements.loginForm.querySelector('button[type="submit"]');
    if (submit) submit.disabled = true;
    const res = await Auth.login(fd.get('email'), fd.get('password'));
    if (submit) submit.disabled = false;
    if (!res.ok) {
      App.elements.loginStatus.classList.add('is-error');
      App.elements.loginStatus.textContent = res.error;
      return;
    }
    App.elements.loginForm.reset();
    App.elements.loginStatus.classList.remove('is-error');
    App.elements.loginStatus.textContent = '';
    App.applyAuthState();
    if (
      typeof MarketMonetizacion !== 'undefined' &&
      MarketMonetizacion.hayRetornoPendiente &&
      MarketMonetizacion.hayRetornoPendiente() &&
      MarketMonetizacion.procesarRetornoPago
    ) {
      MarketMonetizacion.procesarRetornoPago();
    }
  },

  handleLogout() {
    Auth.logout();
    App.applyAuthState();
  },

  showView(name) {
    const sectionByView = {
      mapView: 'mapa',
      perfilView: 'perfil',
      verifyView: 'reportes',
      subirConfianzaView: 'subir-confianza'
    };
    if (name !== 'verifyView' && typeof ReporteQr !== 'undefined' && ReporteQr.detener) {
      ReporteQr.detener();
    }
    ['mapView', 'perfilView', 'verifyView', 'subirConfianzaView'].forEach(n => {
      if (App.elements[n]) App.elements[n].hidden = n !== name;
    });
    App.setMenuActive(sectionByView[name] || 'mapa');
    window.scrollTo(0, 0);
  }
};

document.addEventListener('DOMContentLoaded', () => {
  App.init();
});
