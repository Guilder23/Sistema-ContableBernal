const servicePaymentForm = document.querySelector('[data-register-payment-form]');
const servicePaymentAmount = servicePaymentForm?.querySelector('[data-payment-amount]');

document.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-pay-url]');
    if (!trigger || !servicePaymentForm) return;
    servicePaymentForm.action = trigger.dataset.payUrl;
    servicePaymentForm.reset();
    const balance = Number(trigger.dataset.paySaldo || 0);
    servicePaymentAmount.max = balance.toFixed(2);
    const balanceLabel = document.querySelector('[data-payment-balance]');
    const clientLabel = document.querySelector('[data-payment-client]');
    const conceptLabel = document.querySelector('[data-payment-concept]');
    if (balanceLabel) balanceLabel.textContent = balance.toFixed(2);
    if (clientLabel) clientLabel.textContent = trigger.dataset.payCliente || '';
    if (conceptLabel) conceptLabel.textContent = trigger.dataset.payConcepto || '';
});