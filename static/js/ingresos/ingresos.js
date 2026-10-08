const moduleRoot = document.querySelector('.workspace--ingresos');
if (moduleRoot) moduleRoot.dataset.module = 'ingresos';

document.addEventListener('click', (event) => {
	const closeButton = event.target.closest('[data-close-income-modal]');
	if (closeButton) {
		closeButton.closest('[role="dialog"]')?.setAttribute('hidden', '');
		return;
	}
	const trigger = event.target.closest('[data-open-modal]');
	if (!trigger) return;
	const modal = document.getElementById(trigger.dataset.openModal);
	if (modal) modal.hidden = false;
});

document.addEventListener('keydown', (event) => {
	if (event.key === 'Escape') {
		document.querySelectorAll('.income-modal:not([hidden])').forEach((modal) => { modal.hidden = true; });
	}
});
