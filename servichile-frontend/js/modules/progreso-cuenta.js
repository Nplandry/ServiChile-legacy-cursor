

const ProgresoCuenta = {
  REGISTRO: Object.create(null),

  ESTADOS_PASAPORTE: Object.freeze({
    basico: 'Básico',
    pendiente: 'En revisión',
    verificado: 'Verificado',
    rechazado: 'Rechazado'
  }),

  registrar(tipo, mezcla) {
    const proto = Object.create(ProgresoCuenta.Base);
    const features = Object.assign(
      Object.create(null),
      ProgresoCuenta.Base.FEATURES,
      mezcla.FEATURES || {}
    );
    const inst = Object.assign(proto, mezcla, {
      tipo,
      FEATURES: Object.freeze(features)
    });
    if (Array.isArray(inst.DOCS)) inst.DOCS = Object.freeze(inst.DOCS.slice());
    ProgresoCuenta.REGISTRO[tipo] = inst;
    return inst;
  },

  normalizar(tipo) {
    if (tipo === 'proveedor' || tipo === 'empresa') return 'proveedor';
    if (tipo === 'contratista') return 'contratista';
    return 'persona';
  },

  tipoDe(src) {
    if (!src || typeof src !== 'object') return 'persona';
    const raw = src.tipo_cuenta || (src.perfil && src.perfil.tipo_cuenta) || null;
    return ProgresoCuenta.normalizar(raw);
  },

  de(tipo) {
    const clave = ProgresoCuenta.normalizar(tipo);
    return ProgresoCuenta.REGISTRO[clave] || ProgresoCuenta.REGISTRO.persona;
  },

  para(src) {
    return ProgresoCuenta.de(ProgresoCuenta.tipoDe(src));
  },

  actual() {
    const user = typeof Auth !== 'undefined' ? Auth.getCurrentUser() : null;
    return ProgresoCuenta.para(user);
  },

  esProveedor(src) {
    if (src == null) return ProgresoCuenta.actual().es('proveedor');
    if (src && typeof src.es === 'function' && src.tipo) return src.es('proveedor');
    return ProgresoCuenta.para(src).es('proveedor');
  },

  esEmpresa(src) {
    return ProgresoCuenta.esProveedor(src);
  },

  esPersonaLike(src) {
    const prog =
      src == null
        ? ProgresoCuenta.actual()
        : src && typeof src.es === 'function' && src.tipo
          ? src
          : ProgresoCuenta.para(src);
    return prog.es('persona') || prog.es('contratista');
  },

  etiquetaTipo(tipoOSrc) {
    if (typeof tipoOSrc === 'string') return ProgresoCuenta.de(tipoOSrc).etiquetaCorta();
    return ProgresoCuenta.para(tipoOSrc).etiquetaCorta();
  },

  Base: {
    tipo: 'persona',
    FEATURES: Object.freeze({}),
    DOCS: Object.freeze([]),

    es(tipo) {
      return this.tipo === tipo;
    },

    soporta(feature) {
      return !!this.FEATURES[feature];
    },

    etiquetaCorta() {
      return 'Cuenta';
    },

    etiquetaMenu() {
      return this.etiquetaVista();
    },

    etiquetaVista() {
      return 'Progreso';
    },

    labelNombre() {
      return 'Nombre';
    },

    placeholderNombre() {
      return 'Tu nombre';
    },

    tituloNombreOnboarding() {
      return '¿Cómo te llamas?';
    },

    textoNombreOnboarding() {
      return 'Usaremos tu nombre para acompañarte mejor.';
    },

    textoLeadQr() {
      return '';
    },

    tituloDocumentos() {
      return 'Subir documentos';
    },

    notaDocumentos() {
      return '';
    },

    tiposDocumento() {
      return this.DOCS;
    },

    idsDocumento() {
      const docs = this.tiposDocumento();
      const out = [];
      for (let i = 0; i < docs.length; i++) out.push(docs[i][0]);
      return out;
    },

    snapshot() {
      return {
        tipo: this.tipo,
        titulo: 'Progreso',
        aria: 'Progreso de la cuenta',
        detalleIzq: '',
        detalleDer: '',
        meta: '',
        valor: '0%',
        pct: 0,
        cta: 'Ver detalle',
        extras: {}
      };
    },

    etiquetaNivel(nivel) {
      const n = Number(nivel) || 1;
      const nombres = {
        1: 'Identidad',
        2: 'Cumplimiento',
        3: 'Identidad reforzada'
      };
      return nombres[n] || 'Identidad';
    },

    filasEstado(ctx) {
      const c = this._ctx(ctx);
      const filas = this.filasCabecera(c);
      const cuerpo = c.origen === 'qr' ? this.filasQr(c) : this.filasPerfil(c);
      this._push(filas, cuerpo);
      return filas;
    },

    filasCabecera() {
      return [['Tipo de cuenta', this.etiquetaCorta()]];
    },

    filasPerfil() {
      return [];
    },

    filasQr() {
      return [];
    },

    seccionesVista() {
      return [];
    },

    montarContenido(raiz) {
      if (!raiz) return;
      const frag = document.createDocumentFragment();
      const secs = this.seccionesVista();
      for (let i = 0; i < secs.length; i++) {
        const factory = secs[i];
        if (typeof factory !== 'function') continue;
        const nodo = factory();
        if (nodo) frag.appendChild(nodo);
      }
      raiz.appendChild(frag);
    },

    montarIndicador(contenedor, opts) {
      if (!contenedor) return null;
      this.limpiar(contenedor);
      const snap = this.snapshot();
      if (!snap || snap.oculto) {
        contenedor.hidden = true;
        return null;
      }
      contenedor.hidden = false;
      contenedor.appendChild(this.crearIndicador(opts || {}, snap));
      return contenedor.firstChild;
    },

    crearIndicador(opts, snapPrev) {
      const opciones = opts || {};
      const snap = snapPrev || this.snapshot();
      if (!snap || snap.oculto) return document.createComment('sin-indicador');
      const card = this.el(
        'section',
        'confianza-indicador' + (opciones.onAbrir ? ' confianza-indicador--accion' : '')
      );
      card.setAttribute('aria-label', snap.aria);

      const arriba = this.el('div', 'confianza-indicador__fila confianza-indicador__fila--arriba');
      arriba.appendChild(
        this.el('p', 'confianza-indicador__izq', snap.detalleIzq || snap.meta || '')
      );
      arriba.appendChild(
        this.el('p', 'confianza-indicador__der', snap.detalleDer || snap.valor || '')
      );
      card.appendChild(arriba);

      const track = this.el('div', 'confianza-indicador__track');
      track.setAttribute('role', 'progressbar');
      track.setAttribute('aria-valuemin', '0');
      track.setAttribute('aria-valuemax', '100');
      track.setAttribute('aria-valuenow', String(snap.pct));
      track.setAttribute('aria-label', snap.aria);
      const fill = this.el('div', 'confianza-indicador__fill');
      fill.style.width = snap.pct + '%';
      track.appendChild(fill);
      card.appendChild(track);

      const abajo = this.el('div', 'confianza-indicador__fila confianza-indicador__fila--abajo');
      abajo.appendChild(this.el('h3', 'confianza-indicador__titulo', snap.titulo));

      let cta = null;
      if (typeof opciones.onAbrir === 'function' && snap.cta) {
        cta = this.el(
          opciones.ctaAsButton ? 'button' : 'span',
          'confianza-indicador__cta',
          snap.cta
        );
        if (opciones.ctaAsButton) {
          cta.type = 'button';
          cta.addEventListener('click', opciones.onAbrir);
        }
        abajo.appendChild(cta);
      }
      card.appendChild(abajo);

      if (typeof opciones.onAbrir === 'function') {
        card.tabIndex = 0;
        card.setAttribute('role', 'button');
        const abrir = (e) => {
          if (e.type === 'keydown' && e.key !== 'Enter' && e.key !== ' ') return;
          if (opciones.ctaAsButton && cta && e.target === cta) return;
          e.preventDefault();
          opciones.onAbrir();
        };
        card.addEventListener('click', abrir);
        card.addEventListener('keydown', abrir);
      }

      return card;
    },

    filaTitular(c) {
      return ['Titular', (c.datos && c.datos.nombre) || '-'];
    },

    filaCorreo(c) {
      if (!(c.propio && c.datos && c.datos.email)) return null;
      return ['Correo', c.datos.email];
    },

    filaEstado(src) {
      return ['Estado', this.etiquetaEstadoReporte(src && src.estado_reporte)];
    },

    filaRut(src) {
      return ['RUT', src && src.rut_verificado ? 'Verificado' : 'Sin verificar'];
    },

    filaXp(src) {
      const xp = src && src.xp != null ? src.xp : 0;
      const nivel = (src && src.nivel_xp) || 1;
      return ['XP', xp + ' Nivel ' + nivel];
    },

    filaNivelReporte(src) {
      return ['Nivel de verificación', 'Nivel ' + ((src && src.nivel_reporte) || 1)];
    },

    filaConfiabilidad(src) {
      const score = src && src.score_confiabilidad;
      return [
        'Confiabilidad',
        score == null ? 'Sin trabajos cerrados' : score + ' / 100'
      ];
    },

    _ctx(ctx) {
      const c = ctx || {};
      const perfil = c.perfil || {};
      return {
        origen: c.origen || 'perfil',
        perfil,
        datos: c.datos || perfil,
        propio: !!c.propio
      };
    },

    _push(destino, filas) {
      if (!filas || !filas.length) return destino;
      for (let i = 0; i < filas.length; i++) {
        if (filas[i]) destino.push(filas[i]);
      }
      return destino;
    },

    el(tag, className, text) {
      const n = document.createElement(tag);
      if (className) n.className = className;
      if (text != null) n.textContent = text;
      return n;
    },

    limpiar(el) {
      while (el.firstChild) el.removeChild(el.firstChild);
    },

    formatoIndice(n) {
      const v = Number(n);
      if (!Number.isFinite(v)) return '-';
      return v.toFixed(1) + ' / 10';
    },

    etiquetaEstadoReporte(estado) {
      return ProgresoCuenta.ESTADOS_PASAPORTE[estado] || 'Básico';
    },

    _sc() {
      return typeof SubirConfianza !== 'undefined' ? SubirConfianza : null;
    }
  }
};

ProgresoCuenta.registrar('persona', {
  FEATURES: Object.freeze({
    edad: true,
    xp: true,
    niveles: true,
    biometria: true,
    reporte: true
  }),

  DOCS: [
    ['antecedentes', 'Certificado de antecedentes (Nivel 3)'],
    ['aval', 'Aval o garantía de respaldo (Nivel 3)']
  ],

  etiquetaCorta() {
    return 'Persona';
  },

  etiquetaMenu() {
    return 'Verificación';
  },

  etiquetaVista() {
    return 'Verificación';
  },

  textoLeadQr() {
    return '';
  },

  textoNombreOnboarding() {
    return 'Aparecerá en su reporte QR al validar trabajos o entregas.';
  },

  snapshot() {
    const sc = this._sc();
    if (sc) sc.cargar();
    const hechas = sc ? sc.tareasHechas() : 0;
    const total = sc ? sc.totalTareas() : 0;
    const pct = sc ? sc.progresoPct() : 0;
    const xp = sc ? sc.xpActual() : 0;
    const nivel = sc ? sc.nivelXp() : 1;
    const nombreNivel = this.etiquetaNivel(nivel);
    const detalleIzq = hechas + ' de ' + total + ' requisitos';
    const detalleDer = 'Nivel ' + nivel + ' ' + nombreNivel;
    return {
      tipo: this.tipo,
      titulo: 'Su verificación',
      aria: 'Progreso de verificación',
      detalleIzq,
      detalleDer,
      meta: detalleIzq + ' ' + detalleDer,
      valor: pct + '%',
      pct,
      cta: 'Ver qué desbloquea',
      extras: { hechas, total, xp, nivel, nombreNivel }
    };
  },

  filasPerfil(c) {
    return [
      this.filaNivelReporte(c.perfil),
      this.filaXp(c.perfil),
      this.filaEstado(c.perfil),
      this.filaConfiabilidad(c.perfil)
    ];
  },

  filasQr(c) {
    return [
      this.filaTitular(c),
      this.filaCorreo(c),
      this.filaNivelReporte(c.datos),
      this.filaXp(c.datos),
      this.filaEstado(c.datos),
      this.filaConfiabilidad(c.datos),
      this.filaRut(c.datos)
    ];
  },

  seccionesVista() {
    const sc = this._sc();
    if (!sc) return [];
    return [
      () => sc.bloqueIndicador(),
      () => sc.bloqueChecklist(),
      () => sc.bloqueBiometria(),
      () => sc.bloqueCedula(),
      () => sc.bloqueDocumentos(),
      () => sc.bloqueTablaNiveles()
    ];
  }
});

ProgresoCuenta.registrar('contratista', {
  FEATURES: Object.freeze({
    edad: true,
    xp: true,
    niveles: true,
    biometria: true,
    reporte: true
  }),

  DOCS: [
    ['antecedentes', 'Certificado de antecedentes (Nivel 3)'],
    ['aval', 'Aval o garantía de respaldo (Nivel 3)']
  ],

  etiquetaCorta() {
    return 'Contratista';
  },

  etiquetaMenu() {
    return 'Verificación';
  },

  etiquetaVista() {
    return 'Verificación';
  },

  textoLeadQr() {
    return '';
  },

  tituloNombreOnboarding() {
    return '¿Cómo te llamas?';
  },

  textoNombreOnboarding() {
    return 'Aparecerá en su reporte QR al validar trabajos o entregas.';
  },

  snapshot() {
    return ProgresoCuenta.REGISTRO.persona.snapshot.call(this);
  },

  filasPerfil(c) {
    return ProgresoCuenta.REGISTRO.persona.filasPerfil.call(this, c);
  },

  filasQr(c) {
    return ProgresoCuenta.REGISTRO.persona.filasQr.call(this, c);
  },

  seccionesVista() {
    return ProgresoCuenta.REGISTRO.persona.seccionesVista.call(this);
  }
});

ProgresoCuenta.registrar('proveedor', {
  FEATURES: Object.freeze({
    indice: true,
    docsLegales: true
  }),

  DOCS: [
    ['carpeta_tributaria', 'Carpeta tributaria electrónica (SII)'],
    ['inicio_actividades', 'Inicio de actividades / situación tributaria (SII)'],
    ['vigencia_sociedad', 'Vigencia de la sociedad (RES/CBR)'],
    ['vigencia_poderes', 'Vigencia de poderes'],
    ['poder_representante', 'Poder del representante legal'],
    ['constitucion', 'Constitución / escritura'],
    ['f30', 'F30 antecedentes laborales y previsionales'],
    ['no_quiebra', 'No quiebra / procedimientos concursales'],
    ['antecedentes_rl', 'Antecedentes del representante legal'],
    ['patente', 'Patente municipal vigente'],
    ['titularidad_cuenta', 'Titularidad de cuenta bancaria empresa']
  ],

  etiquetaCorta() {
    return 'Proveedor';
  },

  etiquetaMenu() {
    return 'Verificación proveedor';
  },

  etiquetaVista() {
    return 'Verificación proveedor';
  },

  labelNombre() {
    return 'Responsable';
  },

  placeholderNombre() {
    return 'Nombre del responsable';
  },

  tituloNombreOnboarding() {
    return '¿Cuál es el nombre del responsable?';
  },

  textoNombreOnboarding() {
    return 'Nombre de la persona responsable de la cuenta. Aparecerá en su perfil y reportes.';
  },

  textoLeadQr() {
    return '';
  },

  tituloDocumentos() {
    return 'Documentos para publicar con transparencia';
  },

  notaDocumentos() {
    return '';
  },

  calcularFicha() {
    const sc = this._sc();
    if (sc && typeof sc.fichaEmpresa === 'function') {
      return sc.fichaEmpresa();
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

  snapshot() {
    const sc = this._sc();
    if (sc) sc.cargar();
    if (sc && typeof sc.tieneEmpresa === 'function' && !sc.tieneEmpresa()) {
      return { oculto: true, tipo: this.tipo };
    }
    const ficha = this.calcularFicha();
    if (ficha._sinFicha || ficha.indice_transparencia == null) {
      return { oculto: true, tipo: this.tipo };
    }
    const indice = Number(ficha.indice_transparencia);
    const docs = ficha._docsCargados || 0;
    const totalDocs = ficha._docsTotal || this.idsDocumento().length || 11;
    const pct =
      ficha.indice_pct != null
        ? Math.round(Number(ficha.indice_pct))
        : Math.round((indice / 10) * 100);
    const titularidad = pct >= 100 ? 'Documentos en orden' : 'Falta documentación';
    const detalleIzq = docs + ' de ' + totalDocs + ' documentos legales';
    const nombreFicha = String((ficha && ficha.nombre) || '').trim() || 'Empresa';
    const detalleDer = nombreFicha + ' ★ ' + indice.toFixed(1);
    return {
      tipo: this.tipo,
      titulo: 'Transparencia para publicar',
      aria: 'Transparencia de ' + nombreFicha,
      detalleIzq,
      detalleDer,
      meta: detalleIzq + ' ' + titularidad,
      valor: detalleDer,
      pct,
      cta: 'Ver transparencia',
      extras: { indice, pct, docs, totalDocs, ficha, nombreFicha }
    };
  },

  filasPerfil(c) {
    const ficha = this.calcularFicha();
    const filas = [];
    if (ficha._sinFicha || ficha.indice_transparencia == null) {
      filas.push(['Empresa', 'No registrada']);
    } else {
      filas.push([
        'Índice de transparencia',
        this.formatoIndice(ficha.indice_transparencia)
      ]);
      filas.push([
        'RUT empresa',
        (ficha.rut_empresa && String(ficha.rut_empresa).trim()) || 'Sin registrar'
      ]);
    }
    filas.push(this.filaEstado(c.perfil));
    filas.push([
      'RUT responsable',
      c.perfil && c.perfil.rut_verificado ? 'Verificado' : 'Sin verificar'
    ]);
    return filas;
  },

  filasQr(c) {
    const ficha = this.calcularFicha();
    const filas = [
      ['Responsable', (c.datos && c.datos.nombre) || '-'],
      this.filaCorreo(c)
    ].filter(Boolean);
    if (!ficha._sinFicha && ficha.indice_transparencia != null) {
      filas.push([
        'Índice de transparencia',
        this.formatoIndice(ficha.indice_transparencia)
      ]);
      filas.push([
        'RUT empresa',
        (ficha.rut_empresa && String(ficha.rut_empresa).trim()) || 'Sin registrar'
      ]);
    } else {
      filas.push(['Empresa', 'No registrada']);
    }
    filas.push(this.filaEstado(c.datos));
    filas.push([
      'RUT responsable',
      c.datos && c.datos.rut_verificado ? 'Verificado' : 'Sin verificar'
    ]);
    return filas;
  },

  seccionesVista() {
    const sc = this._sc();
    if (!sc) return [];
    if (typeof sc.tieneEmpresa === 'function' && !sc.tieneEmpresa()) {
      return [() => sc.bloqueSinEmpresa()];
    }
    return [() => sc.bloqueIndicador(), () => sc.bloqueDocumentos()];
  }
});
