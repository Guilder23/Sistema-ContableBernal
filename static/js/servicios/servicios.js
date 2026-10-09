const moduleRoot = document.querySelector('.workspace--servicios');
if (moduleRoot) moduleRoot.dataset.module = 'servicios';

let lastServiceModalTrigger = null;

document.addEventListener('click', (event) => {
	const closeButton = event.target.closest('[data-close-service-modal]');
	if (closeButton) {
		const modal = closeButton.closest('[role="dialog"]');
		if (modal) modal.hidden = true;
		const returnModal = modal?.dataset.returnModal ? document.getElementById(modal.dataset.returnModal) : null;
		if (returnModal) {
			returnModal.hidden = false;
			delete modal.dataset.returnModal;
		}
		lastServiceModalTrigger?.focus();
		return;
	}
	const trigger = event.target.closest('[data-open-modal]');
	if (!trigger) return;
	const modal = document.getElementById(trigger.dataset.openModal);
	if (!modal) return;
	const currentModal = document.querySelector('.service-modal:not([hidden])');
	if (currentModal && currentModal !== modal) {
		modal.dataset.returnModal = currentModal.id;
		currentModal.hidden = true;
	}
	lastServiceModalTrigger = trigger;
	modal.hidden = false;
	modal.querySelector('.service-modal__close')?.focus();
});

document.addEventListener('keydown', (event) => {
	if (event.key !== 'Escape') return;
	const modal = document.querySelector('.service-modal:not([hidden])');
	if (!modal) return;
	modal.hidden = true;
	const returnModal = modal.dataset.returnModal ? document.getElementById(modal.dataset.returnModal) : null;
	if (returnModal) {
		returnModal.hidden = false;
		delete modal.dataset.returnModal;
	}
	lastServiceModalTrigger?.focus();
});
