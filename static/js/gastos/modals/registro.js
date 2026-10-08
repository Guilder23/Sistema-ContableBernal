const createExpenseForm = document.querySelector('[data-create-expense-form]');

const updateCreateSections = (form) => {
    if (!form) return;
    const movementType = form.querySelector('[data-expense-field="tipo"]')?.value || '';
    const category = form.querySelector('[data-expense-field="categoria"]');
    category?.querySelectorAll('[data-categoria-tipo]').forEach((group) => {
        const hidden = Boolean(movementType) && group.dataset.categoriaTipo !== movementType;
        group.hidden = hidden;
        group.disabled = hidden;
        group.querySelectorAll('option').forEach((option) => {
            option.hidden = hidden;
            option.disabled = hidden;
        });
    });
    const selectedGroup = category?.selectedOptions[0]?.parentElement;
    if (selectedGroup?.matches('[data-categoria-tipo]') && selectedGroup.disabled) category.value = '';
    const investment = movementType === 'inversion';
    const investmentSection = form.querySelector('[data-investment-section]');
    if (investmentSection) {
        investmentSection.hidden = !investment;
        investmentSection.querySelectorAll('input, select').forEach((field) => {
            field.disabled = !investment;
            field.required = investment && field.name === 'vida_util_meses';
        });
    }
    const recoverable = form.querySelector('[data-expense-field="recuperable"]')?.checked;
    const recoveryFields = form.querySelector('[data-recovery-fields]');
    if (recoveryFields) {
        recoveryFields.hidden = !recoverable;
        recoveryFields.querySelectorAll('input, select').forEach((field) => {
            field.disabled = !recoverable;
            field.required = recoverable && field.name === 'cliente';
        });
    }
};

document.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-open-modal="modal-registro"]');
    if (!trigger || !createExpenseForm) return;
    createExpenseForm.reset();
    createExpenseForm.action = createExpenseForm.dataset.createUrl;
    updateCreateSections(createExpenseForm);
});

createExpenseForm?.addEventListener('change', (event) => {
    if (event.target.matches('[data-expense-field="tipo"], [data-expense-field="recuperable"]')) {
        updateCreateSections(createExpenseForm);
    }
});

if (createExpenseForm) updateCreateSections(createExpenseForm);