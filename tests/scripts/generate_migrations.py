#!/usr/bin/env python3
"""
Django migration generation script for SenangKira.
Creates migrations for all apps based on the implemented models.
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(command, description):
    """Run a shell command with error handling."""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"   ✅ Success: {description}")
        if result.stdout.strip():
            print(f"   📝 Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Error: {description}")
        print(f"   📝 Error Output: {e.stderr.strip()}")
        return False

def setup_virtual_environment():
    """Ensure virtual environment is activated and dependencies are installed."""
    print("🚀 Setting up Python environment...")
    
    # Check if we're in a virtual environment
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("   ⚠️  Not in a virtual environment. Please activate your virtual environment first:")
        print("   source venv/bin/activate")
        return False
    
    print("   ✅ Virtual environment is active")
    return True

def generate_migrations():
    """Generate Django migrations for all apps."""
    print("\n📋 Generating Django migrations...")
    
    apps = ['authentication', 'clients', 'invoicing', 'expenses']
    
    # First, create migrations for each app
    for app in apps:
        success = run_command(
            f"python manage.py makemigrations {app}",
            f"Creating migrations for {app} app"
        )
        if not success:
            print(f"   ⚠️  Warning: Could not create migrations for {app}")
    
    # Create migrations for all apps together (in case of dependencies)
    run_command(
        "python manage.py makemigrations",
        "Creating any remaining migrations"
    )
    
    # Show migration plan
    run_command(
        "python manage.py showmigrations --plan",
        "Showing migration plan"
    )

def apply_migrations():
    """Apply Django migrations to database."""
    print("\n🗄️  Applying Django migrations...")
    
    # Apply migrations
    success = run_command(
        "python manage.py migrate",
        "Applying all migrations to database"
    )
    
    if success:
        print("   🎉 All migrations applied successfully!")
    else:
        print("   ⚠️  Some migrations may have failed. Check database configuration.")

def validate_models():
    """Validate Django models."""
    print("\n✅ Validating Django models...")
    
    run_command(
        "python manage.py check",
        "Running Django system checks"
    )

def create_superuser_prompt():
    """Prompt to create a superuser."""
    print("\n👤 Superuser Creation:")
    print("   To create a Django admin superuser, run:")
    print("   python manage.py createsuperuser")

def main():
    """Main migration generation workflow."""
    print("🚀 Django Migration Generator for SenangKira")
    print("=" * 50)
    
    # Check environment
    if not setup_virtual_environment():
        sys.exit(1)
    
    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    # Generate migrations
    generate_migrations()
    
    # Ask user if they want to apply migrations
    print("\n" + "=" * 50)
    apply = input("🤔 Do you want to apply migrations to the database? (y/N): ").lower().strip()
    
    if apply in ['y', 'yes']:
        apply_migrations()
        validate_models()
        create_superuser_prompt()
    else:
        print("   📝 Migrations created but not applied.")
        print("   To apply later, run: python manage.py migrate")
    
    print("\n🎉 Migration generation complete!")
    print("\n📖 Next steps:")
    print("   1. Review generated migration files in each app's migrations/ directory")
    print("   2. Apply migrations: python manage.py migrate")
    print("   3. Create superuser: python manage.py createsuperuser")
    print("   4. Run development server: python manage.py runserver")

if __name__ == '__main__':
    main()