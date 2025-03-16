"""
Setup script for Nexus AI Assistant.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

setup(
    name="nexus-ai-assistant",
    version="1.0.0",
    author="Nexus AI Team",
    author_email="info@nexus-ai.example.com",
    description="An intelligent AI assistant with modular architecture and advanced features",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nexus-ai/nexus-assistant",
    project_urls={
        "Bug Tracker": "https://github.com/nexus-ai/nexus-assistant/issues",
        "Documentation": "https://docs.nexus-ai.example.com",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "nexus=nexus.cli:main",
        ],
    },
)
