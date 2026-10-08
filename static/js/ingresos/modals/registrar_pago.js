const paymentIncomeForm = document.querySelector('[data-income-payment-form]');

document.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-open-modal="modal-registrar-pago"]');
    if (!trigger || !paymentIncomeForm) return;
    paymentIncomeForm.reset();
    paymentIncomeForm.querySelector('[data-payment-field="cobro_id"]').value = trigger.dataset.cobroId;
    const amount = paymentIncomeForm.querySelector('[data-payment-field="monto"]');
    amount.max = trigger.dataset.saldo;
    paymentIncomeForm.querySelector('[data-payment-client]').textContent = trigger.dataset.cliente;
    paymentIncomeForm.querySelector('[data-payment-concept]').textContent = trigger.dataset.concepto;
    paymentIncomeForm.querySelector('[data-payment-balance]').textContent = `Bs ${trigger.dataset.saldo}`;
});