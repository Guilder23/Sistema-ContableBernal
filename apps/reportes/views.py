from apps.core.views import pagina_modulo


def index(request):
    return pagina_modulo(request, 'reportes')
