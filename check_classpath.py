#!/usr/bin/env python3
"""Check if JMeter can see the WebSocket plugin classes"""
import sys
from docker_manager import DockerManager

def main():
    dm = DockerManager()
    
    print("Checking JMeter classpath and plugin loading...")
    print("=" * 60)
    
    # Check if plugin JAR is in lib/ext
    print("\n1. Checking plugin JAR location...")
    result = dm.execute_command(
        ["sh", "-c", "ls -la /opt/apache-jmeter-5.5/lib/ext/*websocket*.jar 2>/dev/null || echo 'No WebSocket plugin found'"],
        use_shell=True
    )
    print(result.get("output", "No output"))
    
    # Try to check if JMeter can see the classes by checking the classpath
    print("\n2. Checking JMeter classpath setup...")
    result = dm.execute_command(
        ["sh", "-c", "find /opt/apache-jmeter-5.5 -name 'jmeter.sh' -o -name 'ApacheJMeter.jar' | head -2"],
        use_shell=True
    )
    print(f"JMeter files: {result.get('output', 'Not found')}")
    
    # Check if we can list classes in the JAR
    print("\n3. Checking if we can read the plugin JAR...")
    result = dm.execute_command(
        ["sh", "-c", "unzip -l /opt/apache-jmeter-5.5/lib/ext/jmeter-websocket-samplers.jar 2>/dev/null | grep -i 'OpenWebSocketSampler.class' | head -1 || echo 'Class not found in JAR'"],
        use_shell=True
    )
    print(result.get("output", "No output"))
    
    # Try to run JMeter with verbose class loading to see what's happening
    print("\n4. Testing JMeter class loading...")
    # Create a minimal test that just tries to validate
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
        <HTTPSamplerProxy guiclass="HttpTestSampleGui" testclass="HTTPSamplerProxy" testname="HTTP Request" enabled="true">
          <stringProp name="HTTPSampler.domain">httpbin.org</stringProp>
          <stringProp name="HTTPSampler.port">443</stringProp>
          <stringProp name="HTTPSampler.path">/get</stringProp>
          <stringProp name="HTTPSampler.method">GET</stringProp>
          <stringProp name="HTTPSampler.protocol">https</stringProp>
        </HTTPSamplerProxy>
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
    
    # Copy to container
    container_name = "jmeter-automation"
    container_path = "/tmp/test_classpath.jmx"
    
    cp_result = subprocess.run(
        ["docker", "cp", temp_file, f"{container_name}:{container_path}"],
        capture_output=True,
        text=True
    )
    
    if cp_result.returncode == 0:
        # Try to validate the test plan
        result = dm.execute_command(
            ["/opt/apache-jmeter-5.5/bin/jmeter.sh", "-n", "-t", container_path, "-l", "/tmp/test_classpath.jtl"],
            workdir="/tmp"
        )
        print(f"JMeter validation result: {result.get('success', False)}")
        if not result.get("success"):
            print(f"Error: {result.get('output', 'Unknown error')[:500]}")
        else:
            print("✓ JMeter can run basic tests")
    
    import os
    try:
        os.unlink(temp_file)
    except:
        pass
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

