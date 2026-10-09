document.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-open-modal^="modal-ver-servicio-"]');
    if (!trigger) return;
    const modal = document.getElementById(trigger.dataset.openModal);
    modal?.querySelector('.service-modal__close')?.focus();
});