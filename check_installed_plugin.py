#!/usr/bin/env python3
"""Check what's actually in the installed WebSocket plugin"""
import zipfile
import sys
from pathlib import Path
from docker_manager import DockerManager
from plugin_manager import PluginManager

def main():
    dm = DockerManager()
    pm = PluginManager(dm)
    
    print("Checking installed WebSocket plugin...")
    print("=" * 60)
    
    # Get lib/ext directory
    lib_ext_dir = pm._get_jmeter_lib_ext_path()
    print(f"JMeter lib/ext: {lib_ext_dir}")
    
    # List plugins
    plugins = pm.list_installed_plugins()
    websocket_plugins = [p for p in plugins if "websocket" in p.lower()]
    print(f"\nWebSocket plugins found: {websocket_plugins}")
    
    # Check local plugin file
    plugins_dir = Path(__file__).parent / "jmeter_plugins"
    for jar_file in plugins_dir.glob("*websocket*.jar"):
        print(f"\nAnalyzing: {jar_file.name}")
        print(f"Size: {jar_file.stat().st_size} bytes")
        
        try:
            with zipfile.ZipFile(jar_file, 'r') as jar:
                # Find sampler classes
                class_files = [f for f in jar.namelist() if f.endswith('.class') and 'sampler' in f.lower()]
                print(f"\nSampler classes found ({len(class_files)}):")
                for cls in sorted(class_files)[:20]:  # Show first 20
                    class_name = cls.replace('/', '.').replace('.class', '')
                    print(f"  - {class_name}")
                
                # Check for META-INF/services (plugin registration)
                services_files = [f for f in jar.namelist() if 'META-INF/services' in f]
                if services_files:
                    print(f"\nPlugin registration files:")
                    for f in services_files:
                        print(f"  - {f}")
                        try:
                            content = jar.read(f).decode('utf-8', errors='ignore')
                            print(f"    Content:\n{content[:500]}")
                        except:
                            pass
                
                # Check manifest
                try:
                    manifest = jar.read('META-INF/MANIFEST.MF').decode('utf-8')
                    print(f"\nManifest:")
                    for line in manifest.splitlines()[:20]:
                        print(f"  {line}")
                except:
                    pass
                    
        except Exception as e:
            print(f"Error reading JAR: {e}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

