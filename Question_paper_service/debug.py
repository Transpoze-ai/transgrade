#!/usr/bin/env python3
"""
Complete .env troubleshooting script
Run this to diagnose .env file issues
"""

import os
import sys
from pathlib import Path

def check_file_existence():
    """Check if .env file exists and where"""
    print("=== FILE EXISTENCE CHECK ===")
    current_dir = Path.cwd()
    print(f"Current working directory: {current_dir}")
    
    # Check for .env in current directory
    env_file = current_dir / '.env'
    print(f"Looking for: {env_file}")
    
    if env_file.exists():
        print("✅ .env file found!")
        print(f"   File size: {env_file.stat().st_size} bytes")
        return env_file
    else:
        print("❌ .env file NOT found in current directory")
        
        # Check parent directories
        for parent in current_dir.parents:
            parent_env = parent / '.env'
            if parent_env.exists():
                print(f"📁 Found .env in parent directory: {parent_env}")
                return parent_env
        
        # List all files that start with .env
        print("\nFiles in current directory:")
        env_files = list(current_dir.glob('.env*'))
        if env_files:
            for f in env_files:
                print(f"   - {f.name}")
        else:
            print("   No .env files found")
        
        return None

def check_file_content(env_file_path):
    """Check .env file content"""
    print(f"\n=== FILE CONTENT CHECK ===")
    try:
        with open(env_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if not content.strip():
            print("❌ .env file is empty!")
            return False
        
        lines = content.strip().split('\n')
        print(f"✅ .env file has {len(lines)} lines")
        
        # Check for common issues
        issues = []
        valid_lines = 0
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            if '=' not in line:
                issues.append(f"Line {i}: No '=' found: {line}")
                continue
            
            key, value = line.split('=', 1)
            key = key.strip()
            
            if not key:
                issues.append(f"Line {i}: Empty key")
                continue
                
            # Check for spaces in key
            if ' ' in key:
                issues.append(f"Line {i}: Key contains spaces: '{key}'")
            
            # Check for quotes issues
            if value.startswith('"') and not value.endswith('"'):
                issues.append(f"Line {i}: Unmatched quotes in value")
            
            valid_lines += 1
            
            # Show first few non-sensitive variables
            if valid_lines <= 3 and not any(sensitive in key.upper() for sensitive in ['KEY', 'SECRET', 'PASSWORD', 'TOKEN']):
                print(f"   Sample: {key}={value[:50]}{'...' if len(value) > 50 else ''}")
        
        print(f"Valid configuration lines: {valid_lines}")
        
        if issues:
            print("\n⚠️  ISSUES FOUND:")
            for issue in issues:
                print(f"   {issue}")
        
        return len(issues) == 0
        
    except UnicodeDecodeError:
        print("❌ .env file has encoding issues. Try saving as UTF-8")
        return False
    except Exception as e:
        print(f"❌ Error reading .env file: {e}")
        return False

def test_python_dotenv():
    """Test if python-dotenv is working"""
    print(f"\n=== PYTHON-DOTENV TEST ===")
    
    try:
        from dotenv import load_dotenv
        print("✅ python-dotenv is installed")
    except ImportError:
        print("❌ python-dotenv is NOT installed")
        print("   Install it with: pip install python-dotenv")
        return False
    
    # Test loading
    try:
        result = load_dotenv()
        print(f"load_dotenv() result: {result}")
        
        if result:
            print("✅ .env file loaded successfully")
        else:
            print("❌ .env file was not loaded (file not found or empty)")
            
        return result
    except Exception as e:
        print(f"❌ Error loading .env: {e}")
        return False

def test_environment_variables():
    """Test if environment variables are accessible"""
    print(f"\n=== ENVIRONMENT VARIABLES TEST ===")
    
    # Test variables from your .env file
    test_vars = [
        'OPENAI_API_KEY',
        'S3_BUCKET', 
        'AWS_ACCESS_KEY_ID',
        'DJANGO_API_BASE_URL',
        'FLASK_ENV'
    ]
    
    found_vars = 0
    for var in test_vars:
        value = os.environ.get(var)
        if value:
            found_vars += 1
            # Mask sensitive values
            if any(sensitive in var.upper() for sensitive in ['KEY', 'SECRET', 'PASSWORD', 'TOKEN']):
                display_value = f"***{value[-4:]}" if len(value) > 4 else "***"
            else:
                display_value = value
            print(f"   ✅ {var} = {display_value}")
        else:
            print(f"   ❌ {var} = NOT SET")
    
    print(f"\nFound {found_vars}/{len(test_vars)} variables")
    return found_vars > 0

def manual_load_test():
    """Manually load .env file"""
    print(f"\n=== MANUAL LOAD TEST ===")
    
    env_file = Path('.env')
    if not env_file.exists():
        print("❌ .env file not found for manual test")
        return False
    
    try:
        with open(env_file, 'r') as f:
            lines = f.readlines()
        
        loaded_vars = {}
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove quotes if present
                if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                
                loaded_vars[key] = value
                os.environ[key] = value
        
        print(f"✅ Manually loaded {len(loaded_vars)} variables")
        
        # Test a few
        for key in ['OPENAI_API_KEY', 'S3_BUCKET', 'FLASK_ENV']:
            if key in loaded_vars:
                value = loaded_vars[key]
                display_value = f"***{value[-4:]}" if 'KEY' in key and len(value) > 4 else value
                print(f"   {key} = {display_value}")
        
        return True
        
    except Exception as e:
        print(f"❌ Manual load failed: {e}")
        return False

def main():
    """Run all checks"""
    print("🔍 .env File Troubleshooting Tool")
    print("=" * 50)
    
    # Step 1: Check file existence
    env_file = check_file_existence()
    if not env_file:
        print("\n💡 SOLUTION: Create a .env file in your project root directory")
        return
    
    # Step 2: Check file content
    content_ok = check_file_content(env_file)
    
    # Step 3: Test python-dotenv
    dotenv_ok = test_python_dotenv()
    
    # Step 4: Test environment variables
    env_vars_ok = test_environment_variables()
    
    # Step 5: Manual load test if dotenv failed
    if not env_vars_ok:
        print("\n🔧 Trying manual load...")
        manual_load_test()
        # Test again
        test_environment_variables()
    
    # Summary
    print(f"\n" + "=" * 50)
    print("📋 SUMMARY:")
    print(f"   File exists: {'✅' if env_file else '❌'}")
    print(f"   File content OK: {'✅' if content_ok else '❌'}")
    print(f"   python-dotenv OK: {'✅' if dotenv_ok else '❌'}")
    print(f"   Variables loaded: {'✅' if env_vars_ok else '❌'}")
    
    if not env_vars_ok:
        print(f"\n💡 NEXT STEPS:")
        if not dotenv_ok:
            print("   1. Install python-dotenv: pip install python-dotenv")
        print("   2. Make sure .env is in the same directory as your Python script")
        print("   3. Call load_dotenv() before importing your config")
        print("   4. Check .env file format (KEY=value, no spaces around =)")

if __name__ == "__main__":
    main()