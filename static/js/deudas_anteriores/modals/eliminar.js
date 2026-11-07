document.querySelectorAll('[id^="deuda-modal-eliminar-"] form').forEach((formulario) => {
	formulario.addEventListener('submit', (evento) => {
		if (!window.confirm('Se eliminará la deuda y todo su historial de cobros. ¿Deseas continuar?')) {
			evento.preventDefault();
		}
	});
});
