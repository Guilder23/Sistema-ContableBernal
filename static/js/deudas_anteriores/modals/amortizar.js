document.querySelectorAll('.deuda-form--amortizar').forEach((formulario) => {
	const monto = formulario.elements.monto;
	monto.addEventListener('input', () => monto.setCustomValidity(''));
	formulario.addEventListener('submit', (evento) => {
		if (Number(monto.value) > Number(monto.max)) {
			evento.preventDefault();
			monto.setCustomValidity('El abono supera el saldo pendiente.');
			monto.reportValidity();
		}
	});
});
