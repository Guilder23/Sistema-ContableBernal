import os
from datetime import date, time, timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.clientes.models import Cliente
from apps.historial.models import EntradaHistorial
from apps.usuarios.models import PerfilUsuario

from .google_calendar import eliminar_evento_google, sincronizar_evento_google
from .models import EventoAgenda, GoogleCalendarCredential


class GestionAgendaTests(TestCase):
	def setUp(self):
		user_model = get_user_model()
		self.admin = user_model.objects.create_superuser(username='admin_agenda', password='ClaveLocal123!')
		self.auxiliar = user_model.objects.create_user(username='auxiliar_agenda', password='ClaveLocal123!')
		self.secretario = user_model.objects.create_user(username='secretario_agenda', password='ClaveLocal123!')
		self.secretario.perfil.rol = PerfilUsuario.Rol.SECRETARIO
		self.secretario.perfil.save(update_fields=['rol', 'actualizado_en'])
		self.cliente = Cliente.objects.create(nombre='Cliente agenda', nit='AGENDA-01')
		self.client.force_login(self.admin)

	def datos_evento(self, **cambios):
		return {
			'titulo': 'Reunión de seguimiento',
			'tipo': EventoAgenda.Tipo.CITA,
			'fecha': '2026-10-08',
			'hora_inicio': '09:00',
			'hora_fin': '10:00',
			'cliente': str(self.cliente.pk),
			'responsable': str(self.secretario.pk),
			'estado': EventoAgenda.Estado.PROGRAMADO,
			'lugar': 'Oficina',
			'observaciones': 'Revisar documentación',
			**cambios,
		}

	def test_hora_fin_debe_ser_posterior_a_inicio_aunque_no_haya_responsable(self):
		evento = EventoAgenda(
			titulo='Horario inválido',
			tipo=EventoAgenda.Tipo.RECORDATORIO,
			fecha=date(2026, 10, 8),
			hora_inicio=time(11, 0),
			hora_fin=time(10, 0),
		)
		with self.assertRaises(ValidationError):
			evento.full_clean()

	def test_crea_evento_y_lo_muestra_en_calendario(self):
		respuesta = self.client.post(reverse('agenda:crear'), self.datos_evento())
		self.assertRedirects(respuesta, reverse('agenda:index'))
		evento = EventoAgenda.objects.get(titulo='Reunión de seguimiento')
		self.assertEqual(evento.cliente, self.cliente)
		self.assertEqual(evento.responsable, self.secretario)
		respuesta = self.client.get(reverse('agenda:index'), {'anio': 2026, 'mes': 10})
		self.assertContains(respuesta, 'Reunión de seguimiento')
		self.assertContains(respuesta, 'class="agenda-upcoming__actions"')
		self.assertContains(respuesta, 'class="icon-action icon-action--edit agenda-upcoming__edit"')
		self.assertContains(respuesta, 'data-open-modal="modal-editar-evento"')
		self.assertEqual(respuesta.context['eventos_mes'], 1)

	def test_evento_proximo_muestra_accion_con_icono_eliminar(self):
		evento = EventoAgenda.objects.create(
			titulo='Evento próximo', tipo=EventoAgenda.Tipo.CITA,
			fecha=timezone.localdate() + timedelta(days=1), hora_inicio=time(9, 0),
			hora_fin=time(10, 0), creado_por=self.admin,
		)
		evento_lejano = EventoAgenda.objects.create(
			titulo='Evento dentro de un mes', tipo=EventoAgenda.Tipo.CITA,
			fecha=timezone.localdate() + timedelta(days=30), hora_inicio=time(9, 0),
			hora_fin=time(10, 0), creado_por=self.admin,
		)
		respuesta = self.client.get(reverse('agenda:index'))
		self.assertContains(respuesta, evento_lejano.titulo)
		self.assertEqual(respuesta.context['proximos'].count(), 2)
		self.assertContains(respuesta, f'aria-label="Eliminar {evento.titulo}"')
		self.assertContains(respuesta, f'data-delete-url="/agenda/{evento.pk}/eliminar/"')
		self.assertContains(respuesta, 'icon-action--delete agenda-upcoming__delete')
		self.assertContains(respuesta, '#trash')
		self.assertContains(respuesta, 'icon-action--view agenda-upcoming__view')
		self.assertContains(respuesta, '#eye')

	@patch('apps.agenda.views.sincronizar_evento_google')
	def test_crear_evento_programa_sincronizacion_google_al_confirmar_transaccion(self, sincronizar):
		with self.captureOnCommitCallbacks(execute=True):
			respuesta = self.client.post(reverse('agenda:crear'), self.datos_evento())
		self.assertEqual(respuesta.status_code, 302)
		sincronizar.assert_called_once()

	def test_crear_evento_registra_historial(self):
		self.client.post(reverse('agenda:crear'), self.datos_evento())
		evento_historial = EntradaHistorial.objects.get(seccion=EntradaHistorial.Seccion.AGENDA)
		self.assertEqual(evento_historial.cliente, self.cliente)
		self.assertEqual(evento_historial.usuario, self.admin)
		self.assertIn('Reunión de seguimiento', evento_historial.referencia)

	def test_rechaza_cruce_de_horario_para_el_mismo_responsable(self):
		EventoAgenda.objects.create(
			titulo='Bloque ocupado', tipo=EventoAgenda.Tipo.CITA, fecha=date(2026, 10, 8),
			hora_inicio=time(9, 0), hora_fin=time(10, 0), responsable=self.secretario, creado_por=self.admin,
		)
		respuesta = self.client.post(reverse('agenda:crear'), self.datos_evento(
			titulo='Cita superpuesta', hora_inicio='09:30', hora_fin='10:30',
		))
		self.assertEqual(respuesta.status_code, 400)
		self.assertContains(respuesta, 'se cruza con otro evento', status_code=400)
		self.assertFalse(EventoAgenda.objects.filter(titulo='Cita superpuesta').exists())

	def test_edita_y_elimina_evento(self):
		evento = EventoAgenda.objects.create(
			titulo='Cita inicial', tipo=EventoAgenda.Tipo.CITA, fecha=date(2026, 10, 8),
			hora_inicio=time(9, 0), hora_fin=time(10, 0), responsable=self.secretario, creado_por=self.admin,
		)
		respuesta = self.client.post(reverse('agenda:editar', args=[evento.pk]), self.datos_evento(
			titulo='Cita actualizada', estado=EventoAgenda.Estado.COMPLETADO,
		))
		self.assertRedirects(respuesta, reverse('agenda:index'))
		evento.refresh_from_db()
		self.assertEqual(evento.titulo, 'Cita actualizada')
		self.assertEqual(evento.estado, EventoAgenda.Estado.COMPLETADO)
		respuesta = self.client.post(reverse('agenda:eliminar', args=[evento.pk]))
		self.assertRedirects(respuesta, reverse('agenda:index'))
		self.assertFalse(EventoAgenda.objects.filter(pk=evento.pk).exists())

	@patch('apps.agenda.views.eliminar_evento_google', return_value=False)
	def test_no_elimina_evento_local_si_falla_el_borrado_en_google(self, eliminar_google):
		evento = EventoAgenda.objects.create(
			titulo='Cita vinculada', tipo=EventoAgenda.Tipo.CITA, fecha=date(2026, 10, 8),
			hora_inicio=time(9, 0), hora_fin=time(10, 0), google_event_id='google-id', creado_por=self.admin,
		)
		respuesta = self.client.post(reverse('agenda:eliminar', args=[evento.pk]))
		self.assertEqual(respuesta.status_code, 302)
		self.assertTrue(EventoAgenda.objects.filter(pk=evento.pk).exists())
		eliminar_google.assert_called_once()

	@override_settings(GOOGLE_TOKEN_ENCRYPTION_KEY='')
	def test_refresh_token_se_guarda_cifrado(self):
		cuenta = GoogleCalendarCredential()
		cuenta.set_refresh_token('refresh-token-privado')
		self.assertNotIn('refresh-token-privado', cuenta.refresh_token_encrypted)
		self.assertEqual(cuenta.get_refresh_token(), 'refresh-token-privado')

	@override_settings(
		DEBUG=True,
		GOOGLE_CLIENT_ID='client-id',
		GOOGLE_CLIENT_SECRET='client-secret',
		GOOGLE_REDIRECT_URI='http://127.0.0.1:8000/agenda/google/callback/',
	)
	@patch('apps.agenda.views.sincronizar_eventos_pendientes', return_value=(0, 0))
	@patch('google_auth_oauthlib.flow.Flow.from_client_config')
	def test_callback_local_permite_http_solo_durante_el_intercambio(self, crear_flujo, _sync):
		flujo = Mock()
		flujo.credentials.refresh_token = 'refresh-token-test'
		def verificar_intercambio(**kwargs):
			self.assertEqual(flujo.code_verifier, 'verificador-prueba')
			self.assertEqual(os.environ.get('OAUTHLIB_INSECURE_TRANSPORT'), '1')
		flujo.fetch_token.side_effect = verificar_intercambio
		crear_flujo.return_value = flujo
		sesion = self.client.session
		sesion['google_calendar_oauth_state'] = 'estado-prueba'
		sesion['google_calendar_oauth_code_verifier'] = 'verificador-prueba'
		sesion.save()
		with patch.dict(os.environ, {'OAUTHLIB_INSECURE_TRANSPORT': ''}):
			respuesta = self.client.get(
				reverse('agenda:google_callback'),
				{'state': 'estado-prueba', 'code': 'codigo-prueba'},
				HTTP_HOST='127.0.0.1:8000',
			)
			self.assertEqual(os.environ.get('OAUTHLIB_INSECURE_TRANSPORT'), '')
		self.assertEqual(respuesta.status_code, 302)
		self.assertTrue(GoogleCalendarCredential.objects.exists())

	@patch('apps.agenda.google_calendar._servicio_calendar')
	@override_settings(GOOGLE_TOKEN_ENCRYPTION_KEY='')
	def test_sincroniza_evento_y_guarda_el_id_de_google(self, servicio_calendar):
		servicio = Mock()
		servicio.events.return_value.insert.return_value.execute.return_value = {'id': 'evento-google-123'}
		servicio_calendar.return_value = servicio
		evento = EventoAgenda.objects.create(
			titulo='Cita para Google', tipo=EventoAgenda.Tipo.CITA, fecha=date(2026, 10, 8),
			hora_inicio=time(9, 0), hora_fin=time(10, 0), creado_por=self.admin,
		)
		GoogleCalendarCredential.objects.create(singleton=1, refresh_token_encrypted='encrypted')
		with patch('apps.agenda.google_calendar._credenciales_google', return_value=object()):
			resultado = sincronizar_evento_google(evento.pk)
		evento.refresh_from_db()
		self.assertTrue(resultado)
		self.assertEqual(evento.google_event_id, 'evento-google-123')
		self.assertEqual(evento.google_sync_status, 'synced')
		servicio.events.return_value.insert.assert_called_once()

	@patch('apps.agenda.google_calendar._servicio_calendar')
	def test_elimina_evento_de_google_antes_de_quitarlo_localmente(self, servicio_calendar):
		servicio = Mock()
		servicio_calendar.return_value = servicio
		evento = EventoAgenda.objects.create(
			titulo='Cita para borrar', tipo=EventoAgenda.Tipo.CITA, fecha=date(2026, 10, 8),
			hora_inicio=time(9, 0), hora_fin=time(10, 0), google_event_id='evento-google-456', creado_por=self.admin,
		)
		self.assertTrue(eliminar_evento_google(evento))
		servicio.events.return_value.delete.assert_called_once_with(calendarId='primary', eventId='evento-google-456')

	def test_auxiliar_puede_consultar_pero_no_gestionar(self):
		self.client.force_login(self.auxiliar)
		self.assertEqual(self.client.get(reverse('agenda:index')).status_code, 200)
		self.assertEqual(self.client.post(reverse('agenda:crear'), self.datos_evento()).status_code, 403)

	def test_carga_assets_homonimos_y_modales(self):
		respuesta = self.client.get(reverse('agenda:index'))
		self.assertContains(respuesta, 'css/agenda/agenda.css')
		self.assertContains(respuesta, 'js/agenda/agenda.js')
		for modal in ('crear', 'ver', 'editar', 'eliminar'):
			self.assertContains(respuesta, f'id="modal-{modal}-evento"')
			self.assertContains(respuesta, f'css/agenda/modals/{modal}.css')
			self.assertContains(respuesta, f'js/agenda/modals/{modal}.js')