const createRequirementForm = document.querySelector('[data-create-requirement-form]');

document.addEventListener('click', (event) => {
    if (!event.target.closest('[data-open-modal="modal-crear"]') || !createRequirementForm) return;
    createRequirementForm.reset();
});