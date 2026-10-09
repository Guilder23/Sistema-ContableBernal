const editRequirementForm = document.querySelector('[data-edit-requirement-form]');

document.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-open-modal="modal-editar"]');
    if (!trigger || !editRequirementForm) return;
    editRequirementForm.action = trigger.dataset.editUrl;
    const fields = {
        titulo: 'editTitle',
        descripcion: 'editDescription',
        estado: 'editState',
        prioridad: 'editPriority',
        fecha_limite: 'editDue',
        responsable: 'editResponsible',
    };
    Object.entries(fields).forEach(([name, key]) => {
        const field = editRequirementForm.querySelector(`[data-edit-field="${name}"]`);
        if (field) field.value = trigger.dataset[key] || '';
    });
});