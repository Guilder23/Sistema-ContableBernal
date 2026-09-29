document.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-open-modal="modal-editar"]');
    if (!trigger) return;
    const modal = document.querySelector('#modal-editar');
    const form = modal.querySelector('[data-edit-form]');
    form.action = trigger.dataset.editUrl;
    for (const field of ['username', 'firstName', 'lastName', 'email']) {
        const inputName = field.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
        form.querySelector(`[data-edit-field="${inputName}"]`).value = trigger.dataset[`user${field[0].toUpperCase()}${field.slice(1)}`] || '';
    }
    form.querySelector('[data-edit-field="rol"]').value = trigger.dataset.userRoleValue;
    form.querySelector('[data-edit-field="is_active"]').checked = trigger.dataset.userActive === 'true';
});

const editModalForm = document.querySelector('#modal-editar form');
editModalForm?.addEventListener('submit', (event) => {
    const password = editModalForm.elements.password;
    const confirmation = editModalForm.elements.password_confirm;
    if ((password.value || confirmation.value) && password.value !== confirmation.value) {
        event.preventDefault();
        confirmation.setCustomValidity('Las contraseñas no coinciden.');
        confirmation.reportValidity();
    }
});
editModalForm?.elements.password_confirm.addEventListener('input', (event) => event.currentTarget.setCustomValidity(''));
