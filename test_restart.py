#!/usr/bin/env python3
"""Test script to verify restart and plugin installation"""
import sys
import logging
logging.basicConfig(level=logging.INFO)

from docker_manager import DockerManager
from plugin_manager import PluginManager

def main():
    print("=" * 60)
    print("Testing Container Restart and Plugin Verification")
    print("=" * 60)
    
    dm = DockerManager()
    pm = PluginManager(dm)
    
    # Step 1: Check current container status
    print("\n1. Checking container status...")
    container = dm.get_container()
    if container:
        container.reload()
        print(f"   Container status: {container.status}")
        print(f"   Container ID: {container.id[:12]}")
    else:
        print("   Container not found")
        return 1
    
    # Step 2: List installed plugins
    print("\n2. Checking installed plugins...")
    lib_ext_dir = pm._get_jmeter_lib_ext_path()
    print(f"   JMeter lib/ext: {lib_ext_dir}")
    
    plugins = pm.list_installed_plugins()
    print(f"   Found {len(plugins)} plugins:")
    for plugin in plugins:
        print(f"     - {plugin}")
    
    websocket_found = any("websocket" in p.lower() for p in plugins)
    print(f"\n   WebSocket plugin: {'✓ FOUND' if websocket_found else '✗ NOT FOUND'}")
    
    # Step 3: Restart container
    print("\n3. Restarting container...")
    print("   (This will stop and start the container to load plugins)")
    success = dm.restart_container()
    if success:
        print("   ✓ Container restarted successfully")
    else:
        print("   ✗ Failed to restart container")
        return 1
    
    # Step 4: Verify container is running
    print("\n4. Verifying container is running...")
    import time
    time.sleep(2)
    container = dm.get_container()
    if container:
        container.reload()
        if container.status == "running":
            print("   ✓ Container is running")
        else:
            print(f"   ✗ Container status: {container.status}")
            return 1
    else:
        print("   ✗ Container not found after restart")
        return 1
    
    print("\n" + "=" * 60)
    print("SUCCESS: Container restarted. WebSocket plugin should now be loaded.")
    print("=" * 60)
    print("\nYou can now run the WebSocket test:")
    print('  python main.py -c "run test" -p \'{"test_plan": "websocket_test4.jmx", "generate_report": true, "use_ai": true}\'')
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

