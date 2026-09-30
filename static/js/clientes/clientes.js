const moduleRoot = document.querySelector('.workspace--clientes');
if (moduleRoot) moduleRoot.dataset.module = 'clientes';

const clientFilterForm = document.querySelector('.js-live-filter');
const clientSearchInput = clientFilterForm?.querySelector('[data-live-search]');
let clientSearchTimer;

clientSearchInput?.addEventListener('input', () => {
	window.clearTimeout(clientSearchTimer);
	clientSearchTimer = window.setTimeout(() => clientFilterForm.requestSubmit(), 280);
});

clientFilterForm?.querySelectorAll('[data-live-filter]').forEach((filter) => {
	filter.addEventListener('change', () => clientFilterForm.requestSubmit());
});

let previousClientTrigger = null;

function closeClientModal(modal) {
	if (!modal) return;
	modal.hidden = true;
	document.body.classList.remove('modal-open');
	previousClientTrigger?.focus();
}

document.addEventListener('click', (event) => {
	const trigger = event.target.closest('[data-open-modal]');
	if (trigger) {
		const modal = document.getElementById(trigger.dataset.openModal);
		if (modal?.hidden && ['modal-crear', 'modal-editar'].includes(modal.id)) modal.querySelector('form')?.reset();
		if (modal) {
			previousClientTrigger = trigger;
			modal.hidden = false;
			document.body.classList.add('modal-open');
			modal.querySelector('input:not([type="hidden"]), select, button')?.focus();
		}
	}
	const closer = event.target.closest('[data-close-modal]');
	if (closer) closeClientModal(closer.closest('.client-modal'));
});

document.addEventListener('keydown', (event) => {
	const modal = document.querySelector('.client-modal:not([hidden])');
	if (!modal) return;
	if (event.key === 'Escape') closeClientModal(modal);
	if (event.key === 'Tab') {
		const controls = [...modal.querySelectorAll('a[href], button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled)')];
		const first = controls[0];
		const last = controls[controls.length - 1];
		if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
		else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
	}
});

const initiallyOpenModal = document.querySelector('.client-modal:not([hidden])');
if (initiallyOpenModal) {
	document.body.classList.add('modal-open');
	initiallyOpenModal.querySelector('input:not([type="hidden"]), select, button')?.focus();
}
