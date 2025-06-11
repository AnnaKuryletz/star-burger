from django.core.management import call_command
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'star_burger.settings')
django.setup()


with open('data.json', 'w', encoding='utf-8') as f:
    call_command('dumpdata', '--exclude', 'auth.permission',
                 '--exclude', 'contenttypes', stdout=f)
