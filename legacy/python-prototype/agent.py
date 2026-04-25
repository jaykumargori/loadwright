"""
Main Agentic AI Agent for JMeter Automation
"""
import logging
from typing import Dict, Optional, List, Any
from docker_manager import DockerManager
from jmeter_controller import JMeterController
from test_plan_generator import TestPlanGenerator
from plugin_manager import PluginManager
from llm_client import LLMClient
from websocket_plugin_agent import WebSocketPluginAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JMeterAgent:
    """Main agentic AI agent for JMeter automation"""
    
    def __init__(self, llm_provider: str = "openai", llm_model: str = "gpt-4"):
        """Initialize JMeter Agent"""
        logger.info("Initializing JMeter Agent...")
        
        # Initialize components
        self.docker_manager = DockerManager()
        self.jmeter_controller = JMeterController(self.docker_manager)
        self.llm_client = LLMClient(provider=llm_provider, model=llm_model)
        self.plugin_manager = PluginManager(self.docker_manager)
        self.test_plan_generator = TestPlanGenerator(llm_client=self.llm_client, plugin_manager=self.plugin_manager)
        
        logger.info("JMeter Agent initialized")
    
    def execute_command(self, command: str, params: Dict[str, Any] = None) -> Dict:
        """Execute natural language command"""
        if params is None:
            params = {}
        
        command_lower = command.lower().strip()
        
        # Container management commands
        # IMPORTANT: Check "restart" BEFORE "start" because "restart" contains "start"
        if "restart" in command_lower and "container" in command_lower:
            return self._handle_restart_container()
        
        elif "stop" in command_lower and "container" in command_lower:
            return self._handle_stop_container()
        
        elif "start" in command_lower and "container" in command_lower:
            return self._handle_start_container()
        
        elif "status" in command_lower:
            return self._handle_status()
        
        # Plugin management
        elif "install" in command_lower and "plugin" in command_lower:
            result = self._handle_install_plugin(command, params)
            # If plugin installed successfully, restart container to load it
            if result.get("success") and result.get("message", "").startswith("Plugin"):
                logger.info("Restarting container to load new plugin...")
                restart_result = self._handle_restart_container()
                if restart_result.get("success"):
                    result["message"] += " Container restarted to load plugin."
                else:
                    result["warning"] = "Plugin installed but container restart failed. Please restart manually."
            return result
        
        elif "list" in command_lower and "plugin" in command_lower:
            return self._handle_list_plugins()
        
        # Test creation
        elif "create" in command_lower and ("test" in command_lower or "plan" in command_lower):
            return self._handle_create_test(command, params)
        
        # Test execution
        elif "run" in command_lower or "execute" in command_lower:
            return self._handle_run_test(command, params)
        
        # Test validation
        elif "validate" in command_lower:
            return self._handle_validate_test(command, params)
        
        # WebSocket plugin health check
        elif "websocket" in command_lower and ("check" in command_lower or "verify" in command_lower or "health" in command_lower):
            return self._handle_websocket_plugin_check()
        
        else:
            return {
                "success": False,
                "error": f"Unknown command: {command}",
                "available_commands": self._get_available_commands()
            }
    
    def _handle_start_container(self) -> Dict:
        """Handle container start"""
        try:
            success = self.docker_manager.start_container()
            return {
                "success": success,
                "message": "Container started" if success else "Failed to start container",
                "status": self.docker_manager.get_container_status()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _handle_stop_container(self) -> Dict:
        """Handle container stop"""
        try:
            success = self.docker_manager.stop_container()
            return {
                "success": success,
                "message": "Container stopped" if success else "Failed to stop container"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _handle_restart_container(self) -> Dict:
        """Handle container restart"""
        try:
            success = self.docker_manager.restart_container()
            return {
                "success": success,
                "message": "Container restarted" if success else "Failed to restart container",
                "status": self.docker_manager.get_container_status()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _handle_status(self) -> Dict:
        """Handle status check"""
        try:
            status = self.docker_manager.get_container_status()
            is_running = self.docker_manager.is_container_running()
            return {
                "success": True,
                "container_running": is_running,
                "status": status
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _handle_install_plugin(self, command: str, params: Dict) -> Dict:
        """Handle plugin installation"""
        try:
            plugin_url = params.get("url")
            plugin_name = params.get("name", "plugin")
            plugin_id = params.get("plugin_id")
            github_repo = params.get("github_repo")
            
            if plugin_url:
                success = self.plugin_manager.install_plugin_from_url(plugin_url, plugin_name)
            elif plugin_id:
                success = self.plugin_manager.install_plugin_from_jmeter_plugins_org(plugin_id)
            elif github_repo:
                release_tag = params.get("release_tag", "latest")
                success = self.plugin_manager.install_plugin_from_github(github_repo, release_tag)
            else:
                return {
                    "success": False,
                    "error": "Please provide plugin URL, plugin_id, or github_repo"
                }
            
            return {
                "success": success,
                "message": f"Plugin {plugin_name} installed" if success else f"Failed to install plugin {plugin_name}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _handle_list_plugins(self) -> Dict:
        """Handle list plugins"""
        try:
            plugins = self.plugin_manager.list_installed_plugins()
            return {
                "success": True,
                "plugins": plugins,
                "count": len(plugins)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _handle_websocket_plugin_check(self) -> Dict:
        """Handle WebSocket plugin health check"""
        try:
            ws_agent = WebSocketPluginAgent()
            result = ws_agent.ensure_plugin_working()
            return result
        except Exception as e:
            logger.error(f"WebSocket plugin check failed: {e}")
            import traceback
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    def _handle_create_test(self, command: str, params: Dict) -> Dict:
        """Handle test creation"""
        try:
            test_name = params.get("test_name", "test_plan")
            test_type = params.get("type", "api")  # api, websocket, performance
            
            if "prompt" in params or "description" in params:
                # Use LLM to generate test plan
                prompt = params.get("prompt") or params.get("description")
                test_plan_path = self.test_plan_generator.generate_test_plan_from_prompt(
                    prompt, test_name
                )
            elif test_type == "api":
                endpoints = params.get("endpoints", [])
                threads = params.get("threads", 1)
                ramp_up = params.get("ramp_up", 1)
                loops = params.get("loops", 1)
                test_plan_path = self.test_plan_generator.create_api_test_plan(
                    test_name, endpoints, threads, ramp_up, loops
                )
            elif test_type == "websocket":
                ws_url = params.get("ws_url", "")
                messages = params.get("messages", [])
                threads = params.get("threads", 1)
                ramp_up = params.get("ramp_up", 1)
                loops = params.get("loops", 1)
                response_delay_ms = params.get("response_delay_ms", 750)
                test_plan_path = self.test_plan_generator.create_websocket_test_plan(
                    test_name, ws_url, messages, threads, ramp_up, loops, response_delay_ms
                )
            elif test_type == "performance":
                endpoint = params.get("endpoint", {})
                threads = params.get("threads", 100)
                ramp_up = params.get("ramp_up", 10)
                duration = params.get("duration", 60)
                test_plan_path = self.test_plan_generator.create_performance_test_plan(
                    test_name, endpoint, threads, ramp_up, duration
                )
            else:
                return {
                    "success": False,
                    "error": f"Unknown test type: {test_type}"
                }
            
            if test_plan_path:
                return {
                    "success": True,
                    "test_plan": str(test_plan_path),
                    "message": f"Test plan created: {test_plan_path}"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to create test plan"
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _handle_run_test(self, command: str, params: Dict) -> Dict:
        """Handle test execution"""
        try:
            test_plan = params.get("test_plan")
            if not test_plan:
                return {"success": False, "error": "test_plan parameter required"}
            
            generate_report = params.get("generate_report", False)
            use_ai = params.get("use_ai", True)  # Default to AI-powered reports
            llm_provider = params.get("llm_provider", "openai")
            properties = params.get("properties", {})
            
            if generate_report:
                result = self.jmeter_controller.run_test_with_report(
                    test_plan, 
                    properties=properties,
                    use_ai=use_ai,
                    llm_provider=llm_provider
                )
            else:
                result = self.jmeter_controller.run_test(
                    test_plan, properties=properties
                )
            
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _handle_validate_test(self, command: str, params: Dict) -> Dict:
        """Handle test validation"""
        try:
            test_plan = params.get("test_plan")
            if not test_plan:
                return {"success": False, "error": "test_plan parameter required"}
            
            result = self.jmeter_controller.validate_test_plan(test_plan)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _get_available_commands(self) -> List[str]:
        """Get list of available commands"""
        return [
            "start container",
            "stop container",
            "restart container",
            "status",
            "install plugin",
            "list plugins",
            "create test",
            "run test",
            "validate test"
        ]
    
    def interactive_mode(self):
        """Run in interactive mode"""
        print("JMeter Automation Agent - Interactive Mode")
        print("Type 'help' for available commands or 'exit' to quit")
        
        while True:
            try:
                user_input = input("\n> ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() == "exit":
                    print("Goodbye!")
                    break
                
                if user_input.lower() == "help":
                    print("\nAvailable commands:")
                    for cmd in self._get_available_commands():
                        print(f"  - {cmd}")
                    continue
                
                # Parse command (simplified - could be enhanced with NLP)
                result = self.execute_command(user_input)
                
                if result.get("success"):
                    print(f"✓ Success: {result.get('message', 'Command executed')}")
                    if "test_plan" in result:
                        print(f"  Test plan: {result['test_plan']}")
                    if "results_file" in result:
                        print(f"  Results: {result['results_file']}")
                else:
                    print(f"✗ Error: {result.get('error', 'Unknown error')}")
                    
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")

