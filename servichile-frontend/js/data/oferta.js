
const Oferta = {
  MAX_SERVICIOS: 6,
  MAX_REFERENCIAS: 8,
  MAX_LARGO_SERVICIO: 40,
  MAX_LARGO_REFERENCIA: 80,
  INDUSTRIAS: [
    { id: 'mineria', label: 'Minería' },
    { id: 'retail', label: 'Retail' },
    { id: 'salud', label: 'Salud' },
    { id: 'construccion', label: 'Construcción' },
    { id: 'tecnologia', label: 'Tecnología' },
    { id: 'sector-publico', label: 'Sector público' }
  ],
  CONTRATACIONES: [
    { id: 'cotizacion-directa', label: 'Cotización directa' },
    { id: 'contrato-recurrente', label: 'Contrato recurrente' },
    { id: 'licitacion-oc', label: 'Licitación u orden de compra' },
    { id: 'factura-electronica', label: 'Factura electrónica' }
  ],
  MONTOS: [
    { id: 'bajo', label: 'Menos de $1.000.000' },
    { id: 'medio', label: 'Entre $1.000.000 y $5.000.000' },
    { id: 'alto', label: 'Más de $5.000.000' }
  ],
  PLAZOS: [
    { id: 'menos-2h', label: 'Menos de 2 horas' },
    { id: 'en-el-dia', label: 'En el día' },
    { id: '24-48h', label: '24 a 48 horas' }
  ],
  CONCRETADOS: [
    { id: '1', label: 'Al menos 1 concretado' },
    { id: '5', label: 'Al menos 5 concretados' },
    { id: '10', label: 'Al menos 10 concretados' }
  ],

  etiqueta(lista, id) {
    const item = (lista || []).find((opcion) => opcion.id === id);
    return item ? item.label : '';
  }
};
