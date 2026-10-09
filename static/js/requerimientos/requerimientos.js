const moduleRoot = document.querySelector('.workspace--requerimientos');
if (moduleRoot) moduleRoot.dataset.module = 'requerimientos';

let lastModalTrigger = null;

document.addEventListener('click', (event) => {
	const closeButton = event.target.closest('[data-close-modal]');
	if (closeButton) {
		const dialog = closeButton.closest('[role="dialog"]');
		if (dialog) dialog.hidden = true;
		lastModalTrigger?.focus();
		return;
	}
	const trigger = event.target.closest('[data-open-modal]');
	if (!trigger) return;
	const dialog = document.getElementById(trigger.dataset.openModal);
	if (!dialog) return;
	lastModalTrigger = trigger;
	dialog.hidden = false;
	dialog.querySelector('.requirement-modal__close')?.focus();
});

document.addEventListener('keydown', (event) => {
	if (event.key !== 'Escape') return;
	const openDialog = document.querySelector('.requirement-modal:not([hidden])');
	if (!openDialog) return;
	openDialog.hidden = true;
	lastModalTrigger?.focus();
});
