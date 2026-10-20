const createClientActivitiesByType = {
    persona_natural: ['profesional', 'tecnico', 'alquiler', 'dependiente', 'consultor_en_linea', 'otra'],
    unipersonal: ['comercial', 'servicios', 'industrial', 'constructora', 'agropecuaria', 'minera', 'otra', 'agricola', 'ganadera', 'agroindustrial'],
    juridica: ['comercial', 'servicios', 'industrial', 'constructora', 'agropecuaria', 'minera', 'otra', 'agricola', 'ganadera', 'agroindustrial'],
    sin_fines_lucro: ['asociacion', 'ong', 'otra'],
};

const setCreateSection = (form, selector, visible) => {
    const section = form.querySelector(selector);
    if (!section) return;
    section.hidden = !visible;
    section.querySelectorAll('input, select, textarea').forEach((field) => {
        field.disabled = !visible;
    });
};

const updateCreateClientForm = (form) => {
    const type = form.querySelector('[name="tipo"]').value;
    const activity = form.querySelector('[name="actividad"]');
    const allowed = new Set(createClientActivitiesByType[type] || []);
    Array.from(activity.options).forEach((option) => {
        if (!option.value) return;
        option.hidden = !allowed.has(option.value) && option.value !== activity.value;
        option.disabled = !allowed.has(option.value) && option.value !== activity.value;
    });
    if (activity.value && !allowed.has(activity.value)) activity.value = '';
    const juridica = type === 'juridica';
    const forma = form.querySelector('[name="forma_juridica"]').value;
    const otraActividad = activity.value === 'otra';
    const seprec = form.querySelector('[name="tiene_seprec"]').value === 'si';
    const cambioContador = form.querySelector('[name="cambio_contador"]').checked;
    setCreateSection(form, '[data-client-seprec-name-section]', seprec);
    setCreateSection(form, '[data-client-legal-form-section]', juridica);
    setCreateSection(form, '[data-client-legal-form-detail-section]', juridica && forma === 'otra');
    setCreateSection(form, '[data-client-activity-detail-section]', otraActividad);
    setCreateSection(form, '[data-client-counter-date-section]', cambioContador);
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

const toggleCreateRepresentativeLegalSection = (form) => {
    const checkbox = form.querySelector('[data-toggle-representante-legal]');
    const section = form.querySelector('[data-representante-legal-section]');
    if (!checkbox || !section) return;
    const enabled = checkbox.checked;
    section.hidden = !enabled;
    section.querySelectorAll('input, textarea').forEach((field) => {
        field.disabled = !enabled;
    });
};

const clientCreateForm = document.querySelector('#modal-crear form');

clientCreateForm?.elements.estado?.addEventListener('change', (event) => {
    event.currentTarget.value = event.currentTarget.checked ? 'activo' : 'inactivo';
});

clientCreateForm?.querySelector('[data-toggle-representante-legal]')?.addEventListener('change', (event) => {
    toggleCreateRepresentativeLegalSection(event.currentTarget.closest('form'));
});

clientCreateForm?.addEventListener('change', (event) => {
    if (event.target.matches('[name="tipo"], [name="actividad"], [name="tiene_seprec"], [name="forma_juridica"], [name="cambio_contador"]')) {
        updateCreateClientForm(clientCreateForm);
    }
});

if (clientCreateForm) {
    updateCreateClientForm(clientCreateForm);
    toggleCreateRepresentativeLegalSection(clientCreateForm);
}
