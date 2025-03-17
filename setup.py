"""
Setup script for Nexus AI Assistant.

This script helps set up the Nexus AI Assistant by:
1. Creating necessary directories
2. Installing dependencies
3. Setting up configuration
"""
import os
import argparse
import subprocess
import shutil
import secrets
from pathlib import Path

def create_directories():
    """Create necessary directories."""
    print("Creating directories...")
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    # Create an empty .gitkeep file in data directory
    with open(os.path.join("data", ".gitkeep"), "w") as f:
        pass
        
    print("Directories created.")

def install_dependencies(dev=False):
    """Install Python dependencies."""
    print("Installing dependencies...")
    
    # Install requirements
    if dev:
        subprocess.run(["pip", "install", "-r", "requirements-dev.txt"], check=True)
    else:
        subprocess.run(["pip", "install", "-r", "requirements.txt"], check=True)
        
    print("Dependencies installed.")

def setup_config():
    """Set up configuration files."""
    print("Setting up configuration...")
    
    # Create .env file if it doesn't exist
    env_file = ".env"
    env_example = ".env.example"
    
    if not os.path.exists(env_file) and os.path.exists(env_example):
        print(f"Creating {env_file} from {env_example}")
        shutil.copy(env_example, env_file)
        
        # Generate a secure random secret key
        with open(env_file, "r") as f:
            env_content = f.read()
            
        env_content = env_content.replace("your_secret_key_here", secrets.token_hex(16))
        
        with open(env_file, "w") as f:
            f.write(env_content)
            
        print(f"{env_file} created. Please update with your API keys and configuration.")
    else:
        print(f"{env_file} already exists or {env_example} not found.")
        
    print("Configuration setup complete.")

def main():
    """Run the setup script."""
    parser = argparse.ArgumentParser(description="Set up Nexus AI Assistant")
    parser.add_argument("--dev", action="store_true", help="Install development dependencies")
    args = parser.parse_args()
    
    print("Setting up Nexus AI Assistant...")
    
    create_directories()
    install_dependencies(args.dev)
    setup_config()
    
    print("\nSetup complete! You can now run Nexus AI Assistant with:")
    print("  python app.py")
    print("\nMake sure to update your .env file with the necessary API keys.")

if __name__ == "__main__":
    main()
