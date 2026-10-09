import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.clientes.models import Cliente

from .models import ComentarioRequerimiento, Requerimiento


class GestionRequerimientosTests(TestCase):
	def setUp(self):
		User = get_user_model()
		self.admin = User.objects.create_superuser(username='admin_requerimientos', password='ClaveLocal123!')
		self.auxiliar = User.objects.create_user(username='auxiliar_requerimientos', password='ClaveLocal123!')
		self.cliente = Cliente.objects.create(nombre='Cliente de requerimientos', nit='REQ-001')
		self.client.force_login(self.admin)

	def test_crea_asignado_comenta_y_avanza_en_orden(self):
		respuesta = self.client.post(reverse('requerimientos:crear'), {
			'cliente': self.cliente.pk,
			'titulo': 'Certificado de impuestos',
			'descripcion': 'Preparar y presentar la solicitud.',
			'prioridad': Requerimiento.Prioridad.ALTA,
			'fecha_limite': '2026-10-28',
			'responsable': self.auxiliar.pk,
		})
		self.assertRedirects(respuesta, reverse('requerimientos:index'))
		requerimiento = Requerimiento.objects.get(titulo='Certificado de impuestos')
		self.assertEqual(requerimiento.responsable, self.auxiliar)
		self.assertEqual(requerimiento.estado, Requerimiento.Estado.NUEVO)

		self.client.post(reverse('requerimientos:actualizar', args=[requerimiento.pk]), {'estado': 'terminado'})
		requerimiento.refresh_from_db()
		self.assertEqual(requerimiento.estado, Requerimiento.Estado.NUEVO)
		self.client.post(reverse('requerimientos:actualizar', args=[requerimiento.pk]), {'estado': 'en_proceso'})
		self.client.post(reverse('requerimientos:comentar', args=[requerimiento.pk]), {'texto': 'Solicitud enviada.'})
		self.client.post(reverse('requerimientos:actualizar', args=[requerimiento.pk]), {'estado': 'terminado'})
		requerimiento.refresh_from_db()
		self.assertEqual(requerimiento.estado, Requerimiento.Estado.TERMINADO)
		self.assertIsNotNone(requerimiento.terminado_en)
		self.assertEqual(ComentarioRequerimiento.objects.filter(requerimiento=requerimiento).count(), 1)

	def test_edita_y_elimina_requerimiento(self):
		requerimiento = Requerimiento.objects.create(
			cliente=self.cliente,
			titulo='Solicitud inicial',
			descripcion='Descripción inicial.',
			creado_por=self.admin,
		)
		respuesta = self.client.post(reverse('requerimientos:actualizar', args=[requerimiento.pk]), {
			'titulo': 'Licencia de funcionamiento',
			'descripcion': 'Gestionar la licencia solicitada.',
			'estado': Requerimiento.Estado.EN_PROCESO,
			'prioridad': Requerimiento.Prioridad.ALTA,
		})
		self.assertEqual(respuesta.status_code, 302)
		requerimiento.refresh_from_db()
		self.assertEqual(requerimiento.titulo, 'Licencia de funcionamiento')
		self.assertEqual(requerimiento.estado, Requerimiento.Estado.EN_PROCESO)
		respuesta = self.client.post(reverse('requerimientos:eliminar', args=[requerimiento.pk]))
		self.assertEqual(respuesta.status_code, 302)
		self.assertFalse(Requerimiento.objects.filter(pk=requerimiento.pk).exists())

	def test_index_carga_los_cuatro_modales_y_sus_assets(self):
		requerimiento = Requerimiento.objects.create(
			cliente=self.cliente,
			titulo='Certificado solicitado',
			descripcion='Emitir certificado.',
			creado_por=self.admin,
		)
		respuesta = self.client.get(reverse('requerimientos:index'))
		self.assertEqual(respuesta.status_code, 200)
		self.assertNotContains(respuesta, 'css/clientes/clientes.css')
		self.assertContains(respuesta, 'css/requerimientos/requerimientos.css')
		self.assertContains(respuesta, 'class="button button--primary"')
		self.assertContains(respuesta, 'class="button button--quiet requirement-filter-button"')
		for modal in ('crear', 'editar', 'ver', 'eliminar'):
			self.assertContains(respuesta, f'css/requerimientos/modals/{modal}.css')
			self.assertContains(respuesta, f'js/requerimientos/modals/{modal}.js')
		self.assertContains(respuesta, f'id="modal-ver-{requerimiento.pk}"')
		self.assertContains(respuesta, 'data-open-modal="modal-editar"')
		self.assertContains(respuesta, 'data-open-modal="modal-eliminar"')

	def test_solo_el_responsable_o_gestor_puede_actualizar(self):
		requerimiento = Requerimiento.objects.create(
			cliente=self.cliente,
			titulo='Trámite pendiente',
			descripcion='Seguimiento de trámite.',
			responsable=self.auxiliar,
		)
		self.client.force_login(self.admin)
		self.client.post(reverse('requerimientos:actualizar', args=[requerimiento.pk]), {'estado': 'en_proceso'})
		self.client.force_login(get_user_model().objects.create_user(username='otro_auxiliar', password='ClaveLocal123!'))
		respuesta = self.client.post(reverse('requerimientos:actualizar', args=[requerimiento.pk]), {'estado': 'terminado'})
		self.assertEqual(respuesta.status_code, 403)

	def test_archivo_se_descarga_solo_a_traves_de_sesion_autenticada(self):
		requerimiento = Requerimiento.objects.create(
			cliente=self.cliente,
			titulo='Adjuntar certificado',
			descripcion='Solicitud con respaldo.',
			creado_por=self.admin,
		)
		with tempfile.TemporaryDirectory() as media_root:
			with override_settings(MEDIA_ROOT=media_root):
				self.client.post(reverse('requerimientos:adjuntar', args=[requerimiento.pk]), {
					'archivos': SimpleUploadedFile('certificado.pdf', b'contenido de prueba', content_type='application/pdf'),
				})
				archivo = requerimiento.archivos.get()
				respuesta = self.client.get(reverse('requerimientos:descargar_archivo', args=[archivo.pk]))
				self.assertEqual(respuesta.status_code, 200)
				self.assertTrue(respuesta['Content-Disposition'].startswith('attachment;'))
				b''.join(respuesta.streaming_content)
				respuesta.close()
				self.client.logout()
				respuesta = self.client.get(reverse('requerimientos:descargar_archivo', args=[archivo.pk]))
				self.assertEqual(respuesta.status_code, 302)