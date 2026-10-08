document.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-open-modal="modal-ver"]');
    if (!trigger) return;
    const fields = ['concepto', 'tipo', 'categoria', 'periodicidad', 'monto', 'fecha', 'pago', 'proveedor',
        'responsable', 'comprobante', 'cliente', 'recuperable', 'recuperacion', 'vidaUtil', 'depreciacion',
        'activo', 'ubicacion', 'observaciones'];
    fields.forEach((field) => {
        const target = document.querySelector(`#modal-ver [data-view-field="${field}"]`);
        if (target) target.textContent = trigger.dataset[`view${field[0].toUpperCase()}${field.slice(1)}`] || 'No indicado';
    });
});