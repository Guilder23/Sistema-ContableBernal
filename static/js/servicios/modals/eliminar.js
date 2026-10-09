const deleteServiceForm = document.querySelector('[data-delete-service-form]');

document.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-open-modal="modal-eliminar-servicio"]');
    if (!trigger || !deleteServiceForm) return;
    deleteServiceForm.action = trigger.dataset.deleteUrl;
    const name = document.querySelector('[data-delete-service-name]');
    const warning = document.querySelector('[data-delete-service-warning]');
    const submit = document.querySelector('[data-delete-service-submit]');
    const hasPayments = trigger.dataset.deletePagos === 'true';
    if (name) name.textContent = trigger.dataset.deleteConcepto || 'Este servicio';
    if (warning) warning.hidden = !hasPayments;
    if (submit) submit.disabled = hasPayments;
});