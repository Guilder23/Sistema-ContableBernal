document.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-open-modal="modal-editar"]');
    if (!trigger) return;
    const modal = document.querySelector('#modal-editar');
    const form = modal.querySelector('[data-client-edit-form]');
    form.action = trigger.dataset.editUrl;
    const fields = {
        nombre: trigger.dataset.clientName,
        tipo: trigger.dataset.clientTypeValue,
        nit: trigger.dataset.clientNit,
        ci: trigger.dataset.clientCi,
        actividad: trigger.dataset.clientActivityValue,
        telefono: trigger.dataset.clientPhone,
        whatsapp: trigger.dataset.clientWhatsapp,
        correo: trigger.dataset.clientEmail,
        direccion: trigger.dataset.clientAddress,
        fecha_inicio: trigger.dataset.clientStartDate,
        observaciones: trigger.dataset.clientObservations,
    };
    for (const [name, value] of Object.entries(fields)) {
        form.querySelector(`[data-client-edit-field="${name}"]`).value = value || '';
    }
    form.querySelector('[data-client-edit-field="estado"]').checked = trigger.dataset.clientStatusValue === 'activo';
});

const clientEditForm = document.querySelector('#modal-editar form');
clientEditForm?.elements.estado?.addEventListener('change', (event) => {
    event.currentTarget.value = event.currentTarget.checked ? 'activo' : 'inactivo';
});
