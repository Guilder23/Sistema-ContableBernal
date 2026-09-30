import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Crea el administrador inicial si todavía no existe.'

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
        password = 'admin12345'
        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(username=username)

        if created:
            user.set_password(password)

        user.is_staff = True
        user.is_superuser = True
        user.save()

        self.stdout.write(self.style.SUCCESS(f'Administrador {username} listo.'))