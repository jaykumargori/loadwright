#!/usr/bin/env python3
"""Test if JMeter can actually load the WebSocket plugin"""
import sys
from docker_manager import DockerManager

def main():
    dm = DockerManager()
    
    print("Testing if JMeter can load the WebSocket plugin...")
    print("=" * 60)
    
    # Try to get JMeter to list available samplers or check plugin loading
    # We'll try to run JMeter with a test that should show plugin errors
    
    # First, let's check if we can see JMeter's classpath
    print("\n1. Checking JMeter classpath...")
    result = dm.execute_command(
        ["sh", "-c", "echo $CLASSPATH"],
        use_shell=True
    )
    print(f"   CLASSPATH: {result.get('output', 'Not set')}")
    
    # Check if the plugin JAR is readable
    print("\n2. Checking plugin JAR accessibility...")
    result = dm.execute_command(
        ["ls", "-la", "/opt/apache-jmeter-5.5/lib/ext/JMeter-WebSocketSampler.jar"],
        use_shell=False
    )
    if result["success"]:
        print("   ✓ Plugin JAR exists and is accessible")
        print(f"   {result['output']}")
    else:
        print("   ✗ Plugin JAR not found or not accessible")
        print(f"   Error: {result.get('output', 'Unknown')}")
    
    # Try to check JMeter version and see if it loads plugins
    print("\n3. Checking JMeter version...")
    result = dm.execute_command(
        ["/opt/apache-jmeter-5.5/bin/jmeter.sh", "--version"],
        use_shell=False
    )
    if result["success"]:
        print("   ✓ JMeter version check successful")
        print(f"   {result['output'][:200]}")
    else:
        print("   ✗ Failed to get JMeter version")
        print(f"   Error: {result.get('output', 'Unknown')}")
    
    # Try to validate a simple test plan to see plugin loading errors
    print("\n4. Testing plugin loading with a simple validation...")
    # Create a minimal test that references the plugin
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
        <WebSocketSampler guiclass="WebSocketSamplerGui" testclass="WebSocketSampler" testname="WebSocket Request" enabled="true">
          <stringProp name="WSampler.domain">echo.websocket.events</stringProp>
          <stringProp name="WSampler.port">443</stringProp>
          <stringProp name="WSampler.path">/</stringProp>
          <stringProp name="WSampler.protocol">wss</stringProp>
        </WebSocketSampler>
        <hashTree/>
      </hashTree>
    </hashTree>
  </hashTree>
</jmeterTestPlan>'''
    
    # Write test to container
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jmx', delete=False) as f:
        f.write(test_xml)
        temp_file = f.name
    
    import subprocess
    import os
    container_name = "jmeter-automation"
    container_path = "/tmp/test_plugin.jmx"
    
    # Copy to container
    cp_result = subprocess.run(
        ["docker", "cp", temp_file, f"{container_name}:{container_path}"],
        capture_output=True,
        text=True
    )
    
    if cp_result.returncode == 0:
        # Try to validate it
        result = dm.execute_command(
            ["/opt/apache-jmeter-5.5/bin/jmeter.sh", "-n", "-t", container_path, "-l", "/tmp/test_results.jtl"],
            use_shell=False
        )
        print(f"   Exit code: {result.get('exit_code', 'Unknown')}")
        if "CannotResolveClassException" in result.get("output", ""):
            print("   ✗ Plugin class not found - plugin not loaded")
            print(f"   Error: {result['output'][:500]}")
        elif result["success"]:
            print("   ✓ Test plan validated - plugin might be working!")
        else:
            print(f"   Result: {result.get('output', 'Unknown')[:500]}")
    else:
        print(f"   ✗ Failed to copy test file: {cp_result.stderr}")
    
    # Cleanup
    try:
        os.unlink(temp_file)
    except:
        pass
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

