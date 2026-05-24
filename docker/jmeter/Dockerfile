FROM justb4/jmeter:latest

# Install the WebSocket Samplers plugin by Peter Doornbosch (v1.3.2)
# https://github.com/ptrd/jmeter-websocket-samplers
ARG WS_PLUGIN_VERSION=1.3.2
ADD https://repo1.maven.org/maven2/net/luminis/jmeter/jmeter-websocket-samplers/${WS_PLUGIN_VERSION}/jmeter-websocket-samplers-${WS_PLUGIN_VERSION}.jar \
    /opt/apache-jmeter-5.5/lib/ext/jmeter-websocket-samplers-${WS_PLUGIN_VERSION}.jar
