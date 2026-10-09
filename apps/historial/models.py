from django.conf import settings
from django.db import models


class EntradaHistorial(models.Model):
	class Seccion(models.TextChoices):
		PANEL = 'dashboard', 'Panel de gestión'
		CLIENTES = 'clientes', 'Clientes'
		CREDENCIALES = 'credenciales', 'Credenciales'
		OBLIGACIONES = 'obligaciones', 'Obligaciones'
		TAREAS = 'tareas', 'Tareas'
		DOCUMENTOS = 'documentos', 'Documentos'
		SERVICIOS = 'servicios', 'Servicios y trámites'
		REQUERIMIENTOS = 'requerimientos', 'Requerimientos'
		AGENDA = 'agenda', 'Agenda'
		GASTOS = 'gastos', 'Gastos'
		HONORARIOS = 'honorarios', 'Honorarios'
		INGRESOS = 'ingresos', 'Ingresos'
		USUARIOS = 'usuarios', 'Usuarios'
		NOTIFICACIONES = 'notificaciones', 'Notificaciones'
		CONFIGURACION = 'configuracion', 'Administración'
		REPORTES = 'reportes', 'Reportes'
		HISTORIAL = 'historial', 'Historial y auditoría'
		OTRO = 'otro', 'Otro'

	class TipoAccion(models.TextChoices):
		CREACION = 'creacion', 'Creación'
		MODIFICACION = 'modificacion', 'Modificación'
		OBLIGACION = 'obligacion', 'Obligación / Configuración'
		CREDENCIAL = 'credencial', 'Credencial de acceso'
		TAREA = 'tarea', 'Tarea'
		PAGO = 'pago', 'Pago / Honorario'
		DOCUMENTO = 'documento', 'Documento'
		OTRO = 'otro', 'Otro'

	cliente = models.ForeignKey(
		'clientes.Cliente',
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='historial',
	)
	usuario = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='acciones_historial',
	)
	tipo_accion = models.CharField(
		max_length=24,
		choices=TipoAccion.choices,
		default=TipoAccion.OTRO,
	)
	seccion = models.CharField(max_length=20, choices=Seccion.choices, default=Seccion.OTRO)
	referencia = models.CharField(max_length=180, blank=True, default='')
	titulo = models.CharField(max_length=150)
	descripcion = models.TextField(blank=True)
	creado_en = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ('-creado_en',)
		verbose_name = 'entrada de historial'
		verbose_name_plural = 'entradas de historial'

	def __str__(self):
		return f'[{self.creado_en:%d/%m/%Y %H:%M}] {self.cliente.nombre}: {self.titulo}'
