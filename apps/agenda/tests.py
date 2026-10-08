from datetime import date, time

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.clientes.models import Cliente
from apps.usuarios.models import PerfilUsuario

from .models import EventoAgenda


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