

(function () {
  function rutaActual() {
    var path = location.pathname || '/';
    if (path.length > 1 && path.endsWith('/')) path = path.slice(0, -1);
    return path;
  }

  function normalizar(ruta) {
    if (!ruta) return '';
    var path = ruta.split('?')[0].split('#')[0];
    if (path.length > 1 && path.endsWith('/')) path = path.slice(0, -1);
    return path;
  }

  function esActual(enlace, actual) {
    var path = normalizar(enlace.getAttribute('href'));
    if (path === '/index.html') return actual === '/' || actual === '/index.html';
    return path === actual;
  }

  function marcar(footer) {
    if (footer.dataset.listo === '1') return;
    footer.dataset.listo = '1';
    var actual = rutaActual();
    var enlaces = footer.querySelectorAll('a.app-footer__link');
    for (var i = 0; i < enlaces.length; i++) {
      if (esActual(enlaces[i], actual)) enlaces[i].setAttribute('aria-current', 'page');
      else enlaces[i].removeAttribute('aria-current');
    }
    ubicar(footer);
    syncSkyline();
    vigilar();
  }

  function ubicar(footer) {
    var auth = document.getElementById('authGate');
    if (!auth) return;
    if (!auth.hidden) {
      if (footer.parentElement !== auth) auth.appendChild(footer);
      return;
    }
    if (footer.parentElement === auth) {
      var main = document.querySelector('body > main');
      if (main) main.insertAdjacentElement('afterend', footer);
    }
  }

  function crearSkyline() {
    var el = document.createElement('div');
    el.id = 'appSkyline';
    el.className = 'market-skyline';
    el.setAttribute('aria-hidden', 'true');
    for (var i = 0; i < 30; i++) {
      el.appendChild(document.createElement('span'));
    }
    return el;
  }

  function syncSkyline() {
    var auth = document.getElementById('authGate');

    var enApp = auth ? !!auth.hidden : true;
    document.body.classList.toggle('is-login', !enApp);

    var el = document.getElementById('appSkyline');
    if (!enApp) {
      if (el) el.hidden = true;
      return;
    }
    if (!el) {
      el = crearSkyline();
      document.body.insertBefore(el, document.body.firstChild);
    }
    el.hidden = false;
  }

  function vigilar() {
    var auth = document.getElementById('authGate');
    if (!auth || vigilar.hecho) return;
    vigilar.hecho = true;
    new MutationObserver(function () {
      var footer = document.getElementById('appFooter');
      if (footer) ubicar(footer);
      syncSkyline();
    }).observe(auth, { attributes: true, attributeFilter: ['hidden'] });
  }

  function iniciar() {
    var footer = document.getElementById('appFooter');
    if (footer) marcar(footer);
    else syncSkyline();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }
})();
