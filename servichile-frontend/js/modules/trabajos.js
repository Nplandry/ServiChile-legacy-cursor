
const Trabajos = {
  async crear(businessId) {
    if (!Auth.isAuthenticated()) {
      return { ok: false, error: 'Inicie sesión para abrir un trabajo con este proveedor.' };
    }
    return Auth.request('/v1/trabajos', {
      method: 'POST',
      token: Auth.sesion.token,
      body: { business_id: businessId }
    });
  },

  async mias() {
    if (!Auth.isAuthenticated()) {
      return { ok: false, error: 'Sin sesión.', data: [] };
    }
    return Auth.request('/v1/trabajos', { token: Auth.sesion.token });
  },

  async cancelar(trabajoId) {
    return Auth.request('/v1/trabajos/' + encodeURIComponent(trabajoId), {
      method: 'DELETE',
      token: Auth.sesion.token
    });
  },

  async delNegocio(businessId) {
    return Auth.request(
      '/v1/businesses/' + encodeURIComponent(businessId) + '/trabajos',
      { token: Auth.sesion.token }
    );
  },

  async concretar(businessId, qrToken) {
    return Auth.request(
      '/v1/businesses/' + encodeURIComponent(businessId) + '/trabajos/concretar',
      {
        method: 'POST',
        token: Auth.sesion.token,
        body: { qr_token: qrToken }
      }
    );
  },

  async noConcretado(businessId, trabajoId) {
    return Auth.request(
      '/v1/businesses/' +
        encodeURIComponent(businessId) +
        '/trabajos/' +
        encodeURIComponent(trabajoId) +
        '/no-concretado',
      { method: 'POST', token: Auth.sesion.token }
    );
  },

  etiquetaEstado(estado) {
    return estado === 'abierto' ? 'Abierto' : 'Cerrado';
  },

  claseEstado(estado) {
    return estado === 'abierto'
      ? 'trabajos-estado--abierto'
      : 'trabajos-estado--cerrado';
  },

  formatearFecha(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return '';
    try {
      return d.toLocaleDateString('es-CL', {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
      });
    } catch (e) {
      return '';
    }
  },

  panelTrabajoContratista(n) {
    const wrap = document.createElement('div');
    wrap.className = 'trabajos-panel';

    const titulo = document.createElement('p');
    titulo.className = 'trabajos-panel__titulo';
    titulo.textContent = 'Trabajo con este proveedor';

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'submit-btn trabajos-panel__btn';
    btn.setAttribute('aria-label', 'Abrir trabajo y mostrar código');
    const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    icon.setAttribute('class', 'trabajos-panel__btn-icon');
    icon.setAttribute('viewBox', '0 0 24 24');
    icon.setAttribute('aria-hidden', 'true');
    icon.setAttribute('fill', 'none');
    icon.setAttribute('stroke', 'currentColor');
    icon.setAttribute('stroke-width', '1.8');
    icon.setAttribute('stroke-linecap', 'round');
    icon.setAttribute('stroke-linejoin', 'round');

    [
      'M4 6v12',
      'M7 6v12',
      'M9 6v12',
      'M12 6v12',
      'M14 6v12',
      'M17 6v12',
      'M20 6v12'
    ].forEach((d, i) => {
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', d);
      if (i % 2 === 0) path.setAttribute('stroke-width', '2.4');
      icon.appendChild(path);
    });
    const label = document.createElement('span');
    label.textContent = 'Abrir trabajo';
    btn.append(icon, label);

    const detalle = document.createElement('div');
    detalle.className = 'trabajos-panel__detalle';
    detalle.hidden = true;

    const estadoLocal = document.createElement('p');
    estadoLocal.className = 'status-text status-text--sm';
    estadoLocal.setAttribute('role', 'status');
    estadoLocal.setAttribute('aria-live', 'polite');

    const setEstado = (texto) => {
      estadoLocal.textContent = texto || '';
    };

    const pintarAbierto = (r) => {
      if (!r || !r.qr_token) return;
      detalle.hidden = false;
      while (detalle.firstChild) detalle.removeChild(detalle.firstChild);
      const code = document.createElement('code');
      code.className = 'trabajos-panel__qr';
      code.textContent = r.qr_token;
      const meta = document.createElement('p');
      meta.className = 'field__hint trabajos-panel__hint';
      meta.textContent = 'Muestre este código al proveedor.';
      const cancelar = document.createElement('button');
      cancelar.type = 'button';
      cancelar.className = 'history__clear';
      cancelar.textContent = 'Cancelar trabajo';
      cancelar.addEventListener('click', async () => {
        cancelar.disabled = true;
        const c = await Trabajos.cancelar(r.id);
        cancelar.disabled = false;
        if (!c.ok) {
          setEstado(c.error || 'No se pudo cancelar.');
          return;
        }
        detalle.hidden = true;
        btn.hidden = false;
        setEstado('Trabajo cancelado.');
      });
      detalle.append(code, meta, cancelar);
      btn.hidden = true;
      setEstado('Trabajo abierto. Muestre este código al proveedor.');
    };

    btn.addEventListener('click', async () => {
      btn.disabled = true;
      setEstado('Abriendo trabajo…');
      const res = await Trabajos.crear(n.id);
      btn.disabled = false;
      if (!res.ok) {
        setEstado(res.error || 'No se pudo abrir el trabajo.');
        return;
      }
      pintarAbierto(res.data || {});
    });

    wrap.append(titulo, btn, detalle, estadoLocal);

    Trabajos.mias().then((res) => {
      if (!res || !res.ok || !Array.isArray(res.data)) return;
      const abierto = res.data.find(
        (t) =>
          t &&
          t.estado === 'abierto' &&
          String(t.business_id) === String(n.id) &&
          t.qr_token
      );
      if (abierto) pintarAbierto(abierto);
    });

    return wrap;
  },

  panelConcretarTitular(negocio) {
    const wrap = document.createElement('div');
    wrap.className = 'trabajos-titular';
    wrap.dataset.businessId = String(negocio.id);

    const head = document.createElement('div');
    head.className = 'trabajos-titular__head';
    const titulo = document.createElement('h5');
    titulo.className = 'trabajos-titular__titulo';
    titulo.textContent = 'Trabajos con contratistas';
    const lead = document.createElement('p');
    lead.className = 'trabajos-titular__lead';
    lead.textContent =
      'Pegue el código que le muestra el contratista para cerrar el trabajo.';
    head.append(titulo, lead);

    const form = document.createElement('form');
    form.className = 'trabajos-titular__form';
    form.noValidate = true;

    const field = document.createElement('div');
    field.className = 'field trabajos-titular__campo';
    const label = document.createElement('label');
    label.className = 'field__label';
    label.htmlFor = 'trabajoQr-' + negocio.id;
    label.textContent = 'Código del contratista';

    const fila = document.createElement('div');
    fila.className = 'trabajos-titular__fila';
    const input = document.createElement('input');
    input.id = 'trabajoQr-' + negocio.id;
    input.className = 'field__input trabajos-titular__input';
    input.type = 'text';
    input.autocomplete = 'off';
    input.spellcheck = false;
    input.maxLength = 64;
    input.placeholder = 'Código del trabajo abierto';

    const btnOk = document.createElement('button');
    btnOk.type = 'submit';
    btnOk.className = 'submit-btn trabajos-titular__submit';
    btnOk.textContent = 'Concretar trabajo';
    fila.append(input, btnOk);
    field.append(label, fila);
    form.appendChild(field);

    const status = document.createElement('p');
    status.className = 'status-text status-text--sm';
    status.setAttribute('role', 'status');

    const lista = document.createElement('div');
    lista.className = 'trabajos-titular__lista';

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const token = (input.value || '').trim();
      if (token.length < 10) {
        status.textContent = 'Ingrese el código completo del contratista.';
        input.focus();
        return;
      }
      btnOk.disabled = true;
      status.textContent = 'Registrando…';
      const res = await Trabajos.concretar(negocio.id, token);
      btnOk.disabled = false;
      if (!res.ok) {
        status.textContent = res.error || 'No se pudo marcar como concretado.';
        return;
      }
      input.value = '';
      status.textContent = 'Trabajo concretado.';
      Trabajos.pintarListaTitular(lista, negocio.id, status);
    });

    wrap.append(head, form, status, lista);
    Trabajos.pintarListaTitular(lista, negocio.id, status);
    return wrap;
  },

  crearFilaTrabajo(r, businessId, host, statusEl) {
    const li = document.createElement('li');
    li.className = 'trabajos-titular__li';

    const info = document.createElement('div');
    info.className = 'trabajos-titular__info';

    const badge = document.createElement('span');
    badge.className =
      'trabajos-estado ' + Trabajos.claseEstado(r.estado);
    badge.textContent = Trabajos.etiquetaEstado(r.estado);
    info.appendChild(badge);

    const token = String(r.qr_token || '').trim();
    if (token) {
      const id = document.createElement('code');
      id.className = 'trabajos-titular__id';
      id.textContent = token;
      id.title = token;
      info.appendChild(id);
    }

    const fecha = document.createElement('time');
    fecha.className = 'trabajos-titular__fecha';
    const fechaTxt = Trabajos.formatearFecha(r.creado_en);
    if (r.creado_en) fecha.dateTime = String(r.creado_en);
    fecha.textContent = fechaTxt || 'Sin fecha';
    info.appendChild(fecha);
    li.appendChild(info);

    if (r.estado === 'abierto') {
      const noConc = document.createElement('button');
      noConc.type = 'button';
      noConc.className = 'trabajos-titular__accion-sec';
      noConc.textContent = 'Marcar no concretado';
      noConc.addEventListener('click', async () => {
        noConc.disabled = true;
        const c = await Trabajos.noConcretado(businessId, r.id);
        noConc.disabled = false;
        if (!c.ok) {
          if (statusEl) statusEl.textContent = c.error || 'No se pudo marcar.';
          return;
        }
        if (statusEl) statusEl.textContent = 'Marcado como no concretado.';
        Trabajos.pintarListaTitular(host, businessId, statusEl);
      });
      li.appendChild(noConc);
    }

    return li;
  },

  async pintarListaTitular(host, businessId, statusEl) {
    if (!host) return;
    while (host.firstChild) host.removeChild(host.firstChild);
    const carga = document.createElement('p');
    carga.className = 'field__hint trabajos-titular__carga';
    carga.textContent = 'Cargando trabajos…';
    host.appendChild(carga);

    const res = await Trabajos.delNegocio(businessId);
    while (host.firstChild) host.removeChild(host.firstChild);
    if (!res.ok) {
      const err = document.createElement('p');
      err.className = 'error-text';
      err.textContent = res.error || 'No se pudieron cargar los trabajos.';
      host.appendChild(err);
      return;
    }
    const items = Array.isArray(res.data) ? res.data : [];
    if (!items.length) {
      const vacio = document.createElement('p');
      vacio.className = 'field__hint';
      vacio.textContent = 'Aún no hay trabajos en esta ficha.';
      host.appendChild(vacio);
      return;
    }

    const abiertos = items.filter((r) => r.estado === 'abierto');
    const historial = items.filter((r) => r.estado !== 'abierto');

    const pendientes = document.createElement('section');
    pendientes.className = 'trabajos-titular__bloque';
    const pendTitulo = document.createElement('p');
    pendTitulo.className = 'trabajos-titular__bloque-titulo';
    pendTitulo.textContent =
      abiertos.length === 1
        ? '1 pendiente'
        : abiertos.length + ' pendientes';
    pendientes.appendChild(pendTitulo);

    if (!abiertos.length) {
      const vacio = document.createElement('p');
      vacio.className = 'field__hint';
      vacio.textContent = 'No hay trabajos abiertos por concretar.';
      pendientes.appendChild(vacio);
    } else {
      const ul = document.createElement('ul');
      ul.className = 'trabajos-titular__ul';
      abiertos.forEach((r) => {
        ul.appendChild(Trabajos.crearFilaTrabajo(r, businessId, host, statusEl));
      });
      pendientes.appendChild(ul);
    }
    host.appendChild(pendientes);

    if (!historial.length) return;

    const details = document.createElement('details');
    details.className = 'trabajos-titular__historial';
    const summary = document.createElement('summary');
    summary.className = 'trabajos-titular__historial-sum';
    summary.textContent =
      historial.length === 1
        ? 'Ver 1 trabajo cerrado'
        : 'Ver ' + historial.length + ' trabajos cerrados';
    const ulHist = document.createElement('ul');
    ulHist.className = 'trabajos-titular__ul';
    historial.forEach((r) => {
      ulHist.appendChild(Trabajos.crearFilaTrabajo(r, businessId, host, statusEl));
    });
    details.append(summary, ulHist);
    host.appendChild(details);
  }
};
