#!/usr/bin/env python3
"""
MARSLOG-ClickHouse Syslog Server
Enhanced syslog server with ClickHouse integration and AI parsing
"""

import socket
import threading
import re
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from flask import Blueprint, request, jsonify
import clickhouse_connect
import logging

# Create blueprint for syslog routes
syslog_bp = Blueprint('syslog', __name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClickHouseSyslogServer:
    """Enhanced Syslog server with ClickHouse integration"""
    
    def __init__(self, host='0.0.0.0', port=514, clickhouse_client=None):
        self.host = host
        self.port = port
        self.clickhouse_client = clickhouse_client
        self.running = False
        self.socket = None
        self.threads = []
        
        # Syslog patterns for parsing
        self.syslog_patterns = {
            'rfc3164': re.compile(
                r'^<(?P<priority>\d+)>'
                r'(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+'
                r'(?P<hostname>\S+)\s+'
                r'(?P<tag>[^:\s]+)(?:\[(?P<pid>\d+)\])?:\s*'
                r'(?P<message>.*)'
            ),
            'rfc5424': re.compile(
                r'^<(?P<priority>\d+)>(?P<version>\d+)\s+'
                r'(?P<timestamp>\S+)\s+'
                r'(?P<hostname>\S+)\s+'
                r'(?P<appname>\S+)\s+'
                r'(?P<procid>\S+)\s+'
                r'(?P<msgid>\S+)\s+'
                r'(?P<structured_data>\[.*?\]|\-)\s*'
                r'(?P<message>.*)'
            ),
            'custom': re.compile(
                r'^(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+'
                r'(?P<level>\w+)\s+'
                r'(?P<source>\S+)\s+'
                r'(?P<message>.*)'
            )
        }
        
        # Facility and severity mappings
        self.facilities = {
            0: 'kernel', 1: 'user', 2: 'mail', 3: 'daemon',
            4: 'security', 5: 'syslogd', 6: 'lpr', 7: 'news',
            8: 'uucp', 9: 'cron', 10: 'authpriv', 11: 'ftp',
            16: 'local0', 17: 'local1', 18: 'local2', 19: 'local3',
            20: 'local4', 21: 'local5', 22: 'local6', 23: 'local7'
        }
        
        self.severities = {
            0: 'emergency', 1: 'alert', 2: 'critical', 3: 'error',
            4: 'warning', 5: 'notice', 6: 'info', 7: 'debug'
        }
        
        self.log_levels = {
            0: 'EMERGENCY', 1: 'ALERT', 2: 'CRITICAL', 3: 'ERROR',
            4: 'WARNING', 5: 'NOTICE', 6: 'INFO', 7: 'DEBUG'
        }
    
    def parse_priority(self, priority: int) -> Tuple[str, str, int]:
        """Parse syslog priority into facility and severity"""
        facility_code = priority >> 3
        severity_code = priority & 7
        
        facility = self.facilities.get(facility_code, f'unknown_{facility_code}')
        severity = self.severities.get(severity_code, f'unknown_{severity_code}')
        
        return facility, severity, severity_code
    
    def parse_syslog_message(self, raw_message: str, client_ip: str) -> Dict:
        """Parse syslog message using multiple patterns"""
        parsed = {
            'timestamp': datetime.utcnow(),
            'raw_message': raw_message.strip(),
            'host': client_ip,
            'source': 'syslog',
            'level': 'INFO',
            'message': raw_message.strip(),
            'facility': 'user',
            'severity': 6,
            'program': '',
            'pid': None,
            'parsed_fields': {}
        }
        
        # Try RFC3164 format first
        match = self.syslog_patterns['rfc3164'].match(raw_message)
        if match:
            data = match.groupdict()
            priority = int(data.get('priority', 22))
            facility, severity, severity_code = self.parse_priority(priority)
            
            parsed.update({
                'host': data.get('hostname', client_ip),
                'program': data.get('tag', ''),
                'pid': int(data['pid']) if data.get('pid') else None,
                'message': data.get('message', ''),
                'facility': facility,
                'severity': severity_code,
                'level': self.log_levels.get(severity_code, 'INFO'),
                'parsed_fields': {
                    'priority': priority,
                    'syslog_format': 'rfc3164'
                }
            })
            
            # Parse timestamp if available
            if data.get('timestamp'):
                try:
                    # Convert syslog timestamp to datetime
                    current_year = datetime.now().year
                    timestamp_str = f"{current_year} {data['timestamp']}"
                    parsed['timestamp'] = datetime.strptime(timestamp_str, '%Y %b %d %H:%M:%S')
                except ValueError:
                    pass
            
            return parsed
        
        # Try RFC5424 format
        match = self.syslog_patterns['rfc5424'].match(raw_message)
        if match:
            data = match.groupdict()
            priority = int(data.get('priority', 22))
            facility, severity, severity_code = self.parse_priority(priority)
            
            parsed.update({
                'host': data.get('hostname', client_ip),
                'program': data.get('appname', ''),
                'pid': int(data['procid']) if data.get('procid', '-').isdigit() else None,
                'message': data.get('message', ''),
                'facility': facility,
                'severity': severity_code,
                'level': self.log_levels.get(severity_code, 'INFO'),
                'parsed_fields': {
                    'priority': priority,
                    'version': data.get('version'),
                    'msgid': data.get('msgid'),
                    'structured_data': data.get('structured_data'),
                    'syslog_format': 'rfc5424'
                }
            })
            
            # Parse ISO 8601 timestamp
            if data.get('timestamp') and data['timestamp'] != '-':
                try:
                    # Handle various ISO 8601 formats
                    timestamp_str = data['timestamp'].replace('T', ' ').replace('Z', '+00:00')
                    if '+' in timestamp_str or '-' in timestamp_str[-6:]:
                        # Remove timezone for simplicity
                        timestamp_str = timestamp_str.split('+')[0].split('-')[0]
                    parsed['timestamp'] = datetime.fromisoformat(timestamp_str)
                except ValueError:
                    pass
            
            return parsed
        
        # Try custom format
        match = self.syslog_patterns['custom'].match(raw_message)
        if match:
            data = match.groupdict()
            
            parsed.update({
                'message': data.get('message', ''),
                'level': data.get('level', 'INFO').upper(),
                'source': data.get('source', 'unknown'),
                'parsed_fields': {
                    'syslog_format': 'custom'
                }
            })
            
            # Parse timestamp
            if data.get('timestamp'):
                try:
                    parsed['timestamp'] = datetime.strptime(data['timestamp'], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    pass
            
            return parsed
        
        # If no pattern matches, treat as plain message
        parsed['parsed_fields']['syslog_format'] = 'plain'
        return parsed
    
    def store_log(self, parsed_log: Dict) -> bool:
        """Store parsed log in ClickHouse"""
        if not self.clickhouse_client:
            logger.warning("No ClickHouse client available")
            return False
        
        try:
            # Prepare data for ClickHouse
            log_data = {
                'timestamp': parsed_log['timestamp'],
                'level': parsed_log['level'],
                'message': parsed_log['message'][:65535],  # Limit message length
                'source': parsed_log['source'][:255],
                'host': parsed_log['host'][:255],
                'facility': parsed_log['facility'][:50],
                'severity': parsed_log['severity'],
                'program': parsed_log['program'][:255] if parsed_log['program'] else '',
                'pid': parsed_log['pid'] if parsed_log['pid'] else 0,
                'raw_message': parsed_log['raw_message'][:65535],
                'parsed_fields': parsed_log['parsed_fields']
            }
            
            # Insert into ClickHouse
            self.clickhouse_client.insert('logs', [log_data])
            return True
            
        except Exception as e:
            logger.error(f"Failed to store log in ClickHouse: {e}")
            return False
    
    def handle_client(self, data: bytes, addr: Tuple[str, int]) -> None:
        """Handle incoming syslog message"""
        try:
            client_ip = addr[0]
            raw_message = data.decode('utf-8', errors='ignore')
            
            if not raw_message.strip():
                return
            
            # Parse the syslog message
            parsed_log = self.parse_syslog_message(raw_message, client_ip)
            
            # Store in ClickHouse
            success = self.store_log(parsed_log)
            
            # Log the received message
            logger.info(f"Received from {client_ip}: {parsed_log['level']} - {parsed_log['message'][:100]}")
            
            if not success:
                logger.warning(f"Failed to store log from {client_ip}")
                
        except Exception as e:
            logger.error(f"Error handling syslog message from {addr}: {e}")
    
    def start_server(self) -> None:
        """Start the syslog server"""
        try:
            # Create UDP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            
            logger.info(f"Syslog server started on {self.host}:{self.port}")
            self.running = True
            
            while self.running:
                try:
                    data, addr = self.socket.recvfrom(65536)  # Max UDP packet size
                    
                    # Handle each message in a separate thread
                    thread = threading.Thread(
                        target=self.handle_client,
                        args=(data, addr),
                        daemon=True
                    )
                    thread.start()
                    
                except socket.error as e:
                    if self.running:
                        logger.error(f"Socket error: {e}")
                        time.sleep(1)
                    
        except Exception as e:
            logger.error(f"Failed to start syslog server: {e}")
        finally:
            self.stop_server()
    
    def stop_server(self) -> None:
        """Stop the syslog server"""
        self.running = False
        if self.socket:
            self.socket.close()
        logger.info("Syslog server stopped")

# Global syslog server instance
syslog_server = None

def start_syslog_server(clickhouse_client=None, host='0.0.0.0', port=514):
    """Start the global syslog server"""
    global syslog_server
    
    if syslog_server is None:
        syslog_server = ClickHouseSyslogServer(host, port, clickhouse_client)
        
        # Start server in a separate thread
        server_thread = threading.Thread(
            target=syslog_server.start_server,
            daemon=True
        )
        server_thread.start()
        
        logger.info(f"Syslog server thread started on {host}:{port}")
    
    return syslog_server

def stop_syslog_server():
    """Stop the global syslog server"""
    global syslog_server
    
    if syslog_server:
        syslog_server.stop_server()
        syslog_server = None

# Flask routes for syslog management
@syslog_bp.route('/status', methods=['GET'])
def get_syslog_status():
    """Get syslog server status"""
    global syslog_server
    
    if syslog_server and syslog_server.running:
        return jsonify({
            'status': 'running',
            'host': syslog_server.host,
            'port': syslog_server.port,
            'message': 'Syslog server is running'
        })
    else:
        return jsonify({
            'status': 'stopped',
            'message': 'Syslog server is not running'
        })

@syslog_bp.route('/start', methods=['POST'])
def start_syslog():
    """Start syslog server"""
    data = request.get_json() or {}
    host = data.get('host', '0.0.0.0')
    port = data.get('port', 514)
    
    try:
        # Get ClickHouse client from Flask app context
        from flask import current_app
        clickhouse_client = getattr(current_app, 'clickhouse_client', None)
        
        server = start_syslog_server(clickhouse_client, host, port)
        
        return jsonify({
            'success': True,
            'message': f'Syslog server started on {host}:{port}',
            'status': 'running'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to start syslog server: {str(e)}',
            'status': 'error'
        }), 500

@syslog_bp.route('/stop', methods=['POST'])
def stop_syslog():
    """Stop syslog server"""
    try:
        stop_syslog_server()
        
        return jsonify({
            'success': True,
            'message': 'Syslog server stopped',
            'status': 'stopped'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to stop syslog server: {str(e)}',
            'status': 'error'
        }), 500

@syslog_bp.route('/test', methods=['POST'])
def test_syslog():
    """Send a test syslog message"""
    data = request.get_json() or {}
    message = data.get('message', 'Test message from MARSLOG')
    host = data.get('host', 'localhost')
    port = data.get('port', 514)
    
    try:
        # Send test UDP message
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        test_message = f"<134>{datetime.now().strftime('%b %d %H:%M:%S')} marslog-test: {message}"
        test_socket.sendto(test_message.encode(), (host, port))
        test_socket.close()
        
        return jsonify({
            'success': True,
            'message': 'Test message sent successfully',
            'test_message': test_message
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to send test message: {str(e)}'
        }), 500

if __name__ == '__main__':
    # For testing purposes
    import sys
    
    host = sys.argv[1] if len(sys.argv) > 1 else '0.0.0.0'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 514
    
    server = ClickHouseSyslogServer(host, port)
    
    try:
        server.start_server()
    except KeyboardInterrupt:
        print("\nShutting down syslog server...")
        server.stop_server()
