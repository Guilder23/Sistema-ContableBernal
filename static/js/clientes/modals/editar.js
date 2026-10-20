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

const editClientActivitiesByType = {
    persona_natural: ['profesional', 'tecnico', 'alquiler', 'dependiente', 'consultor_en_linea', 'otra'],
    unipersonal: ['comercial', 'servicios', 'industrial', 'constructora', 'agropecuaria', 'minera', 'otra', 'agricola', 'ganadera', 'agroindustrial'],
    juridica: ['comercial', 'servicios', 'industrial', 'constructora', 'agropecuaria', 'minera', 'otra', 'agricola', 'ganadera', 'agroindustrial'],
    sin_fines_lucro: ['asociacion', 'ong', 'otra'],
};

const setEditClientSection = (form, selector, visible) => {
    const section = form.querySelector(selector);
    if (!section) return;
    section.hidden = !visible;
    section.querySelectorAll('input, select, textarea').forEach((field) => {
        field.disabled = !visible;
    });
};

const updateEditClientForm = (form) => {
    const type = form.querySelector('[name="tipo"]').value;
    const activity = form.querySelector('[name="actividad"]');
    const allowed = new Set(editClientActivitiesByType[type] || []);
    const legacyActivity = type === form.dataset.originalType
        && activity.value === form.dataset.originalActivity
        && activity.value
        && !allowed.has(activity.value);
    Array.from(activity.options).forEach((option) => {
        if (!option.value) return;
        const preservedLegacyOption = legacyActivity && option.value === activity.value;
        option.hidden = !allowed.has(option.value) && !preservedLegacyOption;
        option.disabled = !allowed.has(option.value) && !preservedLegacyOption;
    });
    if (activity.value && !allowed.has(activity.value) && !legacyActivity) activity.value = '';
    const juridica = type === 'juridica';
    const forma = form.querySelector('[name="forma_juridica"]').value;
    const otraActividad = activity.value === 'otra';
    const seprec = form.querySelector('[name="tiene_seprec"]').value === 'si';
    const cambioContador = form.querySelector('[name="cambio_contador"]').checked;
    setEditClientSection(form, '[data-client-seprec-name-section]', seprec);
    setEditClientSection(form, '[data-client-legal-form-section]', juridica);
    setEditClientSection(form, '[data-client-legal-form-detail-section]', juridica && forma === 'otra');
    setEditClientSection(form, '[data-client-activity-detail-section]', otraActividad);
    setEditClientSection(form, '[data-client-counter-date-section]', cambioContador);
    form.querySelectorAll('[data-client-personal-id-field], [data-client-personal-id-row]').forEach((section) => {
        section.hidden = juridica;
        section.querySelectorAll('input, select, textarea').forEach((field) => { field.disabled = juridica; });
    });
    form.querySelector('[name="razon_social"]').required = seprec;
    form.querySelector('[name="forma_juridica"]').required = juridica;
    form.querySelector('[name="forma_juridica_detalle"]').required = juridica && forma === 'otra';
    form.querySelector('[name="actividad_detalle"]').required = otraActividad;
    form.querySelector('[name="fecha_cambio_contador"]').required = cambioContador;
};

const loadClientEditForm = (trigger) => {
    const modal = document.querySelector('#modal-editar');
    const form = modal.querySelector('[data-client-edit-form]');
    form.action = trigger.dataset.editUrl;
    const fields = {
        nombre: trigger.dataset.clientName,
        razon_social: trigger.dataset.clientReasonSocial,
        tipo: trigger.dataset.clientTypeValue,
        forma_juridica: trigger.dataset.clientLegalForm,
        forma_juridica_detalle: trigger.dataset.clientLegalFormDetail,
        actividad_detalle: trigger.dataset.clientActivityDetail,
        tiene_seprec: trigger.dataset.clientHasSeprec,
        tiene_roe: trigger.dataset.clientHasRoe,
        nit: trigger.dataset.clientNit,
        ci: trigger.dataset.clientCi,
        ci_complemento: trigger.dataset.clientCiComplemento,
        ci_expedido: trigger.dataset.clientCiExpedido,
        fecha_nacimiento: trigger.dataset.clientBirthDate,
        cambio_contador: trigger.dataset.clientChangeCounter,
        fecha_cambio_contador: trigger.dataset.clientChangeCounterDate,
        actividad: trigger.dataset.clientActivityValue,
        telefono: trigger.dataset.clientPhone,
        whatsapp: trigger.dataset.clientWhatsapp,
        direccion: trigger.dataset.clientAddress,
        fecha_inicio: trigger.dataset.clientStartDate,
        tipo_facturacion: trigger.dataset.clientBillingType,
        fecha_vencimiento_facturacion: trigger.dataset.clientBillingExpiry,
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
    form.dataset.originalType = trigger.dataset.clientTypeValue || '';
    form.dataset.originalActivity = trigger.dataset.clientActivityValue || '';
    form.querySelector('[data-client-edit-field="estado"]').checked = trigger.dataset.clientStatusValue === 'activo';
    updateEditClientForm(form);
    toggleRepresentanteLegalSection(form);
};

document.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-open-modal="modal-editar"]');
    if (trigger) loadClientEditForm(trigger);
});

document.addEventListener('change', (event) => {
    const form = event.target.closest('[data-client-edit-form]');
    if (form && event.target.matches('[name="tipo"], [name="actividad"], [name="tiene_seprec"], [name="forma_juridica"], [name="cambio_contador"]')) {
        updateEditClientForm(form);
    }
    const checkbox = event.target.closest('[data-toggle-representante-legal]');
    if (!checkbox) return;
    toggleRepresentanteLegalSection(checkbox.closest('form'));
});

const clientEditForm = document.querySelector('#modal-editar form');
clientEditForm?.elements.estado?.addEventListener('change', (event) => {
    event.currentTarget.value = event.currentTarget.checked ? 'activo' : 'inactivo';
});

if (clientEditForm) {
    updateEditClientForm(clientEditForm);
    toggleRepresentanteLegalSection(clientEditForm);
}
