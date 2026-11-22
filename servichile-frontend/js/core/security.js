const Security = {
  sanitizeText: function (text) {
    return String(text).trim().replace(/[<>]/g, '');
  },

  validateNombre: function (nombre) {
    const value = String(nombre || '').trim().replace(/\s+/g, ' ');
    if (value.length < 2 || value.length > 120) return false;
    return /^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' .\-]+$/.test(value);
  },

  validateEmail: function (email) {
    const value = String(email || '').trim().toLowerCase();
    return /^[^\s@]+@[^\s@]+\.[a-zA-Z]{2,}$/.test(value);
  },

  validateEdad: function (edad) {
    const n = Number(edad);
    return Number.isInteger(n) && n >= 14 && n <= 120;
  },

  validateRut: function (rut) {
    const cleaned = String(rut).replace(/\./g, '').replace(/-/g, '').toUpperCase().trim();
    if (/^\d{7,8}[0-9K]$/.test(cleaned) === false) {
      return false;
    }

    const body = cleaned.slice(0, -1);
    const checkDigit = cleaned.slice(-1);

    let sum = 0;
    let multiplier = 2;
    for (let i = body.length - 1; i >= 0; i--) {
      sum += parseInt(body.charAt(i), 10) * multiplier;
      multiplier = multiplier === 7 ? 2 : multiplier + 1;
    }

    const remainder = sum % 11;
    const expected = 11 - remainder;
    let expectedDigit;
    if (expected === 11) {
      expectedDigit = '0';
    } else if (expected === 10) {
      expectedDigit = 'K';
    } else {
      expectedDigit = String(expected);
    }

    return expectedDigit === checkDigit;
  },

  formatRut: function (rut) {
    const cleaned = String(rut).replace(/[^0-9Kk]/g, '').toUpperCase();
    if (cleaned.length < 2) {
      return cleaned;
    }

    const capped = cleaned.length > 9 ? cleaned.slice(0, 9) : cleaned;
    const body = capped.slice(0, -1);
    const check = capped.slice(-1);
    const formattedBody = body.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    return formattedBody + '-' + check;
  },

  formatTelefono: function (tel) {
    const raw = String(tel || '').trim();
    if (!raw) return '';

    let digits = raw.replace(/\D/g, '');
    if (digits.startsWith('56')) digits = digits.slice(2);
    if (digits.startsWith('0')) digits = digits.slice(1);
    if (digits.length > 9) digits = digits.slice(0, 9);

    if (!digits) return '+56 ';
    if (digits.charAt(0) !== '9') {
      digits = '9' + digits;
      if (digits.length > 9) digits = digits.slice(0, 9);
    }
    if (digits.length === 1) return '+56 9';
    if (digits.length <= 5) return '+56 9 ' + digits.slice(1);
    return '+56 9 ' + digits.slice(1, 5) + ' ' + digits.slice(5, 9);
  },

  validateTelefono: function (tel) {
    const raw = String(tel || '').trim();
    if (!raw) return false;
    if (!raw.replace(/\s/g, '').startsWith('+56')) return false;
    const formatted = Security.formatTelefono(raw);
    return /^\+56 9 \d{4} \d{4}$/.test(formatted);
  },

  anonymizeRut: function (rut) {
    const cleaned = String(rut).replace(/\./g, '').replace(/-/g, '').toUpperCase().trim();
    if (cleaned.length < 3) {
      return '[RUT_INVALIDO]';
    }
    const check = cleaned.slice(-1);
    return 'RUT_****-' + check;
  }
};
