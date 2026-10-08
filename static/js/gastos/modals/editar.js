const editExpenseForm = document.querySelector('[data-expense-edit-form]');

const updateEditSections = (form) => {
    if (!form) return;
    const movementType = form.querySelector('[data-edit-field="tipo"]')?.value || '';
    const category = form.querySelector('[data-edit-field="categoria"]');
    category?.querySelectorAll('[data-edit-categoria-tipo]').forEach((group) => {
        const hidden = Boolean(movementType) && group.dataset.editCategoriaTipo !== movementType;
        group.hidden = hidden;
        group.disabled = hidden;
        group.querySelectorAll('option').forEach((option) => {
            option.hidden = hidden;
            option.disabled = hidden;
        });
    });
    const selectedGroup = category?.selectedOptions[0]?.parentElement;
    if (selectedGroup?.matches('[data-edit-categoria-tipo]') && selectedGroup.disabled) category.value = '';
    const investment = movementType === 'inversion';
    const investmentSection = form.querySelector('[data-edit-investment-section]');
    if (investmentSection) {
        investmentSection.hidden = !investment;
        investmentSection.querySelectorAll('input, select').forEach((field) => {
            field.disabled = !investment;
            field.required = investment && field.name === 'vida_util_meses';
        });
    }
    const recoverable = form.querySelector('[data-edit-field="recuperable"]')?.checked;
    const recoveryFields = form.querySelector('[data-edit-recovery-fields]');
    if (recoveryFields) {
        recoveryFields.hidden = !recoverable;
        recoveryFields.querySelectorAll('input, select').forEach((field) => {
            field.disabled = !recoverable;
            field.required = recoverable && field.name === 'cliente';
        });
    }
};

document.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-open-modal="modal-editar"]');
    if (!trigger || !editExpenseForm) return;
    editExpenseForm.action = trigger.dataset.editUrl;
    editExpenseForm.querySelectorAll('[data-edit-categoria-tipo]').forEach((group) => {
        group.hidden = false;
        group.disabled = false;
        group.querySelectorAll('option').forEach((option) => { option.hidden = false; option.disabled = false; });
    });
    const fields = {
        concepto: 'concepto', tipo: 'tipo', categoria: 'categoria', periodicidad: 'periodicidad', monto: 'monto',
        fecha: 'fecha', proveedor: 'proveedor', responsable: 'responsable', comprobante: 'comprobante',
        estado_pago: 'estadoPago', estado_recuperacion: 'estadoRecuperacion', cliente: 'cliente',
        vida_util_meses: 'vidaUtil', estado_activo: 'estadoActivo', ubicacion: 'ubicacion', observaciones: 'observaciones',
    };
    Object.entries(fields).forEach(([name, key]) => {
        const field = editExpenseForm.querySelector(`[data-edit-field="${name}"]`);
        if (field) field.value = trigger.dataset[key] || '';
    });
    const recoverable = editExpenseForm.querySelector('[data-edit-field="recuperable"]');
    if (recoverable) recoverable.checked = trigger.dataset.recuperable === 'true';
    updateEditSections(editExpenseForm);
});

editExpenseForm?.addEventListener('change', (event) => {
    if (event.target.matches('[data-edit-field="tipo"], [data-edit-field="recuperable"]')) {
        updateEditSections(editExpenseForm);
    }
});

if (editExpenseForm) updateEditSections(editExpenseForm);