const createModalForm = document.querySelector('#modal-crear form');

createModalForm?.addEventListener('submit', (event) => {
    const password = createModalForm.elements.password;
    const confirmation = createModalForm.elements.password_confirm;
    if (password.value !== confirmation.value) {
        event.preventDefault();
        confirmation.setCustomValidity('Las contraseñas no coinciden.');
        confirmation.reportValidity();
    }
});

createModalForm?.elements.password_confirm.addEventListener('input', (event) => event.currentTarget.setCustomValidity(''));
