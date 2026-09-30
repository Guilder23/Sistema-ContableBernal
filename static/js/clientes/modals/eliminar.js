document.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-open-modal="modal-eliminar"]');
    if (!trigger) return;
    const modal = document.querySelector('#modal-eliminar');
    modal.querySelector('[data-client-delete-form]').action = trigger.dataset.deleteUrl;
    modal.querySelector('[data-client-delete-name]').textContent = trigger.dataset.clientName || 'este cliente';
});

const clientDeleteForm = document.querySelector('#modal-eliminar form');
clientDeleteForm?.addEventListener('submit', (event) => {
    if (!window.confirm('¿Confirmas la eliminación permanente de este cliente?')) event.preventDefault();
});
