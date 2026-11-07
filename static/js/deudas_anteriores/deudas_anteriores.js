document.querySelectorAll('[data-open-modal]').forEach((boton) => {
	boton.addEventListener('click', () => {
		const modal = document.getElementById(boton.dataset.openModal);
		if (modal instanceof HTMLDialogElement) modal.showModal();
	});
});

document.querySelectorAll('[data-close-modal]').forEach((boton) => {
	boton.addEventListener('click', () => boton.closest('dialog')?.close());
});

document.querySelectorAll('.deuda-modal').forEach((modal) => {
	modal.addEventListener('click', (evento) => {
		if (evento.target === modal) modal.close();
	});
});

const modalInicial = document.querySelector('[data-deuda-modal]')?.dataset.deudaModal;
if (modalInicial) {
	const modal = document.getElementById(`deuda-modal-${modalInicial}`);
	if (modal instanceof HTMLDialogElement) modal.showModal();
}

document.querySelectorAll('.deuda-filtros select').forEach((campo) => {
	campo.addEventListener('keydown', (evento) => {
		if (evento.key === 'Enter') {
			evento.preventDefault();
			campo.form.requestSubmit();
		}
	});
});
