#!/usr/bin/env python3
"""
Build Lambda layer with Python dependencies
Works on Windows, Linux, and Mac
"""
import os
import sys
import subprocess
import shutil

def main():
    # Get paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    layer_dir = os.path.join(script_dir, 'layer')
    python_dir = os.path.join(layer_dir, 'python')
    requirements_file = os.path.join(script_dir, 'requirements-audio.txt')
    
    # Clean up existing layer directory
    if os.path.exists(layer_dir):
        shutil.rmtree(layer_dir)
    
    # Create layer directory structure
    os.makedirs(python_dir, exist_ok=True)
    
    # Try different pip commands (in order of preference)
    pip_commands = [
        [sys.executable, '-m', 'pip', 'install', '-r', requirements_file, '-t', python_dir, '--upgrade'],
        ['pip3', 'install', '-r', requirements_file, '-t', python_dir, '--upgrade'],
        ['pip', 'install', '-r', requirements_file, '-t', python_dir, '--upgrade'],
    ]
    
    success = False
    for cmd in pip_commands:
        try:
            print(f"Trying: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(result.stdout)
            success = True
            break
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Failed: {e}")
            continue
    
    if not success:
        print("Error: Could not install dependencies. Make sure pip is available.")
        sys.exit(1)
    
    print("Layer dependencies installed successfully")
    return 0

if __name__ == '__main__':
    sys.exit(main())

