"""
setup.py - Quick Setup Script
Creates necessary directories and __init__.py files.
Run this first before starting the bot.
"""

import os
import sys


def create_directory(path):
    """Create directory if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"✓ Created directory: {path}")
    else:
        print(f"  Directory exists: {path}")


def create_file(path, content=""):
    """Create file if it doesn't exist."""
    if not os.path.exists(path):
        with open(path, 'w') as f:
            f.write(content)
        print(f"✓ Created file: {path}")
    else:
        print(f"  File exists: {path}")


def setup_project():
    """Setup project structure."""
    print("=" * 60)
    print("SMC SCALPING BOT - SETUP SCRIPT")
    print("=" * 60)
    print()
    
    # Create directories
    print("Creating directories...")
    directories = [
        'config',
        'core',
        'analysis',
        'database',
        'web',
        'web/static',
        'web/templates',
        'utils',
        'tests',
        'logs'
    ]
    
    for directory in directories:
        create_directory(directory)
    
    print()
    
    # Create __init__.py files
    print("Creating __init__.py files...")
    init_files = [
        'config/__init__.py',
        'core/__init__.py',
        'analysis/__init__.py',
        'database/__init__.py',
        'web/__init__.py',
        'utils/__init__.py',
        'tests/__init__.py'
    ]
    
    for init_file in init_files:
        create_file(init_file, "# Package initialization\n")
    
    print()
    
    # Create .env from .env.example if it doesn't exist
    print("Checking environment configuration...")
    if not os.path.exists('.env'):
        if os.path.exists('.env.example'):
            import shutil
            shutil.copy('.env.example', '.env')
            print("✓ Created .env from .env.example")
            print("  ⚠️  IMPORTANT: Edit .env with your MT5 credentials!")
        else:
            print("  ⚠️  .env.example not found. Please create .env manually.")
    else:
        print("  .env file exists")
    
    print()
    
    # Create .gitignore
    print("Creating .gitignore...")
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# Environment
.env
venv/
env/

# Logs
logs/
*.log

# Database
database/trades.db

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
"""
    create_file('.gitignore', gitignore_content)
    
    print()
    print("=" * 60)
    print("SETUP COMPLETE!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Edit .env with your MT5 credentials")
    print("2. Install dependencies: pip install -r requirements.txt")
    print("3. Run the bot: python main.py")
    print("4. Access dashboard: http://localhost:5000")
    print()
    print("For detailed instructions, see QUICKSTART.md")
    print()


def verify_files():
    """Verify all required files exist."""
    print("=" * 60)
    print("VERIFYING PROJECT FILES")
    print("=" * 60)
    print()
    
    required_files = [
        'main.py',
        'requirements.txt',
        'README.md',
        'QUICKSTART.md',
        '.env.example',
        'config/settings.py',
        'config/risk_management.py',
        'core/market_data.py',
        'core/strategy.py',
        'core/order_execution.py',
        'core/trade_manager.py',
        'analysis/indicators.py',
        'analysis/smc_logic.py',
        'analysis/liquidity.py',
        'database/database.py',
        'web/app.py',
        'web/templates/dashboard.html',
        'utils/logger_config.py',
        'utils/helpers.py',
        'tests/test_strategy.py',
        'tests/test_execution.py'
    ]
    
    missing = []
    
    for file in required_files:
        if os.path.exists(file):
            print(f"✓ {file}")
        else:
            print(f"✗ {file} - MISSING")
            missing.append(file)
    
    print()
    
    if missing:
        print(f"⚠️  {len(missing)} files are missing:")
        for f in missing:
            print(f"   - {f}")
        print()
        print("Please ensure all files are created before running the bot.")
        return False
    else:
        print("✓ All required files are present!")
        return True


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'verify':
        verify_files()
    else:
        setup_project()
        print()
        input("Press Enter to verify files...")
        print()
        verify_files()