const sidebar = document.querySelector('#sidebar');
const sidebarBackdrop = document.querySelector('.sidebar-backdrop');
const currentPath = window.location.pathname.replace(/\/$/, '') || '/';

sidebar?.querySelectorAll('.nav-link').forEach((link) => {
    const linkPath = new URL(link.href).pathname.replace(/\/$/, '') || '/';
    if (linkPath === currentPath) link.setAttribute('aria-current', 'page');
    link.addEventListener('click', () => document.dispatchEvent(new CustomEvent('contable:close-sidebar')));
});

sidebarBackdrop?.addEventListener('click', () => document.dispatchEvent(new CustomEvent('contable:close-sidebar')));
