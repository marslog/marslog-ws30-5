#!/usr/bin/env python3
"""
MARSLOG - ClickHouse-based Log Management System
Flask API Server with AI-powered log processing
"""

import os
import sys
import json
import logging
import threading
import socket
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import psutil
import schedule
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ClickHouse imports
try:
    from clickhouse_driver import Client as ClickHouseClient
    CLICKHOUSE_AVAILABLE = True
except ImportError:
    print("ClickHouse driver not available. Please install clickhouse-driver")
    ClickHouseClient = None
    CLICKHOUSE_AVAILABLE = False

def get_clickhouse_client():
    """Get a new ClickHouse client for each request to avoid connection conflicts"""
    return ClickHouseClient(
        host=CONFIG['clickhouse']['host'],
        port=CONFIG['clickhouse']['port'],
        database=CONFIG['clickhouse']['database'],
        user=CONFIG['clickhouse']['user'],
        password=CONFIG['clickhouse']['password'],
        settings={'use_numpy': False}  # Disable numpy for better compatibility
    )

# AI/ML imports for log processing
try:
    from drain3 import TemplateMiner
    from drain3.template_miner_config import TemplateMinerConfig
except ImportError:
    print("Drain3 not available. AI log parsing will be disabled.")
    TemplateMiner = None
    TemplateMinerConfig = None

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins="*")

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables
clickhouse_client = None
template_miner = None
metrics_thread = None
syslog_thread = None

# Configuration
CONFIG = {
    'clickhouse': {
        'host': os.getenv('CLICKHOUSE_HOST', 'localhost'),
        'port': int(os.getenv('CLICKHOUSE_PORT', 9000)),
        'database': os.getenv('CLICKHOUSE_DATABASE', 'marslog'),
        'user': os.getenv('CLICKHOUSE_USER', 'default'),
        'password': os.getenv('CLICKHOUSE_PASSWORD', '')
    },
    'syslog': {
        'host': os.getenv('SYSLOG_HOST', '0.0.0.0'),
        'port': int(os.getenv('SYSLOG_PORT', 514)),
        'enabled': os.getenv('RSYSLOG_ENABLED', 'true').lower() == 'true'
    },
    'metrics': {
        'enabled': os.getenv('METRICS_COLLECTION_ENABLED', 'true').lower() == 'true',
        'interval': int(os.getenv('METRICS_INTERVAL', 60)),
        'cpu_threshold': float(os.getenv('CPU_THRESHOLD', 80)),
        'memory_threshold': float(os.getenv('MEMORY_THRESHOLD', 85)),
        'disk_threshold': float(os.getenv('DISK_THRESHOLD', 90))
    },
    'ai': {
        'enabled': os.getenv('AI_CLASSIFICATION_ENABLED', 'true').lower() == 'true',
        'drain3_enabled': os.getenv('DRAIN3_ENABLED', 'true').lower() == 'true'
    },
    'alerts': {
        'enabled': os.getenv('ALERTS_ENABLED', 'true').lower() == 'true'
    }
}

def init_clickhouse():
    """Initialize ClickHouse connection with retry"""
    global clickhouse_client
    if not CLICKHOUSE_AVAILABLE:
        logger.warning("ClickHouse driver not available")
        return False
    
    max_retries = 10
    retry_interval = 5
    
    for attempt in range(max_retries):
        try:
            clickhouse_client = ClickHouseClient(
                host=CONFIG['clickhouse']['host'],
                port=CONFIG['clickhouse']['port'],
                database=CONFIG['clickhouse']['database'],
                user=CONFIG['clickhouse']['user'],
                password=CONFIG['clickhouse']['password']
            )
            # Test connection
            clickhouse_client.execute('SELECT 1')
            logger.info("ClickHouse connection established")
            return True
        except Exception as e:
            logger.warning(f"ClickHouse connection attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_interval)
            else:
                logger.error("Failed to connect to ClickHouse after all retries")
                return False

def init_ai_processing():
    """Initialize AI log processing with Drain3"""
    global template_miner
    if not CONFIG['ai']['enabled'] or not TemplateMiner:
        return False
    
    try:
        # Simple Drain3 config without loading from JSON
        config = TemplateMinerConfig()
        config.profiling_enabled = False
        config.snapshot_interval_sec = 30
        config.snapshot_compress = True
        template_miner = TemplateMiner(config=config)
        logger.info("AI log processing initialized with Drain3")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize AI processing: {e}")
        return False

def collect_system_metrics():
    """Collect system metrics using psutil"""
    try:
        hostname = socket.gethostname()
        timestamp = datetime.now(timezone.utc)
        
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # Memory metrics
        memory = psutil.virtual_memory()
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        
        # Network metrics
        network = psutil.net_io_counters()
        
        metrics = [
            # CPU
            (timestamp, hostname, 'system', 'cpu.usage.percent', cpu_percent, '%'),
            (timestamp, hostname, 'system', 'cpu.count', cpu_count, 'cores'),
            
            # Memory
            (timestamp, hostname, 'system', 'memory.total', memory.total, 'bytes'),
            (timestamp, hostname, 'system', 'memory.used', memory.used, 'bytes'),
            (timestamp, hostname, 'system', 'memory.percent', memory.percent, '%'),
            
            # Disk
            (timestamp, hostname, 'system', 'disk.total', disk.total, 'bytes'),
            (timestamp, hostname, 'system', 'disk.used', disk.used, 'bytes'),
            (timestamp, hostname, 'system', 'disk.percent', (disk.used / disk.total) * 100, '%'),
            
            # Network
            (timestamp, hostname, 'network', 'bytes.sent', network.bytes_sent, 'bytes'),
            (timestamp, hostname, 'network', 'bytes.recv', network.bytes_recv, 'bytes'),
            (timestamp, hostname, 'network', 'packets.sent', network.packets_sent, 'packets'),
            (timestamp, hostname, 'network', 'packets.recv', network.packets_recv, 'packets'),
        ]
        
        # Insert metrics to ClickHouse
        if clickhouse_client:
            insert_query = """
            INSERT INTO system_metrics 
            (timestamp, host, metric_type, metric_name, metric_value, unit) 
            VALUES
            """
            clickhouse_client.execute(insert_query, metrics)
            
        # Check thresholds and generate alerts
        check_metric_thresholds(hostname, cpu_percent, memory.percent, (disk.used / disk.total) * 100)
        
    except Exception as e:
        logger.error(f"Error collecting system metrics: {e}")

def check_metric_thresholds(hostname: str, cpu: float, memory: float, disk: float):
    """Check metric thresholds and generate alerts"""
    alerts = []
    timestamp = datetime.now(timezone.utc)
    
    if cpu > CONFIG['metrics']['cpu_threshold']:
        alerts.append({
            'timestamp': timestamp,
            'alert_id': f"cpu_high_{hostname}_{int(time.time())}",
            'alert_type': 'cpu_high',
            'severity': 'warning',
            'title': 'High CPU Usage',
            'description': f'CPU usage is {cpu:.1f}% on {hostname}',
            'host': hostname,
            'service': 'system',
            'status': 'active'
        })
    
    if memory > CONFIG['metrics']['memory_threshold']:
        alerts.append({
            'timestamp': timestamp,
            'alert_id': f"memory_high_{hostname}_{int(time.time())}",
            'alert_type': 'memory_high',
            'severity': 'warning',
            'title': 'High Memory Usage',
            'description': f'Memory usage is {memory:.1f}% on {hostname}',
            'host': hostname,
            'service': 'system',
            'status': 'active'
        })
    
    if disk > CONFIG['metrics']['disk_threshold']:
        alerts.append({
            'timestamp': timestamp,
            'alert_id': f"disk_full_{hostname}_{int(time.time())}",
            'alert_type': 'disk_full',
            'severity': 'critical',
            'title': 'Disk Space Critical',
            'description': f'Disk usage is {disk:.1f}% on {hostname}',
            'host': hostname,
            'service': 'system',
            'status': 'active'
        })
    
    # Insert alerts to ClickHouse
    if alerts and clickhouse_client:
        for alert in alerts:
            try:
                clickhouse_client.execute("""
                    INSERT INTO alerts 
                    (timestamp, alert_id, alert_type, severity, title, description, host, service, status) 
                    VALUES
                """, [(
                    alert['timestamp'], alert['alert_id'], alert['alert_type'],
                    alert['severity'], alert['title'], alert['description'],
                    alert['host'], alert['service'], alert['status']
                )])
            except Exception as e:
                logger.error(f"Error inserting alert: {e}")

def process_log_message(message: str, source: str, host: str = None) -> Dict[str, Any]:
    """Process log message with AI classification"""
    processed = {
        'timestamp': datetime.now(timezone.utc),
        'level': 'info',
        'source': source,
        'host': host or socket.gethostname(),
        'service': 'unknown',
        'message': message,
        'raw_message': message,
        'classification': 'unknown',
        'ai_confidence': 0.0
    }
    
    # AI processing with Drain3
    if template_miner and CONFIG['ai']['enabled']:
        try:
            result = template_miner.add_log_message(message)
            if result:
                processed['log_pattern_id'] = result['cluster_id']
                processed['classification'] = classify_log_message(message)
                processed['ai_confidence'] = 0.8  # Placeholder confidence
        except Exception as e:
            logger.error(f"Error in AI log processing: {e}")
    
    return processed

def classify_log_message(message: str) -> str:
    """Simple log classification based on keywords"""
    message_lower = message.lower()
    
    if any(word in message_lower for word in ['error', 'exception', 'failed', 'failure']):
        return 'error'
    elif any(word in message_lower for word in ['warning', 'warn']):
        return 'warning'
    elif any(word in message_lower for word in ['login', 'logout', 'auth', 'sudo']):
        return 'security'
    elif any(word in message_lower for word in ['network', 'connection', 'tcp', 'udp']):
        return 'network'
    elif any(word in message_lower for word in ['system', 'kernel', 'hardware']):
        return 'system'
    else:
        return 'application'

def syslog_server():
    """Simple syslog server"""
    if not CONFIG['syslog']['enabled']:
        return
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((CONFIG['syslog']['host'], CONFIG['syslog']['port']))
        logger.info(f"Syslog server listening on {CONFIG['syslog']['host']}:{CONFIG['syslog']['port']}")
        
        while True:
            data, addr = sock.recvfrom(1024)
            message = data.decode('utf-8', errors='ignore')
            
            # Process the syslog message
            processed = process_log_message(message, 'syslog', addr[0])
            
            # Insert to ClickHouse
            if clickhouse_client:
                try:
                    clickhouse_client.execute("""
                        INSERT INTO logs 
                        (timestamp, level, source, host, service, message, raw_message, classification, ai_confidence) 
                        VALUES
                    """, [(
                        processed['timestamp'], processed['level'], processed['source'],
                        processed['host'], processed['service'], processed['message'],
                        processed['raw_message'], processed['classification'], processed['ai_confidence']
                    )])
                except Exception as e:
                    logger.error(f"Error inserting log to ClickHouse: {e}")
                    
    except Exception as e:
        logger.error(f"Syslog server error: {e}")

def metrics_collector():
    """Background metrics collection"""
    if not CONFIG['metrics']['enabled']:
        return
    
    schedule.every(CONFIG['metrics']['interval']).seconds.do(collect_system_metrics)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

# API Routes
@app.route('/')
def home():
    return jsonify({
        'service': 'MARSLOG API',
        'version': '1.0.0',
        'status': 'running',
        'features': {
            'clickhouse': clickhouse_client is not None,
            'ai_processing': template_miner is not None,
            'metrics_collection': CONFIG['metrics']['enabled'],
            'syslog_server': CONFIG['syslog']['enabled']
        }
    })

@app.route('/api/')
def api_home():
    """API root endpoint with trailing slash"""
    return jsonify({
        'service': 'MARSLOG API',
        'version': '1.0.0',
        'status': 'running',
        'features': {
            'clickhouse': clickhouse_client is not None,
            'ai_processing': template_miner is not None,
            'metrics_collection': CONFIG['metrics']['enabled'],
            'syslog_server': CONFIG['syslog']['enabled']
        }
    })

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.now(timezone.utc).isoformat()})

@app.route('/api/health')
def api_health():
    """Health check endpoint for API"""
    return jsonify({'status': 'ok', 'timestamp': datetime.now(timezone.utc).isoformat()})

@app.route('/api/logs')
def get_logs():
    """Get logs with filtering and pagination"""
    try:
        limit = min(int(request.args.get('limit', 100)), 1000)
        offset = int(request.args.get('offset', 0))
        level = request.args.get('level')
        host = request.args.get('host')
        source = request.args.get('source')
        
        query = "SELECT * FROM logs WHERE 1=1"
        params = []
        
        if level:
            query += " AND level = %s"
            params.append(level)
        if host:
            query += " AND host = %s"
            params.append(host)
        if source:
            query += " AND source = %s"
            params.append(source)
            
        query += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        # Use new client for each request
        client = get_clickhouse_client()
        if client:
            result = client.execute(query, params)
            return jsonify({
                'logs': result,
                'total': len(result),
                'limit': limit,
                'offset': offset
            })
        else:
            return jsonify({'error': 'ClickHouse not available'}), 503
            
    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/logs')
def get_logs_simple():
    """Simple logs endpoint without /api prefix"""
    return get_logs()

@app.route('/api/metrics')
def get_metrics():
    """Get system metrics"""
    try:
        hours = int(request.args.get('hours', 24))
        
        if clickhouse_client:
            result = clickhouse_client.execute("""
                SELECT 
                    toStartOfHour(timestamp) as hour,
                    metric_type,
                    metric_name,
                    avg(metric_value) as avg_value,
                    max(metric_value) as max_value
                FROM system_metrics 
                WHERE timestamp >= now() - INTERVAL %s HOUR
                GROUP BY hour, metric_type, metric_name
                ORDER BY hour DESC
            """, [hours])
            
            return jsonify({'metrics': result})
        else:
            return jsonify({'error': 'ClickHouse not available'}), 503
            
    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts')
def get_alerts():
    """Get alerts"""
    try:
        status = request.args.get('status', 'active')
        
        if clickhouse_client:
            result = clickhouse_client.execute("""
                SELECT * FROM alerts 
                WHERE status = %s
                ORDER BY timestamp DESC
                LIMIT 100
            """, [status])
            
            return jsonify({'alerts': result})
        else:
            return jsonify({'error': 'ClickHouse not available'}), 503
            
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard')
def get_dashboard():
    """Get dashboard statistics"""
    try:
        if clickhouse_client:
            # Get log counts by level
            log_counts = clickhouse_client.execute("""
                SELECT level, count() as count
                FROM logs 
                WHERE timestamp >= now() - INTERVAL 24 HOUR
                GROUP BY level
            """)
            
            # Get active alerts count
            alert_counts = clickhouse_client.execute("""
                SELECT count() as count
                FROM alerts 
                WHERE status = 'active'
            """)
            
            # Get top hosts by log volume
            top_hosts = clickhouse_client.execute("""
                SELECT host, count() as log_count
                FROM logs 
                WHERE timestamp >= now() - INTERVAL 24 HOUR
                GROUP BY host
                ORDER BY log_count DESC
                LIMIT 10
            """)
            
            return jsonify({
                'log_counts': log_counts,
                'active_alerts': alert_counts[0][0] if alert_counts else 0,
                'top_hosts': top_hosts
            })
        else:
            return jsonify({'error': 'ClickHouse not available'}), 503
            
    except Exception as e:
        logger.error(f"Error fetching dashboard data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs', methods=['POST'])
def ingest_log():
    """Ingest a log message via API"""
    try:
        data = request.json
        if not data or 'message' not in data:
            return jsonify({'error': 'Message field required'}), 400
            
        processed = process_log_message(
            data['message'],
            data.get('source', 'api'),
            data.get('host')
        )
        
        # Insert to ClickHouse using new client
        client = get_clickhouse_client()
        if client:
            client.execute("""
                INSERT INTO logs 
                (timestamp, level, source, host, service, message, raw_message, classification, ai_confidence) 
                VALUES
            """, [(
                processed['timestamp'], processed['level'], processed['source'],
                processed['host'], processed['service'], processed['message'],
                processed['raw_message'], processed['classification'], processed['ai_confidence']
            )])
        
        return jsonify({'status': 'success', 'processed': processed})
        
    except Exception as e:
        logger.error(f"Error ingesting log: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/logs', methods=['POST'])
def ingest_log_simple():
    """Simple log ingestion endpoint without /api prefix"""
    return ingest_log()

def initialize_services():
    """Initialize all services"""
    global metrics_thread, syslog_thread
    
    logger.info("Starting MARSLOG services...")
    
    # Initialize ClickHouse
    if not init_clickhouse():
        logger.warning("ClickHouse initialization failed")
    
    # Initialize AI processing
    if not init_ai_processing():
        logger.warning("AI processing initialization failed")
    
    # Start metrics collection in background
    if CONFIG['metrics']['enabled']:
        metrics_thread = threading.Thread(target=metrics_collector, daemon=True)
        metrics_thread.start()
        logger.info("Metrics collection started")
    
    # Start syslog server in background
    if CONFIG['syslog']['enabled']:
        syslog_thread = threading.Thread(target=syslog_server, daemon=True)
        syslog_thread.start()
        logger.info("Syslog server started")

if __name__ == '__main__':
    # Initialize services
    initialize_services()
    
    # Start Flask app
    app.run(
        host=os.getenv('API_HOST', '0.0.0.0'),
        port=int(os.getenv('API_PORT', 5000)),
        debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    )