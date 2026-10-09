const editServiceForm = document.querySelector('[data-edit-service-form]');

document.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-open-modal="modal-editar-servicio"]');
    if (!trigger || !editServiceForm) return;
    editServiceForm.action = trigger.dataset.editUrl;
    const fields = {
        concepto: 'editConcepto',
        descripcion: 'editDescripcion',
        tipo: 'editTipo',
        estado: 'editEstado',
        prioridad: 'editPrioridad',
        fecha_limite: 'editFecha',
        monto_total: 'editMonto',
        responsable: 'editResponsable',
        observaciones: 'editObservaciones',
    };
    Object.entries(fields).forEach(([name, dataName]) => {
        const field = editServiceForm.querySelector(`[data-edit-field="${name}"]`);
        if (!field) return;
        const value = trigger.dataset[dataName] || '';
        field.value = name === 'monto_total' ? value.replace(',', '.') : value;
    });
});