const deleteRequirementForm = document.querySelector('[data-delete-requirement-form]');

document.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-open-modal="modal-eliminar"]');
    if (!trigger || !deleteRequirementForm) return;
    deleteRequirementForm.action = trigger.dataset.deleteUrl;
    const title = document.querySelector('#modal-eliminar [data-delete-title]');
    if (title) title.textContent = trigger.dataset.deleteTitle || 'Este requerimiento';
});