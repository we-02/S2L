#!/usr/bin/env python3
"""
Automated dependency installation script for S2L
"""
import subprocess
import sys
import os

def run_pip_install(packages, description=""):
    """Run pip install for a list of packages."""
    if description:
        print(f"\n📦 Installing {description}...")
    
    for package in packages:
        print(f"   Installing {package}...")
        try:
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", package
            ], capture_output=True, text=True, check=True)
            print(f"   ✅ {package} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Failed to install {package}")
            print(f"      Error: {e.stderr}")
            return False
    return True

def main():
    """Main installation function."""
    print("=" * 60)
    print("S2L Dependency Installation")
    print("=" * 60)
    
    # Core dependencies (always needed)
    core_packages = [
        "pandas>=2.0.0",
        "openpyxl>=3.1.0", 
        "XlsxWriter>=3.1.0",
        "matplotlib>=3.7.0",
        "opencv-python>=4.8.0",
        "tqdm>=4.65.0",
        "pillow>=10.0.0",
        "PyQt6>=6.5.0",
        "numpy>=1.24.0"
    ]
    
    # Cellpose and PyTorch (for SAM support)
    ml_packages = [
        "torch>=2.0.0",
        "torchvision>=0.15.0",
        "cellpose[gui]>=4.0.0"
    ]
    
    # Optional performance packages
    optional_packages = [
        "numba>=0.57.0",
        "transformers>=4.30.0"
    ]
    
    print("This script will install the required dependencies for S2L.")
    print("This may take several minutes depending on your internet connection.")
    
    response = input("\nDo you want to continue? (y/N): ").lower().strip()
    if response not in ['y', 'yes']:
        print("Installation cancelled.")
        return
    
    # Install core packages
    if not run_pip_install(core_packages, "core dependencies"):
        print("❌ Failed to install core dependencies. Please check the errors above.")
        return
    
    # Install ML packages
    print("\n🤖 Installing machine learning packages (this may take a while)...")
    if not run_pip_install(ml_packages, "ML dependencies"):
        print("⚠️  Failed to install some ML dependencies.")
        print("   You can still use traditional Cellpose models.")
        
        # Ask if user wants to continue with optional packages
        response = input("\nDo you want to install optional packages anyway? (y/N): ").lower().strip()
        if response not in ['y', 'yes']:
            print("Skipping optional packages.")
            return
    
    # Install optional packages
    print("\n⚡ Installing optional performance packages...")
    run_pip_install(optional_packages, "optional dependencies")
    
    print("\n" + "=" * 60)
    print("🎉 Installation completed!")
    print("=" * 60)
    
    # Run verification
    print("\nRunning installation verification...")
    try:
        subprocess.run([sys.executable, "verify_installation.py"], check=True)
    except subprocess.CalledProcessError:
        print("⚠️  Verification script failed, but installation may still be successful.")
    except FileNotFoundError:
        print("⚠️  Verification script not found.")
    
    print("\nNext steps:")
    print("1. Run: python verify_installation.py")
    print("2. Run: python test_sam.py")
    print("3. Start the application: python main.py")

if __name__ == "__main__":
    main()