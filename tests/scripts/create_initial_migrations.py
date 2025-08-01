#!/usr/bin/env python
"""
Script to create initial Django migrations that match the existing database schema.
Uses --fake-initial to mark migrations as applied since tables already exist.
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

def setup_django():
    """Setup Django environment."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'senangkira.settings')
    django.setup()

def create_initial_migrations():
    """Create initial migrations for all apps."""
    
    apps = [
        'authentication',
        'clients', 
        'invoicing',
        'expenses',
        'dashboard'
    ]
    
    print("Creating initial migrations...")
    
    # Create migrations for each app
    for app in apps:
        print(f"\nCreating migration for {app}...")
        try:
            execute_from_command_line(['manage.py', 'makemigrations', app])
        except Exception as e:
            print(f"Error creating migration for {app}: {e}")
            continue
    
    print("\n" + "="*50)
    print("Initial migrations created!")
    print("="*50)
    
    print("\nNext steps:")
    print("1. Run: python manage.py migrate --fake-initial")
    print("   (This marks the initial migrations as applied since tables already exist)")
    print("2. Test the setup with: python manage.py check")
    print("3. Create a superuser: python manage.py createsuperuser")

if __name__ == '__main__':
    setup_django()
    create_initial_migrations()