const toggleRepresentanteLegalSection = (form) => {
    const checkbox = form.querySelector('[data-toggle-representante-legal]');
    const section = form.querySelector('[data-representante-legal-section]');
    if (!checkbox || !section) return;
    const enabled = checkbox.checked;
    section.hidden = !enabled;
    section.querySelectorAll('input, textarea').forEach((field) => {
        field.disabled = !enabled;
    });
};

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
        ci_complemento: trigger.dataset.clientCiComplemento,
        ci_expedido: trigger.dataset.clientCiExpedido,
        fecha_nacimiento: trigger.dataset.clientBirthDate,
        cambio_contador: trigger.dataset.clientChangeCounter,
        actividad: trigger.dataset.clientActivityValue,
        telefono: trigger.dataset.clientPhone,
        whatsapp: trigger.dataset.clientWhatsapp,
        correo: trigger.dataset.clientEmail,
        direccion: trigger.dataset.clientAddress,
        fecha_inicio: trigger.dataset.clientStartDate,
        tiene_representante_legal: trigger.dataset.clientHasRepresentative,
        representante_legal_nombre: trigger.dataset.clientRepresentativeName,
        representante_legal_carnet: trigger.dataset.clientRepresentativeId,
        representante_legal_complemento: trigger.dataset.clientRepresentativeComplement,
        representante_legal_expedido: trigger.dataset.clientRepresentativeExpedition,
        representante_legal_celular: trigger.dataset.clientRepresentativeCellphone,
        representante_legal_fecha_nacimiento: trigger.dataset.clientRepresentativeBirthDate,
        observaciones: trigger.dataset.clientObservations,
    };
    for (const [name, value] of Object.entries(fields)) {
        const field = form.querySelector(`[data-client-edit-field="${name}"]`);
        if (!field) continue;
        if (field.type === 'checkbox') {
            field.checked = value === 'true' || value === '1' || value === 'on';
        } else {
            field.value = value || '';
        }
    }
    form.querySelector('[data-client-edit-field="estado"]').checked = trigger.dataset.clientStatusValue === 'activo';
    toggleRepresentanteLegalSection(form);
});

document.addEventListener('change', (event) => {
    const checkbox = event.target.closest('[data-toggle-representante-legal]');
    if (!checkbox) return;
    toggleRepresentanteLegalSection(checkbox.closest('form'));
});

const clientEditForm = document.querySelector('#modal-editar form');
clientEditForm?.elements.estado?.addEventListener('change', (event) => {
    event.currentTarget.value = event.currentTarget.checked ? 'activo' : 'inactivo';
});

if (clientEditForm) {
    toggleRepresentanteLegalSection(clientEditForm);
}
