from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


MODULE_PAGES = {
	'clientes': ('Clientes', 'Ficha general, actividad económica y configuración tributaria de cada cliente.'),
	'credenciales': ('Credenciales', 'Accesos de clientes a Impuestos, Gestora, cajas y otros portales.'),
	'obligaciones': ('Obligaciones', 'Calendario mensual, trimestral y anual de obligaciones contables.'),
	'tareas': ('Tareas', 'Asignaciones, vencimientos, responsables y evidencias de trabajo.'),
	'honorarios': ('Honorarios', 'Tarifas, cargos recurrentes, extras y control de pagos.'),
	'ingresos': ('Ingresos', 'Honorarios cobrados, trabajos extraordinarios y otros ingresos.'),
	'gastos': ('Gastos', 'Gastos generales y montos adelantados por cuenta de clientes.'),
	'servicios': ('Servicios y trámites', 'Servicios recurrentes, cajas, gestiones y trámites extraordinarios.'),
	'requerimientos': ('Requerimientos', 'Solicitudes de clientes, responsables, prioridades y seguimiento.'),
	'agenda': ('Agenda', 'Citas, vencimientos y próximas actividades del estudio.'),
	'documentos': ('Documentos', 'Archivos y respaldos asociados a clientes y trabajos.'),
	'historial': ('Historial', 'Registro de cambios y acontecimientos por cliente.'),
	'notificaciones': ('Notificaciones', 'Avisos de tareas, vencimientos y actividad del equipo.'),
	'reportes': ('Reportes', 'Consultas de ingresos, gastos, deudas y cumplimiento.'),
	'configuracion': ('Administración', 'Parámetros, actividades, reglas, obligaciones y tarifas.'),
	'usuarios': ('Usuarios', 'Cuentas del equipo y administración de acceso al sistema.'),
}


def inicio(request):
	return redirect('dashboard:index')


@login_required
def pagina_modulo(request, modulo):
	titulo, descripcion = MODULE_PAGES[modulo]
	return render(
		request,
		f'{modulo}/{modulo}.html',
		{'titulo_modulo': titulo, 'descripcion_modulo': descripcion, 'modulo_activo': modulo},
	)
