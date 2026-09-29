const menuToggle = document.querySelector('#menu-toggle');
const sidebarQuery = window.matchMedia('(max-width: 980px)');
const sidebarStorageKey = 'contable-sidebar-collapsed';

function isNarrowScreen() {
    return sidebarQuery.matches;
}

function syncMenuToggle() {
    if (!menuToggle) return;

    const isExpanded = isNarrowScreen()
        ? document.body.classList.contains('sidebar-open')
        : !document.body.classList.contains('sidebar-collapsed');
    const label = isNarrowScreen()
        ? (isExpanded ? 'Cerrar navegación' : 'Abrir navegación')
        : (isExpanded ? 'Contraer navegación' : 'Expandir navegación');

    menuToggle.setAttribute('aria-expanded', String(isExpanded));
    menuToggle.setAttribute('aria-label', label);
    menuToggle.title = label;
}

function setSidebarOpen(isOpen) {
    document.body.classList.toggle('sidebar-open', isOpen);
    syncMenuToggle();
}

try {
    if (localStorage.getItem(sidebarStorageKey) === 'true') {
        document.body.classList.add('sidebar-collapsed');
    }
} catch {}

syncMenuToggle();

menuToggle?.addEventListener('click', () => {
    if (isNarrowScreen()) {
        setSidebarOpen(!document.body.classList.contains('sidebar-open'));
        return;
    }

    const isCollapsed = document.body.classList.toggle('sidebar-collapsed');
    try {
        localStorage.setItem(sidebarStorageKey, String(isCollapsed));
    } catch {}
    syncMenuToggle();
});

document.addEventListener('contable:close-sidebar', () => setSidebarOpen(false));
sidebarQuery.addEventListener('change', () => {
    document.body.classList.remove('sidebar-open');
    syncMenuToggle();
});
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
