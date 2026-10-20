from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.agenda.models import EventoAgenda
from apps.usuarios.models import PerfilUsuario

from .models import Cliente


class GestionClientesTests(TestCase):
	def setUp(self):
		self.modelo_usuario = get_user_model()
		self.administrador = self.modelo_usuario.objects.create_superuser(
			username='admin_clientes',
			password='G7!pL2-rT6#vM4x',
		)
		self.secretario = self.modelo_usuario.objects.create_user(
			username='secretario_clientes',
			password='Q8!pL2-rT6#vM4x',
		)
		self.secretario.perfil.rol = PerfilUsuario.Rol.SECRETARIO
		self.secretario.perfil.save(update_fields=['rol', 'actualizado_en'])
		self.auxiliar = self.modelo_usuario.objects.create_user(
			username='auxiliar_clientes',
			password='V7!mQ4-zX9pL2#b',
		)
		self.client.force_login(self.administrador)

	def datos_cliente(self, **cambios):
		return {
			'nombre': 'Comercial El Roble',
			'tipo': Cliente.Tipo.JURIDICA,
			'forma_juridica': Cliente.FormaJuridica.SRL,
			'nit': '123456789',
			'ci': '',
			'actividad': Cliente.Actividad.COMERCIAL,
			'telefono': '2212345',
			'whatsapp': '70123456',
			'correo': 'roble@example.test',
			'direccion': 'La Paz',
			'estado': 'activo',
			'fecha_inicio': '2026-01-15',
			'observaciones': 'Cliente de prueba',
			**cambios,
		}

	def test_directorio_y_modales_tienen_assets_homonimos(self):
		response = self.client.get('/clientes/')
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Tiene SEPREC')
		self.assertContains(response, 'Tiene ROE')
		self.assertContains(response, 'Tipo de facturación')
		self.assertNotContains(response, 'Correo')
		html = response.content.decode()
		for modal in ('crear', 'ver', 'editar', 'eliminar'):
			self.assertContains(response, f'id="modal-{modal}"')
			self.assertRegex(html, rf'css/clientes/modals/{modal}(?:\.[\w-]+)?\.css')
			self.assertRegex(html, rf'js/clientes/modals/{modal}(?:\.[\w-]+)?\.js')

	def test_boton_editar_incluye_datos_guardados_del_cliente(self):
		cliente = Cliente.objects.create(
			nombre='Cliente con datos',
			razon_social='Empresa de prueba SRL',
			tipo=Cliente.Tipo.JURIDICA,
			forma_juridica=Cliente.FormaJuridica.SRL,
			actividad=Cliente.Actividad.SERVICIOS,
			tiene_seprec=True,
			telefono='22123456',
			fecha_inicio=date(2024, 3, 1),
		)
		respuesta = self.client.get('/clientes/')
		self.assertContains(respuesta, f'data-client-name="{cliente.nombre}"')
		self.assertContains(respuesta, f'data-client-reason-social="{cliente.razon_social}"')
		self.assertContains(respuesta, f'data-client-type-value="{cliente.tipo}"')
		self.assertContains(respuesta, f'data-client-legal-form="{cliente.forma_juridica}"')
		self.assertContains(respuesta, f'data-client-activity-value="{cliente.actividad}"')
		self.assertContains(respuesta, f'data-client-phone="{cliente.telefono}"')

	def test_crea_cliente_con_campos_complementarios_y_representante_legal(self):
		response = self.client.post('/clientes/crear/', {
			**self.datos_cliente(
				tipo=Cliente.Tipo.PERSONA_NATURAL,
				actividad=Cliente.Actividad.PROFESIONAL,
			),
			'fecha_nacimiento': '1990-02-15',
			'ci_complemento': 'A',
			'ci_expedido': 'LP',
			'cambio_contador': 'on',
			'fecha_cambio_contador': '2025-02',
			'tiene_representante_legal': 'on',
			'representante_legal_nombre': 'Ana Maria Flores',
			'representante_legal_carnet': '4567890',
			'representante_legal_complemento': 'B',
			'representante_legal_expedido': 'CBBA',
			'representante_legal_celular': '76543210',
			'representante_legal_fecha_nacimiento': '1985-05-20',
		})
		cliente = Cliente.objects.get(nit='123456789')
		self.assertRedirects(response, f'/clientes/{cliente.pk}/')
		self.assertEqual(cliente.fecha_nacimiento.isoformat(), '1990-02-15')
		self.assertEqual(cliente.ci_complemento, 'A')
		self.assertEqual(cliente.ci_expedido, 'LP')
		self.assertTrue(cliente.cambio_contador)
		self.assertTrue(cliente.tiene_representante_legal)
		self.assertEqual(cliente.representante_legal_nombre, 'Ana Maria Flores')
		self.assertEqual(cliente.representante_legal_carnet, '4567890')
		self.assertEqual(cliente.representante_legal_complemento, 'B')
		self.assertEqual(cliente.representante_legal_expedido, 'CBBA')
		self.assertEqual(cliente.representante_legal_celular, '76543210')
		self.assertEqual(cliente.representante_legal_fecha_nacimiento.isoformat(), '1985-05-20')
		self.assertEqual(cliente.fecha_cambio_contador, '2025-02')

	def test_nombre_del_cliente_y_razon_social_se_guardan_separados(self):
		response = self.client.post('/clientes/crear/', {
			**self.datos_cliente(),
			'nombre': 'Juan Pérez',
			'razon_social': 'Constructora Pérez y Asociados SRL',
		})
		cliente = Cliente.objects.get(nit='123456789')
		self.assertRedirects(response, f'/clientes/{cliente.pk}/')
		self.assertEqual(cliente.nombre, 'Juan Pérez')
		self.assertEqual(cliente.razon_social, 'Constructora Pérez y Asociados SRL')

	def test_seprec_exige_razon_social_y_guarda_otro_tipo_juridico(self):
		response = self.client.post('/clientes/crear/', {
			**self.datos_cliente(),
			'tiene_seprec': 'si',
			'forma_juridica': Cliente.FormaJuridica.OTRA,
			'forma_juridica_detalle': 'Sociedad de acciones simplificada',
		})
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Ingresa la razón social o nombre de la empresa.')
		response = self.client.post('/clientes/crear/', {
			**self.datos_cliente(),
			'razon_social': 'Roble S.A.S.',
			'tiene_seprec': 'si',
			'forma_juridica': Cliente.FormaJuridica.OTRA,
			'forma_juridica_detalle': 'Sociedad de acciones simplificada',
		})
		cliente = Cliente.objects.get(nit='123456789')
		self.assertRedirects(response, f'/clientes/{cliente.pk}/')
		self.assertTrue(cliente.tiene_seprec)
		self.assertEqual(cliente.forma_juridica_detalle, 'Sociedad de acciones simplificada')

	def test_persona_juridica_no_guarda_datos_de_identidad_personal(self):
		response = self.client.post('/clientes/crear/', self.datos_cliente(
			ci='1234567', ci_complemento='A', ci_expedido='LP', fecha_nacimiento='1990-02-15',
		))
		cliente = Cliente.objects.get(nit='123456789')
		self.assertRedirects(response, f'/clientes/{cliente.pk}/')
		self.assertEqual(cliente.ci, '')
		self.assertEqual(cliente.ci_complemento, '')
		self.assertEqual(cliente.ci_expedido, '')
		self.assertIsNone(cliente.fecha_nacimiento)

	def test_edita_cliente_con_rubro_historico_no_disponible_para_su_tipo(self):
		cliente = Cliente.objects.create(
			nombre='Persona con rubro histórico',
			tipo=Cliente.Tipo.PERSONA_NATURAL,
			actividad=Cliente.Actividad.COMERCIAL,
		)
		response = self.client.post(f'/clientes/{cliente.pk}/editar/', self.datos_cliente(
			nombre=cliente.nombre,
			tipo=Cliente.Tipo.PERSONA_NATURAL,
			actividad=Cliente.Actividad.COMERCIAL,
			nit='',
			telefono='76543210',
		))
		self.assertRedirects(response, f'/clientes/{cliente.pk}/')
		cliente.refresh_from_db()
		self.assertEqual(cliente.actividad, Cliente.Actividad.COMERCIAL)
		self.assertEqual(cliente.telefono, '76543210')

	def test_vencimiento_facturacion_crea_actualiza_y_quita_recordatorio_de_agenda(self):
		fecha_vencimiento = timezone.localdate() + timedelta(days=30)
		response = self.client.post('/clientes/crear/', self.datos_cliente(
			tipo_facturacion=Cliente.TipoFacturacion.MANUAL,
			fecha_vencimiento_facturacion=fecha_vencimiento.isoformat(),
		))
		cliente = Cliente.objects.get(nit='123456789')
		self.assertRedirects(response, f'/clientes/{cliente.pk}/')
		evento = EventoAgenda.objects.get(pk=cliente.evento_vencimiento_facturacion_id)
		self.assertEqual(evento.fecha, fecha_vencimiento)
		self.assertEqual(evento.tipo, EventoAgenda.Tipo.RECORDATORIO)
		self.assertIn('Notificar vencimiento', evento.titulo)

		fecha_actualizada = fecha_vencimiento + timedelta(days=10)
		response = self.client.post(f'/clientes/{cliente.pk}/editar/', self.datos_cliente(
			tipo_facturacion=Cliente.TipoFacturacion.PORTAL_WEB,
			fecha_vencimiento_facturacion=fecha_actualizada.isoformat(),
		))
		self.assertRedirects(response, f'/clientes/{cliente.pk}/')
		evento.refresh_from_db()
		self.assertEqual(evento.fecha, fecha_actualizada)

		response = self.client.post(f'/clientes/{cliente.pk}/editar/', self.datos_cliente(
			tipo_facturacion='', fecha_vencimiento_facturacion='',
		))
		self.assertRedirects(response, f'/clientes/{cliente.pk}/')
		self.assertFalse(EventoAgenda.objects.filter(pk=evento.pk).exists())

	def test_crea_cliente_con_datos_tributarios_y_contacto(self):
		response = self.client.post('/clientes/crear/', self.datos_cliente())
		cliente = Cliente.objects.get(nit='123456789')
		self.assertRedirects(response, f'/clientes/{cliente.pk}/')
		self.assertEqual(cliente.nombre, 'Comercial El Roble')
		self.assertEqual(cliente.tipo, Cliente.Tipo.JURIDICA)
		self.assertEqual(cliente.fecha_inicio.isoformat(), '2026-01-15')
		self.assertIsNotNone(cliente.creado_en)
		self.assertEqual(cliente.creado_por, self.administrador)

	def test_nit_duplicado_reabre_modal_con_error(self):
		Cliente.objects.create(nombre='Cliente existente', nit='123456789')
		response = self.client.post('/clientes/crear/', self.datos_cliente())
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context['modal_activo'], 'modal-crear')
		self.assertContains(response, 'Ya existe un cliente con ese NIT.')

	def test_edita_consulta_y_elimina_desde_el_directorio(self):
		cliente = Cliente.objects.create(
			nombre='Cliente inicial',
			nit='987654321',
			creado_por=self.secretario,
		)
		response = self.client.post(f'/clientes/{cliente.pk}/editar/', self.datos_cliente(nit='987654321'))
		self.assertRedirects(response, f'/clientes/{cliente.pk}/')
		cliente.refresh_from_db()
		self.assertEqual(cliente.nombre, 'Comercial El Roble')
		self.assertEqual(cliente.creado_por, self.secretario)
		self.assertContains(self.client.get('/clientes/'), 'Comercial El Roble')
		response = self.client.post(f'/clientes/{cliente.pk}/eliminar/')
		self.assertRedirects(response, '/clientes/')
		self.assertFalse(Cliente.objects.filter(pk=cliente.pk).exists())

	def test_auxiliar_solo_consulta_y_secretario_gestiona(self):
		self.client.force_login(self.auxiliar)
		self.assertEqual(self.client.get('/clientes/').status_code, 200)
		self.assertEqual(self.client.post('/clientes/crear/', self.datos_cliente()).status_code, 403)
		self.client.force_login(self.secretario)
		response = self.client.post('/clientes/crear/', self.datos_cliente())
		cliente = Cliente.objects.get(nit='123456789')
		self.assertRedirects(response, f'/clientes/{cliente.pk}/')
		self.assertTrue(Cliente.objects.filter(nit='123456789').exists())

	def test_mutaciones_solo_aceptan_post(self):
		cliente = Cliente.objects.create(nombre='Cliente GET')
		self.assertEqual(self.client.get('/clientes/crear/').status_code, 405)
		self.assertEqual(self.client.get(f'/clientes/{cliente.pk}/editar/').status_code, 405)
		self.assertEqual(self.client.get(f'/clientes/{cliente.pk}/eliminar/').status_code, 405)

	def test_paginacion_conserva_busqueda_y_filtros(self):
		for indice in range(13):
			Cliente.objects.create(
				nombre=f'Cliente listado {indice}',
				nit=f'PAG-{indice:04}',
				tipo=Cliente.Tipo.JURIDICA,
			)
		response = self.client.get('/clientes/?tipo=juridica&estado=activo&page=2')
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context['page_obj'].number, 2)
		self.assertEqual(response.context['total_clientes'], 13)
		self.assertContains(response, 'tipo=juridica&amp;estado=activo&amp;page=1')
