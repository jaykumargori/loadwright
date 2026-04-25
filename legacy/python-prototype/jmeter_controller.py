"""
JMeter Controller for Test Execution
"""
import logging
import time
from pathlib import Path
from typing import Dict, Optional, List
from docker_manager import DockerManager
from config import TESTS_DIR, RESULTS_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JMeterController:
    """Controls JMeter test execution"""
    
    def __init__(self, docker_manager: DockerManager):
        self.docker_manager = docker_manager
        self.tests_dir = TESTS_DIR
        self.results_dir = RESULTS_DIR
    
    def run_test(
        self,
        test_plan: str,
        output_file: Optional[str] = None,
        properties: Optional[Dict[str, str]] = None,
        jvm_args: Optional[str] = None
    ) -> Dict:
        """Run JMeter test plan"""
        try:
            # Ensure container is running
            if not self.docker_manager.is_container_running():
                logger.info("Starting JMeter container...")
                self.docker_manager.start_container()
                time.sleep(2)  # Wait for container to be ready
            
            test_path = Path(test_plan)
            if not test_path.is_absolute():
                test_path = self.tests_dir / test_plan
            
            if not test_path.exists():
                raise FileNotFoundError(f"Test plan not found: {test_path}")
            
            # Generate output file name if not provided
            if not output_file:
                timestamp = int(time.time())
                output_file = f"results_{timestamp}.jtl"
            
            output_path = self.results_dir / output_file
            
            # Build JMeter command
            # The justb4/jmeter image uses /entrypoint.sh which handles HEAP
            cmd_parts = [
                "jmeter",
                "-n",  # Non-GUI mode
                "-t", f"/tests/{test_path.name}",  # Test plan
                "-l", f"/results/{output_file}",  # Results file
            ]
            
            # Add properties
            if properties:
                for key, value in properties.items():
                    cmd_parts.extend(["-J", f"{key}={value}"])
            
            # Add JVM args
            if jvm_args:
                cmd_parts.extend(["-J", f"jmeter.save.saveservice.output_format=xml"])
            
            command_str = " ".join(cmd_parts)
            logger.info(f"Executing JMeter test: {command_str}")
            
            # Execute command - docker_manager will handle entrypoint detection
            result = self.docker_manager.execute_command(cmd_parts, workdir="/tests", use_shell=False)
            
            # Check if results file was created
            result_file_exists = False
            if result["success"]:
                # Verify results file
                check_result = self.docker_manager.execute_command(
                    f"test -f /results/{output_file}"
                )
                result_file_exists = check_result["success"]
            
            return {
                "success": result["success"] and result_file_exists,
                "exit_code": result["exit_code"],
                "output": result["output"],
                "test_plan": str(test_path),
                "results_file": str(output_path) if result_file_exists else None,
                "command": command_str
            }
            
        except Exception as e:
            logger.error(f"Failed to run test: {e}")
            return {
                "success": False,
                "error": str(e),
                "test_plan": test_plan
            }
    
    def run_test_with_report(
        self,
        test_plan: str,
        report_dir: Optional[str] = None,
        properties: Optional[Dict[str, str]] = None,
        use_ai: bool = True,
        llm_provider: str = "openai"
    ) -> Dict:
        """Run test and generate AI-powered HTML report"""
        try:
            timestamp = int(time.time())
            if not report_dir:
                report_dir = f"report_{timestamp}"
            
            report_path = self.results_dir / report_dir
            
            # Run test first
            test_result = self.run_test(test_plan, properties=properties)
            
            if not test_result["success"]:
                return test_result
            
            # Generate HTML report
            if not test_result.get("results_file"):
                logger.warning("No results file to generate report from")
                return {
                    **test_result,
                    "report_generated": False,
                    "report_dir": str(report_path),
                    "report_output": "No results file available"
                }
            
            results_file_path = Path(test_result["results_file"])
            
            if use_ai:
                # Use AI-powered report generator
                logger.info("Generating AI-powered HTML report...")
                from ai_report_generator import AIReportGenerator
                
                report_generator = AIReportGenerator(llm_provider=llm_provider)
                test_name = Path(test_plan).stem
                report_generated = report_generator.generate_html_report(
                    results_file_path,
                    report_path,
                    test_name
                )
                
                return {
                    **test_result,
                    "report_generated": report_generated,
                    "report_dir": str(report_path),
                    "report_file": str(report_path / "index.html"),
                    "report_type": "ai_powered"
                }
            else:
                # Use standard JMeter HTML report
                results_file = results_file_path.name
                cmd_parts = [
                    "jmeter",
                    "-g", f"/results/{results_file}",
                    "-o", f"/results/{report_dir}"
                ]
                
                logger.info("Generating standard HTML report...")
                report_result = self.docker_manager.execute_command(cmd_parts, workdir="/results", use_shell=False)
                
                # Check if report directory was created
                if report_result["success"]:
                    check_report = self.docker_manager.execute_command(
                        ["test", "-d", f"/results/{report_dir}"],
                        workdir="/results"
                    )
                    if not check_report["success"]:
                        logger.warning(f"Report directory not found: /results/{report_dir}")
                        report_result["success"] = False
                else:
                    logger.error(f"Report generation failed: {report_result.get('output', 'Unknown error')}")
                
                return {
                    **test_result,
                    "report_generated": report_result["success"],
                    "report_dir": str(report_path),
                    "report_output": report_result["output"],
                    "report_type": "standard"
                }
            
        except Exception as e:
            logger.error(f"Failed to run test with report: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def run_distributed_test(
        self,
        test_plan: str,
        remote_hosts: List[str],
        output_file: Optional[str] = None
    ) -> Dict:
        """Run distributed test across multiple JMeter servers"""
        try:
            if not self.docker_manager.is_container_running():
                self.docker_manager.start_container()
            
            test_path = Path(test_plan)
            if not test_path.is_absolute():
                test_path = self.tests_dir / test_plan
            
            if not output_file:
                timestamp = int(time.time())
                output_file = f"results_{timestamp}.jtl"
            
            # Build command with remote hosts
            hosts = ",".join(remote_hosts)
            cmd_parts = [
                "jmeter",
                "-n",
                "-t", f"/tests/{test_path.name}",
                "-R", hosts,
                "-l", f"/results/{output_file}"
            ]
            
            logger.info(f"Running distributed test on {hosts}")
            result = self.docker_manager.execute_command(cmd_parts, workdir="/tests")
            
            return {
                "success": result["success"],
                "exit_code": result["exit_code"],
                "output": result["output"],
                "remote_hosts": remote_hosts,
                "results_file": str(self.results_dir / output_file) if result["success"] else None
            }
            
        except Exception as e:
            logger.error(f"Failed to run distributed test: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def validate_test_plan(self, test_plan: str) -> Dict:
        """Validate JMeter test plan"""
        try:
            test_path = Path(test_plan)
            if not test_path.is_absolute():
                test_path = self.tests_dir / test_plan
            
            if not test_path.exists():
                return {
                    "valid": False,
                    "error": f"Test plan not found: {test_path}"
                }
            
            # Check XML validity
            import xml.etree.ElementTree as ET
            try:
                tree = ET.parse(test_path)
                root = tree.getroot()
                
                # Basic validation
                if root.tag != "jmeterTestPlan":
                    return {
                        "valid": False,
                        "error": "Invalid JMeter test plan structure"
                    }
                
                return {
                    "valid": True,
                    "test_plan": str(test_path)
                }
            except ET.ParseError as e:
                return {
                    "valid": False,
                    "error": f"XML parsing error: {e}"
                }
                
        except Exception as e:
            logger.error(f"Failed to validate test plan: {e}")
            return {
                "valid": False,
                "error": str(e)
            }
    
    def get_test_results(self, results_file: str) -> Dict:
        """Get test results summary"""
        try:
            results_path = Path(results_file)
            if not results_path.is_absolute():
                results_path = self.results_dir / results_file
            
            if not results_path.exists():
                return {
                    "success": False,
                    "error": f"Results file not found: {results_path}"
                }
            
            # Parse JTL file (simplified - would need proper parsing)
            with open(results_path, "r") as f:
                lines = f.readlines()
            
            # Basic summary
            total_samples = len([l for l in lines if l.strip() and not l.startswith("timeStamp")])
            
            return {
                "success": True,
                "results_file": str(results_path),
                "total_samples": total_samples,
                "file_size": results_path.stat().st_size
            }
            
        except Exception as e:
            logger.error(f"Failed to get test results: {e}")
            return {
                "success": False,
                "error": str(e)
            }

