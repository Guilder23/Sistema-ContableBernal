const moduleRoot = document.querySelector('.workspace--usuarios');
if (moduleRoot) moduleRoot.dataset.module = 'usuarios';

const userFilterForm = document.querySelector('.js-live-filter');
const userSearchInput = userFilterForm?.querySelector('[data-live-search]');
let userSearchTimer;

userSearchInput?.addEventListener('input', () => {
	window.clearTimeout(userSearchTimer);
	userSearchTimer = window.setTimeout(() => userFilterForm.requestSubmit(), 280);
});

userFilterForm?.querySelectorAll('[data-live-filter]').forEach((filter) => {
	filter.addEventListener('change', () => userFilterForm.requestSubmit());
});

let modalAnterior = null;

function abrirModal(modal, boton) {
	if (!modal) return;
	modalAnterior = boton;
	modal.hidden = false;
	document.body.classList.add('modal-open');
	modal.querySelector('input:not([type="hidden"]), select, button')?.focus();
}

function cerrarModal(modal) {
	if (!modal) return;
	modal.hidden = true;
	document.body.classList.remove('modal-open');
	modalAnterior?.focus();
}

document.addEventListener('click', (event) => {
	const botonAbrir = event.target.closest('[data-open-modal]');
	if (botonAbrir) {
		const modal = document.getElementById(botonAbrir.dataset.openModal);
		if (modal?.hidden && ['modal-crear', 'modal-editar'].includes(modal.id)) modal.querySelector('form')?.reset();
		abrirModal(modal, botonAbrir);
	}
	const botonCerrar = event.target.closest('[data-close-modal]');
	if (botonCerrar) cerrarModal(botonCerrar.closest('.user-modal'));
});

document.addEventListener('keydown', (event) => {
	if (event.key === 'Escape') {
		const modalAbierto = document.querySelector('.user-modal:not([hidden])');
		if (modalAbierto) cerrarModal(modalAbierto);
	}
	const modal = event.target.closest('.user-modal:not([hidden])');
	if (event.key === 'Tab' && modal) {
		const controles = [...modal.querySelectorAll('a[href], button:not(:disabled), input:not(:disabled), select:not(:disabled)')];
		const primero = controles[0];
		const ultimo = controles[controles.length - 1];
		if (event.shiftKey && document.activeElement === primero) { event.preventDefault(); ultimo?.focus(); }
		else if (!event.shiftKey && document.activeElement === ultimo) { event.preventDefault(); primero?.focus(); }
	}
});

const modalInicial = document.querySelector('.user-modal:not([hidden])');
if (modalInicial) {
	document.body.classList.add('modal-open');
	modalInicial.querySelector('input:not([type="hidden"]), select, button')?.focus();
}
