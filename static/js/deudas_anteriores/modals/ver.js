document.querySelectorAll('[id^="deuda-modal-ver-"]').forEach((modal) => {
	modal.addEventListener('close', () => modal.scrollTo(0, 0));
});
