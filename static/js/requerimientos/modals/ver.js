document.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-open-modal^="modal-ver-"]');
    if (!trigger) return;
    const modal = document.getElementById(trigger.dataset.openModal);
    modal?.querySelector('.requirement-modal__close')?.focus();
});