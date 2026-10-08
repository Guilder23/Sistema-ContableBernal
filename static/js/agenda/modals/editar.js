const editAgendaForm = document.querySelector('[data-agenda-edit-form]');

document.addEventListener('click', (event) => {
	const trigger = event.target.closest('[data-open-modal="modal-editar-evento"]');
	if (!trigger || !editAgendaForm) return;
	editAgendaForm.action = trigger.dataset.eventEditUrl;
	const mapping = {
		titulo: 'titulo', tipo: 'tipo', fecha: 'fecha', hora_inicio: 'horaInicio', hora_fin: 'horaFin',
		cliente: 'cliente', responsable: 'responsable', estado: 'estado', lugar: 'lugar', observaciones: 'observaciones',
	};
	Object.entries(mapping).forEach(([name, key]) => {
		const field = editAgendaForm.querySelector(`[data-edit-field="${name}"]`);
		if (field) field.value = trigger.dataset[name] || '';
	});
});