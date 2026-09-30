from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Notificacion


class NotificacionesTests(TestCase):
	def setUp(self):
		user_model = get_user_model()
		self.usuario = user_model.objects.create_user(username='destinatario', password='Avisos123!')
		self.otro_usuario = user_model.objects.create_user(username='otro', password='Avisos456!')
		self.aviso = Notificacion.objects.create(
			destinatario=self.usuario,
			tipo=Notificacion.Tipo.TAREA_ASIGNADA,
			titulo='Te asignaron una tarea',
			mensaje='RCV - Septiembre 2026 · Cliente de prueba',
			url='/tareas/',
		)
		Notificacion.objects.create(
			destinatario=self.otro_usuario,
			tipo=Notificacion.Tipo.TAREA_COMPLETADA,
			titulo='Aviso privado de otra persona',
			mensaje='No debe aparecer para el destinatario actual.',
		)

	def test_bandeja_y_campana_solo_muestran_avisos_del_usuario(self):
		self.client.force_login(self.usuario)
		respuesta = self.client.get(reverse('notificaciones:index'))
		self.assertEqual(respuesta.status_code, 200)
		self.assertContains(respuesta, 'Te asignaron una tarea')
		self.assertNotContains(respuesta, 'Aviso privado de otra persona')
		self.assertContains(respuesta, 'data-unread-count="1"')

	def test_usuario_marca_su_aviso_como_leido(self):
		self.client.force_login(self.usuario)
		respuesta = self.client.post(reverse('notificaciones:marcar_leida', args=(self.aviso.pk,)))
		self.assertEqual(respuesta.status_code, 302)
		self.aviso.refresh_from_db()
		self.assertIsNotNone(self.aviso.leida_en)

	def test_no_se_puede_marcar_aviso_ajeno(self):
		self.client.force_login(self.otro_usuario)
		respuesta = self.client.post(reverse('notificaciones:marcar_leida', args=(self.aviso.pk,)))
		self.assertEqual(respuesta.status_code, 404)

	def test_marcar_todas_leidas(self):
		self.client.force_login(self.usuario)
		respuesta = self.client.post(reverse('notificaciones:marcar_todas_leidas'))
		self.assertEqual(respuesta.status_code, 302)
		self.assertFalse(Notificacion.objects.filter(destinatario=self.usuario, leida_en__isnull=True).exists())
