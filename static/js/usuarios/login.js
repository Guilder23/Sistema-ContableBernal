const passwordInput = document.querySelector('#password');
const passwordToggle = document.querySelector('#toggle-password');
const currentYear = document.querySelector('[data-current-year]');

if (currentYear) currentYear.textContent = String(new Date().getFullYear());

passwordToggle?.addEventListener('click', () => {
    const isVisible = passwordInput.type === 'text';
    passwordInput.type = isVisible ? 'password' : 'text';
    passwordToggle.textContent = isVisible ? 'Mostrar' : 'Ocultar';
    passwordToggle.setAttribute('aria-pressed', String(!isVisible));
    passwordToggle.setAttribute('aria-label', isVisible ? 'Mostrar contraseña' : 'Ocultar contraseña');
});
