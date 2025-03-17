"""
Package configuration for Nexus AI Assistant.
"""

from setuptools import find_namespace_packages

# Package metadata
PACKAGE_NAME = "nexus-ai-assistant"
PACKAGE_VERSION = "1.0.0"
PACKAGE_DESCRIPTION = "An intelligent AI assistant with modular architecture and advanced features"
PACKAGE_AUTHOR = "Nexus AI Team"
PACKAGE_AUTHOR_EMAIL = "info@nexus-ai.example.com"
PACKAGE_URL = "https://github.com/nexus-ai/nexus-assistant"
PACKAGE_LICENSE = "MIT"

# Package configuration
package_config = {
    "name": PACKAGE_NAME,
    "version": PACKAGE_VERSION,
    "description": PACKAGE_DESCRIPTION,
    "author": PACKAGE_AUTHOR,
    "author_email": PACKAGE_AUTHOR_EMAIL,
    "url": PACKAGE_URL,
    "license": PACKAGE_LICENSE,
    "packages": find_namespace_packages(include=["nexus", "nexus.*"]),
    "include_package_data": True,
    "zip_safe": False,
    "python_requires": ">=3.10",
    "entry_points": {
        "console_scripts": [
            "nexus=nexus.cli:main",
        ],
    },
    "classifiers": [
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
}

# Package dependencies
dependencies = [
    "Flask>=2.3.3",
    "python-dotenv>=1.0.0",
    "spacy>=3.7.2",
    "transformers>=4.35.2",
    "pandas>=2.1.1",
    "scikit-learn>=1.3.2",
    "requests>=2.31.0",
    "google-auth>=2.23.0",
    "Flask-Limiter>=2.8.0",
    "Flask-CORS>=4.3.0",
    "redis>=4.6.0",
    "celery>=5.3.1",
    "flower>=1.2.0",
    "openai>=0.28.1",
    "bleach>=6.0.0",
    "defusedxml>=0.7.1",
    "pytest>=7.4.0",
    "prometheus_client>=0.15.0",
    "Flask-SQLAlchemy>=3.0.5",
    "chromadb>=0.4.18",
    "sentence-transformers>=2.2.2",
    "beautifulsoup4>=4.12.2",
    "SpeechRecognition>=3.10.0",
    "pyttsx3>=2.90",
    "watchdog>=3.0.0",
    "psutil>=5.9.5",
]

# Development dependencies
dev_dependencies = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "black>=23.7.0",
    "isort>=5.12.0",
    "flake8>=6.1.0",
    "mypy>=1.5.1",
    "sphinx>=7.1.2",
    "sphinx-rtd-theme>=1.3.0",
]

# Extra dependencies
extra_dependencies = {
    "dev": dev_dependencies,
    "test": [
        "pytest>=7.4.0",
        "pytest-cov>=4.1.0",
    ],
    "docs": [
        "sphinx>=7.1.2",
        "sphinx-rtd-theme>=1.3.0",
    ],
    "gpu": [
        "torch>=2.0.0",
        "GPUtil>=1.4.0",
    ],
}

# Package data
package_data = {
    "nexus": [
        "presentation/web/templates/*.html",
        "presentation/web/static/css/*.css",
        "presentation/web/static/js/*.js",
        "presentation/web/static/img/*.png",
        "presentation/web/static/img/*.jpg",
        "presentation/web/static/img/*.svg",
    ],
}

# Data files
data_files = [
    ("", ["LICENSE", "README.md"]),
]
