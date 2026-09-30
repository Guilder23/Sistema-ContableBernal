const moduleRoot = document.querySelector('.workspace--tareas');
const evidenceForms = moduleRoot?.querySelectorAll('.task-evidence-form');

evidenceForms?.forEach((form) => {
	const input = form.querySelector('input[type="file"]');
	const label = form.querySelector('label span');
	const originalLabel = label?.textContent;

	input?.addEventListener('change', () => {
		if (label) label.textContent = input.files?.[0]?.name || originalLabel;
	});
});

moduleRoot?.querySelectorAll('form[action*="evidencia/eliminar/"]').forEach((form) => {
	form.addEventListener('submit', (event) => {
		if (!window.confirm('¿Quitar la evidencia de esta tarea?')) event.preventDefault();
	});
});
