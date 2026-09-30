from apps.historial.models import EntradaHistorial


def registrar_historial(cliente, usuario, tipo_accion, titulo, descripcion=''):
	try:
		return EntradaHistorial.objects.create(
			cliente=cliente,
			usuario=usuario if getattr(usuario, 'is_authenticated', False) else None,
			tipo_accion=tipo_accion,
			titulo=titulo,
			descripcion=descripcion,
		)
	except Exception:
		return None
