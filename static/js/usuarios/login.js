const passwordInput = document.querySelector('#password');
const passwordToggle = document.querySelector('#toggle-password');
const currentYear = document.querySelector('[data-current-year]');
const loginForm = document.querySelector('#login-form');
const usernameInput = document.querySelector('#username');

if (currentYear) currentYear.textContent = String(new Date().getFullYear());

passwordToggle?.addEventListener('click', () => {
    const isVisible = passwordInput.type === 'text';
    passwordInput.type = isVisible ? 'password' : 'text';
    passwordToggle.setAttribute('aria-pressed', String(!isVisible));
    passwordToggle.setAttribute('aria-label', isVisible ? 'Mostrar contraseña' : 'Ocultar contraseña');
    
    const eyeOpen = passwordToggle.querySelector('.eye-open');
    const eyeClosed = passwordToggle.querySelector('.eye-closed');
    if (eyeOpen && eyeClosed) {
        eyeOpen.style.display = isVisible ? 'block' : 'none';
        eyeClosed.style.display = isVisible ? 'none' : 'block';
    }
});

loginForm?.addEventListener('submit', (event) => {
    for (const field of [usernameInput, passwordInput]) {
        const missing = !field.value.trim();
        field.setCustomValidity(missing ? 'Completa este campo para continuar.' : '');
        field.setAttribute('aria-invalid', String(missing));
    }
    const firstInvalid = loginForm.querySelector('[aria-invalid="true"]');
    if (firstInvalid) {
        event.preventDefault();
        firstInvalid.focus();
        firstInvalid.reportValidity();
    }
});

loginForm?.querySelectorAll('input').forEach((field) => {
    field.addEventListener('input', () => {
        field.setCustomValidity('');
        field.setAttribute('aria-invalid', 'false');
    });
});
