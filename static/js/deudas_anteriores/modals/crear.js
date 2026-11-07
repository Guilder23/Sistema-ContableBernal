const modalCrear = document.getElementById('deuda-modal-crear');
if (modalCrear) modalCrear.querySelectorAll('input[type="date"]').forEach((fecha) => {
	fecha.max = modalCrear.dataset.maxDate;
});
