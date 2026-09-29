const menuToggle = document.querySelector('#menu-toggle');

function setSidebarOpen(isOpen) {
    document.body.classList.toggle('sidebar-open', isOpen);
    menuToggle?.setAttribute('aria-expanded', String(isOpen));
}

menuToggle?.addEventListener('click', () => {
    setSidebarOpen(menuToggle.getAttribute('aria-expanded') !== 'true');
});

document.addEventListener('contable:close-sidebar', () => setSidebarOpen(false));
document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') setSidebarOpen(false);
});
