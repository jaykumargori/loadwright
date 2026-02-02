"""
AI-Powered Test Plan Generator for JMeter
"""
import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
from pathlib import Path
from config import TESTS_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestPlanGenerator:
    """Generates JMeter test plans using AI/LLM"""
    
    def __init__(self, llm_client=None, plugin_manager=None):
        self.llm_client = llm_client
        self.tests_dir = TESTS_DIR
        self.plugin_manager = plugin_manager
    
    def generate_test_plan_from_prompt(self, prompt: str, test_name: str) -> Optional[Path]:
        """Generate test plan from natural language prompt using LLM"""
        if not self.llm_client:
            logger.warning("LLM client not configured, using template-based generation")
            return self._generate_basic_test_plan(test_name, prompt)
        
        try:
            # Use LLM to generate test plan structure
            llm_prompt = f"""
            Generate a JMeter test plan XML based on the following requirements:
            {prompt}
            
            Provide the complete JMeter test plan XML structure. Include:
            - TestPlan element with appropriate properties
            - ThreadGroup with configured threads, ramp-up, and loops
            - HTTP Request Samplers if API testing is needed
            - WebSocket Samplers if WebSocket testing is needed
            - Listeners for results
            
            Return only valid JMeter XML.
            """
            
            response = self.llm_client.generate(llm_prompt)
            test_plan_xml = self._extract_xml_from_response(response)
            
            if test_plan_xml:
                return self._save_test_plan(test_name, test_plan_xml)
            else:
                logger.warning("Failed to extract XML from LLM response, using template")
                return self._generate_basic_test_plan(test_name, prompt)
                
        except Exception as e:
            logger.error(f"Failed to generate test plan with LLM: {e}")
            return self._generate_basic_test_plan(test_name, prompt)
    
    def create_api_test_plan(
        self,
        test_name: str,
        endpoints: List[Dict],
        threads: int = 1,
        ramp_up: int = 1,
        loops: int = 1
    ) -> Path:
        """Create API test plan"""
        root = ET.Element("jmeterTestPlan", version="1.2", properties="5.0", jmeter="5.6")
        
        hash_tree = ET.SubElement(root, "hashTree")
        
        # Test Plan
        test_plan = ET.SubElement(hash_tree, "TestPlan", guiclass="TestPlanGui", testclass="TestPlan", testname="Test Plan", enabled="true")
        test_plan_elements = ET.SubElement(test_plan, "elementProp", name="TestPlan.arguments", elementType="Arguments", guiclass="ArgumentsPanel", testclass="Arguments", testname="User Defined Variables", enabled="true")
        ET.SubElement(test_plan_elements, "collectionProp", name="Arguments.arguments")
        ET.SubElement(test_plan, "stringProp", name="TestPlan.comments")
        ET.SubElement(test_plan, "boolProp", name="TestPlan.functional_mode").text = "false"
        ET.SubElement(test_plan, "boolProp", name="TestPlan.serialize_threadgroups").text = "false"
        ET.SubElement(test_plan, "elementProp", name="TestPlan.arguments", elementType="Arguments", guiclass="ArgumentsPanel", testclass="Arguments", testname="User Defined Variables", enabled="true")
        ET.SubElement(test_plan, "stringProp", name="TestPlan.user_define_classpath")
        
        hash_tree2 = ET.SubElement(hash_tree, "hashTree")
        
        # Thread Group
        thread_group = ET.SubElement(hash_tree2, "ThreadGroup", guiclass="ThreadGroupGui", testclass="ThreadGroup", testname="Thread Group", enabled="true")
        ET.SubElement(thread_group, "stringProp", name="ThreadGroup.on_sample_error").text = "continue"
        ET.SubElement(thread_group, "elementProp", name="ThreadGroup.main_controller", elementType="LoopController", guiclass="LoopControllerGui", testclass="LoopController", testname="Loop Controller", enabled="true")
        ET.SubElement(thread_group.find("elementProp"), "boolProp", name="LoopController.continue_forever").text = "false"
        ET.SubElement(thread_group.find("elementProp"), "intProp", name="LoopController.loops").text = str(loops)
        ET.SubElement(thread_group, "stringProp", name="ThreadGroup.num_threads").text = str(threads)
        ET.SubElement(thread_group, "stringProp", name="ThreadGroup.ramp_time").text = str(ramp_up)
        ET.SubElement(thread_group, "boolProp", name="ThreadGroup.scheduler").text = "false"
        ET.SubElement(thread_group, "stringProp", name="ThreadGroup.duration")
        ET.SubElement(thread_group, "stringProp", name="ThreadGroup.delay")
        
        hash_tree3 = ET.SubElement(hash_tree2, "hashTree")
        
        # Add HTTP Requests directly under ThreadGroup's hashTree
        for endpoint in endpoints:
            http_request = ET.SubElement(hash_tree3, "HTTPSamplerProxy", guiclass="HttpTestSampleGui", testclass="HTTPSamplerProxy", testname=endpoint.get("name", "HTTP Request"), enabled="true")
            ET.SubElement(http_request, "boolProp", name="HTTPSampler.postBodyRaw").text = "false"
            ET.SubElement(http_request, "elementProp", name="HTTPsampler.Arguments", elementType="Arguments", guiclass="HTTPArgumentsPanel", testclass="Arguments", testname="User Defined Variables", enabled="true")
            ET.SubElement(http_request.find("elementProp"), "collectionProp", name="Arguments.arguments")
            ET.SubElement(http_request, "stringProp", name="HTTPSampler.domain").text = endpoint.get("domain", "")
            port_elem = ET.SubElement(http_request, "stringProp", name="HTTPSampler.port")
            port_value = endpoint.get("port", "")
            if port_value:
                port_elem.text = str(port_value)
            ET.SubElement(http_request, "stringProp", name="HTTPSampler.protocol").text = endpoint.get("protocol", "https")
            ET.SubElement(http_request, "stringProp", name="HTTPSampler.contentEncoding")
            ET.SubElement(http_request, "stringProp", name="HTTPSampler.path").text = endpoint.get("path", "/")
            ET.SubElement(http_request, "stringProp", name="HTTPSampler.method").text = endpoint.get("method", "GET")
            ET.SubElement(http_request, "boolProp", name="HTTPSampler.follow_redirects").text = "true"
            ET.SubElement(http_request, "boolProp", name="HTTPSampler.auto_redirects").text = "false"
            ET.SubElement(http_request, "boolProp", name="HTTPSampler.use_keepalive").text = "true"
            ET.SubElement(http_request, "boolProp", name="HTTPSampler.DO_MULTIPART_POST").text = "false"
            ET.SubElement(http_request, "stringProp", name="HTTPSampler.embedded_url_re")
            ET.SubElement(http_request, "stringProp", name="HTTPSampler.connect_timeout")
            ET.SubElement(http_request, "stringProp", name="HTTPSampler.response_timeout")
            
            hash_tree5 = ET.SubElement(hash_tree3, "hashTree")
            
            # Response Assertion
            assertion = ET.SubElement(hash_tree5, "ResponseAssertion", guiclass="AssertionGui", testclass="ResponseAssertion", testname="Response Assertion", enabled="true")
            ET.SubElement(assertion, "collectionProp", name="Asserion.test_strings")
            ET.SubElement(assertion, "stringProp", name="Assertion.custom_message")
            ET.SubElement(assertion, "stringProp", name="Assertion.test_field").text = "Assertion.response_code"
            ET.SubElement(assertion, "boolProp", name="Assertion.assume_success").text = "false"
            ET.SubElement(assertion, "intProp", name="Assertion.test_type").text = "1"
            
            hash_tree6 = ET.SubElement(hash_tree5, "hashTree")
        
        # View Results Tree Listener (at ThreadGroup level)
        listener = ET.SubElement(hash_tree3, "ResultCollector", guiclass="ViewResultsFullVisualizer", testclass="ResultCollector", testname="View Results Tree", enabled="true")
        ET.SubElement(listener, "boolProp", name="ResultCollector.error_logging").text = "false"
        ET.SubElement(listener, "objProp")
        ET.SubElement(listener, "stringProp", name="filename")
        hash_tree7 = ET.SubElement(hash_tree3, "hashTree")
        
        # Summary Report
        summary = ET.SubElement(hash_tree7, "ResultCollector", guiclass="SummaryReport", testclass="ResultCollector", testname="Summary Report", enabled="true")
        ET.SubElement(summary, "boolProp", name="ResultCollector.error_logging").text = "false"
        ET.SubElement(summary, "objProp")
        ET.SubElement(summary, "stringProp", name="filename")
        hash_tree8 = ET.SubElement(hash_tree7, "hashTree")
        
        # Save test plan with proper formatting
        tree = ET.ElementTree(root)
        test_file = self.tests_dir / f"{test_name}.jmx"
        
        # Format XML with indentation for better readability and debugging
        def indent(elem, level=0):
            i = "\n" + level * "  "
            if len(elem):
                if not elem.text or not elem.text.strip():
                    elem.text = i + "  "
                if not elem.tail or not elem.tail.strip():
                    elem.tail = i
                for child in elem:
                    indent(child, level+1)
                if not child.tail or not child.tail.strip():
                    child.tail = i
            else:
                if level and (not elem.tail or not elem.tail.strip()):
                    elem.tail = i
        
        indent(root)
        
        tree.write(test_file, encoding="utf-8", xml_declaration=True)
        
        logger.info(f"API test plan created: {test_file}")
        return test_file
    
    def create_websocket_test_plan(
        self,
        test_name: str,
        ws_url: str = None,
        messages: List[str] = None,
        threads: int = 1,
        ramp_up: int = 1,
        loops: int = 1,
        response_delay_ms: int = 750
    ) -> Path:
        """Create WebSocket test plan using WebSocket Sampler
        
        Args:
            test_name: Name of the test plan
            ws_url: WebSocket URL (default: wss://echo.websocket.events - a working echo server)
            messages: List of messages to send
            threads: Number of threads
            ramp_up: Ramp-up time in seconds
            loops: Number of loops
            response_delay_ms: Delay in milliseconds before closing connection (default: 750ms, range: 500-1000ms)
        """
        # Use a working WebSocket echo server if none provided
        # Note: echo.websocket.org is deprecated. Alternatives:
        # - wss://echo.websocket.events (public echo server)
        # - ws://localhost:8080 (local test server)
        # - Your own WebSocket server
        if not ws_url:
            ws_url = "wss://echo.websocket.events"
        
        if not messages:
            messages = ["Hello", "World"]
        logger.info(f"Creating WebSocket test plan: {test_name}")
        
        # Check and install WebSocket plugin if needed
        if self.plugin_manager:
            logger.info("Checking for WebSocket plugin...")
            installed_plugins = self.plugin_manager.list_installed_plugins()
            websocket_plugin_found = any("websocket" in plugin.lower() for plugin in installed_plugins)
            
            if not websocket_plugin_found:
                # Use WebSocket Plugin Agent to ensure plugin is installed and working
                from websocket_plugin_agent import WebSocketPluginAgent
                logger.info("Using WebSocket Plugin Agent to verify installation...")
                ws_agent = WebSocketPluginAgent()
                agent_result = ws_agent.ensure_plugin_working()
                
                if agent_result.get("success"):
                    logger.info("WebSocket plugin verified and working")
                    success = True
                else:
                    logger.warning(f"WebSocket plugin agent failed: {agent_result.get('error')}")
                    success = False
            else:
                # Plugin found, but verify it's working
                logger.info("WebSocket plugin found. Verifying it's working...")
                from websocket_plugin_agent import WebSocketPluginAgent
                ws_agent = WebSocketPluginAgent()
                test_result = ws_agent.test_plugin_working()
                
                if not test_result.get("success"):
                    logger.warning("WebSocket plugin found but test failed. Reinstalling...")
                    agent_result = ws_agent.ensure_plugin_working()
                    success = agent_result.get("success", False)
                else:
                    success = True
                    logger.info("WebSocket plugin already installed and working")
            
            # Handle restart if plugin was installed/reinstalled
            if success and not websocket_plugin_found:
                logger.info("WebSocket plugin installed successfully")
                # Restart container to load the new plugin
                if self.plugin_manager.docker_manager:
                    logger.info("Restarting container to load WebSocket plugin...")
                    restart_success = self.plugin_manager.docker_manager.restart_container()
                    if restart_success:
                        logger.info("Container restarted successfully")
                    else:
                        logger.warning("Failed to restart container. You may need to restart it manually.")
            elif not success:
                logger.warning("Failed to install WebSocket plugin. Test plan will be created but may not work without the plugin.")
                logger.warning("You can manually install it using:")
                logger.warning("  python main.py -c 'websocket check'")
        
        root = ET.Element("jmeterTestPlan", version="1.2", properties="5.0", jmeter="5.6")
        hash_tree = ET.SubElement(root, "hashTree")
        
        # Test Plan
        test_plan = ET.SubElement(hash_tree, "TestPlan", guiclass="TestPlanGui", testclass="TestPlan", testname="Test Plan", enabled="true")
        ET.SubElement(test_plan, "elementProp", name="TestPlan.arguments", elementType="Arguments", guiclass="ArgumentsPanel", testclass="Arguments", testname="User Defined Variables", enabled="true")
        ET.SubElement(test_plan.find("elementProp"), "collectionProp", name="Arguments.arguments")
        ET.SubElement(test_plan, "stringProp", name="TestPlan.comments")
        ET.SubElement(test_plan, "boolProp", name="TestPlan.functional_mode").text = "false"
        ET.SubElement(test_plan, "boolProp", name="TestPlan.serialize_threadgroups").text = "false"
        ET.SubElement(test_plan, "stringProp", name="TestPlan.user_define_classpath")
        
        hash_tree2 = ET.SubElement(hash_tree, "hashTree")
        
        # Thread Group
        thread_group = ET.SubElement(hash_tree2, "ThreadGroup", guiclass="ThreadGroupGui", testclass="ThreadGroup", testname="Thread Group", enabled="true")
        ET.SubElement(thread_group, "stringProp", name="ThreadGroup.on_sample_error").text = "continue"
        loop_controller = ET.SubElement(thread_group, "elementProp", name="ThreadGroup.main_controller", elementType="LoopController", guiclass="LoopControllerGui", testclass="LoopController", testname="Loop Controller", enabled="true")
        ET.SubElement(loop_controller, "boolProp", name="LoopController.continue_forever").text = "false"
        ET.SubElement(loop_controller, "intProp", name="LoopController.loops").text = str(loops)
        ET.SubElement(thread_group, "stringProp", name="ThreadGroup.num_threads").text = str(threads)
        ET.SubElement(thread_group, "stringProp", name="ThreadGroup.ramp_time").text = str(ramp_up)
        ET.SubElement(thread_group, "boolProp", name="ThreadGroup.scheduler").text = "false"
        ET.SubElement(thread_group, "stringProp", name="ThreadGroup.duration")
        ET.SubElement(thread_group, "stringProp", name="ThreadGroup.delay")
        
        hash_tree3 = ET.SubElement(hash_tree2, "hashTree")
        
        # Parse WebSocket URL
        if ws_url.startswith("ws://"):
            protocol = "ws"
            url_parts = ws_url[5:].split("/", 1)
        elif ws_url.startswith("wss://"):
            protocol = "wss"
            url_parts = ws_url[6:].split("/", 1)
        else:
            protocol = "ws"
            url_parts = ws_url.split("/", 1)
        
        host_port = url_parts[0].split(":")
        domain = host_port[0]
        port = host_port[1] if len(host_port) > 1 else ("443" if protocol == "wss" else "80")
        path = "/" + url_parts[1] if len(url_parts) > 1 else "/"
        
        # Detect which WebSocket plugin is installed
        # Check for Luminis-Arnhem plugin (jmeter-websocket-samplers)
        installed_plugins = self.plugin_manager.list_installed_plugins() if self.plugin_manager else []
        is_luminis_plugin = any("jmeter-websocket-samplers" in p.lower() or "luminis" in p.lower() for p in installed_plugins)
        
        if is_luminis_plugin:
            # Use Luminis-Arnhem plugin samplers
            # Full package names: eu.luminis.jmeter.wssampler.OpenWebSocketSampler, etc.
            # XML element names: OpenWebSocketSampler (simple name)
            # testclass attribute: Full package name (eu.luminis.jmeter.wssampler.OpenWebSocketSampler)
            logger.info("Using Luminis-Arnhem WebSocket plugin samplers")
            
            # Step 1: Open Connection
            # Use full package-qualified class name as XML element name
            # This is required for JMeter's XStream to resolve the class in non-GUI mode
            ws_open = ET.SubElement(hash_tree3, "eu.luminis.jmeter.wssampler.OpenWebSocketSampler", 
                                   guiclass="eu.luminis.jmeter.wssampler.OpenWebSocketSamplerGui", 
                                   testclass="eu.luminis.jmeter.wssampler.OpenWebSocketSampler", 
                                   testname="WebSocket Open Connection", enabled="true")
            ET.SubElement(ws_open, "stringProp", name="OpenWebSocketSampler.server").text = domain
            ET.SubElement(ws_open, "stringProp", name="OpenWebSocketSampler.port").text = port
            ET.SubElement(ws_open, "stringProp", name="OpenWebSocketSampler.path").text = path
            ET.SubElement(ws_open, "stringProp", name="OpenWebSocketSampler.protocol").text = protocol
            ET.SubElement(ws_open, "stringProp", name="OpenWebSocketSampler.implementation").text = "RFC6455"
            ET.SubElement(ws_open, "stringProp", name="OpenWebSocketSampler.responseTimeout").text = "5000"
            ET.SubElement(ws_open, "stringProp", name="OpenWebSocketSampler.connectionTimeout").text = "5000"
            ET.SubElement(hash_tree3, "hashTree")
            
            # Step 2: Send messages using RequestResponseWebSocketSampler
            for i, message in enumerate(messages):
                ws_request_response = ET.SubElement(hash_tree3, "eu.luminis.jmeter.wssampler.RequestResponseWebSocketSampler", 
                                                   guiclass="eu.luminis.jmeter.wssampler.RequestResponseWebSocketSamplerGui", 
                                                   testclass="eu.luminis.jmeter.wssampler.RequestResponseWebSocketSampler", 
                                                   testname=f"WebSocket Send/Receive {i+1}", enabled="true")
                ET.SubElement(ws_request_response, "stringProp", name="RequestResponseWebSocketSampler.request").text = message
                ET.SubElement(ws_request_response, "stringProp", name="RequestResponseWebSocketSampler.responseTimeout").text = "5000"
                ET.SubElement(hash_tree3, "hashTree")
            
            # Step 3: Constant Timer - Wait for response before closing
            # This ensures we receive responses from the server before closing the connection
            # Default delay is 750ms (middle of 500-1000ms range)
            delay_ms = max(500, min(1000, response_delay_ms))  # Clamp between 500-1000ms
            constant_timer = ET.SubElement(hash_tree3, "ConstantTimer", 
                                          guiclass="ConstantTimerGui", 
                                          testclass="ConstantTimer", 
                                          testname="Wait for Response", enabled="true")
            ET.SubElement(constant_timer, "stringProp", name="ConstantTimer.delay").text = str(delay_ms)
            ET.SubElement(hash_tree3, "hashTree")
            
            # Step 4: Close Connection
            ws_close = ET.SubElement(hash_tree3, "eu.luminis.jmeter.wssampler.CloseWebSocketSampler", 
                                    guiclass="eu.luminis.jmeter.wssampler.CloseWebSocketSamplerGui", 
                                    testclass="eu.luminis.jmeter.wssampler.CloseWebSocketSampler", 
                                    testname="WebSocket Close Connection", enabled="true")
            ET.SubElement(hash_tree3, "hashTree")
        else:
            # Use MaciejZaleski plugin (WebSocketSampler) - legacy support
            logger.info("Using MaciejZaleski WebSocket plugin (WebSocketSampler)")
            ws_sampler = ET.SubElement(hash_tree3, "WebSocketSampler", guiclass="WebSocketSamplerGui", testclass="WebSocketSampler", testname="WebSocket Request", enabled="true")
            ET.SubElement(ws_sampler, "stringProp", name="WSampler.domain").text = domain
            ET.SubElement(ws_sampler, "stringProp", name="WSampler.port").text = port
            ET.SubElement(ws_sampler, "stringProp", name="WSampler.path").text = path
            ET.SubElement(ws_sampler, "stringProp", name="WSampler.protocol").text = protocol
            ET.SubElement(ws_sampler, "stringProp", name="WSampler.request_data").text = "\n".join(messages) if messages else ""
            ET.SubElement(ws_sampler, "stringProp", name="WSampler.response_timeout").text = "5000"
            ET.SubElement(ws_sampler, "stringProp", name="WSampler.connection_timeout").text = "5000"
            ET.SubElement(ws_sampler, "boolProp", name="WSampler.streaming_connection").text = "false"
            ET.SubElement(ws_sampler, "boolProp", name="WSampler.close_connection").text = "true"
            ET.SubElement(hash_tree3, "hashTree")
        
        # Response Assertion (directly under ThreadGroup's hashTree, not nested)
        assertion = ET.SubElement(hash_tree3, "ResponseAssertion", guiclass="AssertionGui", testclass="ResponseAssertion", testname="Response Assertion", enabled="true")
        ET.SubElement(assertion, "collectionProp", name="Asserion.test_strings")
        ET.SubElement(assertion, "stringProp", name="Assertion.custom_message")
        ET.SubElement(assertion, "stringProp", name="Assertion.test_field").text = "Assertion.response_code"
        ET.SubElement(assertion, "boolProp", name="Assertion.assume_success").text = "false"
        ET.SubElement(assertion, "intProp", name="Assertion.test_type").text = "1"
        ET.SubElement(hash_tree3, "hashTree")
        
        # Save test plan
        tree = ET.ElementTree(root)
        test_file = self.tests_dir / f"{test_name}.jmx"
        
        # Format XML
        def indent(elem, level=0):
            i = "\n" + level * "  "
            if len(elem):
                if not elem.text or not elem.text.strip():
                    elem.text = i + "  "
                if not elem.tail or not elem.tail.strip():
                    elem.tail = i
                for child in elem:
                    indent(child, level+1)
                if not child.tail or not child.tail.strip():
                    child.tail = i
            else:
                if level and (not elem.tail or not elem.tail.strip()):
                    elem.tail = i
        
        indent(root)
        tree.write(test_file, encoding="utf-8", xml_declaration=True)
        
        logger.info(f"WebSocket test plan created: {test_file}")
        return test_file
    
    def create_performance_test_plan(
        self,
        test_name: str,
        endpoint: Dict,
        threads: int = 100,
        ramp_up: int = 10,
        duration: int = 60
    ) -> Path:
        """Create performance/load test plan"""
        return self.create_api_test_plan(
            test_name,
            [endpoint],
            threads,
            ramp_up,
            loops=-1  # Infinite loops for duration-based tests
        )
    
    def _generate_basic_test_plan(self, test_name: str, prompt: str) -> Path:
        """Generate basic test plan from prompt (template-based)"""
        # Extract basic info from prompt
        endpoints = [{"name": "Test API", "domain": "httpbin.org", "path": "/get", "method": "GET"}]
        return self.create_api_test_plan(test_name, endpoints)
    
    def _extract_xml_from_response(self, response: str) -> Optional[str]:
        """Extract XML from LLM response"""
        # Try to find XML content in response
        if "<?xml" in response:
            start = response.find("<?xml")
            end = response.rfind("</jmeterTestPlan>") + len("</jmeterTestPlan>")
            if end > start:
                return response[start:end]
        return None
    
    def _save_test_plan(self, test_name: str, xml_content: str) -> Path:
        """Save test plan to file"""
        test_file = self.tests_dir / f"{test_name}.jmx"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(xml_content)
        logger.info(f"Test plan saved: {test_file}")
        return test_file

