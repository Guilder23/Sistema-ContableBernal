document.addEventListener('DOMContentLoaded', () => {
  // Manejo de pestañas
  const tabButtons = document.querySelectorAll('.client-tab-btn');
  const tabPanes = document.querySelectorAll('.client-tab-pane');

  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      tabButtons.forEach(b => b.classList.remove('active'));
      tabPanes.forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const targetId = btn.dataset.tab;
      const targetPane = document.getElementById(targetId);
      if (targetPane) targetPane.classList.add('active');
    });
  });

  // Selector de sistema personalizado en creación
  const selectSistema = document.getElementById('cred-select-sistema');
  const campoPersonalizado = document.getElementById('cred-campo-personalizado');
  if (selectSistema && campoPersonalizado) {
    selectSistema.addEventListener('change', () => {
      campoPersonalizado.style.display = selectSistema.value === 'otro' ? 'block' : 'none';
    });
  }

  // Selector de sistema personalizado en edición
  const editSelectSistema = document.getElementById('edit-cred-select-sistema');
  const editCampoPersonalizado = document.getElementById('edit-cred-campo-personalizado');
  if (editSelectSistema && editCampoPersonalizado) {
    editSelectSistema.addEventListener('change', () => {
      editCampoPersonalizado.style.display = editSelectSistema.value === 'otro' ? 'block' : 'none';
    });
  }

  // Revelar / Ocultar contraseña en listado de credenciales
  document.querySelectorAll('.btn-mini-reveal').forEach(btn => {
    btn.addEventListener('click', async () => {
      const credId = btn.dataset.credId;
      const passBox = document.getElementById(`cred-pass-${credId}`);
      if (!passBox) return;

      if (passBox.dataset.revealed === 'true') {
        passBox.textContent = '••••••••••••';
        passBox.dataset.revealed = 'false';
        btn.title = 'Mostrar contraseña';
      } else {
        try {
          const resp = await fetch(`/credenciales/${credId}/revelar/`);
          if (resp.ok) {
            const data = await resp.json();
            passBox.textContent = data.password;
            passBox.dataset.revealed = 'true';
            btn.title = 'Ocultar contraseña';
          }
        } catch (e) {
          console.error('Error al revelar contraseña:', e);
        }
      }
    });
  });

  // Copiar contraseña o usuario
  document.querySelectorAll('.btn-mini-copy').forEach(btn => {
    btn.addEventListener('click', () => {
      const copyVal = btn.dataset.copyValue;
      if (copyVal) {
        navigator.clipboard.writeText(copyVal).then(() => {
          const originalTitle = btn.title;
          btn.title = '¡Copiado!';
          setTimeout(() => btn.title = originalTitle, 2000);
        });
      }
    });
  });

  // Toggle de visibilidad de password en inputs
  document.querySelectorAll('.btn-toggle-eye').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = btn.previousElementSibling;
      if (input && input.tagName === 'INPUT') {
        input.type = input.type === 'password' ? 'text' : 'password';
      }
    });
  });

  // Cargar datos en Modal de Edición de Credencial
  document.querySelectorAll('[data-open-modal="modal-editar-credencial"]').forEach(btn => {
    btn.addEventListener('click', () => {
      const form = document.getElementById('form-editar-credencial');
      if (!form) return;
      form.action = btn.dataset.editUrl;
      const sistemaSelect = document.getElementById('edit-cred-select-sistema');
      if (sistemaSelect) {
        sistemaSelect.value = btn.dataset.sistema;
        if (editCampoPersonalizado) {
          editCampoPersonalizado.style.display = btn.dataset.sistema === 'otro' ? 'block' : 'none';
        }
      }
      const sistemaPers = document.getElementById('edit-cred-sistema-pers');
      if (sistemaPers) sistemaPers.value = btn.dataset.sistemaPers || '';
      const usuarioInput = document.getElementById('edit-cred-usuario');
      if (usuarioInput) usuarioInput.value = btn.dataset.usuario || '';
      const urlInput = document.getElementById('edit-cred-url');
      if (urlInput) urlInput.value = btn.dataset.url || '';
      const extraInput = document.getElementById('edit-cred-codigo-extra');
      if (extraInput) extraInput.value = btn.dataset.codigoExtra || '';
      const obsInput = document.getElementById('edit-cred-observaciones');
      if (obsInput) obsInput.value = btn.dataset.observaciones || '';
    });
  });

  // Cargar datos en Modal de Eliminación de Credencial
  document.querySelectorAll('[data-open-modal="modal-eliminar-credencial"]').forEach(btn => {
    btn.addEventListener('click', () => {
      const form = document.getElementById('form-eliminar-credencial');
      if (!form) return;
      form.action = btn.dataset.deleteUrl;
      const label = document.getElementById('delete-cred-sistema');
      if (label) label.textContent = btn.dataset.sistemaNombre || 'el sistema';
    });
  });
});
