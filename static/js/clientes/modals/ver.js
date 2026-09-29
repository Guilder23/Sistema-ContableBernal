document.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-open-modal="modal-ver"]');
    if (!trigger) return;
    const modal = document.querySelector('#modal-ver');
    if (!modal) return;
    const row = trigger.closest('tr');
    const fields = {
        name: trigger.dataset.clientName || 'Cliente',
        type: trigger.dataset.clientType,
        activity: trigger.dataset.clientActivity,
        nit: trigger.dataset.clientNit,
        ci: trigger.dataset.clientCi,
        phone: trigger.dataset.clientPhone,
        whatsapp: trigger.dataset.clientWhatsapp,
        email: trigger.dataset.clientEmail,
        address: trigger.dataset.clientAddress,
        status: trigger.dataset.clientStatus,
        'start-date': trigger.dataset.clientStartDate,
        observations: trigger.dataset.clientObservations,
        'created-at': row?.dataset.clientCreatedAt,
        'created-by': row?.dataset.clientCreatedBy,
    };
    for (const [key, value] of Object.entries(fields)) {
        const field = modal.querySelector(`[data-client-field="${key}"]`);
        if (field) field.textContent = value || '—';
    }
});
