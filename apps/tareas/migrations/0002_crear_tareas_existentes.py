from django.db import migrations


def crear_tareas_existentes(apps, schema_editor):
    Obligacion = apps.get_model('obligaciones', 'Obligacion')
    Tarea = apps.get_model('tareas', 'Tarea')
    for obligacion_id in Obligacion.objects.values_list('id', flat=True).iterator():
        Tarea.objects.get_or_create(obligacion_id=obligacion_id)


class Migration(migrations.Migration):
    dependencies = [('tareas', '0001_initial')]
    operations = [migrations.RunPython(crear_tareas_existentes, migrations.RunPython.noop)]
