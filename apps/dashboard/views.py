from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone


@login_required
def index(request):
	return render(request, 'dashboard/dashboard.html', {'fecha_actual': timezone.localdate()})
