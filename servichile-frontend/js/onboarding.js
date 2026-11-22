const Onboarding = {
  VERSION: 57,
  STORAGE_KEY: 'servichile.onboarding.v57',

  pasos: [
    {
      id: 'tipo_cuenta',
      type: 'choice',
      campo: 'tipo_cuenta',
      titulo: '¿Cómo vas a usar ServiChile?',
      texto: 'Proveedor: publicar y mejorar su índice. Contratista y persona: verificar y evaluar con QR.',
      opciones: [
        { value: 'proveedor', label: 'Proveedor' },
        { value: 'contratista', label: 'Contratista' },
        { value: 'persona', label: 'Persona' }
      ]
    },
    {
      id: 'nombre',
      type: 'text',
      campo: 'nombre',
      titulo: '¿Cómo te llamas?',
      texto: 'Aparecerá en tu reporte QR al validar una visita o entrega.',
      placeholder: 'Tu nombre',
      inputType: 'text'
    },
    {
      id: 'rut_responsable',
      type: 'text',
      campo: 'rut_responsable',
      titulo: '¿Cuál es el RUT del responsable?',
      texto: 'RUT de la persona responsable de la cuenta. Podrá editarlo en Perfil.',
      placeholder: '12.345.678-9',
      inputType: 'text'
    },
    {
      id: 'edad',
      type: 'text',
      campo: 'edad',
      titulo: '¿Qué edad tienes?',
      texto: 'Solo para completar tu perfil de verificación.',
      placeholder: 'Ej: 32',
      inputType: 'number'
    },
    {
      id: 'email',
      type: 'text',
      campo: 'email',
      titulo: '¿Cuál es tu correo?',
      texto: 'Lo usarás para iniciar sesión.',
      placeholder: 'correo@ejemplo.cl',
      inputType: 'email'
    },
    {
      id: 'password',
      type: 'text',
      campo: 'password',
      titulo: 'Crea una contraseña',
      texto: 'Mínimo 8 caracteres.',
      placeholder: 'Contraseña',
      inputType: 'password'
    },
    {
      id: 'fin',
      type: 'summary',
      titulo: 'Listo para verificar tratos',
      texto: 'Crearemos tu cuenta. Después podrás explorar, verificar y usar QR de reporte.',
      cta: 'Crear cuenta y entrar'
    }
  ],

  index: 0,
  datos: {},
  elements: {},

  init() {
    Auth.init();
    Onboarding.elements.deck = document.getElementById('deck');
    Onboarding.elements.progress = document.getElementById('progress');
    Onboarding.elements.prevBtn = document.getElementById('prevBtn');
    Onboarding.elements.stepStatus = document.getElementById('stepStatus');
    Onboarding.restore();
    Onboarding.renderProgress();
    Onboarding.elements.prevBtn.addEventListener('click', Onboarding.goBack);
    Onboarding.renderCard();
  },

  restore() {
    try {
      localStorage.removeItem('servichile.onboarding');
    } catch {}
    try {
      const raw = localStorage.getItem(Onboarding.STORAGE_KEY);
      if (raw) {
        Onboarding.datos = JSON.parse(raw) || {};
        if ('password' in Onboarding.datos) {
          delete Onboarding.datos.password;
          Onboarding.save();
        }
      }
    } catch (e) {
      Onboarding.datos = {};
    }

    if (!Onboarding.datos.tipo_cuenta) {
      Onboarding.index = 0;
    }
  },

  save() {

    const borrador = Object.assign({}, Onboarding.datos);
    delete borrador.password;
    try {
      localStorage.setItem(Onboarding.STORAGE_KEY, JSON.stringify(borrador));
    } catch {}
  },

  renderProgress() {
    Onboarding.clear(Onboarding.elements.progress);
    Onboarding.pasosVisibles().forEach((p, i) => {
      const dot = document.createElement('span');
      dot.className = 'onboarding__dot' + (i <= Onboarding.index ? ' onboarding__dot--done' : '');
      Onboarding.elements.progress.appendChild(dot);
    });
  },

  clear(el) {
    while (el.firstChild) {
      el.removeChild(el.firstChild);
    }
  },

  progreso() {
    return typeof ProgresoCuenta !== 'undefined'
      ? ProgresoCuenta.para({ tipo_cuenta: Onboarding.datos.tipo_cuenta })
      : null;
  },

  esProveedor() {
    const prog = Onboarding.progreso();
    return prog ? prog.es('proveedor') : Onboarding.datos.tipo_cuenta === 'proveedor';
  },

  esEmpresa() {
    return Onboarding.esProveedor();
  },

  pasosVisibles() {
    const prog = Onboarding.progreso();
    return Onboarding.pasos.filter((p) => {
      if (p.id === 'edad') {
        return prog ? prog.soporta('edad') : !Onboarding.esProveedor();
      }
      if (p.id === 'rut_responsable') {
        return Onboarding.esProveedor();
      }
      return true;
    });
  },

  pasoActual() {
    return Onboarding.pasosVisibles()[Onboarding.index];
  },

  copyPaso(paso) {
    if (!paso) return { titulo: '', texto: '' };
    const prog = Onboarding.progreso();
    if (paso.id === 'nombre' && prog && prog.es('proveedor')) {
      return {
        titulo: prog.tituloNombreOnboarding(),
        texto: prog.textoNombreOnboarding()
      };
    }
    if (paso.id === 'fin' && Onboarding.datos.tipo_cuenta === 'proveedor') {
      return {
        titulo: 'Listo para explorar',
        texto:
          'Crearemos tu cuenta. Entra, mira fichas de otros proveedores y publica la tuya cuando quieras. Publicar ficha se paga con Webpay (precio en Perfil); el informe de proveedor se vende aparte.'
      };
    }
    return { titulo: paso.titulo, texto: paso.texto };
  },

  renderCard() {
    const visibles = Onboarding.pasosVisibles();
    if (Onboarding.index >= visibles.length) {
      Onboarding.index = Math.max(0, visibles.length - 1);
    }
    const paso = Onboarding.pasoActual();
    Onboarding.clear(Onboarding.elements.deck);
    Onboarding.elements.prevBtn.hidden = Onboarding.index === 0;
    Onboarding.elements.stepStatus.textContent = '';
    Onboarding.renderProgress();

    const card = document.createElement('article');
    card.className = 'onboarding__card';
    const copy = Onboarding.copyPaso(paso);

    const title = document.createElement('h1');
    title.className = 'onboarding__card-title';
    title.textContent = copy.titulo;
    card.appendChild(title);

    const text = document.createElement('p');
    text.className = 'onboarding__card-text';
    text.textContent = copy.texto;
    card.appendChild(text);

    if (paso.type === 'text') {
      Onboarding.renderTextStep(card, paso);
    } else if (paso.type === 'choice') {
      Onboarding.renderChoiceStep(card, paso);
    } else if (paso.type === 'summary') {
      Onboarding.renderSummaryStep(card, paso);
    } else {
      Onboarding.renderWelcomeStep(card, paso);
    }

    Onboarding.elements.deck.appendChild(card);
    Onboarding.enableSwipe(card);
  },

  renderWelcomeStep(card, paso) {
    const btn = Onboarding.makeButton(paso.cta || 'Siguiente');
    btn.addEventListener('click', Onboarding.goNext);
    card.appendChild(btn);
  },

  renderTextStep(card, paso) {
    const field = document.createElement('div');
    field.className = 'field';
    const input = document.createElement('input');
    input.className = 'field__input';
    input.type = paso.inputType || 'text';
    const prog = Onboarding.progreso();
    input.placeholder =
      paso.id === 'nombre' && prog
        ? prog.placeholderNombre()
        : paso.placeholder || '';
    input.value = Onboarding.datos[paso.campo] || '';
    input.maxLength = paso.inputType === 'password' ? 40 : 120;
    if (paso.inputType === 'number') {
      input.min = '0';
      input.max = '120';
    }
    if (paso.inputType === 'email') {
      input.autocomplete = 'username';
    }
    if (paso.inputType === 'password') {
      input.autocomplete = 'new-password';
    }
    if (paso.campo === 'rut_responsable' && typeof Security !== 'undefined') {
      input.maxLength = 12;
      input.addEventListener('input', () => {
        input.value = Security.formatRut(input.value);
      });
      if (input.value) input.value = Security.formatRut(input.value);
    }
    field.appendChild(input);
    card.appendChild(field);

    const btn = Onboarding.makeButton('Siguiente');
    btn.addEventListener('click', () => {
      const value = input.value.trim();
      const error = Onboarding.validateField(paso, value);
      if (error) {
        Onboarding.elements.stepStatus.textContent = error;
        input.focus();
        return;
      }
      Onboarding.datos[paso.campo] = value;
      Onboarding.save();
      Onboarding.goNext();
    });
    card.appendChild(btn);
    setTimeout(() => input.focus(), 50);
  },

  validateField(paso, value) {
    if (!value) {
      return 'Por favor, completa este campo.';
    }
    if (paso.campo === 'nombre') {
      if (typeof Security !== 'undefined' && !Security.validateNombre(value)) {
        return 'Ingrese un nombre válido (solo letras, espacios y . \'-).';
      }
      if (String(value).trim().length < 2) {
        return 'Ingrese un nombre de al menos 2 caracteres.';
      }
    }
    if (paso.campo === 'email') {
      if (typeof Security !== 'undefined') {
        if (!Security.validateEmail(value)) {
          return 'Ingrese un correo válido, por ejemplo nombre@dominio.cl';
        }
      } else if (!/^[^\s@]+@[^\s@]+\.[a-zA-Z]{2,}$/.test(value)) {
        return 'Ingrese un correo válido, por ejemplo nombre@dominio.cl';
      }
    }
    if (paso.campo === 'edad') {
      if (typeof Security !== 'undefined') {
        if (!Security.validateEdad(value)) {
          return 'Ingrese una edad entre 14 y 120 años.';
        }
      } else {
        const edad = Number(value);
        if (!Number.isInteger(edad) || edad < 14 || edad > 120) {
          return 'Ingrese una edad entre 14 y 120 años.';
        }
      }
    }
    if (paso.campo === 'password' && value.length < 8) {
      return 'La contraseña debe tener al menos 8 caracteres.';
    }
    if (paso.campo === 'rut_responsable') {
      if (typeof Security !== 'undefined' && !Security.validateRut(value)) {
        return 'Ingrese un RUT válido, p. ej. 12.345.678-9.';
      }
    }
    return '';
  },

  renderChoiceStep(card, paso) {
    const list = document.createElement('div');
    list.className = 'onboarding__choices';
    paso.opciones.forEach(op => {
      const choice = document.createElement('button');
      choice.type = 'button';
      choice.className = 'onboarding__choice';
      if (Onboarding.datos[paso.campo] === op.value) {
        choice.classList.add('onboarding__choice--selected');
      }
      choice.textContent = op.label;
      choice.addEventListener('click', () => {
        Onboarding.datos[paso.campo] = op.value;
        Onboarding.save();
        Onboarding.goNext();
      });
      list.appendChild(choice);
    });
    card.appendChild(list);
  },

  etiquetaTipoCuenta(valor) {
    const ok =
      valor === 'proveedor' || valor === 'contratista' || valor === 'persona';
    if (!ok) return valor || 'Sin responder';
    return typeof ProgresoCuenta !== 'undefined'
      ? ProgresoCuenta.de(valor).etiquetaCorta()
      : valor === 'proveedor'
        ? 'Proveedor'
        : valor === 'contratista'
          ? 'Contratista'
          : 'Persona';
  },

  renderSummaryStep(card, paso) {
    const list = document.createElement('dl');
    list.className = 'onboarding__summary';
    const prog = Onboarding.progreso();
    const campos = [
      ['Tipo', Onboarding.etiquetaTipoCuenta(Onboarding.datos.tipo_cuenta)],
      [prog ? prog.labelNombre() : 'Nombre', Onboarding.datos.nombre],
      Onboarding.esProveedor()
        ? ['RUT responsable', Onboarding.datos.rut_responsable]
        : null,
      prog && prog.soporta('edad') ? ['Edad', Onboarding.datos.edad] : null,
      ['Correo', Onboarding.datos.email]
    ].filter(Boolean);
    campos.forEach(([k, v]) => {
      const dt = document.createElement('dt');
      dt.textContent = k;
      const dd = document.createElement('dd');
      dd.textContent = v || 'Sin responder';
      list.appendChild(dt);
      list.appendChild(dd);
    });
    card.appendChild(list);

    const btn = Onboarding.makeButton(paso.cta || 'Finalizar');
    btn.addEventListener('click', () => Onboarding.finish(btn));
    card.appendChild(btn);
  },

  makeButton(text) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'submit-btn onboarding__cta';
    btn.textContent = text;
    return btn;
  },

  goNext() {
    if (Onboarding.index < Onboarding.pasosVisibles().length - 1) {
      Onboarding.index += 1;
      Onboarding.renderCard();
    }
  },

  goBack() {
    if (Onboarding.index > 0) {
      Onboarding.index -= 1;
      Onboarding.renderCard();
    }
  },

  async finish(btn) {
    if (!Onboarding.datos.tipo_cuenta) {
      Onboarding.index = Onboarding.pasosVisibles().findIndex((p) => p.campo === 'tipo_cuenta');
      Onboarding.renderCard();
      Onboarding.elements.stepStatus.textContent =
        'Elija si es proveedor, contratista o persona.';
      return;
    }

    if (!Onboarding.datos.password) {
      Onboarding.index = Onboarding.pasosVisibles().findIndex((p) => p.campo === 'password');
      Onboarding.renderCard();
      Onboarding.elements.stepStatus.textContent = 'Por seguridad, vuelva a escribir su contraseña.';
      return;
    }
    btn.disabled = true;
    btn.textContent = 'Creando tu cuenta...';
    Onboarding.elements.stepStatus.textContent = '';

    const prog = Onboarding.progreso();
    const res = await Auth.onboardApi({
      nombre: Onboarding.datos.nombre,
      email: Onboarding.datos.email,
      password: Onboarding.datos.password,
      edad: prog && prog.soporta('edad') ? Onboarding.datos.edad : undefined,
      tipo_cuenta: Onboarding.datos.tipo_cuenta
    });

    if (!res.ok) {
      btn.disabled = false;
      btn.textContent = 'Crear cuenta y entrar';
      Onboarding.elements.stepStatus.textContent = res.error;
      return;
    }

    try {
      localStorage.removeItem(Onboarding.STORAGE_KEY);
      localStorage.removeItem('servichile.rut_empresa_pendiente');
    } catch {}

    let avisoRut = '';
    if (Onboarding.esProveedor() && Onboarding.datos.rut_responsable && Auth.actualizarPerfil) {
      const rutRes = await Auth.actualizarPerfil({
        rut: String(Onboarding.datos.rut_responsable).trim()
      });
      if (!rutRes.ok) {
        avisoRut =
          ' La cuenta quedó creada, pero el RUT del responsable no se guardó: ' +
          (rutRes.error || 'inténtelo en Perfil.');
      }
    }

    Onboarding.clear(Onboarding.elements.deck);
    const done = document.createElement('article');
    done.className = 'onboarding__card onboarding__card--done';
    const title = document.createElement('h1');
    title.className = 'onboarding__card-title';
    title.textContent = '¡Bienvenido, ' + (res.user.nombre || '') + '!';
    const text = document.createElement('p');
    text.className = 'onboarding__card-text';
    text.textContent = Onboarding.esProveedor()
      ? 'Cuenta proveedor lista. Puede publicar en el marketplace y validar con QR.' +
        avisoRut
      : 'Cuenta lista. Puede explorar proveedores y validar a la otra parte con QR.';
    done.appendChild(title);
    done.appendChild(text);
    Onboarding.elements.deck.appendChild(done);
    Onboarding.elements.prevBtn.hidden = true;

    setTimeout(() => {
      window.location.href = '../index.html';
    }, avisoRut ? 2200 : 900);
  },

  enableSwipe(card) {
    const paso = Onboarding.pasoActual();
    if (!paso || paso.type === 'choice' || paso.type === 'text' || paso.type === 'summary') {
      return;
    }
    let startX = 0;
    let currentX = 0;
    let dragging = false;

    const start = x => {
      dragging = true;
      startX = x;
      currentX = x;
      card.style.transition = 'none';
    };
    const move = x => {
      if (!dragging) {
        return;
      }
      currentX = x;
      const delta = currentX - startX;
      card.style.transform = 'translateX(' + delta + 'px) rotate(' + (delta / 25) + 'deg)';
    };
    const end = () => {
      if (!dragging) {
        return;
      }
      dragging = false;
      const delta = currentX - startX;
      card.style.transition = 'transform 0.25s ease';
      if (delta > 90) {
        card.style.transform = 'translateX(120%) rotate(12deg)';
        setTimeout(Onboarding.goNext, 180);
      } else if (delta < -90 && Onboarding.index > 0) {
        card.style.transform = 'translateX(-120%) rotate(-12deg)';
        setTimeout(Onboarding.goBack, 180);
      } else {
        card.style.transform = '';
      }
    };

    card.addEventListener('touchstart', e => start(e.touches[0].clientX), { passive: true });
    card.addEventListener('touchmove', e => move(e.touches[0].clientX), { passive: true });
    card.addEventListener('touchend', end);
    card.addEventListener('mousedown', e => start(e.clientX));
    window.addEventListener('mousemove', e => move(e.clientX));
    window.addEventListener('mouseup', end);
  }
};

document.addEventListener('DOMContentLoaded', Onboarding.init);
