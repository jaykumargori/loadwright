#!/usr/bin/env python3
"""Inspect the installed WebSocket plugin to find correct class names"""
import zipfile
import sys
from pathlib import Path
from docker_manager import DockerManager
from plugin_manager import PluginManager

def main():
    dm = DockerManager()
    pm = PluginManager(dm)
    
    print("=" * 60)
    print("Inspecting Installed WebSocket Plugin")
    print("=" * 60)
    
    # Check local plugin file
    plugins_dir = Path(__file__).parent / "jmeter_plugins"
    websocket_jars = list(plugins_dir.glob("*websocket*.jar"))
    
    if not websocket_jars:
        print("No WebSocket plugin JAR found locally")
        return 1
    
    for jar_file in websocket_jars:
        print(f"\n📦 Analyzing: {jar_file.name}")
        print(f"   Size: {jar_file.stat().st_size:,} bytes")
        
        try:
            with zipfile.ZipFile(jar_file, 'r') as jar:
                # Find all sampler classes
                all_classes = [f for f in jar.namelist() if f.endswith('.class')]
                sampler_classes = [
                    f for f in all_classes 
                    if 'sampler' in f.lower() or 'Sampler' in f
                ]
                
                print(f"\n   Total classes: {len(all_classes)}")
                print(f"   Sampler-related classes: {len(sampler_classes)}")
                
                if sampler_classes:
                    print(f"\n   🔍 Sampler Classes Found:")
                    for cls in sorted(sampler_classes)[:30]:  # Show first 30
                        class_name = cls.replace('/', '.').replace('.class', '')
                        # Extract just the class name (last part)
                        simple_name = class_name.split('.')[-1]
                        print(f"      - {simple_name} ({class_name})")
                
                # Check for META-INF/services (plugin registration)
                services_files = [f for f in jar.namelist() if 'META-INF/services' in f]
                if services_files:
                    print(f"\n   📋 Plugin Registration Files:")
                    for f in services_files:
                        print(f"      - {f}")
                        try:
                            content = jar.read(f).decode('utf-8', errors='ignore')
                            print(f"        Content:\n{content[:300]}")
                        except:
                            pass
                
                # Check manifest
                try:
                    manifest = jar.read('META-INF/MANIFEST.MF').decode('utf-8', errors='ignore')
                    print(f"\n   📄 Manifest (first 20 lines):")
                    for line in manifest.splitlines()[:20]:
                        if line.strip():
                            print(f"        {line}")
                except:
                    pass
                
                # Look for package info
                packages = set()
                for cls in all_classes:
                    parts = cls.split('/')
                    if len(parts) > 2:
                        pkg = '/'.join(parts[:-1])
                        packages.add(pkg)
                
                websocket_packages = [p for p in packages if 'websocket' in p.lower()]
                if websocket_packages:
                    print(f"\n   📁 WebSocket Packages Found:")
                    for pkg in sorted(websocket_packages):
                        print(f"      - {pkg.replace('/', '.')}")
                
        except Exception as e:
            print(f"   ❌ Error reading JAR: {e}")
            import traceback
            traceback.print_exc()
    
    # Also check what's in the container
    print("\n" + "=" * 60)
    print("Checking Container Plugin Installation")
    print("=" * 60)
    
    lib_ext_dir = pm._get_jmeter_lib_ext_path()
    if lib_ext_dir:
        print(f"   JMeter lib/ext: {lib_ext_dir}")
        result = dm.execute_command(
            ["sh", "-c", f"ls -la {lib_ext_dir}/*websocket*.jar 2>/dev/null"],
            use_shell=True
        )
        if result.get("success") and result.get("output"):
            print(f"   ✅ Plugin JARs in container:")
            print(result["output"])
        else:
            print(f"   ❌ No WebSocket plugin JARs found in container")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

