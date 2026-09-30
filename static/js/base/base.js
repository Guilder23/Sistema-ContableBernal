const pageError = document.querySelector('[role="alert"], .flash--error');

if (pageError) {
    pageError.setAttribute('tabindex', '-1');
    pageError.focus({ preventScroll: true });
}
