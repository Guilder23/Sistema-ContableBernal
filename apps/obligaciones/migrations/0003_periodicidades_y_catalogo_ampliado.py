from django.db import migrations, models


def crear_obligaciones_adicionales(apps, schema_editor):
    TipoObligacion = apps.get_model('obligaciones', 'TipoObligacion')
    registros = (
        ('bancarizacion', 'Bancarización', 'mensual'),
        ('formulario_608', 'Formulario 608', 'mensual'),
        ('informacion_hotelera', 'Información hotelera (Hoteles)', 'bimensual'),
        ('informacion_construccion', 'Envío de información de construcción', 'semestral'),
    )
    for codigo, nombre, periodicidad in registros:
        TipoObligacion.objects.get_or_create(
            codigo=codigo,
            defaults={
                'nombre': nombre,
                'periodicidad': periodicidad,
                'regla_vencimiento': 'ultimo_habil',
                'dia_vencimiento': None,
                'meses_despues_periodo': 1,
                'activa': True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [('obligaciones', '0002_catalogo_inicial')]

    operations = [
        migrations.AlterField(
            model_name='tipoobligacion',
            name='periodicidad',
            field=models.CharField(
                choices=[
                    ('mensual', 'Mensual'),
                    ('bimensual', 'Bimensual'),
                    ('trimestral', 'Trimestral'),
                    ('semestral', 'Semestral'),
                    ('anual', 'Anual'),
                ],
                max_length=12,
            ),
        ),
        migrations.RunPython(crear_obligaciones_adicionales, migrations.RunPython.noop),
    ]
