# backend/manage.py
import os
import click
from flask.cli import FlaskGroup
# Adjust import path assuming manage.py is in backend/ and app factory is in backend/app/
from app import create_app, db
from app.models import User, ConversationTurn # Import your models
# Import RAG ingestion logic if you create it
# from app.assistant.rag.ingest import ingest_documents # Example

# Create an app instance for the commands
# Loads .env implicitly if Flask-DotEnv is installed or via FlaskGroup internals
flask_env = os.getenv('FLASK_ENV', 'development')
app_instance = create_app(flask_env) # Renamed to avoid conflict with flask 'app' context

# Use FlaskGroup to integrate Flask context with Click
# Pass the factory function directly
cli = FlaskGroup(create_app=lambda: create_app(os.getenv('FLASK_ENV', 'development')))

@cli.command('create_db')
def create_db():
    """Creates the database tables."""
    click.echo("Creating database tables...")
    # Ensure commands run within application context
    with app_instance.app_context():
        db.create_all()
    click.echo("Database tables created.")

@cli.command('drop_db')
def drop_db():
    """Drops the database tables."""
    if click.confirm('Are you sure you want to lose all your data?'):
        click.echo("Dropping database tables...")
        with app_instance.app_context():
            db.drop_all()
        click.echo("Database tables dropped.")

@cli.command('seed_db')
def seed_db():
    """Seeds the database with initial data (optional)."""
    click.echo("Seeding database...")
    with app_instance.app_context():
        # Add example user or other initial data if needed
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@example.com')
            admin.set_password('password') # Change in real app
            db.session.add(admin)
            db.session.commit()
            click.echo("Admin user created.")
        else:
            click.echo("Admin user already exists.")
    click.echo("Database seeded.")

@cli.command('list_routes')
def list_routes():
    """Lists all registered routes."""
    import urllib
    output = []
    # Use the app instance created for the CLI context
    for rule in app_instance.url_map.iter_rules():
        options = {}
        for arg in rule.arguments:
            options[arg] = "[{0}]".format(arg)

        methods = ','.join(rule.methods)
        # url = urllib.parse.unquote(rule.endpoint) # rule.endpoint is the function name, rule itself is the path
        line = "{:50s} {:20s} {}".format(rule.endpoint, methods, str(rule)) # Use str(rule) for the path
        output.append(line)

    click.echo("\nRegistered Routes:")
    for line in sorted(output):
        click.echo(line)
    click.echo("-" * 70)


# --- Add RAG related commands ---
# @cli.command('rag_ingest')
# @click.argument('source_dir')
# def rag_ingest(source_dir):
#     """Ingests documents from a directory into the vector store."""
#     if not os.path.isdir(source_dir):
#         click.echo(f"Error: Source directory '{source_dir}' not found.")
#         return
#     click.echo(f"Starting ingestion from '{source_dir}'...")
#     try:
#         # Call your ingestion logic function here
#         # count = ingest_documents(source_dir)
#         count = 0 # Placeholder
#         click.echo(f"Ingestion complete. Added {count} document chunks.")
#     except Exception as e:
#         click.echo(f"Ingestion failed: {e}")

if __name__ == '__main__':
    cli()

# How to use:
# In terminal, cd to backend directory, activate venv
# Set FLASK_APP=manage.py (e.g., export FLASK_APP=manage.py)
# flask create_db
# flask list_routes
