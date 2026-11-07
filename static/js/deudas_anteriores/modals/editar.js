document.querySelectorAll('[id^="deuda-modal-editar-"]').forEach((modal) => {
	modal.querySelectorAll('input[type="date"]').forEach((fecha) => {
		fecha.max = modal.dataset.maxDate;
	});
});
