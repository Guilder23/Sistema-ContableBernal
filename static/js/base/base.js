const menuToggle = document.querySelector('#menu-toggle');
const menuBackdrop = document.querySelector('.menu-backdrop');

function setMenuOpen(isOpen) {
    document.body.classList.toggle('sidebar-open', isOpen);
    menuToggle?.setAttribute('aria-expanded', String(isOpen));
}

menuToggle?.addEventListener('click', () => {
    setMenuOpen(menuToggle.getAttribute('aria-expanded') !== 'true');
});

menuBackdrop?.addEventListener('click', () => setMenuOpen(false));

document.querySelectorAll('.side-nav .nav-link').forEach((link) => {
    const currentPath = window.location.pathname.replace(/\/$/, '') || '/';
    const linkPath = new URL(link.href).pathname.replace(/\/$/, '') || '/';
    if (currentPath === linkPath) link.setAttribute('aria-current', 'page');
    link.addEventListener('click', () => setMenuOpen(false));
});

document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') setMenuOpen(false);
});
