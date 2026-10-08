const moduleRoot = document.querySelector('.workspace--agenda');
if (moduleRoot) moduleRoot.dataset.module = 'agenda';

document.addEventListener('click', (event) => {
	const closeButton = event.target.closest('[data-close-agenda-modal]');
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
		document.querySelectorAll('[role="dialog"]:not([hidden])').forEach((modal) => { modal.hidden = true; });
	}
});
