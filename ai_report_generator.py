"""
AI-Powered HTML Report Generator for JMeter Results
"""
import logging
import csv
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from llm_client import LLMClient
from config import RESULTS_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIReportGenerator:
    """Generates dynamic HTML reports using AI analysis of JMeter results"""
    
    def __init__(self, llm_provider: str = "openai", llm_model: str = "gpt-4"):
        self.llm_client = LLMClient(provider=llm_provider, model=llm_model)
        self.results_dir = RESULTS_DIR
    
    def parse_jtl_file(self, jtl_path: Path) -> Dict:
        """Parse JMeter JTL results file"""
        try:
            results = {
                "samples": [],
                "total_samples": 0,
                "successful": 0,
                "failed": 0,
                "total_time": 0,
                "min_response_time": float('inf'),
                "max_response_time": 0,
                "total_bytes": 0,
                "errors": [],
                "endpoints": {},
                "response_codes": {}
            }
            
            with open(jtl_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    elapsed = float(row.get('elapsed', 0))
                    success = row.get('success', 'true').lower() == 'true'
                    response_code = row.get('responseCode', '')
                    label = row.get('label', 'Unknown')
                    bytes_sent = int(row.get('bytes', 0))
                    
                    results["samples"].append({
                        "timestamp": int(row.get('timeStamp', 0)),
                        "elapsed": elapsed,
                        "label": label,
                        "response_code": response_code,
                        "success": success,
                        "bytes": bytes_sent,
                        "url": row.get('URL', ''),
                        "latency": float(row.get('Latency', 0)),
                        "thread_name": row.get('threadName', '')
                    })
                    
                    results["total_samples"] += 1
                    if success:
                        results["successful"] += 1
                    else:
                        results["failed"] += 1
                        failure_msg = row.get('failureMessage', '')
                        if failure_msg:
                            results["errors"].append({
                                "label": label,
                                "error": failure_msg,
                                "response_code": response_code
                            })
                    
                    results["total_time"] += elapsed
                    results["min_response_time"] = min(results["min_response_time"], elapsed)
                    results["max_response_time"] = max(results["max_response_time"], elapsed)
                    results["total_bytes"] += bytes_sent
                    
                    # Track endpoints
                    if label not in results["endpoints"]:
                        results["endpoints"][label] = {
                            "count": 0,
                            "success": 0,
                            "failed": 0,
                            "total_time": 0,
                            "min_time": float('inf'),
                            "max_time": 0
                        }
                    results["endpoints"][label]["count"] += 1
                    results["endpoints"][label]["total_time"] += elapsed
                    results["endpoints"][label]["min_time"] = min(results["endpoints"][label]["min_time"], elapsed)
                    results["endpoints"][label]["max_time"] = max(results["endpoints"][label]["max_time"], elapsed)
                    if success:
                        results["endpoints"][label]["success"] += 1
                    else:
                        results["endpoints"][label]["failed"] += 1
                    
                    # Track response codes
                    if response_code:
                        results["response_codes"][response_code] = results["response_codes"].get(response_code, 0) + 1
            
            # Calculate averages
            if results["total_samples"] > 0:
                results["avg_response_time"] = results["total_time"] / results["total_samples"]
                results["success_rate"] = (results["successful"] / results["total_samples"]) * 100
                results["error_rate"] = (results["failed"] / results["total_samples"]) * 100
            else:
                results["avg_response_time"] = 0
                results["success_rate"] = 0
                results["error_rate"] = 0
            
            # Calculate endpoint averages
            for endpoint in results["endpoints"].values():
                if endpoint["count"] > 0:
                    endpoint["avg_time"] = endpoint["total_time"] / endpoint["count"]
                    endpoint["success_rate"] = (endpoint["success"] / endpoint["count"]) * 100
            
            if results["min_response_time"] == float('inf'):
                results["min_response_time"] = 0
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to parse JTL file: {e}")
            return {}
    
    def generate_ai_analysis(self, results: Dict) -> str:
        """Generate AI analysis of test results"""
        if not self.llm_client.is_available():
            return """
            <div style="padding: 20px; background: #fff3cd; border: 1px solid #ffc107; border-radius: 5px; margin: 15px 0;">
                <h3 style="color: #856404; margin-bottom: 10px;">⚠️ AI Analysis Not Available</h3>
                <p style="color: #856404; margin-bottom: 10px;">
                    To enable AI-powered analysis, please set one of the following environment variables:
                </p>
                <ul style="color: #856404; margin-left: 20px;">
                    <li><code>OPENAI_API_KEY</code> - For OpenAI (GPT-4, GPT-3.5)</li>
                    <li><code>ANTHROPIC_API_KEY</code> - For Anthropic (Claude)</li>
                    <li><code>GEMINI_API_KEY</code> - For Google Gemini</li>
                </ul>
                <p style="color: #856404; margin-top: 10px;">
                    Example: <code>export OPENAI_API_KEY="your-api-key"</code>
                </p>
            </div>
            """
        
        try:
            # Prepare summary for AI
            summary = {
                "total_samples": results.get("total_samples", 0),
                "successful": results.get("successful", 0),
                "failed": results.get("failed", 0),
                "success_rate": round(results.get("success_rate", 0), 2),
                "avg_response_time": round(results.get("avg_response_time", 0), 2),
                "min_response_time": round(results.get("min_response_time", 0), 2),
                "max_response_time": round(results.get("max_response_time", 0), 2),
                "total_bytes": results.get("total_bytes", 0),
                "endpoints": len(results.get("endpoints", {})),
                "errors": len(results.get("errors", [])),
                "response_codes": results.get("response_codes", {})
            }
            
            # Get top errors
            top_errors = results.get("errors", [])[:5]
            
            prompt = f"""Analyze the following JMeter performance test results and provide:
1. Executive Summary (2-3 sentences)
2. Key Findings (bullet points)
3. Performance Insights (response times, throughput)
4. Error Analysis (if any errors)
5. Recommendations (actionable items)

Test Results Summary:
{json.dumps(summary, indent=2)}

Top Errors:
{json.dumps(top_errors, indent=2)}

Endpoint Performance:
{json.dumps({k: {"avg_time": round(v.get("avg_time", 0), 2), "success_rate": round(v.get("success_rate", 0), 2), "count": v.get("count", 0)} for k, v in results.get("endpoints", {}).items()}, indent=2)}

Provide a comprehensive analysis in HTML format with proper formatting, charts recommendations, and actionable insights."""
            
            analysis = self.llm_client.generate(prompt, max_tokens=3000)
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to generate AI analysis: {e}")
            return f"<p>Error generating AI analysis: {str(e)}</p>"
    
    def generate_html_report(self, jtl_path: Path, output_path: Path, test_name: str = "JMeter Test") -> bool:
        """Generate dynamic HTML report with AI analysis"""
        try:
            logger.info(f"Parsing results from: {jtl_path}")
            results = self.parse_jtl_file(jtl_path)
            
            if not results or results.get("total_samples", 0) == 0:
                logger.warning("No results to generate report from")
                return False
            
            logger.info("Generating AI analysis...")
            ai_analysis = self.generate_ai_analysis(results)
            
            # Generate HTML report
            html_content = self._create_html_template(results, ai_analysis, test_name, jtl_path.name)
            
            # Save report
            output_path.mkdir(parents=True, exist_ok=True)
            report_file = output_path / "index.html"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"AI-powered HTML report generated: {report_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate HTML report: {e}")
            return False
    
    def _create_html_template(self, results: Dict, ai_analysis: str, test_name: str, jtl_filename: str) -> str:
        """Create HTML template with embedded data and AI analysis"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Prepare data for charts
        endpoint_data = []
        for name, data in results.get("endpoints", {}).items():
            endpoint_data.append({
                "name": name,
                "avg_time": round(data.get("avg_time", 0), 2),
                "success_rate": round(data.get("success_rate", 0), 2),
                "count": data.get("count", 0)
            })
        
        response_codes_json = json.dumps(results.get("response_codes", {}))
        endpoint_data_json = json.dumps(endpoint_data)
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI-Powered JMeter Test Report - {test_name}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .header p {{
            opacity: 0.9;
            font-size: 1.1em;
        }}
        .content {{
            padding: 30px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 25px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }}
        .stat-card:hover {{
            transform: translateY(-5px);
        }}
        .stat-card h3 {{
            color: #667eea;
            font-size: 2em;
            margin-bottom: 10px;
        }}
        .stat-card p {{
            color: #666;
            font-size: 1.1em;
        }}
        .success {{ color: #10b981; }}
        .error {{ color: #ef4444; }}
        .warning {{ color: #f59e0b; }}
        .ai-analysis {{
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 25px;
            margin: 30px 0;
            border-radius: 5px;
        }}
        .ai-analysis h2 {{
            color: #667eea;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .ai-analysis h2::before {{
            content: "🤖";
            font-size: 1.5em;
        }}
        .chart-container {{
            background: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .chart-container h3 {{
            color: #333;
            margin-bottom: 15px;
        }}
        .endpoint-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .endpoint-table th {{
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
        }}
        .endpoint-table td {{
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }}
        .endpoint-table tr:hover {{
            background: #f5f7fa;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            background: #f8f9fa;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 AI-Powered JMeter Test Report</h1>
            <p>{test_name} | Generated: {timestamp}</p>
            <p>Source: {jtl_filename}</p>
        </div>
        
        <div class="content">
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>{results.get('total_samples', 0):,}</h3>
                    <p>Total Samples</p>
                </div>
                <div class="stat-card">
                    <h3 class="success">{results.get('successful', 0):,}</h3>
                    <p>Successful</p>
                </div>
                <div class="stat-card">
                    <h3 class="error">{results.get('failed', 0):,}</h3>
                    <p>Failed</p>
                </div>
                <div class="stat-card">
                    <h3>{round(results.get('success_rate', 0), 2)}%</h3>
                    <p>Success Rate</p>
                </div>
                <div class="stat-card">
                    <h3>{round(results.get('avg_response_time', 0), 2)} ms</h3>
                    <p>Avg Response Time</p>
                </div>
                <div class="stat-card">
                    <h3>{round(results.get('min_response_time', 0), 2)} ms</h3>
                    <p>Min Response Time</p>
                </div>
                <div class="stat-card">
                    <h3>{round(results.get('max_response_time', 0), 2)} ms</h3>
                    <p>Max Response Time</p>
                </div>
                <div class="stat-card">
                    <h3>{round(results.get('total_bytes', 0) / 1024, 2)} KB</h3>
                    <p>Total Data</p>
                </div>
            </div>
            
            <div class="ai-analysis">
                <h2>AI Analysis & Insights</h2>
                <div>{ai_analysis}</div>
            </div>
            
            <div class="chart-container">
                <h3>Response Code Distribution</h3>
                <canvas id="responseCodeChart"></canvas>
            </div>
            
            <div class="chart-container">
                <h3>Endpoint Performance (Average Response Time)</h3>
                <canvas id="endpointChart"></canvas>
            </div>
            
            <div class="chart-container">
                <h3>Endpoint Success Rates</h3>
                <canvas id="successRateChart"></canvas>
            </div>
            
            <h3 style="margin-top: 30px;">Endpoint Details</h3>
            <table class="endpoint-table">
                <thead>
                    <tr>
                        <th>Endpoint</th>
                        <th>Requests</th>
                        <th>Success Rate</th>
                        <th>Avg Time (ms)</th>
                        <th>Min Time (ms)</th>
                        <th>Max Time (ms)</th>
                    </tr>
                </thead>
                <tbody>
                    {self._generate_endpoint_rows(results.get('endpoints', {}))}
                </tbody>
            </table>
            
            {self._generate_errors_section(results.get('errors', []))}
        </div>
        
        <div class="footer">
            <p>Generated by JMeter Automation Tool with AI Analysis | {timestamp}</p>
        </div>
    </div>
    
    <script>
        // Response Code Chart
        const responseCodes = {response_codes_json};
        const ctx1 = document.getElementById('responseCodeChart').getContext('2d');
        new Chart(ctx1, {{
            type: 'doughnut',
            data: {{
                labels: Object.keys(responseCodes),
                datasets: [{{
                    data: Object.values(responseCodes),
                    backgroundColor: [
                        '#10b981', '#f59e0b', '#ef4444', '#3b82f6', '#8b5cf6'
                    ]
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ position: 'bottom' }}
                }}
            }}
        }});
        
        // Endpoint Performance Chart
        const endpointData = {endpoint_data_json};
        const ctx2 = document.getElementById('endpointChart').getContext('2d');
        new Chart(ctx2, {{
            type: 'bar',
            data: {{
                labels: endpointData.map(e => e.name),
                datasets: [{{
                    label: 'Average Response Time (ms)',
                    data: endpointData.map(e => e.avg_time),
                    backgroundColor: '#667eea'
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{ beginAtZero: true }}
                }}
            }}
        }});
        
        // Success Rate Chart
        const ctx3 = document.getElementById('successRateChart').getContext('2d');
        new Chart(ctx3, {{
            type: 'line',
            data: {{
                labels: endpointData.map(e => e.name),
                datasets: [{{
                    label: 'Success Rate (%)',
                    data: endpointData.map(e => e.success_rate),
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    fill: true
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{ beginAtZero: true, max: 100 }}
                }}
            }}
        }});
    </script>
</body>
</html>"""
        return html
    
    def _generate_endpoint_rows(self, endpoints: Dict) -> str:
        """Generate HTML rows for endpoint table"""
        rows = []
        for name, data in endpoints.items():
            success_rate = round(data.get("success_rate", 0), 2)
            success_class = "success" if success_rate >= 95 else "warning" if success_rate >= 80 else "error"
            rows.append(f"""
                <tr>
                    <td><strong>{name}</strong></td>
                    <td>{data.get('count', 0)}</td>
                    <td class="{success_class}">{success_rate}%</td>
                    <td>{round(data.get('avg_time', 0), 2)}</td>
                    <td>{round(data.get('min_time', 0), 2)}</td>
                    <td>{round(data.get('max_time', 0), 2)}</td>
                </tr>
            """)
        return "".join(rows)
    
    def _generate_errors_section(self, errors: List) -> str:
        """Generate errors section if there are any"""
        if not errors:
            return ""
        
        error_html = """
            <div class="chart-container" style="background: #fef2f2; border-left: 4px solid #ef4444;">
                <h3 style="color: #ef4444;">Errors & Failures</h3>
                <ul style="list-style: none; padding: 0;">
        """
        for error in errors[:10]:  # Show top 10 errors
            error_html += f"""
                    <li style="padding: 10px; margin: 5px 0; background: white; border-radius: 5px;">
                        <strong>{error.get('label', 'Unknown')}</strong>: {error.get('error', 'No error message')}
                        <br><small>Response Code: {error.get('response_code', 'N/A')}</small>
                    </li>
            """
        error_html += """
                </ul>
            </div>
        """
        return error_html

