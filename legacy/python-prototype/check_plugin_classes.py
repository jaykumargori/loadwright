#!/usr/bin/env python3
"""Check what classes are in the WebSocket plugin JAR"""
import zipfile
import sys
from pathlib import Path

def main():
    plugins_dir = Path(__file__).parent / "jmeter_plugins"
    websocket_jar = None
    
    # Find WebSocket plugin JAR
    for jar_file in plugins_dir.glob("*.jar"):
        if "websocket" in jar_file.name.lower():
            websocket_jar = jar_file
            break
    
    if not websocket_jar:
        print("WebSocket plugin JAR not found in jmeter_plugins directory")
        return 1
    
    print(f"Found WebSocket plugin: {websocket_jar.name}")
    print(f"Size: {websocket_jar.stat().st_size} bytes")
    print("\n" + "=" * 60)
    print("Checking JAR contents...")
    print("=" * 60)
    
    try:
        with zipfile.ZipFile(websocket_jar, 'r') as jar:
            # List all files
            all_files = jar.namelist()
            
            # Find class files
            class_files = [f for f in all_files if f.endswith('.class')]
            
            # Find sampler-related classes
            sampler_classes = [f for f in class_files if 'sampler' in f.lower() or 'Sampler' in f]
            
            print(f"\nTotal files in JAR: {len(all_files)}")
            print(f"Class files: {len(class_files)}")
            print(f"\nSampler-related classes:")
            for cls in sorted(sampler_classes):
                # Convert path to class name
                class_name = cls.replace('/', '.').replace('.class', '')
                print(f"  - {class_name}")
            
            # Check for META-INF/services files (JMeter plugin registration)
            meta_inf_files = [f for f in all_files if 'META-INF' in f]
            if meta_inf_files:
                print(f"\nMETA-INF files (plugin registration):")
                for f in meta_inf_files:
                    print(f"  - {f}")
                    if f.endswith('.properties') or 'services' in f:
                        try:
                            content = jar.read(f).decode('utf-8')
                            print(f"    Content:\n{content}")
                        except:
                            pass
            
            # Check manifest
            try:
                manifest = jar.read('META-INF/MANIFEST.MF').decode('utf-8')
                print(f"\nManifest:")
                print(manifest[:500])
            except:
                pass
            
            # Look for any XML or properties files that might indicate the class name
            config_files = [f for f in all_files if f.endswith('.xml') or f.endswith('.properties')]
            if config_files:
                print(f"\nConfiguration files:")
                for f in config_files[:10]:  # Limit to first 10
                    print(f"  - {f}")
                    if 'sampler' in f.lower():
                        try:
                            content = jar.read(f).decode('utf-8', errors='ignore')
                            if len(content) < 500:
                                print(f"    Content:\n{content}")
                        except:
                            pass
            
    except Exception as e:
        print(f"Error reading JAR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

