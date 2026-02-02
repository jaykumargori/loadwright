#!/usr/bin/env python3
"""Script to verify WebSocket plugin installation"""
import sys
from docker_manager import DockerManager
from plugin_manager import PluginManager

def main():
    dm = DockerManager()
    pm = PluginManager(dm)
    
    print("Checking WebSocket plugin installation...")
    
    # Get lib/ext directory
    lib_ext_dir = pm._get_jmeter_lib_ext_path()
    print(f"JMeter lib/ext directory: {lib_ext_dir}")
    
    if not lib_ext_dir:
        print("ERROR: Could not find JMeter lib/ext directory")
        return 1
    
    # List plugins
    plugins = pm.list_installed_plugins()
    print(f"\nInstalled plugins ({len(plugins)}):")
    for plugin in plugins:
        print(f"  - {plugin}")
    
    # Check for WebSocket plugin
    websocket_plugins = [p for p in plugins if "websocket" in p.lower()]
    if websocket_plugins:
        print(f"\n✓ WebSocket plugin found: {websocket_plugins}")
    else:
        print("\n✗ WebSocket plugin NOT found")
        print("\nInstalling WebSocket plugin...")
        success = pm.install_plugin_from_url(
            "https://github.com/MaciejZaleski/JMeter-WebSocketSampler/releases/download/v1.0.3/JMeterWebSocketSampler-1.0.3-SNAPSHOT.jar",
            "websocket-sampler"
        )
        if success:
            print("✓ Plugin installed successfully")
            print("\n⚠️  IMPORTANT: Container must be restarted for plugin to load!")
            print("   Run: python main.py -c 'restart container'")
        else:
            print("✗ Failed to install plugin")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

