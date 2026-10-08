const deleteExpenseForm = document.querySelector('[data-delete-expense-form]');

document.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-open-modal="modal-eliminar"]');
    if (!trigger || !deleteExpenseForm) return;
    deleteExpenseForm.action = trigger.dataset.deleteUrl;
    const concept = document.querySelector('#modal-eliminar [data-delete-concept]');
    if (concept) concept.textContent = trigger.dataset.deleteConcept || 'este movimiento';
});