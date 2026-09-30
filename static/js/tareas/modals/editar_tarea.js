const taskTable = document.querySelector('.workspace--tareas');
const taskModal = document.querySelector('#modal-editar-tarea');
const taskModalTriggerSelector = '[data-open-task-modal]';
let activeTaskTrigger = null;

function setTaskReturnUrl(form, url) {
  const returnField = form?.querySelector('input[name="volver"]');
  if (returnField) returnField.value = url;
}

function openTaskModal(trigger) {
  if (!taskModal) return;
  activeTaskTrigger = trigger;
  const data = trigger.dataset;
  const managerCanAssign = data.taskCanManage === 'true';

  taskModal.querySelector('#task-modal-title').textContent = data.taskTitle;
  taskModal.querySelector('[data-task-summary-client]').textContent = data.taskClient;
  taskModal.querySelector('[data-task-summary-period]').textContent = `${data.taskFrequency} · ${data.taskPeriod}`;
  taskModal.querySelector('[data-task-summary-due]').textContent = `Vence: ${data.taskDue}`;
  taskModal.querySelector('[data-task-summary-state]').textContent = `Estado actual: ${data.taskStateLabel}`;

  const assignmentForm = taskModal.querySelector('[data-task-assignment-form]');
  if (assignmentForm) {
    assignmentForm.action = data.assignUrl;
    assignmentForm.elements.responsable_id.value = data.taskResponsibleId;
    assignmentForm.elements.prioridad.value = data.taskPriority;
    assignmentForm.elements.observaciones.value = data.taskNotes;
    assignmentForm.hidden = !managerCanAssign;
    setTaskReturnUrl(assignmentForm, data.returnUrl);
  }

  const statusForm = taskModal.querySelector('[data-task-status-form]');
  statusForm.action = data.statusUrl;
  statusForm.elements.estado.value = data.taskState;
  setTaskReturnUrl(statusForm, data.returnUrl);

  const uploadForm = taskModal.querySelector('[data-task-upload-form]');
  uploadForm.action = data.uploadUrl;
  uploadForm.querySelector('[data-task-file]').value = '';
  uploadForm.hidden = !(managerCanAssign || data.taskResponsibleId);
  setTaskReturnUrl(uploadForm, data.returnUrl);

  const downloadLink = taskModal.querySelector('[data-task-download]');
  const noEvidence = taskModal.querySelector('[data-task-no-evidence]');
  const uploader = taskModal.querySelector('[data-task-evidence-uploader]');
  const deleteForm = taskModal.querySelector('[data-task-delete-form]');
  if (data.taskEvidence) {
    downloadLink.href = data.downloadUrl;
    downloadLink.textContent = `Descargar ${data.taskEvidence}`;
    downloadLink.hidden = false;
    noEvidence.hidden = true;
    uploader.textContent = data.taskEvidenceBy ? `Subida por ${data.taskEvidenceBy}` : '';
    uploader.hidden = !data.taskEvidenceBy;
    deleteForm.action = data.deleteEvidenceUrl;
    deleteForm.hidden = !(managerCanAssign || data.taskResponsibleId);
    setTaskReturnUrl(deleteForm, data.returnUrl);
  } else {
    downloadLink.removeAttribute('href');
    downloadLink.hidden = true;
    noEvidence.hidden = false;
    uploader.hidden = true;
    deleteForm.hidden = true;
  }

  taskModal.hidden = false;
  taskModal.querySelector('[data-modal-close-button]')?.focus();
}

function closeTaskModal() {
  if (!taskModal) return;
  taskModal.hidden = true;
  activeTaskTrigger?.focus();
}

taskTable?.addEventListener('click', (event) => {
  const trigger = event.target.closest(taskModalTriggerSelector);
  if (trigger) openTaskModal(trigger);
});

taskModal?.addEventListener('click', (event) => {
  if (event.target.closest('[data-close-task-modal]')) closeTaskModal();
});

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && taskModal && !taskModal.hidden) closeTaskModal();
});
