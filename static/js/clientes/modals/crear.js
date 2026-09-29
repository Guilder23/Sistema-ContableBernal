const clientCreateForm = document.querySelector('#modal-crear form');

clientCreateForm?.elements.estado?.addEventListener('change', (event) => {
    event.currentTarget.value = event.currentTarget.checked ? 'activo' : 'inactivo';
});
