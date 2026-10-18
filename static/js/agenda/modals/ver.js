document.addEventListener('click', (event) => {
	const trigger = event.target.closest('[data-open-modal="modal-ver-evento"]');
	if (!trigger) return;
	const modal = document.querySelector('#modal-ver-evento');
	const fields = {
		title: 'eventTitle', type: 'eventType', date: 'eventDate', start: 'eventStart', end: 'eventEnd',
		client: 'eventClient', owner: 'eventOwner', state: 'eventState', place: 'eventPlace', notes: 'eventNotes',
	};
	Object.entries(fields).forEach(([name, key]) => {
		const field = modal.querySelector(`[data-view-field="${name}"]`);
		if (field) field.textContent = trigger.dataset[key] || 'No indicado';
	});
	const deleteTrigger = modal.querySelector('[data-delete-event-trigger]');
	if (deleteTrigger) {
		deleteTrigger.dataset.openModal = 'modal-eliminar-evento';
		deleteTrigger.dataset.deleteUrl = trigger.dataset.eventDeleteUrl || '';
		deleteTrigger.dataset.deleteTitle = trigger.dataset.eventTitle || '';
	}
});