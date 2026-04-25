#!/usr/bin/env python3
"""Copy WebSocket plugin JAR from local Downloads/lib/ext to Docker container"""
import sys
import subprocess
from pathlib import Path
from docker_manager import DockerManager
from plugin_manager import PluginManager

def main():
    dm = DockerManager()
    pm = PluginManager(dm)
    
    print("=" * 60)
    print("Copying WebSocket Plugin from Local System to Docker")
    print("=" * 60)
    
    # Find the plugin JAR in Downloads
    downloads_paths = [
        Path.home() / "Downloads" / "lib" / "ext",
        Path.home() / "Downloads",
        Path("/Users/jaykumargori/Downloads/lib/ext"),
        Path("/Users/jaykumargori/Downloads"),
    ]
    
    plugin_jar = None
    for base_path in downloads_paths:
        if not base_path.exists():
            continue
        
        # Look for WebSocket plugin JARs
        for pattern in ["*websocket*.jar", "*WebSocket*.jar", "*.jar"]:
            jars = list(base_path.glob(pattern))
            if jars:
                # Prefer WebSocket-related JARs
                websocket_jars = [j for j in jars if "websocket" in j.name.lower()]
                if websocket_jars:
                    plugin_jar = websocket_jars[0]
                    break
                elif pattern == "*.jar" and jars:
                    # If no WebSocket-specific JAR found, use the first JAR
                    plugin_jar = jars[0]
                    break
        
        if plugin_jar:
            break
    
    if not plugin_jar:
        print("\n❌ No JAR file found in Downloads folder")
        print("\nSearched in:")
        for path in downloads_paths:
            print(f"  - {path}")
        print("\nPlease ensure the WebSocket plugin JAR is in one of these locations:")
        print("  - ~/Downloads/lib/ext/*.jar")
        print("  - ~/Downloads/*.jar")
        return 1
    
    print(f"\n✓ Found plugin JAR: {plugin_jar}")
    print(f"  Size: {plugin_jar.stat().st_size:,} bytes")
    
    # Get container lib/ext directory
    lib_ext_dir = pm._get_jmeter_lib_ext_path()
    if not lib_ext_dir:
        print("\n❌ Could not find JMeter lib/ext directory in container")
        return 1
    
    print(f"\n📦 Copying to container: {lib_ext_dir}")
    
    # Get container name
    container = dm.get_container()
    if not container:
        print("\n❌ Container not found. Starting container...")
        if not dm.start_container():
            print("❌ Failed to start container")
            return 1
        container = dm.get_container()
    
    # Copy using Docker SDK
    print(f"\nCopying {plugin_jar.name} to container...")
    try:
        import docker
        import tarfile
        import io
        
        client = docker.from_env()
        container_obj = client.containers.get("jmeter-automation")
        
        # Create lib/ext directory if it doesn't exist
        dm.execute_command(["mkdir", "-p", lib_ext_dir], use_shell=False)
        
        # Create a tar archive in memory
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode='w') as tar:
            tar.add(plugin_jar, arcname=plugin_jar.name)
        tar_stream.seek(0)
        
        # Put archive in container
        container_obj.put_archive(lib_ext_dir, tar_stream.read())
        
        print("✓ Plugin copied successfully")
    except Exception as e:
        print(f"❌ Failed to copy using Docker SDK: {e}")
        print("Trying alternative method using execute_command...")
        # Fallback: read file and write to container
        try:
            with open(plugin_jar, 'rb') as f:
                jar_data = f.read()
            
            # Write to /tmp first
            write_result = dm.execute_command(
                ["sh", "-c", f"cat > /tmp/{plugin_jar.name}"],
                use_shell=True
            )
            
            # Use docker SDK to copy from host
            import docker
            client = docker.from_env()
            container_obj = client.containers.get("jmeter-automation")
            
            # Create tar and put archive
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                tarinfo = tarfile.TarInfo(name=plugin_jar.name)
                tarinfo.size = len(jar_data)
                tar.addfile(tarinfo, io.BytesIO(jar_data))
            tar_stream.seek(0)
            
            container_obj.put_archive(lib_ext_dir, tar_stream.read())
            print("✓ Plugin copied successfully (alternative method)")
        except Exception as e2:
            print(f"❌ All copy methods failed: {e2}")
            import traceback
            traceback.print_exc()
            return 1
    
    # Verify it's there
    verify_result = dm.execute_command(
        ["sh", "-c", f"ls -lh {lib_ext_dir}/{plugin_jar.name}"],
        use_shell=True
    )
    
    if verify_result.get("success"):
        print(f"\n✓ Verification: Plugin is in container")
        print(verify_result.get("output", ""))
    else:
        print("\n⚠️  Warning: Could not verify plugin in container")
    
    # Restart container to load plugin
    print("\n🔄 Restarting container to load plugin...")
    if dm.restart_container():
        print("✓ Container restarted successfully")
    else:
        print("⚠️  Container restart failed, but plugin should load on next JMeter run")
    
    # List all WebSocket plugins in container
    print("\n📋 WebSocket plugins in container:")
    list_result = dm.execute_command(
        ["sh", "-c", f"ls -lh {lib_ext_dir}/*websocket*.jar 2>/dev/null || echo 'No WebSocket plugins found'"],
        use_shell=True
    )
    print(list_result.get("output", "No output"))
    
    print("\n" + "=" * 60)
    print("✓ Plugin installation complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Create a new WebSocket test plan:")
    print('   python main.py -c "create test" -p \'{"test_name": "websocket_test", "type": "websocket", "ws_url": "wss://echo.websocket.events", "messages": ["Hello"]}\'')
    print("\n2. Run the test:")
    print('   python main.py -c "run test" -p \'{"test_plan": "websocket_test.jmx"}\'')
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

