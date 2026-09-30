document.addEventListener("click", (event) => {
  const trigger = event.target.closest('[data-open-modal="modal-ver"]');
  if (!trigger) return;
  const modal = document.querySelector("#modal-ver");
  if (!modal) return;
  const row = trigger.closest("tr");
  modal.querySelector('[data-view-field="name"]').textContent =
    trigger.dataset.userName || trigger.dataset.userUsername || "Usuario";
  modal.querySelector('[data-view-field="username"]').textContent =
    trigger.dataset.userUsername || "";
  modal.querySelector('[data-view-field="email"]').textContent =
    trigger.dataset.userEmail || "No registrado";
  modal.querySelector('[data-view-field="role"]').textContent =
    trigger.dataset.userRole || "";
  modal.querySelector('[data-view-field="status"]').textContent =
    trigger.dataset.userStatus || "";
  modal.querySelector('[data-view-field="created-at"]').textContent =
    row?.dataset.userCreatedAt || "Sin registro";
  modal.querySelector('[data-view-field="created-by"]').textContent =
    row?.dataset.userCreatedBy || "Sin registro";
});
