document.addEventListener('DOMContentLoaded', () => {
  // Modal de registro de pago
  document.querySelectorAll('[data-open-modal="modal-registrar-pago"]').forEach(btn => {
    btn.addEventListener('click', () => {
      const cobroId = btn.dataset.cobroId;
      const clienteNombre = btn.dataset.clienteNombre || '—';
      const concepto = btn.dataset.concepto || '—';
      const saldo = btn.dataset.saldo || '0.00';

      const inputCobroId = document.getElementById('pago-cobro-id');
      const labelCliente = document.getElementById('pago-cliente-nombre');
      const labelConcepto = document.getElementById('pago-concepto');
      const labelSaldo = document.getElementById('pago-saldo-pendiente');
      const inputMonto = document.getElementById('pago-monto');

      if (inputCobroId) inputCobroId.value = cobroId;
      if (labelCliente) labelCliente.textContent = clienteNombre;
      if (labelConcepto) labelConcepto.textContent = concepto;
      if (labelSaldo) labelSaldo.textContent = `Bs ${saldo}`;
      if (inputMonto) inputMonto.value = saldo;
    });
  });

  // Cálculo en vivo de tarifa sugerida en ficha de cliente
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
