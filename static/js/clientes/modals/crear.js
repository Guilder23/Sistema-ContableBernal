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

if (clientCreateForm) {
    toggleCreateRepresentativeLegalSection(clientCreateForm);
}
