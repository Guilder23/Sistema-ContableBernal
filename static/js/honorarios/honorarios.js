document.addEventListener('DOMContentLoaded', () => {
  const inputMensual = document.getElementById('tarifa-monto-mensual');
  const inputsExtras = document.querySelectorAll('.tarifa-extra-input');
  const displayTotal = document.getElementById('tarifa-total-sugerido');

  function recalcularTotalTarifa() {
    if (!displayTotal) return;
    let base = parseFloat(inputMensual?.value || 0) || 0;
    inputsExtras.forEach(inp => {
      base += parseFloat(inp.value || 0) || 0;
    });
    displayTotal.textContent = `Bs ${base.toFixed(2)}`;
  }

  if (inputMensual) {
    inputMensual.addEventListener('input', recalcularTotalTarifa);
    inputsExtras.forEach(inp => inp.addEventListener('input', recalcularTotalTarifa));
  }
});
