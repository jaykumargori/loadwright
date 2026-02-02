#!/usr/bin/env python3
"""Remove incompatible WebSocket plugin and install a compatible one"""
import sys
from docker_manager import DockerManager
from plugin_manager import PluginManager

def main():
    print("=" * 60)
    print("Fixing WebSocket Plugin Installation")
    print("=" * 60)
    
    dm = DockerManager()
    pm = PluginManager(dm)
    
    # Step 1: Remove old plugin
    print("\n1. Removing old WebSocket plugin...")
    lib_ext_dir = pm._get_jmeter_lib_ext_path()
    if lib_ext_dir:
        result = dm.execute_command(
            ["rm", "-f", f"{lib_ext_dir}/JMeter-WebSocketSampler.jar"],
            use_shell=False
        )
        if result["success"]:
            print("   ✓ Old plugin removed")
        else:
            print(f"   ⚠ Could not remove: {result.get('output', 'Unknown')}")
    
    # Step 2: Try installing a newer version
    print("\n2. Installing compatible WebSocket plugin...")
    # Try the latest version from MaciejZaleski
    ws_url = "https://github.com/MaciejZaleski/JMeter-WebSocketSampler/releases/download/v1.0.3/JMeterWebSocketSampler-1.0.3-SNAPSHOT.jar"
    success = pm.install_plugin_from_url(ws_url, "websocket-sampler")
    
    if not success:
        print("   ⚠ Failed to install v1.0.3, trying alternative...")
        # Try a different approach - maybe the plugin needs to be built differently
        # Or we need to check dependencies
        print("   The plugin may be incompatible with JMeter 5.5")
        print("   Consider using HTTP-based WebSocket testing or a different plugin")
        return 1
    
    print("   ✓ Plugin installed")
    
    # Step 3: Restart container
    print("\n3. Restarting container to load plugin...")
    restart_success = dm.restart_container()
    if restart_success:
        print("   ✓ Container restarted")
    else:
        print("   ✗ Failed to restart container")
        return 1
    
    # Step 4: Verify installation
    print("\n4. Verifying plugin installation...")
    plugins = pm.list_installed_plugins()
    websocket_plugins = [p for p in plugins if "websocket" in p.lower()]
    if websocket_plugins:
        print(f"   ✓ WebSocket plugin found: {websocket_plugins}")
    else:
        print("   ✗ WebSocket plugin not found after installation")
        return 1
    
    print("\n" + "=" * 60)
    print("SUCCESS: WebSocket plugin reinstalled and container restarted")
    print("=" * 60)
    print("\nNote: If you still get 'CannotResolveClassException', the plugin")
    print("may be incompatible with JMeter 5.5. Consider:")
    print("  1. Using JMeter 5.4 or earlier")
    print("  2. Using a different WebSocket plugin")
    print("  3. Using HTTP-based WebSocket testing")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

