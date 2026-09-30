const settingsModal = document.querySelector('#modal-obligation-settings');
const settingsTrigger = document.querySelector('[data-open-settings]');

settingsTrigger?.addEventListener('click', () => {
  settingsModal.hidden = false;
  settingsModal.querySelector('[data-settings-tab="catalogo"]')?.focus();
});

settingsModal?.addEventListener('click', (event) => {
  if (event.target.closest('[data-close-settings]')) {
    settingsModal.hidden = true;
    settingsTrigger?.focus();
    return;
  }

  const tab = event.target.closest('[data-settings-tab]');
  if (!tab) return;

  settingsModal.querySelectorAll('[data-settings-tab]').forEach((item) => {
    const selected = item === tab;
    item.setAttribute('aria-selected', String(selected));
    item.tabIndex = selected ? 0 : -1;
  });
  settingsModal.querySelectorAll('[data-settings-panel]').forEach((panel) => {
    panel.hidden = panel.dataset.settingsPanel !== tab.dataset.settingsTab;
  });
});

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && settingsModal && !settingsModal.hidden) {
    settingsModal.hidden = true;
    settingsTrigger?.focus();
  }
});
