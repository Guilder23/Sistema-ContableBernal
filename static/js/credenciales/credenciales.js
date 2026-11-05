const moduleRoot = document.querySelector('.workspace--credenciales');
if (moduleRoot) moduleRoot.dataset.module = 'credenciales';

let enviandoCredencial = false;
document.querySelectorAll('form[action*="/credenciales/crear/"], form#form-editar-credencial').forEach(form => {
  form.addEventListener('submit', () => {
    enviandoCredencial = true;
  });
});

window.addEventListener('pagehide', () => {
  if (enviandoCredencial || !navigator.sendBeacon) return;
  const csrf = document.querySelector('input[name="csrfmiddlewaretoken"]');
  if (!csrf) return;
  const datos = new FormData();
  datos.append('csrfmiddlewaretoken', csrf.value);
  navigator.sendBeacon('/credenciales/salir/', datos);
});
