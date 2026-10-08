const createAgendaForm = document.querySelector('[data-agenda-create-form]');

document.addEventListener('click', (event) => {
	const trigger = event.target.closest('[data-open-modal="modal-crear-evento"]');
	if (!trigger || !createAgendaForm) return;
	createAgendaForm.reset();
});