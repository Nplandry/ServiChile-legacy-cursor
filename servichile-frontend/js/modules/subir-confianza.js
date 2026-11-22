
const SubirConfianza = {
  STORAGE_KEY: 'servichile.subirConfianza.cache',
  STORAGE_KEY_LEGACY: 'servichile.subirConfianza.mock',
  carruselIdx: 0,
  tablaAbierta: false,

  NIVELES: [
    {
      id: 1,
      titulo: 'Nivel 1 Identidad',
      evalua: 'Que la persona sea real, accesible y localizable',
      requisito: 'Cuenta activa, identidad verificada y datos de contacto con mayoría de edad.',
      usos: 'Primeros contactos, QR de reporte y primeros trabajos con baja fricción.',
      discriminatorio: false,
      discriminatorioNota: 'NO - base para cualquier trato',
      tareas: [
        {
          id: 'n1-registro',
          label: 'Crear cuenta e iniciar sesión',
          como: 'Se completa al registrarse y mantener una sesión activa en la plataforma.'
        },
        {
          id: 'n1-cedula',
          label: 'Verificar su identidad',
          como: 'Se completa al verificar el RUT en el perfil o al validar la foto frontal del carnet (OCR local, sin reverso).'
        },
        {
          id: 'n1-perfil',
          label: 'Completar teléfono y edad',
          como: 'Se completa al guardar un teléfono móvil y declarar edad de 18 años o más.'
        }
      ]
    },
    {
      id: 2,
      titulo: 'Nivel 2 Cumplimiento',
      evalua: 'Que concreté trabajos y mantenga buen historial',
      requisito: 'Al menos un trabajo concretado, reputación alta y pocos no concretados.',
      usos: 'Trabajos concretados, entregas y tratos recurrentes con respaldo de comportamiento.',
      discriminatorio: false,
      discriminatorioNota: 'NO - se gana concretando trabajos',
      tareas: [
        {
          id: 'n2-concretados',
          label: 'Concretar al menos un trabajo',
          como: 'Se completa cuando el titular marca al menos un trabajo como concretado.'
        },
        {
          id: 'n2-puntualidad',
          label: 'Mantener buena reputación',
          como: 'Se completa cuando el puntaje de confiabilidad alcanza 85% o más.'
        },
        {
          id: 'n2-no-concretados',
          label: 'Mantener pocos no concretados',
          como: 'Se completa cuando la tasa de trabajos no concretados se mantiene bajo 15%.'
        }
      ]
    },
    {
      id: 3,
      titulo: 'Nivel 3 Identidad reforzada',
      evalua: 'Mayor certeza para tratos de alto valor',
      requisito: 'Antecedentes, verificación facial y un aval o garantía.',
      usos: 'Contratos sensibles, entregas de alto valor y menor riesgo para ambas partes.',
      discriminatorio: false,
      discriminatorioNota: 'NO - refuerza identidad, no mide plata',
      tareas: [
        {
          id: 'n3-antecedentes',
          label: 'Presentar certificado de antecedentes',
          como: 'Se completa al cargar el certificado de antecedentes o un certificado comercial equivalente.'
        },
        {
          id: 'n3-biometria',
          label: 'Confirmar identidad con foto',
          como: 'Se completa al aprobar la verificación facial; se guarda una copia comprimida con retención limitada.'
        },
        {
          id: 'n3-aval',
          label: 'Registrar un aval o garantía',
          como: 'Se completa al cargar un aval, garantía o documento de respaldo.'
        }
      ]
    }
  ],

  state: {
    docs: [],
    biometriaOk: false
  },
  empresas: null,
  reputacionMia: null,
  STORAGE_EMPRESA: 'servichile.empresa.seleccionada',

  async init() {
    SubirConfianza.cargar();
    const raiz = document.getElementById('subirConfianzaRaiz');
    if (!raiz) return;
    await SubirConfianza.cargarEmpresas();
    SubirConfianza.render(raiz);
  },

  storageQuien() {
    const user = typeof Auth !== 'undefined' ? Auth.getCurrentUser() : null;
    return user && user.email ? String(user.email).toLowerCase() : 'anon';
  },

  claveSeleccion() {
    return SubirConfianza.STORAGE_EMPRESA + ':' + SubirConfianza.storageQuien();
  },

  leerSeleccionId() {
    try {
      return localStorage.getItem(SubirConfianza.claveSeleccion()) || '';
    } catch (_) {
      return '';
    }
  },

  guardarSeleccionId(id) {
    try {
      if (id) localStorage.setItem(SubirConfianza.claveSeleccion(), String(id));
      else localStorage.removeItem(SubirConfianza.claveSeleccion());
    } catch (_) {

    }
  },

  elegirNegocio(lista) {
    if (!Array.isArray(lista) || !lista.length) return null;
    const want = SubirConfianza.leerSeleccionId();
    if (want) {
      const hit = lista.find((n) => String(n.id) === want);
      if (hit) return hit;
    }
    return lista[0];
  },

  async cargarEmpresas() {
    SubirConfianza.empresas = [];
    SubirConfianza.reputacionMia = null;
    if (typeof Auth === 'undefined' || !Auth.isAuthenticated() || !Auth.request) {
      return [];
    }
    try {
      const mias = await Auth.request('/v1/businesses/mias', {
        token: Auth.sesion.token
      });
      const lista = mias && Array.isArray(mias.data) ? mias.data : [];
      SubirConfianza.empresas = lista;
      if (!lista.length) return [];
      const actual = SubirConfianza.elegirNegocio(lista);
      if (actual && actual.id) SubirConfianza.guardarSeleccionId(actual.id);
      SubirConfianza.sincronizarDocsEmpresaDesdeApi(actual);
      const res = await Auth.request(
        '/v1/businesses/' + encodeURIComponent(actual.id) + '/reputation',
        { token: Auth.sesion.token }
      );
      if (res && res.ok && res.data) {
        SubirConfianza.reputacionMia = res.data;

        if (actual.indice_transparencia == null && res.data.indice_transparencia != null) {
          actual.indice_transparencia = res.data.indice_transparencia;
        }
        if (actual.indice_pct == null && res.data.indice_pct != null) {
          actual.indice_pct = res.data.indice_pct;
        }
      }
      return lista;
    } catch (_e) {
      SubirConfianza.empresas = [];
      return [];
    }
  },

  tieneEmpresa() {
    return Array.isArray(SubirConfianza.empresas) && SubirConfianza.empresas.length > 0;
  },

  empresaActual() {
    return SubirConfianza.elegirNegocio(SubirConfianza.empresas);
  },

  storageKey() {
    return SubirConfianza.STORAGE_KEY + ':' + SubirConfianza.storageQuien();
  },

  cargar() {
    try {
      const quien = SubirConfianza.storageQuien();
      const clave = SubirConfianza.STORAGE_KEY + ':' + quien;
      const legacy = SubirConfianza.STORAGE_KEY_LEGACY + ':' + quien;
      let raw = localStorage.getItem(clave);
      if (!raw) {
        raw = localStorage.getItem(legacy);
        if (raw) {
          localStorage.setItem(clave, raw);
          localStorage.removeItem(legacy);
        }
      }
      try {
        localStorage.removeItem(SubirConfianza.STORAGE_KEY_LEGACY);
      } catch {}
      if (!raw) {
        SubirConfianza.state = { docs: [], biometriaOk: false };
      } else {
        const parsed = JSON.parse(raw);
        SubirConfianza.state.docs = Array.isArray(parsed.docs) ? parsed.docs : [];
        SubirConfianza.state.biometriaOk = false;
      }
    } catch {
      SubirConfianza.state = { docs: [], biometriaOk: false };
    }
    SubirConfianza.sincronizarBiometria();
  },

  sincronizarBiometria() {
    const serverOk = !!SubirConfianza.perfil().biometria_verificada;
    SubirConfianza.state.biometriaOk = serverOk;
    SubirConfianza.guardar();
  },

  guardar() {
    try {
      localStorage.setItem(
        SubirConfianza.storageKey(),
        JSON.stringify({
          docs: SubirConfianza.state.docs

        })
      );
    } catch {}
  },

  perfil() {
    const user = typeof Auth !== 'undefined' ? Auth.getCurrentUser() : null;
    return (user && user.perfil) || {};
  },

  esProveedor() {
    return typeof ProgresoCuenta !== 'undefined'
      ? ProgresoCuenta.esProveedor()
      : SubirConfianza.perfil().tipo_cuenta === 'proveedor';
  },

  esEmpresa() {
    return SubirConfianza.esProveedor();
  },

  biometriaHecha() {
    return !!SubirConfianza.perfil().biometria_verificada;
  },

  tiposDocumento() {
    return typeof ProgresoCuenta !== 'undefined'
      ? ProgresoCuenta.actual().tiposDocumento()
      : [];
  },

  fichaEmpresa() {
    const empresa = SubirConfianza.empresaActual();
    const rep = SubirConfianza.reputacionMia;
    if (!empresa) {
      return {
        id: null,
        nombre: 'Sin empresa',
        indice_transparencia: null,
        indice_pct: null,
        _docsCargados: 0,
        _docsTotal: 0,
        _sinFicha: true
      };
    }
    const ids =
      typeof ProgresoCuenta !== 'undefined'
        ? ProgresoCuenta.de('proveedor').idsDocumento()
        : [];
    let docs = 0;
    for (let i = 0; i < ids.length; i++) {
      if (SubirConfianza.tieneDoc(ids[i])) docs += 1;
    }

    const repOk =
      !!rep &&
      (rep.business_id == null || String(rep.business_id) === String(empresa.id));
    if (repOk && rep.docs_verificados != null) docs = Number(rep.docs_verificados);
    const totalDocs =
      repOk && rep.docs_total != null ? Number(rep.docs_total) : ids.length || 11;

    const enMarket =
      typeof Market !== 'undefined' && Array.isArray(Market.negocios)
        ? Market.negocios.find((n) => n && String(n.id) === String(empresa.id))
        : null;
    const indice =
      enMarket && enMarket.indice_transparencia != null
        ? Number(enMarket.indice_transparencia)
        : empresa.indice_transparencia != null
          ? Number(empresa.indice_transparencia)
          : repOk && rep.indice_transparencia != null
            ? Number(rep.indice_transparencia)
            : null;
    const pct =
      enMarket && enMarket.indice_pct != null
        ? Number(enMarket.indice_pct)
        : empresa.indice_pct != null
          ? Number(empresa.indice_pct)
          : repOk && rep.indice_pct != null
            ? Number(rep.indice_pct)
            : indice != null
              ? Math.round((indice / 10) * 100)
              : null;
    return {
      id: empresa.id,
      nombre: empresa.nombre || 'Mi empresa',
      rut_empresa: (empresa.rut_empresa || '').trim() || null,
      telefono: (empresa.telefono || '').trim() || null,
      sitio_web: (empresa.sitio_web || '').trim() || null,
      direccion: (empresa.direccion || '').trim() || null,
      indice_transparencia: indice,
      indice_pct: pct,
      _docsCargados: docs,
      _docsTotal: totalDocs,
      _sinFicha: false
    };
  },

  bloqueSinEmpresa() {
    if (typeof ReporteEmpresa !== 'undefined' && ReporteEmpresa.renderAvisoSinFicha) {
      return ReporteEmpresa.renderAvisoSinFicha();
    }
    const box = document.createElement('section');
    box.className = 'reporte-sin-ficha';
    const titulo = document.createElement('h2');
    titulo.className = 'section-heading';
    titulo.textContent = 'Aún no tiene una ficha de empresa';
    const lead = document.createElement('p');
    lead.className = 'section-lead';
    lead.textContent =
      'Cree su empresa en Perfil para ver el índice de transparencia y cargar documentos legales.';
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'submit-btn';
    btn.textContent = 'Ir a Perfil a crear la empresa';
    btn.addEventListener('click', () => {
      if (typeof App !== 'undefined' && App.openSection) App.openSection('perfil');
    });
    box.append(titulo, lead, btn);
    return box;
  },

  docVigente(meta) {
    if (!meta || !meta.verificado) return false;
    if (!meta.vence_en) return true;
    const hasta = Date.parse(meta.vence_en);
    if (!Number.isFinite(hasta)) return true;
    return hasta >= Date.now();
  },

  tieneDoc(tipo) {
    const local = SubirConfianza.state.docs.find(
      (d) => d.tipo === tipo && d.verificado !== false && d.caducado !== true
    );
    if (local) {
      if (local.vence_en && Date.parse(local.vence_en) < Date.now()) return false;
      return true;
    }
    const empresa = SubirConfianza.empresaActual();
    const docs = empresa && empresa.docs_empresa;
    return !!(docs && docs[tipo] && SubirConfianza.docVigente(docs[tipo]));
  },

  tiposDocEmpresa() {
    return [
      'carpeta_tributaria',
      'inicio_actividades',
      'vigencia_sociedad',
      'vigencia_poderes',
      'poder_representante',
      'constitucion',
      'f30',
      'no_quiebra',
      'antecedentes_rl',
      'patente',
      'titularidad_cuenta'
    ];
  },

  tiposDocEmpresaPades() {
    return [
      'carpeta_tributaria',
      'inicio_actividades',
      'vigencia_sociedad',
      'vigencia_poderes',
      'poder_representante',
      'constitucion',
      'f30',
      'no_quiebra',
      'antecedentes_rl'
    ];
  },

  sincronizarDocsEmpresaDesdeApi(empresa) {
    if (!empresa || !empresa.docs_empresa || typeof empresa.docs_empresa !== 'object') {
      return;
    }
    const tipos = SubirConfianza.tiposDocEmpresa();
    tipos.forEach((tipo) => {
      const meta = empresa.docs_empresa[tipo];
      if (!meta || !meta.verificado) {
        SubirConfianza.state.docs = SubirConfianza.state.docs.filter((d) => d.tipo !== tipo);
        return;
      }
      const caducado = !SubirConfianza.docVigente(meta);
      SubirConfianza.state.docs = SubirConfianza.state.docs.filter((d) => d.tipo !== tipo);
      SubirConfianza.state.docs.unshift({
        id: 'api-' + tipo,
        tipo,
        nombre: tipo + '.pdf',
        fecha: meta.verificado_en || new Date().toISOString(),
        vence_en: meta.vence_en || null,
        score: meta.score,
        verificado: true,
        caducado
      });
    });
    SubirConfianza.guardar();
  },

  scoreConfiabilidad() {
    const score = SubirConfianza.perfil().score_confiabilidad;
    if (score == null || score === '') return null;
    const n = Number(score);
    return Number.isFinite(n) ? n : null;
  },

  tasaNoConcretados() {
    const score = SubirConfianza.scoreConfiabilidad();
    if (score == null) return null;
    return Math.round((100 - score) * 10) / 10;
  },

  edadNumerica() {
    const n = Number(SubirConfianza.perfil().edad);
    return Number.isFinite(n) ? n : null;
  },

  telefonoOk() {
    const tel = SubirConfianza.perfil().telefono;
    return !!(tel && String(tel).trim());
  },

  estaHecha(tareaId) {
    return SubirConfianza.estadoPunto(tareaId) === 'ok';
  },

  estadoPunto(tareaId) {
    const perfil = SubirConfianza.perfil();
    const score = SubirConfianza.scoreConfiabilidad();
    const tasa = SubirConfianza.tasaNoConcretados();

    switch (tareaId) {
      case 'n1-registro':
        return typeof Auth !== 'undefined' && Auth.isAuthenticated() ? 'ok' : 'pendiente';
      case 'n1-cedula':
        if (perfil.rut_verificado || perfil.cedula_verificada) return 'ok';
        return 'pendiente';
      case 'n1-perfil': {
        const edad = SubirConfianza.edadNumerica();
        const edadOk = edad != null && edad >= 18;
        const telOk = SubirConfianza.telefonoOk();
        if (edadOk && telOk) return 'ok';
        if (edad != null || telOk) return 'progreso';
        return 'pendiente';
      }
      case 'n2-concretados':

        return score != null ? 'ok' : 'pendiente';
      case 'n2-puntualidad':
        if (score != null && score >= 85) return 'ok';
        if (score != null) return 'progreso';
        return 'pendiente';
      case 'n2-no-concretados':
        if (tasa != null && tasa < 15) return 'ok';
        if (tasa != null) return 'progreso';
        return 'pendiente';
      case 'n3-antecedentes':

        return SubirConfianza.perfil().antecedentes_verificados ? 'ok' : 'pendiente';
      case 'n3-biometria':
        return SubirConfianza.biometriaHecha() ? 'ok' : 'pendiente';
      case 'n3-aval':
        if (SubirConfianza.perfil().aval_verificado) return 'ok';
        return SubirConfianza.tieneDoc('aval') ? 'ok' : 'pendiente';
      default:
        return 'pendiente';
    }
  },

  etiquetaPunto(estado) {
    if (estado === 'ok') return 'Cumplido';
    if (estado === 'progreso') return 'En progreso';
    return 'Pendiente';
  },

  detallePunto(tareaId) {
    const perfil = SubirConfianza.perfil();
    const score = SubirConfianza.scoreConfiabilidad();
    const tasa = SubirConfianza.tasaNoConcretados();
    const estado = SubirConfianza.estadoPunto(tareaId);

    switch (tareaId) {
      case 'n1-registro':
        return estado === 'ok'
          ? 'Cuenta activa e inició sesión correctamente.'
          : 'Debe crear una cuenta e iniciar sesión.';
      case 'n1-cedula':
        if (perfil.cedula_verificada) return 'Carnet validado (foto frontal).';
        if (perfil.rut_verificado) return 'Identidad verificada con RUT.';
        return 'Falta verificar el RUT o validar la foto frontal del carnet.';
      case 'n1-perfil': {
        const edad = SubirConfianza.edadNumerica();
        const telOk = SubirConfianza.telefonoOk();
        const edadOk = edad != null && edad >= 18;
        if (edadOk && telOk) return 'Teléfono y mayoría de edad completados.';
        if (edad != null && edad < 18) return 'Debe declarar 18 años o más.';
        if (edadOk) return 'Edad completa. Falta el teléfono móvil.';
        if (telOk) return 'Teléfono completo. Falta declarar la edad.';
        return 'Complete el teléfono móvil y la edad (18 o más).';
      }
      case 'n2-concretados':
        return estado === 'ok'
          ? 'Ya registra al menos un trabajo concretado.'
          : 'Aún no hay trabajos concretados con un proveedor.';
      case 'n2-puntualidad':
        if (score == null) return 'Sin puntaje aún: se calcula con su historial.';
        if (score >= 85) return 'Puntaje de confiabilidad ' + score + '% (meta 85% alcanzada).';
        return 'Puntaje actual ' + score + '%. Debe llegar a 85% o más.';
      case 'n2-no-concretados':
        if (tasa == null) return 'Sin historial aún para medir no concretados.';
        if (tasa < 15) return 'Tasa de no concretados ' + tasa + '% (bajo el 15% exigido).';
        return 'Tasa de no concretados ' + tasa + '%. Debe bajar del 15%.';
      case 'n3-antecedentes': {
        if (perfil.antecedentes_verificados) {
          const anot =
            perfil.antecedentes_anotaciones === true
              ? 'Anotaciones: Sí'
              : perfil.antecedentes_anotaciones === false
                ? 'Anotaciones: No'
                : 'Anotaciones: -';
          return 'Certificado verificado. ' + anot + ' (no afecta el puntaje).';
        }
        return estado === 'ok'
          ? 'Certificado de antecedentes cargado.'
          : 'Debe cargar el certificado de antecedentes.';
      }
      case 'n3-biometria':
        return estado === 'ok'
          ? 'Verificación facial completada.'
          : 'Complete la verificación facial más abajo.';
      case 'n3-aval': {
        if (perfil.aval_verificado) {
          const partes = ['Aval/garantía verificado'];
          if (perfil.aval_tipo) partes.push(perfil.aval_tipo);
          if (perfil.aval_score != null) partes.push('score ' + perfil.aval_score);
          return partes.join(' ') + '.';
        }
        return estado === 'ok'
          ? 'Aval o garantía registrado.'
          : 'Debe cargar un aval, boleta o póliza.';
      }
      default:
        return SubirConfianza.etiquetaPunto(estado);
    }
  },

  totalTareas() {
    return SubirConfianza.NIVELES.reduce((n, nivel) => n + nivel.tareas.length, 0);
  },

  tareasHechas() {
    return SubirConfianza.NIVELES.reduce(
      (n, nivel) => n + nivel.tareas.filter(t => SubirConfianza.estaHecha(t.id)).length,
      0
    );
  },

  progresoPct() {
    const total = SubirConfianza.totalTareas();
    if (!total) return 0;
    return Math.round((SubirConfianza.tareasHechas() / total) * 100);
  },

  nivelSugerido() {
    let nivel = 0;
    for (const n of SubirConfianza.NIVELES) {
      if (n.tareas.every(t => SubirConfianza.estaHecha(t.id))) nivel = n.id;
      else break;
    }
    return Math.max(1, nivel || (SubirConfianza.estaHecha('n1-registro') ? 1 : 0));
  },

  xpActual() {
    const perfil = SubirConfianza.perfil();
    const n = Number(perfil && perfil.xp);
    return Number.isFinite(n) && n >= 0 ? Math.floor(n) : 0;
  },

  nivelXp() {
    const perfil = SubirConfianza.perfil();
    const n = Number(perfil && perfil.nivel_xp);
    if (Number.isFinite(n) && n >= 1) return Math.min(3, Math.floor(n));
    return SubirConfianza.nivelSugerido();
  },

  resumenProgreso() {
    const snap = ProgresoCuenta.actual().snapshot();
    const x = snap.extras || {};
    return {
      tipo: snap.tipo,
      hechas: x.hechas != null ? x.hechas : 0,
      total: x.total != null ? x.total : 0,
      pct: snap.pct,
      nivel: x.nivel != null ? x.nivel : 1,
      xp: x.xp != null ? x.xp : 0,
      meta: snap.meta,
      valor: snap.valor,
      titulo: snap.titulo
    };
  },

  montarIndicador(contenedor, opts) {
    return ProgresoCuenta.actual().montarIndicador(contenedor, opts || {});
  },

  render(raiz) {
    SubirConfianza.limpiar(raiz);
    const selector = SubirConfianza.renderSelectorEmpresas();
    if (selector) raiz.appendChild(selector);
    ProgresoCuenta.actual().montarContenido(raiz);
  },

  renderSelectorEmpresas() {
    const lista = Array.isArray(SubirConfianza.empresas)
      ? SubirConfianza.empresas
      : [];
    if (lista.length < 2) return null;
    const actual = SubirConfianza.empresaActual();

    const box = document.createElement('div');
    box.className = 'reporte__selector';
    box.setAttribute('aria-label', 'Seleccionar empresa');

    const label = document.createElement('label');
    label.className = 'reporte__selector-label';
    label.htmlFor = 'confianzaEmpresaSelect';
    label.textContent = 'Empresa';

    const select = document.createElement('select');
    select.id = 'confianzaEmpresaSelect';
    select.className = 'ui-select';
    select.setAttribute('aria-label', 'Elija a qué empresa aplican estos documentos');

    lista.forEach((n) => {
      const opt = document.createElement('option');
      opt.value = String(n.id);
      opt.textContent = n.nombre || 'Empresa';
      if (actual && String(actual.id) === String(n.id)) opt.selected = true;
      select.appendChild(opt);
    });

    select.addEventListener('change', async () => {
      const id = select.value;
      SubirConfianza.guardarSeleccionId(id);
      if (typeof ReporteEmpresa !== 'undefined' && ReporteEmpresa.guardarSeleccionId) {
        ReporteEmpresa.guardarSeleccionId(id);
      }
      select.disabled = true;
      await SubirConfianza.cargarEmpresas();
      const raiz = document.getElementById('subirConfianzaRaiz');
      if (raiz) SubirConfianza.render(raiz);
    });

    box.append(label, select);
    return box;
  },

  bloqueDesgloseEmpresa() {
    if (!SubirConfianza.tieneEmpresa()) return null;
    const ficha = SubirConfianza.fichaEmpresa();
    const rep = SubirConfianza.reputacionMia;
    if (ficha.indice_transparencia == null) return null;
    if (typeof Market === 'undefined' || !Market.bloqueDesgloseIndice) {
      const fallback = document.createElement('p');
      fallback.className = 'section-lead';
      fallback.textContent = 'El desglose del índice no está disponible.';
      return fallback;
    }
    return Market.bloqueDesgloseIndice(
      ficha,
      rep,
      ficha.indice_transparencia,
      false
    );
  },

  bloqueIndicador(opts) {
    return ProgresoCuenta.actual().crearIndicador(opts || {});
  },

  bloqueChecklist() {
    const wrap = document.createElement('section');
    wrap.className = 'confianza-todo';
    wrap.setAttribute('aria-label', 'Lista para subir de nivel');

    const titulo = document.createElement('h3');
    titulo.className = 'section-heading';
    titulo.textContent = 'Qué desbloquea cada verificación';

    const lead = document.createElement('p');
    lead.className = 'section-lead';
    lead.textContent =
      'Cumpla solo lo necesario según el tipo de trato. Cada nivel refuerza identidad y cumplimiento.';

    const normales = SubirConfianza.NIVELES.filter(n => !n.especial);
    const especiales = SubirConfianza.NIVELES.filter(n => n.especial);

    wrap.append(
      titulo,
      lead,
      SubirConfianza.carruselNiveles(normales),
      ...especiales.map(n => SubirConfianza.renderGrupo(n))
    );
    return wrap;
  },

  carruselNiveles(niveles) {
    const max = Math.max(0, niveles.length - 1);
    if (SubirConfianza.carruselIdx > max) SubirConfianza.carruselIdx = max;
    if (SubirConfianza.carruselIdx < 0) SubirConfianza.carruselIdx = 0;

    const root = document.createElement('div');
    root.className = 'confianza-carrusel';
    root.setAttribute('aria-roledescription', 'carrusel');
    root.setAttribute('aria-label', 'Niveles 1 a 3');

    const cabecera = document.createElement('header');
    cabecera.className = 'confianza-carrusel__cabecera';

    const nav = document.createElement('div');
    nav.className = 'confianza-carrusel__nav';

    const prev = document.createElement('button');
    prev.type = 'button';
    prev.className = 'confianza-carrusel__btn';
    prev.setAttribute('aria-label', 'Nivel anterior');
    const prevIcon = document.createElement('span');
    prevIcon.setAttribute('aria-hidden', 'true');
    prevIcon.textContent = '‹';
    prev.appendChild(prevIcon);

    const tituloWrap = document.createElement('div');
    tituloWrap.className = 'confianza-carrusel__titulo-wrap';

    const badge = document.createElement('span');
    badge.className = 'confianza-carrusel__badge';
    badge.setAttribute('aria-hidden', 'true');

    const meta = document.createElement('h4');
    meta.className = 'confianza-carrusel__titulo';
    meta.setAttribute('aria-live', 'polite');

    const resumen = document.createElement('span');
    resumen.className = 'confianza-carrusel__resumen';

    tituloWrap.append(badge, meta, resumen);

    const next = document.createElement('button');
    next.type = 'button';
    next.className = 'confianza-carrusel__btn';
    next.setAttribute('aria-label', 'Nivel siguiente');
    const nextIcon = document.createElement('span');
    nextIcon.setAttribute('aria-hidden', 'true');
    nextIcon.textContent = '›';
    next.appendChild(nextIcon);

    nav.append(prev, tituloWrap, next);

    const regla = document.createElement('hr');
    regla.className = 'confianza-carrusel__hr';

    cabecera.append(nav, regla);

    const viewport = document.createElement('div');
    viewport.className = 'confianza-carrusel__viewport';

    const track = document.createElement('div');
    track.className = 'confianza-carrusel__track';

    const slides = niveles.map((nivel, i) => {
      const slide = document.createElement('div');
      slide.className = 'confianza-carrusel__slide';
      slide.setAttribute('aria-hidden', i === SubirConfianza.carruselIdx ? 'false' : 'true');
      slide.appendChild(SubirConfianza.renderGrupo(nivel, { sinCabecera: true }));
      track.appendChild(slide);
      return slide;
    });

    viewport.appendChild(track);

    const dots = document.createElement('div');
    dots.className = 'confianza-carrusel__dots';
    dots.setAttribute('role', 'tablist');
    dots.setAttribute('aria-label', 'Elegir nivel');

    const dotBtns = niveles.map((nivel, i) => {
      const dot = document.createElement('button');
      dot.type = 'button';
      dot.className = 'confianza-carrusel__dot';
      dot.setAttribute('role', 'tab');
      dot.setAttribute('aria-label', nivel.titulo);
      dot.addEventListener('click', () => irA(i));
      dots.appendChild(dot);
      return dot;
    });

    function pintar() {
      const idx = SubirConfianza.carruselIdx;
      track.style.transform = 'translateX(-' + idx * 100 + '%)';
      slides.forEach((slide, i) => {
        slide.setAttribute('aria-hidden', i === idx ? 'false' : 'true');
      });
      dotBtns.forEach((dot, i) => {
        const activo = i === idx;
        dot.classList.toggle('confianza-carrusel__dot--activo', activo);
        dot.setAttribute('aria-selected', activo ? 'true' : 'false');
      });
      prev.disabled = idx <= 0;
      next.disabled = idx >= max;
      const n = niveles[idx];
      if (n) {
        badge.textContent = String(n.id);
        meta.textContent = n.titulo + ' ' + n.evalua;
        const done = n.tareas.filter(t => SubirConfianza.estaHecha(t.id)).length;
        resumen.textContent = done + '/' + n.tareas.length + ' Tareas Completadas';
      } else {
        badge.textContent = '';
        meta.textContent = '';
        resumen.textContent = '';
      }
    }

    function irA(i) {
      SubirConfianza.carruselIdx = Math.max(0, Math.min(max, i));
      pintar();
    }

    prev.addEventListener('click', () => irA(SubirConfianza.carruselIdx - 1));
    next.addEventListener('click', () => irA(SubirConfianza.carruselIdx + 1));

    root.append(cabecera, viewport, dots);
    pintar();
    return root;
  },

  renderGrupo(nivel, opts) {
    const sinCabecera = !!(opts && opts.sinCabecera);
    const grupo = document.createElement('div');
    grupo.className =
      'confianza-todo__grupo' +
      (nivel.especial ? ' confianza-todo__grupo--especial' : '') +
      (sinCabecera ? ' confianza-todo__grupo--en-carrusel' : '');

    if (!sinCabecera) {
      const head = document.createElement('header');
      head.className = 'confianza-todo__grupo-head';

      const badge = document.createElement('span');
      badge.className = 'confianza-todo__badge';
      badge.textContent = String(nivel.id);

      const nombre = document.createElement('h4');
      nombre.className = 'confianza-todo__grupo-titulo';
      nombre.textContent = nivel.titulo + ' ' + nivel.evalua;

      const doneCount = nivel.tareas.filter(t => SubirConfianza.estaHecha(t.id)).length;
      const resumen = document.createElement('span');
      resumen.className = 'confianza-todo__resumen';
      resumen.textContent = doneCount + '/' + nivel.tareas.length + ' Tareas Completadas';

      head.append(badge, nombre, resumen);
      grupo.appendChild(head);
    }

    const ul = document.createElement('ul');
    ul.className = 'confianza-todo__items';

    nivel.tareas.forEach(tarea => {
      const punto = SubirConfianza.estadoPunto(tarea.id);
      const detalle = SubirConfianza.detallePunto(tarea.id);
      const li = document.createElement('li');
      li.className = 'confianza-todo__item confianza-todo__item--' + punto;

      const estadoWrap = document.createElement('div');
      estadoWrap.className = 'confianza-todo__estado';

      const estado = document.createElement('span');
      estado.className = 'confianza-todo__punto confianza-todo__punto--' + punto;
      estado.setAttribute('aria-hidden', 'true');

      const estadoTxt = document.createElement('span');
      estadoTxt.className = 'confianza-todo__estado-txt confianza-todo__estado-txt--' + punto;
      estadoTxt.textContent = SubirConfianza.etiquetaPunto(punto);

      estadoWrap.append(estado, estadoTxt);

      const cuerpo = document.createElement('div');
      cuerpo.className = 'confianza-todo__cuerpo';

      const label = document.createElement('p');
      label.className = 'confianza-todo__label';
      label.textContent = tarea.label;

      const detalleEl = document.createElement('p');
      detalleEl.className = 'confianza-todo__detalle';
      detalleEl.textContent = detalle;

      const como = document.createElement('p');
      como.className = 'confianza-todo__como';
      como.textContent = tarea.como;

      cuerpo.append(label, detalleEl, como);
      li.append(estadoWrap, cuerpo);
      li.setAttribute(
        'aria-label',
        SubirConfianza.etiquetaPunto(punto) + ': ' + tarea.label + '. ' + detalle
      );
      ul.appendChild(li);
    });

    grupo.appendChild(ul);
    return grupo;
  },

  bloqueDocumentos() {
    const wrap = document.createElement('section');
    wrap.className = 'confianza-docs config-card';
    wrap.setAttribute('aria-label', 'Subir documentos');

    const head = document.createElement('div');
    head.className = 'confianza-docs__head';

    const prog = typeof ProgresoCuenta !== 'undefined' ? ProgresoCuenta.actual() : null;
    const titulo = document.createElement('h3');
    titulo.className = 'section-heading';
    titulo.textContent = prog ? prog.tituloDocumentos() : 'Subir documentos';

    const notaTxt = prog ? prog.notaDocumentos() : '';
    head.appendChild(titulo);
    if (notaTxt) {
      const nota = document.createElement('p');
      nota.className = 'confianza-docs__nota';
      nota.textContent = notaTxt;
      head.appendChild(nota);
    }

    const form = document.createElement('form');
    form.className = 'confianza-docs__form';
    form.noValidate = true;

    const fieldTipo = document.createElement('div');
    fieldTipo.className = 'field';
    const labelTipo = document.createElement('label');
    labelTipo.className = 'field__label';
    labelTipo.htmlFor = 'confianzaDocTipo';
    labelTipo.textContent = 'Tipo de documento';
    const select = document.createElement('select');
    select.id = 'confianzaDocTipo';
    select.className = 'ui-select';
    SubirConfianza.tiposDocumento().forEach(([value, text]) => {
      const opt = document.createElement('option');
      opt.value = value;
      opt.textContent = text;
      select.appendChild(opt);
    });
    fieldTipo.append(labelTipo, select);

    const drop = document.createElement('div');
    drop.className = 'confianza-docs__drop';

    const input = document.createElement('input');
    input.id = 'confianzaDocArchivo';
    input.className = 'confianza-docs__file';
    input.type = 'file';
    input.accept = '.pdf,image/jpeg,image/png,application/pdf';

    const dropLabel = document.createElement('label');
    dropLabel.className = 'confianza-docs__drop-label';
    dropLabel.htmlFor = 'confianzaDocArchivo';

    const dropTitulo = document.createElement('span');
    dropTitulo.className = 'confianza-docs__drop-titulo';
    dropTitulo.textContent = 'Elegir archivo';

    const dropNombre = document.createElement('span');
    dropNombre.className = 'confianza-docs__drop-nombre';
    dropNombre.textContent = 'Ningún archivo seleccionado';

    dropLabel.append(dropTitulo, dropNombre);
    drop.append(input, dropLabel);

    const actualizarArchivo = () => {
      const archivo = input.files && input.files[0];
      drop.classList.toggle('confianza-docs__drop--lleno', !!archivo);
      dropNombre.textContent = archivo
        ? archivo.name + ' ' + SubirConfianza.formatoTamano(archivo.size)
        : select.value === 'cedula'
          ? 'Ninguna foto seleccionada'
          : 'Ningún archivo seleccionado';
    };

    const sincronizarTipoArchivo = () => {
      const esCarnet = select.value === 'cedula';
      const esAval = select.value === 'aval';
      const esDocEmpresa = SubirConfianza.tiposDocEmpresa().includes(select.value);
      const soloPdf =
        esAval || esDocEmpresa || select.value === 'antecedentes';
      drop.hidden = false;
      input.accept = esCarnet
        ? 'image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp'
        : soloPdf
          ? 'application/pdf,.pdf'
          : '.pdf,image/jpeg,image/png,application/pdf';
      dropTitulo.textContent = esCarnet
        ? 'Foto frontal del carnet'
        : esAval
          ? 'PDF de aval o garantía'
          : esDocEmpresa
            ? 'PDF del documento legal'
            : 'Elegir archivo';
      if (esCarnet && input.files && input.files[0]) {
        const tipo = (input.files[0].type || '').toLowerCase();
        if (tipo && !tipo.startsWith('image/')) {
          input.value = '';
        }
      }
      if (soloPdf && input.files && input.files[0]) {
        const f = input.files[0];
        const ok =
          String(f.type || '') === 'application/pdf' || /\.pdf$/i.test(f.name || '');
        if (!ok) input.value = '';
      }
      actualizarArchivo();
    };

    input.addEventListener('change', actualizarArchivo);
    select.addEventListener('change', sincronizarTipoArchivo);
    sincronizarTipoArchivo();

    ['dragenter', 'dragover'].forEach(ev => {
      drop.addEventListener(ev, e => {
        e.preventDefault();
        drop.classList.add('confianza-docs__drop--activo');
      });
    });
    ['dragleave', 'drop'].forEach(ev => {
      drop.addEventListener(ev, e => {
        e.preventDefault();
        drop.classList.remove('confianza-docs__drop--activo');
      });
    });
    drop.addEventListener('drop', e => {
      const files = e.dataTransfer && e.dataTransfer.files;
      if (!files || !files.length) return;
      try {
        const dt = new DataTransfer();
        dt.items.add(files[0]);
        input.files = dt.files;
      } catch {
        return;
      }
      actualizarArchivo();
    });

    const acciones = document.createElement('div');
    acciones.className = 'confianza-docs__acciones';

    const btn = document.createElement('button');
    btn.className = 'submit-btn confianza-docs__submit';
    btn.type = 'submit';
    btn.textContent = 'Registrar documento';

    const status = document.createElement('p');
    status.className = 'status-text confianza-docs__status';
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');

    acciones.append(btn, status);
    form.append(fieldTipo, drop, acciones);

    form.addEventListener('submit', async e => {
      e.preventDefault();
      const tipo = select.value;
      const archivo = input.files && input.files[0];
      if (!archivo) {
        status.textContent =
          select.value === 'cedula'
            ? 'Seleccione la foto frontal del carnet.'
            : 'Seleccione un archivo.';
        return;
      }
      if (tipo === 'cedula') {
        const mime = (archivo.type || '').toLowerCase();
        const esImagen =
          mime.startsWith('image/') ||
          /\.(jpe?g|png|webp)$/i.test(archivo.name || '');
        if (!esImagen) {
          status.textContent =
            'Del carnet solo se acepta la foto frontal (JPG o PNG). No se pide el reverso.';
          return;
        }
      }
      if (tipo === 'antecedentes') {
        if (SubirConfianza.perfil().antecedentes_verificados) {
          status.textContent = 'El certificado de antecedentes ya está verificado.';
          return;
        }
        btn.disabled = true;
        status.textContent = 'Validando certificado…';
        const res =
          typeof Auth !== 'undefined' && Auth.verificarAntecedentes
            ? await Auth.verificarAntecedentes(archivo)
            : { ok: false, error: 'Sesión no disponible.' };
        btn.disabled = false;
        if (!res.ok) {
          status.textContent = res.error || 'No se pudo validar el certificado.';
          return;
        }
        const data = res.antecedentes || {};
        SubirConfianza.state.docs = SubirConfianza.state.docs.filter(
          (d) => d.tipo !== 'antecedentes'
        );
        SubirConfianza.state.docs.unshift({
          id: String(Date.now()),
          tipo: 'antecedentes',
          nombre: archivo.name,
          tamano: archivo.size,
          fecha: new Date().toISOString(),
          anotaciones: data.antecedentes_anotaciones,
          score: data.antecedentes_score,
          verificado: true
        });
        SubirConfianza.guardar();
        SubirConfianza.init();
        return;
      }
      if (tipo === 'aval') {
        const mime = (archivo.type || '').toLowerCase();
        const esPdf = mime === 'application/pdf' || /\.pdf$/i.test(archivo.name || '');
        if (!esPdf) {
          status.textContent = 'Del aval/garantía solo se acepta PDF.';
          return;
        }
        if (SubirConfianza.perfil().aval_verificado) {
          status.textContent = 'El aval o garantía ya está verificado.';
          return;
        }
        btn.disabled = true;
        status.textContent = 'Validando aval/garantía…';
        const res =
          typeof Auth !== 'undefined' && Auth.verificarAval
            ? await Auth.verificarAval(archivo)
            : { ok: false, error: 'Sesión no disponible.' };
        btn.disabled = false;
        if (!res.ok) {
          status.textContent = res.error || 'No se pudo validar el aval/garantía.';
          return;
        }
        const data = res.aval || {};
        SubirConfianza.state.docs = SubirConfianza.state.docs.filter((d) => d.tipo !== 'aval');
        SubirConfianza.state.docs.unshift({
          id: String(Date.now()),
          tipo: 'aval',
          nombre: archivo.name,
          tamano: archivo.size,
          fecha: new Date().toISOString(),
          score: data.aval_score,
          avalTipo: data.aval_tipo,
          verificado: true
        });
        SubirConfianza.guardar();
        SubirConfianza.init();
        return;
      }
      if (SubirConfianza.tiposDocEmpresa().includes(tipo)) {
        const mime = (archivo.type || '').toLowerCase();
        const esPdf = mime === 'application/pdf' || /\.pdf$/i.test(archivo.name || '');
        if (!esPdf) {
          status.textContent = 'Solo se acepta PDF.';
          return;
        }
        const empresa = SubirConfianza.empresaActual();
        if (!empresa || !empresa.id) {
          status.textContent = 'Cree primero su empresa en Perfil.';
          return;
        }
        if (SubirConfianza.tieneDoc(tipo)) {
          status.textContent = 'Ese documento legal ya está verificado.';
          return;
        }
        btn.disabled = true;
        status.textContent = 'Validando documento legal…';
        const res =
          typeof Auth !== 'undefined' && Auth.verificarDocEmpresa
            ? await Auth.verificarDocEmpresa(empresa.id, tipo, archivo)
            : { ok: false, error: 'Sesión no disponible.' };
        btn.disabled = false;
        if (!res.ok) {
          status.textContent = res.error || 'No se pudo validar el documento.';
          return;
        }
        const data = res.documento || {};
        if (data.docs_empresa) {
          empresa.docs_empresa = data.docs_empresa;
        }
        if (data.indice_transparencia != null) {
          empresa.indice_transparencia = data.indice_transparencia;
        }
        if (data.indice_pct != null) {
          empresa.indice_pct = data.indice_pct;
        }
        SubirConfianza.reputacionMia = Object.assign({}, SubirConfianza.reputacionMia || {}, {
          indice_transparencia: data.indice_transparencia,
          indice_pct: data.indice_pct,
          docs_verificados: data.docs_verificados,
          docs_total: data.docs_total
        });
        const metaTipo =
          (data.docs_empresa && data.docs_empresa[tipo]) || {};
        SubirConfianza.state.docs = SubirConfianza.state.docs.filter((d) => d.tipo !== tipo);
        SubirConfianza.state.docs.unshift({
          id: String(Date.now()),
          tipo,
          nombre: archivo.name,
          tamano: archivo.size,
          fecha: metaTipo.verificado_en || new Date().toISOString(),
          vence_en: metaTipo.vence_en || null,
          score: data.score,
          verificado: true,
          caducado: false
        });
        SubirConfianza.guardar();
        SubirConfianza.init();
        return;
      }
      if (SubirConfianza.tieneDoc(tipo)) {
        status.textContent = 'Ese tipo de documento ya está registrado.';
        return;
      }
      SubirConfianza.state.docs.unshift({
        id: String(Date.now()),
        tipo,
        nombre: archivo.name,
        tamano: archivo.size,
        fecha: new Date().toISOString()
      });
      SubirConfianza.guardar();
      SubirConfianza.init();
    });

    const listaWrap = document.createElement('div');
    listaWrap.className = 'confianza-docs__registrados';

    const listaTitulo = document.createElement('h4');
    listaTitulo.className = 'confianza-docs__lista-titulo';
    listaTitulo.textContent = 'Documentos registrados';

    const lista = document.createElement('ul');
    lista.className = 'confianza-docs__lista';
    if (!SubirConfianza.state.docs.length) {
      const vacio = document.createElement('li');
      vacio.className = 'confianza-docs__vacio';
      vacio.textContent = 'Aún no hay documentos. Sube uno para desbloquear su requisito.';
      lista.appendChild(vacio);
    } else {
      SubirConfianza.state.docs.forEach(doc => {
        const li = document.createElement('li');
        li.className = 'confianza-docs__item';
        if (doc.caducado) li.classList.add('confianza-docs__item--caducado');

        const icono = document.createElement('span');
        icono.className = 'confianza-docs__item-icono';
        icono.setAttribute('aria-hidden', 'true');
        icono.textContent = 'PDF';

        const cuerpo = document.createElement('div');
        cuerpo.className = 'confianza-docs__item-cuerpo';

        const nombre = document.createElement('strong');
        nombre.textContent = doc.nombre;

        const meta = document.createElement('span');
        let metaTxt =
          SubirConfianza.etiquetaTipo(doc.tipo) +
          ' ' +
          SubirConfianza.formatoFecha(doc.fecha) +
          (doc.tamano != null ? ' ' + SubirConfianza.formatoTamano(doc.tamano) : '');
        if (doc.tipo === 'antecedentes' && doc.verificado) {
          metaTxt +=
            ' Anotaciones: ' +
            (doc.anotaciones === true ? 'Sí' : doc.anotaciones === false ? 'No' : '-');
          if (doc.score != null) metaTxt += ' Score ' + doc.score;
        }
        if (doc.tipo === 'aval' && doc.verificado) {
          if (doc.avalTipo) metaTxt += ' ' + doc.avalTipo;
          if (doc.score != null) metaTxt += ' Score ' + doc.score;
        }
        if (doc.vence_en) {
          metaTxt +=
            ' ' +
            (doc.caducado ? 'Caducó' : 'Vence') +
            ' ' +
            SubirConfianza.formatoFecha(doc.vence_en);
        }
        if (doc.caducado) {
          metaTxt += ' Revalide subiendo un PDF nuevo';
        }
        meta.textContent = metaTxt;

        cuerpo.append(nombre, meta);
        li.append(icono, cuerpo);

        if (
          SubirConfianza.tiposDocEmpresa().includes(doc.tipo) &&
          doc.verificado &&
          !doc.caducado
        ) {
          const btnRev = document.createElement('button');
          btnRev.type = 'button';
          btnRev.className = 'history__clear confianza-docs__revocar';
          btnRev.textContent = 'Revocar';
          btnRev.addEventListener('click', async () => {
            const empresa = SubirConfianza.empresaActual();
            if (!empresa || !empresa.id) {
              status.textContent = 'No hay empresa asociada.';
              return;
            }
            if (
              !window.confirm(
                '¿Revocar «' +
                  SubirConfianza.etiquetaTipo(doc.tipo) +
                  '»? Dejará de contar en el índice hasta que revalide.'
              )
            ) {
              return;
            }
            btnRev.disabled = true;
            status.textContent = 'Revocando documento…';
            const res =
              typeof Auth !== 'undefined' && Auth.revocarDocEmpresa
                ? await Auth.revocarDocEmpresa(empresa.id, doc.tipo)
                : { ok: false, error: 'Sesión no disponible.' };
            btnRev.disabled = false;
            if (!res.ok) {
              status.textContent = res.error || 'No se pudo revocar.';
              return;
            }
            const data = res.documento || {};
            if (data.docs_empresa) empresa.docs_empresa = data.docs_empresa;
            if (data.indice_transparencia != null) {
              empresa.indice_transparencia = data.indice_transparencia;
            }
            if (data.indice_pct != null) empresa.indice_pct = data.indice_pct;
            SubirConfianza.reputacionMia = Object.assign(
              {},
              SubirConfianza.reputacionMia || {},
              {
                indice_transparencia: data.indice_transparencia,
                indice_pct: data.indice_pct,
                docs_verificados: data.docs_verificados,
                docs_total: data.docs_total,
                docs_empresa: data.docs_empresa
              }
            );
            SubirConfianza.state.docs = SubirConfianza.state.docs.filter(
              (d) => d.tipo !== doc.tipo
            );
            SubirConfianza.guardar();
            status.textContent =
              data.motivo || 'Documento revocado. Puede revalidar subiendo un PDF nuevo.';
            SubirConfianza.init();
          });
          li.appendChild(btnRev);
        }

        lista.appendChild(li);
      });
    }

    listaWrap.append(listaTitulo, lista);
    wrap.append(head, form, listaWrap);
    return wrap;
  },

  cedulaHecha() {
    const p = SubirConfianza.perfil();
    return !!(p.cedula_verificada || p.rut_verificado);
  },

  bloqueCedula() {
    const wrap = document.createElement('section');
    wrap.className = 'confianza-bio config-card';
    wrap.setAttribute('aria-label', 'Validación de cédula');

    const titulo = document.createElement('h3');
    titulo.className = 'section-heading';
    titulo.textContent = 'Foto frontal del carnet';

    const lead = document.createElement('p');
    lead.className = 'section-lead';

    const status = document.createElement('p');
    status.className = 'status-text confianza-bio__status';
    status.setAttribute('role', 'status');

    const perfil = SubirConfianza.perfil();
    if (perfil.cedula_verificada) {
      lead.textContent =
        'Carnet validado (OCR + face-match con su selfie).';
      const partes = [];
      if (perfil.cedula_verificada_en) {
        partes.push('Validada el ' + SubirConfianza.formatoFecha(perfil.cedula_verificada_en));
      }
      if (perfil.cedula_score != null) partes.push('score ' + perfil.cedula_score + '/100');
      status.textContent = (partes.join(' ') || 'Cédula verificada') + '.';
      wrap.append(titulo, lead, status);
      return wrap;
    }

    if (!perfil.biometria_verificada) {
      lead.textContent =
        'Primero complete la verificación biométrica (selfie). Se usa para comparar el rostro del carnet.';
      status.textContent = 'Bloqueado hasta tener selfie biométrica.';
      wrap.append(titulo, lead, status);
      return wrap;
    }

    if (perfil.rut_verificado) {
      lead.textContent =
        'Ya tiene RUT verificado. Puede reforzar con la foto frontal: OCR + face-match contra su selfie.';
    } else {
      lead.textContent =
        'Encaje el frente del carnet en el marco. Se valida con OCR local, ROI del RUN y face-match contra su selfie.';
    }

    const previewWrap = document.createElement('div');
    previewWrap.className = 'confianza-cedula__preview-wrap';
    previewWrap.hidden = true;
    const preview = document.createElement('img');
    preview.className = 'confianza-cedula__preview-img';
    preview.alt = 'Vista previa del carnet';
    previewWrap.append(preview);

    const file = document.createElement('input');
    file.type = 'file';
    file.accept = 'image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp';
    file.className = 'confianza-docs__file';
    file.id = 'confianzaCedulaArchivo';

    const dropLabel = document.createElement('label');
    dropLabel.className = 'confianza-docs__drop-label';
    dropLabel.htmlFor = 'confianzaCedulaArchivo';
    dropLabel.innerHTML =
      '<span class="confianza-docs__drop-titulo">Elegir foto frontal</span>' +
      '<span class="confianza-docs__drop-hint">Solo el frente JPG o PNG sin reverso</span>' +
      '<span class="confianza-docs__drop-nombre" id="confianzaCedulaNombre">Ninguna foto seleccionada</span>';

    const drop = document.createElement('div');
    drop.className = 'confianza-docs__drop';
    drop.append(file, dropLabel);

    const acciones = document.createElement('div');
    acciones.className = 'confianza-bio__acciones';

    const btnCam = document.createElement('button');
    btnCam.type = 'button';
    btnCam.className = 'confianza-bio__btn confianza-bio__btn--cam';
    btnCam.textContent = 'Abrir cámara (trasera)';

    const btnCapturar = document.createElement('button');
    btnCapturar.type = 'button';
    btnCapturar.className = 'confianza-bio__btn';
    btnCapturar.textContent = 'Capturar carnet';
    btnCapturar.hidden = true;

    const btnReintentar = document.createElement('button');
    btnReintentar.type = 'button';
    btnReintentar.className = 'confianza-bio__btn confianza-bio__btn--retry';
    btnReintentar.textContent = 'Reintentar captura';
    btnReintentar.hidden = true;

    acciones.append(btnCam, btnCapturar, btnReintentar);

    const visor = document.createElement('div');
    visor.className = 'confianza-cedula__visor';
    visor.hidden = true;
    const video = document.createElement('video');
    video.className = 'confianza-cedula__video';
    video.setAttribute('playsinline', '');
    video.muted = true;
    video.autoplay = true;
    video.playsInline = true;
    const mascara = document.createElement('div');
    mascara.className = 'confianza-cedula__mascara';
    mascara.setAttribute('aria-hidden', 'true');
    const guia = document.createElement('p');
    guia.className = 'confianza-cedula__guia';
    guia.textContent = 'Encaje el frente del carnet en el marco';
    const canvas = document.createElement('canvas');
    canvas.hidden = true;
    visor.append(video, mascara, guia, canvas);

    const consentWrap = document.createElement('label');
    consentWrap.className = 'confianza-bio__consent';
    const consent = document.createElement('input');
    consent.type = 'checkbox';
    consent.id = 'confianzaCedulaConsent';
    const consentTxt = document.createElement('span');
    consentTxt.textContent =
      'Autorizo procesar la foto frontal de mi carnet.';
    consentWrap.append(consent, consentTxt);

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'submit-btn confianza-bio__enviar';
    btn.textContent = 'Validar carnet';
    btn.disabled = true;

    let archivoElegido = null;
    let stream = null;
    let enviando = false;
    let previewUrl = null;
    const nombreSpan = () => document.getElementById('confianzaCedulaNombre');

    function actualizarEnviar() {
      btn.disabled = enviando || !(archivoElegido && consent.checked);
    }

    function limpiarPreviewUrl() {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
        previewUrl = null;
      }
    }

    function setArchivo(archivo, etiqueta) {
      archivoElegido = archivo || null;
      limpiarPreviewUrl();
      const span = nombreSpan();
      if (span) {
        span.textContent = archivoElegido
          ? (etiqueta || archivoElegido.name) +
            ' ' +
            SubirConfianza.formatoTamano(archivoElegido.size)
          : 'Ninguna foto seleccionada';
      }
      drop.classList.toggle('confianza-docs__drop--lleno', !!archivoElegido);
      if (archivoElegido) {
        previewUrl = URL.createObjectURL(archivoElegido);
        preview.src = previewUrl;
        previewWrap.hidden = false;
        btnReintentar.hidden = false;
      } else {
        previewWrap.hidden = true;
        preview.removeAttribute('src');
        btnReintentar.hidden = true;
      }
      actualizarEnviar();
      if (archivoElegido && !consent.checked) {
        status.textContent = 'Foto lista. Marque el consentimiento para validar.';
      } else if (archivoElegido) {
        status.textContent = 'Foto lista. Pulse Validar carnet.';
      }
    }

    function detenerCamara() {
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
        stream = null;
      }
      video.srcObject = null;
    }

    async function abrirCamara() {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        status.textContent = 'Este dispositivo no permite usar la cámara.';
        return;
      }
      btnCam.disabled = true;
      status.textContent = 'Abriendo cámara trasera…';
      try {
        detenerCamara();
        setArchivo(null);
        file.value = '';
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: { ideal: 'environment' },
            width: { ideal: 1600 },
            height: { ideal: 900 }
          },
          audio: false
        });
        video.srcObject = stream;
        await video.play();
        visor.hidden = false;
        btnCapturar.hidden = false;
        btnReintentar.hidden = true;
        status.textContent = 'Encaje el carnet en el marco blanco y capture.';
      } catch {
        detenerCamara();
        status.textContent = 'No se pudo abrir la cámara. Use Elegir foto frontal.';
      } finally {
        btnCam.disabled = false;
      }
    }

    function prepararReintento(mensaje) {
      detenerCamara();
      visor.hidden = true;
      btnCapturar.hidden = true;
      setArchivo(null);
      file.value = '';
      btnReintentar.hidden = false;
      status.textContent = mensaje;
      actualizarEnviar();
    }

    file.addEventListener('change', () => {
      const f = file.files && file.files[0];
      if (!f) {
        setArchivo(null);
        return;
      }
      if (!String(f.type || '').startsWith('image/')) {
        status.textContent = 'Solo se acepta la foto frontal (JPG o PNG).';
        file.value = '';
        setArchivo(null);
        return;
      }
      detenerCamara();
      visor.hidden = true;
      btnCapturar.hidden = true;
      setArchivo(f);
    });

    consent.addEventListener('change', () => {
      actualizarEnviar();
      if (archivoElegido && !enviando) {
        status.textContent = consent.checked
          ? 'Foto lista. Pulse Validar carnet.'
          : 'Foto lista. Marque el consentimiento para validar.';
      }
    });

    btnCam.addEventListener('click', () => {
      abrirCamara();
    });

    btnReintentar.addEventListener('click', () => {
      abrirCamara();
    });

    btnCapturar.addEventListener('click', async () => {
      if (!stream || video.videoWidth < 2) {
        status.textContent = 'La cámara aún no está lista.';
        return;
      }

      const vw = video.videoWidth;
      const vh = video.videoHeight;
      const targetRatio = 1.586;
      let cw;
      let ch;
      if (vw / vh > targetRatio) {
        ch = Math.floor(vh * 0.78);
        cw = Math.floor(ch * targetRatio);
      } else {
        cw = Math.floor(vw * 0.88);
        ch = Math.floor(cw / targetRatio);
      }
      const sx = Math.floor((vw - cw) / 2);
      const sy = Math.floor((vh - ch) / 2);
      canvas.width = cw;
      canvas.height = ch;
      const ctx = canvas.getContext('2d', { alpha: false });
      ctx.drawImage(video, sx, sy, cw, ch, 0, 0, cw, ch);
      const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.93));
      detenerCamara();
      visor.hidden = true;
      btnCapturar.hidden = true;
      if (!blob || blob.size < 1500) {
        prepararReintento('No se pudo capturar. Reintente o suba un archivo.');
        return;
      }
      setArchivo(new File([blob], 'carnet-frontal.jpg', { type: 'image/jpeg' }), 'Captura');
    });

    btn.addEventListener('click', async () => {
      if (enviando) return;
      if (!archivoElegido) {
        status.textContent = 'Seleccione o capture la foto frontal.';
        return;
      }
      if (!consent.checked) {
        status.textContent = 'Debe aceptar el procesamiento de la foto del carnet.';
        actualizarEnviar();
        return;
      }
      enviando = true;
      actualizarEnviar();
      status.textContent = 'Validando: OCR + face-match con su selfie…';
      const res = await Auth.verificarCedula(archivoElegido);
      if (!res.ok) {
        enviando = false;
        prepararReintento(
          (res.error || 'No se pudo validar el carnet.') + ' Pulse Reintentar captura.'
        );
        return;
      }
      detenerCamara();
      limpiarPreviewUrl();
      SubirConfianza.init();
    });

    wrap.append(
      titulo,
      lead,
      drop,
      previewWrap,
      visor,
      acciones,
      consentWrap,
      btn,
      status
    );
    return wrap;
  },

  bloqueBiometria() {
    const wrap = document.createElement('section');
    wrap.className = 'confianza-bio config-card';
    wrap.setAttribute('aria-label', 'Verificación biométrica');

    const titulo = document.createElement('h3');
    titulo.className = 'section-heading';
    titulo.textContent = 'Verificación biométrica';

    const lead = document.createElement('p');
    lead.className = 'section-lead';

    const status = document.createElement('p');
    status.className = 'status-text confianza-bio__status';
    status.setAttribute('role', 'status');

    const hecha = SubirConfianza.biometriaHecha();

    if (hecha) {
      const perfil = SubirConfianza.perfil();
      lead.textContent =
        'Identidad verificada. Se guardó una copia comprimida de la selfie con acceso restringido y retención limitada.';
      const partes = [];
      if (perfil.biometria_verificada_en) {
        partes.push(
          'Completada el ' + SubirConfianza.formatoFecha(perfil.biometria_verificada_en)
        );
      } else {
        partes.push('Biometría completada');
      }
      if (perfil.biometria_retener_hasta) {
        partes.push(
          'retención hasta ' + SubirConfianza.formatoFecha(perfil.biometria_retener_hasta)
        );
      }
      if (perfil.biometria_bytes) {
        partes.push(SubirConfianza.formatoTamano(perfil.biometria_bytes));
      }
      status.textContent = partes.join(' ') + '.';
      wrap.append(titulo, lead, status);
      return wrap;
    }

    lead.textContent =
      'Abra la cámara frontal, encuadre su rostro y capture la selfie. Se guardará una copia comprimida solo para verificación de identidad, con retención limitada, y se borrará al eliminar la cuenta.';

    const visor = document.createElement('div');
    visor.className = 'confianza-bio__preview';
    visor.hidden = true;

    const video = document.createElement('video');
    video.className = 'confianza-bio__video-src';
    video.setAttribute('playsinline', '');
    video.setAttribute('muted', '');
    video.muted = true;
    video.autoplay = true;
    video.playsInline = true;

    const canvas = document.createElement('canvas');
    canvas.className = 'confianza-bio__canvas';
    canvas.setAttribute('aria-label', 'Vista de la selfie');

    visor.append(video, canvas);

    let stream = null;
    let archivoElegido = null;
    let rafId = 0;
    let congelado = false;
    const ctx = canvas.getContext('2d', { alpha: false });

    function detenerLoop() {
      if (rafId) {
        cancelAnimationFrame(rafId);
        rafId = 0;
      }
    }

    function detenerCamara() {
      detenerLoop();
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
        stream = null;
      }
      video.srcObject = null;
    }

    function pintarFrame() {
      if (!stream || congelado || !ctx) return;
      const w = video.videoWidth;
      const h = video.videoHeight;
      if (w > 0 && h > 0) {
        if (canvas.width !== w || canvas.height !== h) {
          canvas.width = w;
          canvas.height = h;
        }

        ctx.save();
        ctx.translate(w, 0);
        ctx.scale(-1, 1);
        ctx.drawImage(video, 0, 0, w, h);
        ctx.restore();
      }
      rafId = requestAnimationFrame(pintarFrame);
    }

    const acciones = document.createElement('div');
    acciones.className = 'confianza-bio__acciones';

    const btnAbrir = document.createElement('button');
    btnAbrir.type = 'button';
    btnAbrir.className = 'confianza-bio__btn confianza-bio__btn--cam';
    btnAbrir.textContent = 'Abrir cámara';

    const btnCapturar = document.createElement('button');
    btnCapturar.type = 'button';
    btnCapturar.className = 'confianza-bio__btn';
    btnCapturar.textContent = 'Capturar selfie';
    btnCapturar.hidden = true;

    const btnOtra = document.createElement('button');
    btnOtra.type = 'button';
    btnOtra.className = 'confianza-bio__btn';
    btnOtra.textContent = 'Volver a capturar';
    btnOtra.hidden = true;

    const btn = document.createElement('button');
    btn.className = 'submit-btn confianza-bio__enviar';
    btn.type = 'button';
    btn.textContent = 'Verificar identidad';
    btn.disabled = true;

    const consentWrap = document.createElement('label');
    consentWrap.className = 'confianza-bio__consent';
    const consent = document.createElement('input');
    consent.type = 'checkbox';
    consent.id = 'confianzaBioConsent';
    const consentTxt = document.createElement('span');
    consentTxt.textContent =
      'Autorizo guardar una copia comprimida de mi selfie para verificar identidad, con acceso restringido y retención limitada. Se borrará al eliminar mi cuenta.';
    consentWrap.append(consent, consentTxt);

    let enviando = false;

    function mensajeListo() {
      if (!archivoElegido) return;
      status.textContent = consent.checked
        ? 'Selfie lista. Pulse Verificar identidad.'
        : 'Selfie lista. Marque el consentimiento para continuar.';
    }

    function actualizarEnviar() {
      btn.disabled = enviando || !(archivoElegido && consent.checked);
      btn.setAttribute('aria-disabled', btn.disabled ? 'true' : 'false');
    }

    function uiInicial() {
      btnAbrir.hidden = false;
      btnAbrir.disabled = false;
      btnAbrir.textContent = 'Abrir cámara';
      btnCapturar.hidden = true;
      btnOtra.hidden = true;
      actualizarEnviar();
    }

    function uiCamaraLista() {
      btnAbrir.hidden = true;
      btnCapturar.hidden = false;
      btnOtra.hidden = true;
      actualizarEnviar();
    }

    function uiTrasCaptura() {
      btnAbrir.hidden = true;
      btnCapturar.hidden = true;
      btnOtra.hidden = false;
      actualizarEnviar();
      mensajeListo();
    }

    consent.addEventListener('change', () => {
      actualizarEnviar();
      if (archivoElegido && !enviando) mensajeListo();
    });
    uiInicial();

    btnAbrir.addEventListener('click', async () => {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        status.textContent = 'Este dispositivo no permite usar la cámara desde el navegador.';
        return;
      }
      btnAbrir.disabled = true;
      btnCapturar.hidden = true;
      status.textContent = 'Pidiendo acceso a la cámara…';
      try {
        detenerCamara();
        archivoElegido = null;
        congelado = false;
        actualizarEnviar();
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: { ideal: 'user' },
            width: { ideal: 640 },
            height: { ideal: 480 }
          },
          audio: false
        });
        video.srcObject = stream;
        await video.play();
        await new Promise((resolve) => {
          if (video.videoWidth > 0) {
            resolve();
            return;
          }
          const listo = () => {
            video.removeEventListener('loadeddata', listo);
            resolve();
          };
          video.addEventListener('loadeddata', listo);
          setTimeout(resolve, 1500);
        });
        visor.hidden = false;
        detenerLoop();
        pintarFrame();
        uiCamaraLista();
        status.textContent = 'Centre su rostro y pulse Capturar selfie.';
      } catch {
        detenerCamara();
        status.textContent = 'No se pudo abrir la cámara. Permita el acceso e intente de nuevo.';
        uiInicial();
      }
    });

    btnCapturar.addEventListener('click', async () => {
      if (!stream || !ctx || canvas.width < 2 || canvas.height < 2) {
        status.textContent = 'La cámara aún no está lista.';
        return;
      }

      congelado = true;
      detenerLoop();

      const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.92));
      if (!blob || blob.size < 500) {
        congelado = false;
        pintarFrame();
        archivoElegido = null;
        actualizarEnviar();
        status.textContent = 'No se pudo capturar la foto. Intente de nuevo.';
        return;
      }

      archivoElegido = new File([blob], 'selfie.jpg', { type: 'image/jpeg' });

      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
        stream = null;
      }
      video.srcObject = null;
      uiTrasCaptura();
    });

    btnOtra.addEventListener('click', () => {
      if (enviando) return;
      archivoElegido = null;
      congelado = false;
      actualizarEnviar();
      uiInicial();
      btnAbrir.click();
    });

    btn.addEventListener('click', async () => {
      if (enviando) return;
      if (!archivoElegido) {
        status.textContent = 'Primero capture una selfie.';
        actualizarEnviar();
        return;
      }
      if (!consent.checked) {
        status.textContent =
          'Debe aceptar el almacenamiento de la selfie comprimida para continuar.';
        actualizarEnviar();
        return;
      }
      enviando = true;
      actualizarEnviar();
      status.textContent = 'Verificando y guardando copia comprimida…';
      const res = await Auth.verificarBiometria(archivoElegido);
      if (!res.ok) {
        enviando = false;
        status.textContent = res.error || 'No se pudo verificar.';
        actualizarEnviar();
        return;
      }
      detenerCamara();
      SubirConfianza.sincronizarBiometria();
      SubirConfianza.init();
    });

    acciones.append(btnAbrir, btnCapturar, btnOtra);

    const nota = document.createElement('p');
    nota.className = 'confianza-bio__nota';
    nota.textContent =
      'Dato sensible: la foto no se publica. Solo metadata aparece en su perfil (tamaño y fecha de retención).';

    wrap.append(titulo, lead, visor, acciones, consentWrap, btn, status, nota);
    return wrap;
  },

  bloqueTablaNiveles() {
    const wrap = document.createElement('section');
    wrap.className = 'confianza-tabla';
    wrap.setAttribute('aria-label', 'Referencia de niveles');

    const details = document.createElement('details');
    details.className = 'confianza-tabla__details';
    details.open = !!SubirConfianza.tablaAbierta;
    details.addEventListener('toggle', () => {
      SubirConfianza.tablaAbierta = details.open;
    });

    const summary = document.createElement('summary');
    summary.className = 'confianza-tabla__summary';

    const summaryTitulo = document.createElement('span');
    summaryTitulo.className = 'confianza-tabla__summary-titulo';
    summaryTitulo.textContent = 'Referencia de niveles';

    const summaryLead = document.createElement('span');
    summaryLead.className = 'confianza-tabla__summary-lead';
    summaryLead.textContent = 'Qué evalúa cada nivel, qué pide y para qué sirve.';

    const chevron = document.createElement('span');
    chevron.className = 'confianza-tabla__chevron';
    chevron.setAttribute('aria-hidden', 'true');
    chevron.textContent = '▾';

    summary.append(summaryTitulo, summaryLead, chevron);

    const panel = document.createElement('div');
    panel.className = 'confianza-tabla__panel';

    const scroll = document.createElement('div');
    scroll.className = 'confianza-tabla__scroll';

    const table = document.createElement('table');
    table.className = 'confianza-tabla__grid';

    const thead = document.createElement('thead');
    const trHead = document.createElement('tr');
    ['Nivel', 'Qué evalúa', 'Requisito o métrica', 'Casos de uso', '¿Discriminatorio por dinero?'].forEach(
      t => {
        const th = document.createElement('th');
        th.scope = 'col';
        th.textContent = t;
        trHead.appendChild(th);
      }
    );
    thead.appendChild(trHead);

    const tbody = document.createElement('tbody');
    SubirConfianza.NIVELES.forEach(n => {
      const tr = document.createElement('tr');
      if (n.especial) tr.className = 'confianza-tabla__row--especial';
      [n.titulo, n.evalua, n.requisito, n.usos, n.discriminatorioNota].forEach((texto, i) => {
        const td = document.createElement('td');
        td.textContent = texto;
        if (i === 0) td.className = 'confianza-tabla__nivel';
        if (i === 4) {
          td.className = n.discriminatorio
            ? 'confianza-tabla__flag confianza-tabla__flag--si'
            : 'confianza-tabla__flag confianza-tabla__flag--no';
        }
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });

    table.append(thead, tbody);
    scroll.appendChild(table);
    panel.appendChild(scroll);
    details.append(summary, panel);
    wrap.appendChild(details);
    return wrap;
  },

  etiquetaTipo(tipo) {
    const mapa = {
      cedula: 'Carnet (frontal)',
      antecedentes: 'Antecedentes',
      aval: 'Aval / garantía',
      carpeta_tributaria: 'Carpeta tributaria (SII)',
      inicio_actividades: 'Inicio de actividades (SII)',
      vigencia_sociedad: 'Vigencia de la sociedad',
      vigencia_poderes: 'Vigencia de poderes',
      poder_representante: 'Poder representante',
      constitucion: 'Constitución',
      f30: 'F30 Dirección del Trabajo',
      no_quiebra: 'No quiebra / concursal',
      antecedentes_rl: 'Antecedentes representante',
      patente: 'Patente municipal',
      titularidad_cuenta: 'Titularidad cuenta bancaria'
    };
    return mapa[tipo] || tipo;
  },

  formatoFecha(iso) {
    try {
      return new Date(iso).toLocaleString('es-CL', { dateStyle: 'short', timeStyle: 'short' });
    } catch {
      return iso;
    }
  },

  formatoTamano(bytes) {
    const n = Number(bytes);
    if (!Number.isFinite(n) || n < 0) return '';
    if (n < 1024) return n + ' B';
    if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB';
    return (n / (1024 * 1024)).toFixed(1) + ' MB';
  },

  limpiar(el) {
    while (el.firstChild) el.removeChild(el.firstChild);
  }
};
