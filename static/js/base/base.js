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

document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') setMenuOpen(false);
});
