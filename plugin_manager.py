"""
Plugin Manager for JMeter Plugins
"""
import logging
import os
import requests
import zipfile
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Optional
from docker_manager import DockerManager
from config import JMETER_PLUGINS_DIR, JMETER_CONTAINER_NAME

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PluginManager:
    """Manages JMeter plugins installation and management"""
    
    # Popular JMeter plugin repositories
    PLUGIN_REPOSITORIES = {
        "jmeter-plugins": "https://jmeter-plugins.org/get/",
        "github": "https://github.com/"
    }
    
    def __init__(self, docker_manager: DockerManager):
        self.docker_manager = docker_manager
        self.plugins_dir = JMETER_PLUGINS_DIR
        self.plugins_dir.mkdir(exist_ok=True)
    
    def install_plugin_from_url(self, url: str, plugin_name: str) -> bool:
        """Install plugin from URL"""
        try:
            logger.info(f"Downloading plugin from {url}")
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Check if URL points to a jar file directly
            if url.endswith('.jar'):
                plugin_file = self.plugins_dir / f"{plugin_name}.jar"
                with open(plugin_file, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.info(f"JAR file downloaded: {plugin_file}")
                return self._copy_to_container(plugin_file, plugin_name)
            
            # Otherwise, treat as zip
            plugin_file = self.plugins_dir / f"{plugin_name}.zip"
            
            with open(plugin_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Plugin downloaded: {plugin_file}")
            
            # Extract if it's a zip file
            extract_dir = None
            if zipfile.is_zipfile(plugin_file):
                extract_dir = self.plugins_dir / plugin_name
                extract_dir.mkdir(exist_ok=True)
                
                with zipfile.ZipFile(plugin_file, "r") as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                logger.info(f"Plugin extracted to {extract_dir}")
                
                # Look for jar files in extracted directory
                jar_files = list(extract_dir.rglob("*.jar"))
                if jar_files:
                    logger.info(f"Found {len(jar_files)} JAR file(s) in extracted archive")
                    # Copy all jar files found
                    success = True
                    for jar_file in jar_files:
                        if not self._copy_to_container(jar_file, plugin_name):
                            success = False
                    return success
                else:
                    logger.warning("No JAR files found in extracted archive. Trying to copy the zip file itself.")
            
            # Fallback: try to copy the zip file or extracted directory
            return self._copy_to_container(plugin_file, plugin_name)
            
        except Exception as e:
            logger.error(f"Failed to install plugin: {e}")
            return False
    
    def install_plugin_from_jmeter_plugins_org(self, plugin_id: str) -> bool:
        """Install plugin from jmeter-plugins.org or Maven Central
        
        Args:
            plugin_id: Plugin ID in format 'groupId:artifactId' or 'groupId:artifactId:version'
                      Example: 'nl.armatiek:jmeter-websocket-samplers' or 'nl.armatiek:jmeter-websocket-samplers:1.2.6'
                      If version is not specified, will fetch the latest version from Maven Central
        """
        try:
            parts = plugin_id.split(':')
            group_id = parts[0]
            artifact_id = parts[1] if len(parts) > 1 else None
            
            if not artifact_id:
                logger.error(f"Invalid plugin_id format: {plugin_id}")
                return False
            
            # Special handling for Luminis-Arnhem WebSocket plugin
            if ("luminis" in group_id.lower() or "armatiek" in group_id.lower()) and "websocket" in artifact_id.lower():
                logger.info("Installing Peter Doornbosch's WebSocket Sampler (Luminis-Arnhem)")
                # If version is specified, use it directly
                if len(parts) == 3:
                    version = parts[2]
                    maven_url = f"https://repo1.maven.org/maven2/{group_id.replace('.', '/')}/{artifact_id}/{version}/{artifact_id}-{version}.jar"
                    logger.info(f"Installing version {version} from Maven Central: {maven_url}")
                    if self.install_plugin_from_url(maven_url, artifact_id):
                        return True
                else:
                    # Try to get latest version from Maven Central
                    latest_version = self._get_latest_version_from_maven(group_id, artifact_id)
                    if latest_version:
                        logger.info(f"Latest version from Maven Central: {latest_version}")
                        maven_url = f"https://repo1.maven.org/maven2/{group_id.replace('.', '/')}/{artifact_id}/{latest_version}/{artifact_id}-{latest_version}.jar"
                        if self.install_plugin_from_url(maven_url, artifact_id):
                            return True
                
                # Fallback: Try GitHub releases
                logger.info("Maven Central failed, trying GitHub releases...")
                return self.install_plugin_from_github("Luminis-Arnhem/jmeter-websocket-samplers", "latest")
            
            # If version is specified, use it
            if len(parts) == 3:
                version = parts[2]
                maven_url = f"https://repo1.maven.org/maven2/{group_id.replace('.', '/')}/{artifact_id}/{version}/{artifact_id}-{version}.jar"
                logger.info(f"Installing specific version from Maven Central: {maven_url}")
                if self.install_plugin_from_url(maven_url, artifact_id):
                    return True
            else:
                # Fetch latest version from Maven Central metadata
                logger.info(f"Fetching latest version of {group_id}:{artifact_id} from Maven Central...")
                latest_version = self._get_latest_version_from_maven(group_id, artifact_id)
                
                if latest_version:
                    logger.info(f"Latest version found: {latest_version}")
                    maven_url = f"https://repo1.maven.org/maven2/{group_id.replace('.', '/')}/{artifact_id}/{latest_version}/{artifact_id}-{latest_version}.jar"
                    if self.install_plugin_from_url(maven_url, artifact_id):
                        return True
                else:
                    logger.warning("Could not determine latest version from Maven Central, trying jmeter-plugins.org...")
            
            # Fallback to jmeter-plugins.org
            url = f"{self.PLUGIN_REPOSITORIES['jmeter-plugins']}{plugin_id}/"
            return self.install_plugin_from_url(url, artifact_id)
        except Exception as e:
            logger.error(f"Failed to install from jmeter-plugins.org: {e}")
            return False
    
    def _get_latest_version_from_maven(self, group_id: str, artifact_id: str) -> Optional[str]:
        """Get latest version from Maven Central metadata"""
        try:
            # Maven Central metadata URL
            metadata_url = f"https://repo1.maven.org/maven2/{group_id.replace('.', '/')}/{artifact_id}/maven-metadata.xml"
            logger.info(f"Fetching Maven metadata: {metadata_url}")
            
            response = requests.get(metadata_url, timeout=10)
            response.raise_for_status()
            
            # Parse XML to get latest version
            root = ET.fromstring(response.text)
            
            # Find latest version
            versioning = root.find('versioning')
            if versioning is not None:
                latest = versioning.find('latest')
                if latest is not None and latest.text:
                    return latest.text
                
                # Fallback: get the last version from versions list
                versions = versioning.find('versions')
                if versions is not None:
                    version_list = [v.text for v in versions.findall('version') if v.text]
                    if version_list:
                        # Filter out snapshot versions and get the latest
                        release_versions = [v for v in version_list if not v.endswith('-SNAPSHOT')]
                        if release_versions:
                            # Sort and get latest
                            from packaging import version as packaging_version
                            try:
                                release_versions.sort(key=packaging_version.parse, reverse=True)
                                return release_versions[0]
                            except:
                                # Fallback to simple string comparison
                                release_versions.sort(reverse=True)
                                return release_versions[0]
                        # If no release versions, return the latest snapshot
                        version_list.sort(reverse=True)
                        return version_list[0]
            
            return None
        except Exception as e:
            logger.warning(f"Failed to get latest version from Maven Central: {e}")
            return None
    
    def install_plugin_from_github(self, repo: str, release_tag: str = "latest") -> bool:
        """Install plugin from GitHub release"""
        try:
            # Get latest release info
            api_url = f"https://api.github.com/repos/{repo}/releases"
            if release_tag == "latest":
                api_url += "/latest"
            else:
                api_url += f"/tags/{release_tag}"
            
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            release_data = response.json()
            
            # For latest release, it's a single object, for tags it's an array
            if isinstance(release_data, list):
                release_data = release_data[0] if release_data else {}
            
            # Find jar file in assets
            jar_asset = None
            for asset in release_data.get("assets", []):
                if asset["name"].endswith(".jar"):
                    jar_asset = asset
                    break
            
            if jar_asset:
                return self.install_plugin_from_url(jar_asset["browser_download_url"], repo.split("/")[-1])
            
            if not jar_asset:
                    # Try downloading from release page directly
                    logger.warning(f"No jar file found in release assets for {repo}. Trying alternative method...")
                    # For WebSocket plugin, try direct download
                    if "websocket" in repo.lower():
                        if "luminis" in repo.lower() or "arnhem" in repo.lower():
                            # Luminis-Arnhem plugin - try to get the JAR from releases
                            # This plugin has multiple samplers, not a single WebSocketSampler
                            logger.info("Luminis-Arnhem plugin uses different sampler names. Trying to install...")
                            # Try to find the JAR in the latest release
                            releases_url = f"https://api.github.com/repos/{repo}/releases/latest"
                            try:
                                rel_response = requests.get(releases_url, timeout=10)
                                if rel_response.status_code == 200:
                                    release_data = rel_response.json()
                                    for asset in release_data.get("assets", []):
                                        if asset["name"].endswith(".jar") and "jmeter-websocket" in asset["name"].lower():
                                            return self.install_plugin_from_url(asset["browser_download_url"], "websocket-samplers")
                            except:
                                pass
                        # MaciejZaleski plugin - try direct download URL
                        ws_url = "https://github.com/MaciejZaleski/JMeter-WebSocketSampler/releases/latest/download/WebSocketSampler-1.4.0.jar"
                        return self.install_plugin_from_url(ws_url, "websocket-sampler")
                    raise Exception("No jar file found in release")
            
            return self.install_plugin_from_url(jar_asset["browser_download_url"], repo.split("/")[-1])
            
        except Exception as e:
            logger.error(f"Failed to install plugin from GitHub: {e}")
            return False
    
    def _copy_to_container(self, plugin_file: Path, plugin_name: str) -> bool:
        """Copy plugin to JMeter container"""
        try:
            # Copy file to container's lib/ext directory
            container = self.docker_manager.get_container()
            if not container:
                logger.error("Container not found")
                return False
            
            # Get JMeter lib/ext directory path
            lib_ext_dir = self._get_jmeter_lib_ext_path()
            if not lib_ext_dir:
                logger.error("Could not find or create JMeter lib/ext directory")
                return False
            
            # If it's a jar file, copy directly using Docker SDK
            if plugin_file.suffix == '.jar':
                try:
                    import docker
                    import tarfile
                    import io
                    
                    client = docker.from_env()
                    container_obj = client.containers.get(JMETER_CONTAINER_NAME)
                    
                    # Create a tar archive in memory
                    tar_stream = io.BytesIO()
                    with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                        tar.add(plugin_file, arcname=plugin_file.name)
                    tar_stream.seek(0)
                    
                    # Put archive in container
                    container_obj.put_archive(lib_ext_dir, tar_stream.read())
                    logger.info(f"Plugin JAR copied to container: {plugin_file.name} -> {lib_ext_dir}")
                    return True
                except ImportError:
                    logger.warning("Docker SDK not available, trying subprocess method...")
                    # Fallback to subprocess
                    import subprocess
                    dest_path = f"{JMETER_CONTAINER_NAME}:{lib_ext_dir}/{plugin_file.name}"
                    result = subprocess.run(
                        ["docker", "cp", str(plugin_file), dest_path],
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode == 0:
                        logger.info(f"Plugin JAR copied to container: {plugin_file.name} -> {lib_ext_dir}")
                        return True
                    else:
                        logger.error(f"Failed to copy plugin: {result.stderr}")
                        return False
                except Exception as e:
                    logger.error(f"Failed to copy plugin using Docker SDK: {e}")
                    return False
            
            # If it's a zip file, extract and find jar files
            import zipfile
            import tempfile
            
            jar_files = []
            if zipfile.is_zipfile(plugin_file):
                # Extract jar files from zip
                with tempfile.TemporaryDirectory() as temp_dir:
                    with zipfile.ZipFile(plugin_file, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)
                    
                    # Find all jar files recursively
                    temp_path = Path(temp_dir)
                    jar_files = list(temp_path.rglob("*.jar"))
            
            # Copy all found jar files to container
            if jar_files:
                # Get JMeter lib/ext directory path
                lib_ext_dir = self._get_jmeter_lib_ext_path()
                if not lib_ext_dir:
                    logger.error("Could not find or create JMeter lib/ext directory")
                    return False
                
                import subprocess
                success_count = 0
                for jar_file in jar_files:
                    dest_path = f"{JMETER_CONTAINER_NAME}:{lib_ext_dir}/{jar_file.name}"
                    result = subprocess.run(
                        ["docker", "cp", str(jar_file), dest_path],
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode == 0:
                        logger.info(f"Plugin file copied to container: {jar_file.name}")
                        success_count += 1
                    else:
                        logger.error(f"Failed to copy plugin file {jar_file.name}: {result.stderr}")
                        # Try alternative method
                        temp_path = f"{JMETER_CONTAINER_NAME}:/tmp/{jar_file.name}"
                        cp_result = subprocess.run(
                            ["docker", "cp", str(jar_file), temp_path],
                            capture_output=True,
                            text=True
                        )
                        if cp_result.returncode == 0:
                            move_result = self.docker_manager.execute_command(
                                ["mv", f"/tmp/{jar_file.name}", f"{lib_ext_dir}/"]
                            )
                            if move_result["success"]:
                                logger.info(f"Plugin file moved to container: {jar_file.name}")
                                success_count += 1
                
                return success_count > 0
            else:
                logger.error("No JAR files found to copy")
                return False
                
        except Exception as e:
            logger.error(f"Failed to copy plugin to container: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _get_jmeter_lib_ext_path(self) -> Optional[str]:
        """Get the JMeter lib/ext directory path"""
        try:
            # Find JMeter installation directory
            find_jmeter = self.docker_manager.execute_command(
                ["sh", "-c", "find /opt -type d -name 'apache-jmeter*' 2>/dev/null | head -1"]
            )
            
            if find_jmeter["success"] and find_jmeter.get("output"):
                jmeter_dir = find_jmeter["output"].strip()
                if jmeter_dir:
                    lib_ext_dir = f"{jmeter_dir}/lib/ext"
                    # Ensure directory exists
                    mkdir_result = self.docker_manager.execute_command(
                        ["mkdir", "-p", lib_ext_dir]
                    )
                    return lib_ext_dir
            return None
        except Exception as e:
            logger.error(f"Failed to find JMeter lib/ext directory: {e}")
            return None
    
    def list_installed_plugins(self) -> List[str]:
        """List installed plugins in container"""
        try:
            lib_ext_dir = self._get_jmeter_lib_ext_path()
            if not lib_ext_dir:
                return []
            
            result = self.docker_manager.execute_command(
                ["sh", "-c", f"ls -la {lib_ext_dir}/ | grep -E '\\.jar$'"],
                use_shell=True
            )
            
            if result["success"]:
                plugins = [
                    line.split()[-1] 
                    for line in result["output"].splitlines() 
                    if ".jar" in line
                ]
                return plugins
            return []
        except Exception as e:
            logger.error(f"Failed to list plugins: {e}")
            return []
    
    def remove_plugin(self, plugin_name: str) -> bool:
        """Remove plugin from container"""
        try:
            result = self.docker_manager.execute_command(
                f"rm -f /opt/apache-jmeter/lib/ext/{plugin_name}"
            )
            return result["success"]
        except Exception as e:
            logger.error(f"Failed to remove plugin: {e}")
            return False
    
    def install_plugin_via_plugins_manager(self, plugin_id: str) -> bool:
        """Install plugin using JMeter Plugins Manager (PluginsManagerCMD)
        
        Args:
            plugin_id: Plugin ID (e.g., 'jpgc-websocket' or 'nl.armatiek:jmeter-websocket-samplers')
        
        Returns:
            True if installation successful, False otherwise
        """
        try:
            # First, download Plugins Manager if not present
            lib_ext_dir = self._get_jmeter_lib_ext_path()
            if not lib_ext_dir:
                logger.error("Could not find JMeter lib/ext directory")
                return False
            
            plugins_manager_jar = f"{lib_ext_dir}/jmeter-plugins-manager.jar"
            cmdrunner_jar = f"{lib_ext_dir}/cmdrunner.jar"
            
            # Check if Plugins Manager is installed
            check_result = self.docker_manager.execute_command(
                ["sh", "-c", f"test -f {plugins_manager_jar} && echo 'exists' || echo 'missing'"],
                use_shell=True
            )
            
            if "missing" in check_result.get("output", ""):
                logger.info("Plugins Manager not found. Downloading...")
                # Download Plugins Manager
                pm_url = "https://jmeter-plugins.org/get/"
                try:
                    response = requests.get(pm_url, timeout=10)
                    if response.status_code == 200:
                        # The URL might redirect or return HTML, try direct download
                        pm_direct_url = "https://repo1.maven.org/maven2/kg/apc/jmeter-plugins-manager/1.7/jmeter-plugins-manager-1.7.jar"
                        cmdrunner_url = "https://repo1.maven.org/maven2/kg/apc/cmdrunner/2.3/cmdrunner-2.3.jar"
                        
                        # Download both
                        for url, dest in [(pm_direct_url, plugins_manager_jar), (cmdrunner_url, cmdrunner_jar)]:
                            logger.info(f"Downloading {url}...")
                            resp = requests.get(url, timeout=30)
                            resp.raise_for_status()
                            
                            # Copy to container
                            import tempfile
                            import subprocess
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.jar') as f:
                                f.write(resp.content)
                                temp_file = f.name
                            
                            # Copy to container
                            container_name = self.docker_manager.get_container().name if self.docker_manager.get_container() else JMETER_CONTAINER_NAME
                            cp_result = subprocess.run(
                                ["docker", "cp", temp_file, f"{container_name}:{dest}"],
                                capture_output=True,
                                text=True
                            )
                            import os
                            os.unlink(temp_file)
                            
                            if cp_result.returncode != 0:
                                logger.warning(f"Failed to copy {dest}: {cp_result.stderr}")
                                return False
                        
                        logger.info("Plugins Manager installed successfully")
                    else:
                        logger.warning("Could not download Plugins Manager. Using manual installation method.")
                        return False
                except Exception as e:
                    logger.warning(f"Failed to download Plugins Manager: {e}. Using manual installation method.")
                    return False
            
            # Now use Plugins Manager to install the plugin
            logger.info(f"Installing plugin {plugin_id} via Plugins Manager...")
            
            # Find JMeter home
            jmeter_home_result = self.docker_manager.execute_command(
                ["sh", "-c", "find /opt -maxdepth 2 -name 'apache-jmeter*' -type d | head -1"],
                use_shell=True
            )
            jmeter_home = jmeter_home_result.get("output", "").strip() if jmeter_home_result.get("success") else "/opt/apache-jmeter-5.5"
            
            # Run Plugins Manager command
            install_cmd = [
                "java",
                "-cp", f"{plugins_manager_jar}:{cmdrunner_jar}",
                "org.jmeterplugins.repository.PluginManagerCMDInstaller",
                "install",
                plugin_id
            ]
            
            result = self.docker_manager.execute_command(
                install_cmd,
                workdir=lib_ext_dir,
                use_shell=False
            )
            
            if result.get("success"):
                logger.info(f"Plugin {plugin_id} installed via Plugins Manager")
                return True
            else:
                logger.warning(f"Plugins Manager installation failed: {result.get('output', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to install via Plugins Manager: {e}")
            return False
    
    def verify_plugin_installed(self, plugin_name_pattern: str) -> bool:
        """Verify if a plugin is installed by checking lib/ext directory
        
        Args:
            plugin_name_pattern: Pattern to match plugin name (e.g., 'websocket')
        
        Returns:
            True if plugin found, False otherwise
        """
        try:
            lib_ext_dir = self._get_jmeter_lib_ext_path()
            if not lib_ext_dir:
                return False
            
            result = self.docker_manager.execute_command(
                ["sh", "-c", f"ls -1 {lib_ext_dir}/*{plugin_name_pattern}*.jar 2>/dev/null | wc -l"],
                use_shell=True
            )
            
            if result.get("success"):
                count = result.get("output", "0").strip()
                return int(count) > 0
            
            return False
        except Exception as e:
            logger.error(f"Failed to verify plugin: {e}")
            return False
    
    def install_common_plugins(self) -> Dict[str, bool]:
        """Install common useful plugins"""
        common_plugins = {
            "jmeter-plugins-standard": "kg.apc:jmeter-plugins-standard:1.4.0",
            "jmeter-plugins-extras": "kg.apc:jmeter-plugins-extras:1.4.0",
            "jmeter-plugins-webdriver": "kg.apc:jmeter-plugins-webdriver:3.4",
        }
        
        results = {}
        for name, plugin_id in common_plugins.items():
            logger.info(f"Installing {name}...")
            results[name] = self.install_plugin_from_jmeter_plugins_org(plugin_id)
        
        return results

