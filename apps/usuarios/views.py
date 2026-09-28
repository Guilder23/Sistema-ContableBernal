from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from apps.core.views import pagina_modulo


def login_view(request):
	if request.user.is_authenticated:
		return redirect('dashboard:index')

	siguiente = request.POST.get('next') or request.GET.get('next', '')
	error = ''
	if request.method == 'POST':
		usuario = request.POST.get('username', '').strip()
		contrasena = request.POST.get('password', '')
		cuenta = authenticate(request, username=usuario, password=contrasena)
		if cuenta is not None:
			login(request, cuenta)
			if siguiente and url_has_allowed_host_and_scheme(
				siguiente,
				allowed_hosts={request.get_host()},
				require_https=request.is_secure(),
			):
				return redirect(siguiente)
			return redirect('dashboard:index')
		error = 'Usuario o contraseña incorrectos.'

	return render(request, 'usuarios/login.html', {'error': error, 'siguiente': siguiente})


@login_required
def logout_view(request):
	if request.method == 'POST':
		logout(request)
	return redirect('usuarios:login')


@login_required
def index(request):
	return pagina_modulo(request, 'usuarios')
