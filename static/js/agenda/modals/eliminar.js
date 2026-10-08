const deleteAgendaForm = document.querySelector('[data-agenda-delete-form]');

document.addEventListener('click', (event) => {
	const trigger = event.target.closest('[data-open-modal="modal-eliminar-evento"]');
	if (!trigger || !deleteAgendaForm) return;
	deleteAgendaForm.action = trigger.dataset.deleteUrl;
	const title = document.querySelector('#modal-eliminar-evento [data-delete-event-title]');
	if (title) title.textContent = trigger.dataset.deleteTitle || 'este evento';
});