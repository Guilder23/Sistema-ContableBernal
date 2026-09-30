document.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-open-modal="modal-eliminar"]');
    if (!trigger) return;
    const modal = document.querySelector('#modal-eliminar');
    modal.querySelector('[data-delete-form]').action = trigger.dataset.deleteUrl;
    modal.querySelector('[data-delete-name]').textContent = trigger.dataset.userName || 'esta cuenta';
});

const deleteModalForm = document.querySelector('#modal-eliminar form');
deleteModalForm?.addEventListener('submit', (event) => {
    if (!window.confirm('¿Confirmas la eliminación permanente de esta cuenta?')) event.preventDefault();
});
