const menuToggle = document.querySelector('#menu-toggle');

function setSidebarOpen(isOpen) {
    document.body.classList.toggle('sidebar-open', isOpen);
    menuToggle?.setAttribute('aria-expanded', String(isOpen));
}

menuToggle?.addEventListener('click', () => {
    setSidebarOpen(menuToggle.getAttribute('aria-expanded') !== 'true');
});

document.addEventListener('contable:close-sidebar', () => setSidebarOpen(false));
document.addEventListener('click', (event) => {
    if (event.target.closest('.navbar-menu > summary')) return;
    document.querySelectorAll('.navbar-menu[open]').forEach((menu) => {
        if (!menu.contains(event.target)) menu.open = false;
    });
});

document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
        setSidebarOpen(false);
        document.querySelectorAll('.navbar-menu[open]').forEach((menu) => { menu.open = false; });
    }
});
