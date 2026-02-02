#!/usr/bin/env python3
"""Verify WebSocket plugin installation and accessibility"""
import sys
from docker_manager import DockerManager
from plugin_manager import PluginManager

def main():
    dm = DockerManager()
    pm = PluginManager(dm)
    
    print("=" * 60)
    print("WebSocket Plugin Verification")
    print("=" * 60)
    
    # 1. Check if plugin JAR exists
    print("\n1. Checking if WebSocket plugin JAR exists...")
    lib_ext_dir = pm._get_jmeter_lib_ext_path()
    if not lib_ext_dir:
        print("   ❌ Could not find JMeter lib/ext directory")
        return 1
    
    print(f"   JMeter lib/ext: {lib_ext_dir}")
    
    result = dm.execute_command(
        ["sh", "-c", f"ls -la {lib_ext_dir}/*websocket*.jar 2>/dev/null || echo 'NOT FOUND'"],
        use_shell=True
    )
    
    output = result.get("output", "").strip()
    if "NOT FOUND" in output or not output:
        print("   ❌ WebSocket plugin JAR not found!")
        print("\n   Installing WebSocket plugin...")
        from websocket_plugin_agent import WebSocketPluginAgent
        ws_agent = WebSocketPluginAgent()
        install_result = ws_agent.install_plugin()
        if not install_result.get("success"):
            print(f"   ❌ Installation failed: {install_result.get('error', 'Unknown error')}")
            return 1
        print("   ✓ Plugin installed")
    else:
        print("   ✓ WebSocket plugin JAR found:")
        for line in output.splitlines():
            if ".jar" in line:
                print(f"      {line}")
    
    # 2. Verify plugin is accessible
    print("\n2. Verifying plugin is accessible...")
    verify_result = pm.verify_plugin_installed("websocket")
    if verify_result:
        print("   ✓ Plugin verified in lib/ext")
    else:
        print("   ❌ Plugin verification failed")
        return 1
    
    # 3. Check if JMeter can see the classes
    print("\n3. Testing if JMeter can load plugin classes...")
    # Create a minimal test that uses the plugin
    test_xml = '''<?xml version='1.0' encoding='utf-8'?>
<jmeterTestPlan version="1.2" properties="5.0" jmeter="5.6">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="Test Plan" enabled="true">
      <stringProp name="TestPlan.comments"></stringProp>
      <boolProp name="TestPlan.functional_mode">false</boolProp>
      <boolProp name="TestPlan.serialize_threadgroups">false</boolProp>
    </TestPlan>
    <hashTree>
      <ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup" testname="Thread Group" enabled="true">
        <stringProp name="ThreadGroup.on_sample_error">continue</stringProp>
        <elementProp name="ThreadGroup.main_controller" elementType="LoopController" guiclass="LoopControllerGui" testclass="LoopController" testname="Loop Controller" enabled="true">
          <boolProp name="LoopController.continue_forever">false</boolProp>
          <intProp name="LoopController.loops">1</intProp>
        </elementProp>
        <stringProp name="ThreadGroup.num_threads">1</stringProp>
        <stringProp name="ThreadGroup.ramp_time">1</stringProp>
        <boolProp name="ThreadGroup.scheduler">false</boolProp>
      </ThreadGroup>
      <hashTree>
        <OpenWebSocketSampler guiclass="eu.luminis.jmeter.wssampler.OpenWebSocketSamplerGui" testclass="eu.luminis.jmeter.wssampler.OpenWebSocketSampler" testname="WebSocket Open Connection" enabled="true">
          <stringProp name="OpenWebSocketSampler.server">echo.websocket.events</stringProp>
          <stringProp name="OpenWebSocketSampler.port">443</stringProp>
          <stringProp name="OpenWebSocketSampler.path">/</stringProp>
          <stringProp name="OpenWebSocketSampler.protocol">wss</stringProp>
        </OpenWebSocketSampler>
        <hashTree/>
      </hashTree>
    </hashTree>
  </hashTree>
</jmeterTestPlan>'''
    
    import tempfile
    import subprocess
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jmx', delete=False) as f:
        f.write(test_xml)
        temp_file = f.name
    
    container_name = "jmeter-automation"
    container_path = "/tmp/verify_plugin.jmx"
    
    # Copy to container
    cp_result = subprocess.run(
        ["docker", "cp", temp_file, f"{container_name}:{container_path}"],
        capture_output=True,
        text=True
    )
    
    if cp_result.returncode == 0:
        # Try to validate the test plan (this will fail if classes can't be loaded)
        result = dm.execute_command(
            ["/opt/apache-jmeter-5.5/bin/jmeter.sh", "-n", "-t", container_path, "-l", "/tmp/verify_plugin.jtl"],
            workdir="/tmp"
        )
        
        if result.get("success"):
            print("   ✓ JMeter can load WebSocket plugin classes!")
            print("   ✓ Plugin is working correctly")
        else:
            output = result.get("output", "")
            if "CannotResolveClassException" in output or "OpenWebSocketSampler" in output:
                print("   ❌ JMeter cannot resolve WebSocket plugin classes")
                print("   This means the plugin JAR is present but not being loaded")
                print("\n   Possible solutions:")
                print("   1. Restart the container: python main.py -c 'restart container'")
                print("   2. Check JMeter logs: docker exec jmeter-automation cat /tests/jmeter.log | tail -50")
                print("   3. Verify classpath includes lib/ext/*")
                return 1
            else:
                print("   ⚠ Test had errors but not related to class loading:")
                print(f"      {output[:200]}")
    else:
        print(f"   ⚠ Could not copy test file: {cp_result.stderr}")
    
    import os
    try:
        os.unlink(temp_file)
    except:
        pass
    
    print("\n" + "=" * 60)
    print("✓ Verification complete!")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())

