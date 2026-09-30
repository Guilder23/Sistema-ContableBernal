from datetime import date
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.clientes.models import Cliente
from apps.notificaciones.models import Notificacion
from apps.obligaciones.models import ConfiguracionCliente, Obligacion, TipoObligacion
from apps.obligaciones.services import generar_obligaciones
from apps.usuarios.models import PerfilUsuario

from .models import Tarea


class TareasIntegracionTests(TestCase):
	def setUp(self):
		user_model = get_user_model()
		self.admin = user_model.objects.create_superuser(username='admin_tareas', password='AdminTareas123!')
		self.auxiliar = user_model.objects.create_user(username='auxiliar_1', password='Auxiliar123!')
		PerfilUsuario.objects.update_or_create(
			usuario=self.auxiliar,
			defaults={'rol': PerfilUsuario.Rol.AUXILIAR},
		)
		self.otra_persona = user_model.objects.create_user(username='auxiliar_2', password='Auxiliar456!')
		PerfilUsuario.objects.update_or_create(
			usuario=self.otra_persona,
			defaults={'rol': PerfilUsuario.Rol.AUXILIAR},
		)
		self.cliente = Cliente.objects.create(
			nombre='Empresa tareas',
			nit='987654-3',
			actividad=Cliente.Actividad.COMERCIAL,
		)
		self.tipo = TipoObligacion.objects.get(codigo='rcv')
		self.obligacion = self.crear_obligacion('Empresa tareas')
		self.tarea = Tarea.objects.create(obligacion=self.obligacion)

	def crear_obligacion(self, nombre, tipo=None, cliente=None, mes=9, anio=2026):
		cliente = cliente or self.cliente
		tipo = tipo or self.tipo
		return Obligacion.objects.create(
			cliente=cliente,
			tipo=tipo,
			anio=anio,
			periodo_numero=mes if tipo.periodicidad == TipoObligacion.Periodicidad.MENSUAL else 0,
			periodo_inicio=date(anio, mes, 1),
			periodo_fin=date(anio, mes, 30),
			fecha_vencimiento=date(2026, 10, 9),
		)

	def test_generar_obligacion_crea_tarea_una_sola_vez(self):
		otro_cliente = Cliente.objects.create(
			nombre='Cliente automático', nit='111222-1', actividad=Cliente.Actividad.COMERCIAL,
		)
		ConfiguracionCliente.objects.create(cliente=otro_cliente, tipo=self.tipo, fecha_inicio=date(2026, 1, 1))
		primera = generar_obligaciones(TipoObligacion.Periodicidad.MENSUAL, 2026, 9)
		segunda = generar_obligaciones(TipoObligacion.Periodicidad.MENSUAL, 2026, 9)
		obligacion = Obligacion.objects.get(cliente=otro_cliente, tipo=self.tipo, anio=2026, periodo_numero=9)
		self.assertTrue(Tarea.objects.filter(obligacion=obligacion).exists())
		self.assertEqual(primera['tareas_creadas'], 1)
		self.assertEqual(segunda['tareas_creadas'], 0)

	def test_gestor_asigna_y_ajusta_prioridad_y_notas(self):
		self.client.force_login(self.admin)
		respuesta = self.client.post(reverse('tareas:asignar', args=(self.tarea.pk,)), {
			'responsable_id': self.auxiliar.pk,
			'prioridad': 'alta',
			'observaciones': 'Revisar comprobantes del período',
		})
		self.assertEqual(respuesta.status_code, 302)
		self.tarea.refresh_from_db()
		self.assertEqual(self.tarea.responsable, self.auxiliar)
		self.assertEqual(self.tarea.asignada_por, self.admin)
		self.assertEqual(self.tarea.prioridad, Tarea.Prioridad.ALTA)
		self.assertTrue(Notificacion.objects.filter(
			destinatario=self.auxiliar,
			tipo=Notificacion.Tipo.TAREA_ASIGNADA,
			leida_en__isnull=True,
		).exists())

	def test_auxiliar_solo_ve_y_actualiza_sus_tareas(self):
		otro_cliente = Cliente.objects.create(
			nombre='Cliente privado de otro auxiliar', nit='123123-4', actividad=Cliente.Actividad.COMERCIAL,
		)
		otra_obligacion = self.crear_obligacion('Cliente privado de otro auxiliar', cliente=otro_cliente)
		otra_tarea = Tarea.objects.create(obligacion=otra_obligacion, responsable=self.otra_persona)
		self.tarea.responsable = self.auxiliar
		self.tarea.save(update_fields=('responsable',))
		self.client.force_login(self.auxiliar)
		respuesta = self.client.get(reverse('tareas:index'))
		self.assertContains(respuesta, 'Empresa tareas')
		self.assertNotContains(respuesta, 'Cliente privado de otro auxiliar')
		respuesta = self.client.post(reverse('tareas:actualizar_estado', args=(self.tarea.pk,)), {
			'estado': Obligacion.Estado.COMPLETADA,
		})
		self.assertEqual(respuesta.status_code, 302)
		self.obligacion.refresh_from_db()
		self.assertEqual(self.obligacion.estado, Obligacion.Estado.COMPLETADA)
		self.assertEqual(self.obligacion.completada_por, self.auxiliar)
		self.assertTrue(Notificacion.objects.filter(
			destinatario=self.admin,
			tipo=Notificacion.Tipo.TAREA_COMPLETADA,
			actor=self.auxiliar,
		).exists())
		respuesta = self.client.post(reverse('tareas:actualizar_estado', args=(otra_tarea.pk,)), {
			'estado': Obligacion.Estado.COMPLETADA,
		})
		self.assertEqual(respuesta.status_code, 404)

	def test_evidencia_se_valida_y_descarga_con_acceso(self):
		media = TemporaryDirectory()
		self.addCleanup(media.cleanup)
		ajustes = override_settings(MEDIA_ROOT=media.name)
		ajustes.enable()
		self.addCleanup(ajustes.disable)
		self.tarea.responsable = self.auxiliar
		self.tarea.save(update_fields=('responsable',))
		self.client.force_login(self.auxiliar)
		respuesta = self.client.post(reverse('tareas:subir_evidencia', args=(self.tarea.pk,)), {
			'evidencia': SimpleUploadedFile('respaldo.pdf', b'%PDF evidencia', content_type='application/pdf'),
		})
		self.assertEqual(respuesta.status_code, 302)
		self.tarea.refresh_from_db()
		self.assertEqual(self.tarea.evidencia_subida_por, self.auxiliar)
		respuesta = self.client.get(reverse('tareas:descargar_evidencia', args=(self.tarea.pk,)))
		self.assertEqual(respuesta.status_code, 200)
		self.assertIn(b'%PDF evidencia', b''.join(respuesta.streaming_content))

	def test_pantalla_filtra_por_estado_y_muestra_tarea(self):
		self.tarea.responsable = self.auxiliar
		self.tarea.save(update_fields=('responsable',))
		self.client.force_login(self.auxiliar)
		respuesta = self.client.get(reverse('tareas:index'), {'estado': Obligacion.Estado.PENDIENTE})
		self.assertEqual(respuesta.status_code, 200)
		self.assertContains(respuesta, 'RCV - Septiembre 2026')
		self.assertContains(respuesta, 'data-open-task-modal')
		self.assertNotContains(respuesta, 'data-task-assignment-form')

	def test_gestor_ve_formulario_de_asignacion_en_el_modal(self):
		self.client.force_login(self.admin)
		respuesta = self.client.get(reverse('tareas:index'))
		self.assertEqual(respuesta.status_code, 200)
		self.assertContains(respuesta, 'data-task-assignment-form')
		self.assertContains(respuesta, 'Guardar asignación')
