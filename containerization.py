"""
Containerization support for Nexus AI Assistant.

This module provides Docker configuration and container management.
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class DockerConfig:
    """Docker configuration generator."""
    
    def __init__(self, project_root: str):
        """Initialize Docker configuration generator.
        
        Args:
            project_root: Project root directory
        """
        self.project_root = Path(project_root)
        
    def generate_dockerfile(self, output_path: str = None) -> str:
        """Generate Dockerfile.
        
        Args:
            output_path: Output path for Dockerfile
            
        Returns:
            Dockerfile content
        """
        dockerfile_content = """FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential \\
    libffi-dev \\
    git \\
    && apt-get clean \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "run.py"]
"""
        
        if output_path:
            output_file = Path(output_path)
            output_file.write_text(dockerfile_content)
            logger.info(f"Dockerfile generated at {output_path}")
        
        return dockerfile_content
    
    def generate_docker_compose(self, output_path: str = None) -> str:
        """Generate docker-compose.yml.
        
        Args:
            output_path: Output path for docker-compose.yml
            
        Returns:
            docker-compose.yml content
        """
        docker_compose_content = """version: '3.8'

services:
  app:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - .:/app
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/nexus
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    restart: unless-stopped

  db:
    image: postgres:14
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=nexus
    ports:
      - "5432:5432"
    restart: unless-stopped

  redis:
    image: redis:7
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    restart: unless-stopped

  celery:
    build: .
    command: celery -A nexus.application.tasks.celery_app worker --loglevel=info
    volumes:
      - .:/app
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/nexus
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - app
      - redis
    restart: unless-stopped

  celery-beat:
    build: .
    command: celery -A nexus.application.tasks.celery_app beat --loglevel=info
    volumes:
      - .:/app
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/nexus
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - app
      - redis
    restart: unless-stopped

  flower:
    build: .
    command: celery -A nexus.application.tasks.celery_app flower --port=5555
    ports:
      - "5555:5555"
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/nexus
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - app
      - redis
      - celery
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
"""
        
        if output_path:
            output_file = Path(output_path)
            output_file.write_text(docker_compose_content)
            logger.info(f"docker-compose.yml generated at {output_path}")
        
        return docker_compose_content
    
    def generate_dockerignore(self, output_path: str = None) -> str:
        """Generate .dockerignore.
        
        Args:
            output_path: Output path for .dockerignore
            
        Returns:
            .dockerignore content
        """
        dockerignore_content = """# Git
.git
.gitignore

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/
env/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Docker
.dockerignore
Dockerfile
docker-compose.yml

# Logs
logs/
*.log

# Database
*.db
*.sqlite3

# Tests
tests/
test/
pytest_cache/
.coverage
htmlcov/

# Documentation
docs/
README.md
LICENSE

# Misc
.DS_Store
"""
        
        if output_path:
            output_file = Path(output_path)
            output_file.write_text(dockerignore_content)
            logger.info(f".dockerignore generated at {output_path}")
        
        return dockerignore_content
    
    def generate_all(self, output_dir: str = None) -> Dict[str, str]:
        """Generate all Docker configuration files.
        
        Args:
            output_dir: Output directory for Docker configuration files
            
        Returns:
            Dictionary of file names and contents
        """
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
        else:
            output_path = self.project_root
        
        dockerfile_path = output_path / "Dockerfile"
        docker_compose_path = output_path / "docker-compose.yml"
        dockerignore_path = output_path / ".dockerignore"
        
        dockerfile_content = self.generate_dockerfile(dockerfile_path)
        docker_compose_content = self.generate_docker_compose(docker_compose_path)
        dockerignore_content = self.generate_dockerignore(dockerignore_path)
        
        return {
            "Dockerfile": dockerfile_content,
            "docker-compose.yml": docker_compose_content,
            ".dockerignore": dockerignore_content
        }
