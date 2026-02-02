"""
Docker Manager for JMeter Container Operations
"""
import docker
import logging
from typing import Optional, Dict, List
from config import JMETER_IMAGE, JMETER_CONTAINER_NAME, DOCKER_VOLUMES, JMETER_HEAP, JMETER_OPTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DockerManager:
    """Manages Docker operations for JMeter container"""
    
    def __init__(self):
        try:
            self.client = docker.from_env()
        except Exception as e:
            logger.error(f"Failed to connect to Docker: {e}")
            raise
    
    def is_container_running(self) -> bool:
        """Check if JMeter container is running"""
        try:
            container = self.client.containers.get(JMETER_CONTAINER_NAME)
            return container.status == "running"
        except docker.errors.NotFound:
            return False
    
    def get_container(self) -> Optional[docker.models.containers.Container]:
        """Get JMeter container if it exists"""
        try:
            return self.client.containers.get(JMETER_CONTAINER_NAME)
        except docker.errors.NotFound:
            return None
    
    def pull_image(self) -> None:
        """Pull JMeter Docker image"""
        logger.info(f"Pulling JMeter image: {JMETER_IMAGE}")
        self.client.images.pull(JMETER_IMAGE)
        logger.info("Image pulled successfully")
    
    def start_container(self, detach: bool = True) -> bool:
        """Start JMeter container"""
        try:
            container = self.get_container()
            
            if container:
                if container.status == "running":
                    logger.info("Container is already running")
                    return True
                elif container.status == "exited":
                    # Container exists but is stopped, remove it and create new one
                    logger.info("Removing stopped container to recreate...")
                    container.remove(force=True)
                    container = None
                else:
                    logger.info("Starting existing container")
                    container.start()
                    return True
            
            # Create new container
            logger.info("Creating new JMeter container")
            
            # Check if image exists, pull if not
            try:
                self.client.images.get(JMETER_IMAGE)
            except docker.errors.ImageNotFound:
                logger.info(f"Image {JMETER_IMAGE} not found locally, pulling...")
                self.pull_image()
            
            # Convert volumes to Docker SDK format
            volumes_dict = {
                host_path: {"bind": container_path, "mode": "rw"}
                for host_path, container_path in DOCKER_VOLUMES.items()
            }
            
            # The justb4/jmeter image has an entrypoint that might conflict
            # We need to either override the entrypoint or use a command that works with it
            # Try using entrypoint=None to override, then use tail to keep it running
            container = self.client.containers.run(
                JMETER_IMAGE,
                name=JMETER_CONTAINER_NAME,
                volumes=volumes_dict,
                detach=detach,
                tty=True,
                stdin_open=True,
                environment={
                    "HEAP": JMETER_HEAP,
                    "JMETER_OPTS": JMETER_OPTS
                },
                entrypoint=["/bin/sh"],  # Override entrypoint with shell
                command=["-c", "tail -f /dev/null"]  # Keep container running
            )
            logger.info(f"Container started: {container.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start container: {e}")
            return False
    
    def stop_container(self) -> bool:
        """Stop JMeter container"""
        try:
            container = self.get_container()
            if container:
                container.stop()
                logger.info("Container stopped")
                return True
            logger.warning("Container not found")
            return False
        except Exception as e:
            logger.error(f"Failed to stop container: {e}")
            return False
    
    def restart_container(self) -> bool:
        """Restart JMeter container"""
        logger.info("=" * 60)
        logger.info("RESTARTING CONTAINER TO LOAD PLUGINS")
        logger.info("=" * 60)
        try:
            container = self.get_container()
            if container:
                # Force restart even if running
                container.reload()
                current_status = container.status
                logger.info(f"Current container status: {current_status}")
                
                if current_status == "running":
                    logger.info("Stopping container...")
                    container.stop(timeout=10)
                    # Wait for container to fully stop
                    import time
                    time.sleep(2)
                    container.reload()
                    logger.info(f"Container stopped. Status: {container.status}")
                
                logger.info("Starting container...")
                container.start()
                # Wait for container to be ready
                import time
                time.sleep(3)
                container.reload()
                if container.status == "running":
                    logger.info("✓ Container restarted successfully")
                    logger.info(f"Container status: {container.status}")
                    return True
                else:
                    logger.error(f"Container failed to start. Status: {container.status}")
                    return False
            else:
                # If container doesn't exist, start it
                logger.info("Container not found, starting new container...")
                return self.start_container()
        except Exception as e:
            logger.error(f"Failed to restart container: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Fallback to stop/start
            try:
                logger.info("Attempting fallback: stop then start...")
                self.stop_container()
                import time
                time.sleep(2)
            except Exception as stop_error:
                logger.error(f"Failed to stop container: {stop_error}")
            return self.start_container()
    
    def remove_container(self, force: bool = False) -> bool:
        """Remove JMeter container"""
        try:
            container = self.get_container()
            if container:
                container.remove(force=force)
                logger.info("Container removed")
                return True
            logger.warning("Container not found")
            return False
        except Exception as e:
            logger.error(f"Failed to remove container: {e}")
            return False
    
    def execute_command(self, command, workdir: str = "/tests", use_shell: bool = None) -> Dict:
        """Execute command in JMeter container
        
        Args:
            command: Command as string or list. If string, will be split into list.
            workdir: Working directory in container
            use_shell: If True, execute via shell (for commands with pipes, etc.)
                      If None, auto-detect based on command content
        """
        try:
            container = self.get_container()
            if not container:
                raise Exception("Container not found. Please start the container first.")
            
            if container.status != "running":
                container.start()
            
            # Auto-detect if shell is needed (for pipes, redirects, etc.)
            if use_shell is None:
                if isinstance(command, str):
                    use_shell = any(char in command for char in ['|', '&', '>', '<', ';'])
                else:
                    use_shell = False
            
            # Convert string command to list if needed (and not using shell)
            if isinstance(command, str):
                if use_shell:
                    # For shell commands, wrap in sh -c
                    cmd_list = ["sh", "-c", command]
                else:
                    # For JMeter commands, split carefully to preserve quoted arguments
                    import shlex
                    cmd_list = shlex.split(command)
            else:
                if use_shell:
                    # Convert list to string for shell execution
                    import shlex
                    cmd_list = ["sh", "-c", " ".join(shlex.quote(str(arg)) for arg in command)]
                else:
                    cmd_list = command
            
            # Execute command
            # For justb4/jmeter, jmeter commands need proper Java heap setup
            if isinstance(cmd_list, list) and len(cmd_list) > 0 and cmd_list[0] == "jmeter":
                jmeter_args = cmd_list[1:]  # Get args after "jmeter"
                
                # Calculate heap sizes from HEAP env var (e.g., "1g" -> 1024m)
                heap_str = JMETER_HEAP.rstrip('gGmM')
                heap_unit = JMETER_HEAP[-1].lower() if len(JMETER_HEAP) > 0 and JMETER_HEAP[-1].lower() in ['g', 'm'] else 'g'
                try:
                    heap_value = int(heap_str)
                    if heap_unit == 'g':
                        heap_mb = heap_value * 1024
                    else:
                        heap_mb = heap_value
                except ValueError:
                    heap_mb = 1024  # Default to 1GB if parsing fails
                
                # Calculate Xmn (new generation) as 25% of heap
                xmn = heap_mb // 4
                
                # Find JMeter installation directory
                find_jmeter_dir = container.exec_run(
                    ["sh", "-c", "find /opt -type d -name 'apache-jmeter*' 2>/dev/null | head -1"],
                    stdout=True,
                    stderr=True
                )
                
                jmeter_dir = None
                if find_jmeter_dir.exit_code == 0 and find_jmeter_dir.output:
                    output = find_jmeter_dir.output.decode("utf-8", errors="ignore").strip()
                    if output:
                        jmeter_dir = output
                
                # Try to use jmeter.sh script which sets up classpath correctly
                if jmeter_dir:
                    jmeter_script = f"{jmeter_dir}/bin/jmeter.sh"
                    # Check if script exists
                    check_script = container.exec_run(
                        ["test", "-f", jmeter_script],
                        stdout=True,
                        stderr=True
                    )
                    
                    if check_script.exit_code == 0:
                        # Use jmeter.sh script - it handles plugin loading and XStream alias registration
                        # The script automatically includes lib/ext in the classpath and initializes plugins
                        logger.info(f"Using JMeter script: {jmeter_script}")
                        # Use the script with HEAP environment variable and ensure JMETER_HOME is set
                        exec_result = container.exec_run(
                            [jmeter_script] + jmeter_args,
                            workdir=workdir,
                            stdout=True,
                            stderr=True,
                            environment={
                                "HEAP": f"{heap_mb}m",
                                "JMETER_OPTS": JMETER_OPTS,
                                "JMETER_HOME": jmeter_dir,
                                "CLASSPATH": f"{jmeter_dir}/lib/ext/*"  # Ensure plugins are in classpath
                            }
                        )
                    else:
                        # Script doesn't exist, try direct Java with classpath
                        logger.info(f"Using JMeter jar with classpath from: {jmeter_dir}")
                        jmeter_jar = f"{jmeter_dir}/bin/ApacheJMeter.jar"
                        lib_dir = f"{jmeter_dir}/lib"
                        lib_ext_dir = f"{jmeter_dir}/lib/ext"
                        
                        # Build classpath with all jars in lib and lib/ext directories
                        # lib/ext contains plugins, which must be on the classpath
                        java_cmd = [
                            "java",
                            f"-Xmn{xmn}m",
                            f"-Xms{heap_mb}m",
                            f"-Xmx{heap_mb}m",
                            "-Dlog4j2.formatMsgNoLookups=true",
                            f"-cp", f"{jmeter_jar}:{lib_dir}/*:{lib_ext_dir}/*",
                            "org.apache.jmeter.NewDriver"
                        ] + jmeter_args
                        
                        exec_result = container.exec_run(
                            java_cmd,
                            workdir=workdir,
                            stdout=True,
                            stderr=True,
                            environment={
                                "JMETER_HOME": jmeter_dir
                            }
                        )
                else:
                    # Fallback: use entrypoint with just the args (no "jmeter" prefix)
                    logger.info("Using entrypoint script with args only")
                    exec_result = container.exec_run(
                        ["/entrypoint.sh"] + jmeter_args,
                        workdir=workdir,
                        stdout=True,
                        stderr=True
                    )
            else:
                # For other commands, execute normally
                exec_result = container.exec_run(
                    cmd_list,
                    workdir=workdir,
                    stdout=True,
                    stderr=True
                )
            
            return {
                "exit_code": exec_result.exit_code,
                "output": exec_result.output.decode("utf-8") if exec_result.output else "",
                "success": exec_result.exit_code == 0
            }
        except Exception as e:
            logger.error(f"Failed to execute command: {e}")
            return {
                "exit_code": -1,
                "output": str(e),
                "success": False
            }
    
    def get_logs(self, tail: int = 100) -> str:
        """Get container logs"""
        try:
            container = self.get_container()
            if container:
                return container.logs(tail=tail).decode("utf-8")
            return "Container not found"
        except Exception as e:
            logger.error(f"Failed to get logs: {e}")
            return str(e)
    
    def get_container_status(self) -> Dict:
        """Get detailed container status"""
        try:
            container = self.get_container()
            if container:
                container.reload()
                return {
                    "id": container.id,
                    "status": container.status,
                    "image": container.image.tags[0] if container.image.tags else "unknown",
                    "created": container.attrs["Created"],
                    "ports": container.attrs.get("NetworkSettings", {}).get("Ports", {})
                }
            return {"status": "not_found"}
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return {"status": "error", "error": str(e)}

