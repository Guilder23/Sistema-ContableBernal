const createServiceForm = document.querySelector('[data-create-service-form]');
const clientChoice = createServiceForm?.querySelector('[data-client-choice]');
const newClientFields = createServiceForm?.querySelector('[data-new-client-fields]');
const initialPayment = createServiceForm?.querySelector('[data-initial-payment]');
const initialPaymentMethod = createServiceForm?.querySelector('[data-initial-payment-method]');
const servicePrice = createServiceForm?.querySelector('[name="monto_total"]');

const updateCreateServiceFields = () => {
    const creatingClient = clientChoice?.value === 'nuevo';
    if (newClientFields) newClientFields.hidden = !creatingClient;
    newClientFields?.querySelectorAll('input').forEach((field) => {
        field.required = creatingClient && field.hasAttribute('data-new-client-required');
        field.disabled = !creatingClient;
    });
    const hasInitialPayment = Number(initialPayment?.value || 0) > 0;
    if (initialPaymentMethod) initialPaymentMethod.hidden = !hasInitialPayment;
    initialPaymentMethod?.querySelector('select')?.toggleAttribute('required', hasInitialPayment);
    if (initialPayment && servicePrice?.value) initialPayment.max = servicePrice.value;
};

clientChoice?.addEventListener('change', updateCreateServiceFields);
initialPayment?.addEventListener('input', updateCreateServiceFields);
servicePrice?.addEventListener('input', updateCreateServiceFields);
createServiceForm?.addEventListener('reset', () => requestAnimationFrame(updateCreateServiceFields));
document.addEventListener('click', (event) => {
    if (event.target.closest('[data-open-modal="modal-crear-servicio"]')) createServiceForm?.reset();
});
updateCreateServiceFields();