from apps.historial.models import EntradaHistorial


def registrar_historial(
	cliente,
	usuario,
	tipo_accion,
	titulo,
	descripcion='',
	seccion=EntradaHistorial.Seccion.OTRO,
	referencia='',
):
	try:
		return EntradaHistorial.objects.create(
			cliente=cliente,
			usuario=usuario if getattr(usuario, 'is_authenticated', False) else None,
			tipo_accion=tipo_accion,
			seccion=seccion,
			referencia=(referencia or getattr(cliente, 'nombre', ''))[:180],
			titulo=titulo,
			descripcion=descripcion,
		)
	except Exception:
		return None
