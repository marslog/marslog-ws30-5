"""
AI/ML Log Parser for MARSLOG-ClickHouse
Intelligent log parsing with pattern recognition and anomaly detection
Enhanced for ClickHouse integration
"""

import json
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
from flask import Blueprint, request, jsonify
import logging
from collections import defaultdict, Counter
import statistics
from .utils import get_clickhouse_client

ai_parser_bp = Blueprint('ai_parser', __name__)
logger = logging.getLogger(__name__)

class AILogParser:
    def __init__(self):
        self.patterns = {
            'timestamp': [
                r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}',
                r'\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}',
                r'\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}',
                r'\d{10}',  # Unix timestamp
                r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z?',
            ],
            'ip_address': [
                r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
                r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b',  # IPv6
            ],
            'severity': [
                r'\b(?:DEBUG|INFO|WARN|ERROR|FATAL|TRACE|NOTICE|ALERT|EMERG|CRIT)\b',
                r'\b(?:debug|info|warn|error|fatal|trace|notice|alert|emerg|crit)\b',
            ],
            'facility': [
                r'\b(?:kernel|user|mail|daemon|auth|syslog|lpr|news|uucp|cron|authpriv|ftp|local[0-7])\b',
            ],
            'user': [
                r'user\s*[:=]\s*([^\s,]+)',
                r'username\s*[:=]\s*([^\s,]+)',
                r'uid\s*[:=]\s*(\d+)',
            ],
            'process': [
                r'([a-zA-Z_][a-zA-Z0-9_-]*)\[\d+\]',
                r'process\s*[:=]\s*([^\s,]+)',
                r'pid\s*[:=]\s*(\d+)',
            ],
            'network': [
                r'port\s*[:=]\s*(\d+)',
                r'src\s*[:=]\s*([^\s,]+)',
                r'dst\s*[:=]\s*([^\s,]+)',
                r'proto\s*[:=]\s*([^\s,]+)',
            ],
            'file_path': [
                r'\/(?:[^\/\s]+\/)*[^\/\s]+',
                r'[A-Za-z]:\\(?:[^\\/:*?"<>|\s]+\\)*[^\\/:*?"<>|\s]*',
            ],
            'url': [
                r'https?:\/\/[^\s]+',
                r'ftp:\/\/[^\s]+',
            ],
            'email': [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            ],
            'attack_indicators': [
                r'\b(?:exploit|attack|malware|virus|trojan|backdoor|shellcode|injection|xss|sqli)\b',
                r'\b(?:unauthorized|forbidden|denied|blocked|failed|breach)\b',
                r'\b(?:suspicious|anomaly|anomalous|unusual|unexpected)\b',
                r'\b(?:intrusion|penetration|brute.*force|dos|ddos)\b',
            ],
            'error_indicators': [
                r'\b(?:error|fail|exception|timeout|refused|unreachable|denied)\b',
                r'\b(?:404|500|503|502|501|401|403|407|408|429)\b',
            ]
        }
        
        self.log_types = {
            'apache_access': r'^(\S+) \S+ \S+ \[([^\]]+)\] "([^"]*)" (\d+) (\d+)',
            'apache_error': r'^\[([^\]]+)\] \[([^\]]+)\] \[([^\]]+)\] (.+)',
            'nginx_access': r'^(\S+) - \S+ \[([^\]]+)\] "([^"]*)" (\d+) (\d+)',
            'syslog': r'^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}) (\S+) ([^:]+): (.+)',
            'windows_event': r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+(\S+)\s+(.+)',
            'firewall': r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+(.+)\s+SRC=(\S+)\s+DST=(\S+)',
            'auth_log': r'^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}) (\S+) ([^:]+): (.+)',
            'cisco_asa': r'^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}) (\S+) %ASA-(\d)-(\d+): (.+)',
            'palo_alto': r'^(\d{4}\/\d{2}\/\d{2}\s+\d{2}:\d{2}:\d{2}),([^,]+),([^,]+),([^,]+),(.+)',
            'json_log': r'^\{.*\}$',
        }
        
        self.anomaly_thresholds = {
            'high_error_rate': 0.1,  # 10% error rate
            'unusual_traffic': 3.0,   # 3 standard deviations
            'new_source_threshold': 10,  # New IPs per hour
            'failed_auth_threshold': 5,  # Failed auth attempts per minute
            'large_transfer_threshold': 50_000_000,  # 50MB
            'rapid_request_threshold': 0.05,  # 50ms between requests
        }
        
        # ML-like features for pattern learning
        self.learned_patterns = defaultdict(Counter)
        self.baseline_metrics = {}
        self.client = None

    def get_client(self):
        """Get ClickHouse client instance"""
        if not self.client:
            self.client = get_clickhouse_client()
        return self.client

    def detect_log_type(self, log_line: str) -> str:
        """Auto-detect log type using regex patterns"""
        for log_type, pattern in self.log_types.items():
            if re.search(pattern, log_line, re.IGNORECASE):
                return log_type
        return 'unknown'

    def extract_fields(self, log_line: str, log_type: str = None) -> Dict[str, Any]:
        """Extract structured fields from log line"""
        if not log_type:
            log_type = self.detect_log_type(log_line)
        
        fields = {
            'raw_log': log_line,
            'log_type': log_type,
            'timestamp': None,
            'parsed_fields': {},
            'risk_score': 0,
            'anomaly_indicators': [],
            'confidence': 0.0
        }
        
        # Extract common patterns
        for field_type, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, log_line, re.IGNORECASE)
                if matches:
                    if field_type == 'timestamp':
                        fields['timestamp'] = self.normalize_timestamp(matches[0])
                    else:
                        fields['parsed_fields'][field_type] = matches
        
        # Type-specific parsing
        if log_type in self.log_types:
            match = re.search(self.log_types[log_type], log_line, re.IGNORECASE)
            if match:
                fields['parsed_fields'].update(self.parse_by_type(match, log_type))
                fields['confidence'] = 0.9  # High confidence for known formats
        else:
            fields['confidence'] = 0.5  # Medium confidence for unknown formats
        
        # Calculate risk score
        fields['risk_score'] = self.calculate_risk_score(log_line, fields['parsed_fields'])
        
        # Detect anomalies
        fields['anomaly_indicators'] = self.detect_anomalies(fields)
        
        return fields

    def normalize_timestamp(self, timestamp_str: str) -> Optional[str]:
        """Normalize various timestamp formats to ISO format"""
        try:
            # Unix timestamp
            if timestamp_str.isdigit():
                return datetime.fromtimestamp(int(timestamp_str)).isoformat()
            
            # Standard formats
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%d/%m/%Y %H:%M:%S',
                '%b %d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%fZ',
                '%Y-%m-%d %H:%M:%S.%f',
                '%d/%b/%Y:%H:%M:%S %z',
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(timestamp_str, fmt)
                    if dt.year == 1900:  # Add current year for syslog format
                        dt = dt.replace(year=datetime.now().year)
                    return dt.isoformat()
                except ValueError:
                    continue
            
            return timestamp_str
        except Exception:
            return None

    def parse_by_type(self, match, log_type: str) -> Dict[str, Any]:
        """Parse specific log types with dedicated logic"""
        parsed = {}
        
        if log_type == 'apache_access':
            parsed.update({
                'client_ip': match.group(1),
                'timestamp': match.group(2),
                'request': match.group(3),
                'status_code': int(match.group(4)),
                'bytes_sent': int(match.group(5)) if match.group(5) != '-' else 0
            })
        
        elif log_type == 'nginx_access':
            parsed.update({
                'client_ip': match.group(1),
                'timestamp': match.group(2),
                'request': match.group(3),
                'status_code': int(match.group(4)),
                'bytes_sent': int(match.group(5)) if match.group(5) != '-' else 0
            })
        
        elif log_type == 'syslog':
            parsed.update({
                'timestamp': match.group(1),
                'hostname': match.group(2),
                'process': match.group(3),
                'message': match.group(4)
            })
        
        elif log_type == 'firewall':
            parsed.update({
                'timestamp': match.group(1),
                'action': match.group(2),
                'protocol': match.group(3),
                'source_ip': match.group(4),
                'dest_ip': match.group(5)
            })
        
        elif log_type == 'cisco_asa':
            parsed.update({
                'timestamp': match.group(1),
                'hostname': match.group(2),
                'severity': match.group(3),
                'message_id': match.group(4),
                'message': match.group(5)
            })
        
        elif log_type == 'json_log':
            try:
                json_data = json.loads(match.group(0))
                parsed.update(json_data)
            except json.JSONDecodeError:
                pass
        
        return parsed

    def calculate_risk_score(self, log_line: str, parsed_fields: Dict) -> int:
        """Calculate risk score from 0-100 based on indicators"""
        score = 0
        
        # Attack indicators (high weight)
        for pattern in self.patterns['attack_indicators']:
            if re.search(pattern, log_line, re.IGNORECASE):
                score += 35
        
        # Error indicators (medium weight)
        for pattern in self.patterns['error_indicators']:
            if re.search(pattern, log_line, re.IGNORECASE):
                score += 20
        
        # High-risk status codes
        if 'status_code' in parsed_fields:
            status = parsed_fields['status_code']
            if status in [401, 403]:
                score += 25  # Authentication/Authorization failures
            elif status in [404, 500, 502, 503]:
                score += 15  # Application errors
            elif status in [429]:
                score += 30  # Rate limiting (potential DoS)
        
        # Suspicious activity patterns
        if re.search(r'(root|admin|administrator)', log_line, re.IGNORECASE):
            score += 15
        
        if re.search(r'(failed|denied|unauthorized|blocked)', log_line, re.IGNORECASE):
            score += 20
        
        # SQL injection patterns
        if re.search(r'(union.*select|drop.*table|exec.*sp_|<script)', log_line, re.IGNORECASE):
            score += 40
        
        # Network-based risks
        if 'ip_address' in parsed_fields:
            for ip in parsed_fields['ip_address']:
                # Check for private IP ranges (lower risk)
                if re.match(r'^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)', ip):
                    score -= 5  # Lower risk for internal IPs
                else:
                    score += 10  # Higher risk for external IPs
        
        # Large data transfers
        if 'bytes_sent' in parsed_fields and parsed_fields['bytes_sent'] > self.anomaly_thresholds['large_transfer_threshold']:
            score += 25
        
        return min(score, 100)  # Cap at 100

    def detect_anomalies(self, fields: Dict) -> List[str]:
        """Detect anomalous patterns in log entry"""
        anomalies = []
        parsed = fields['parsed_fields']
        
        # High risk score
        if fields['risk_score'] > 60:
            anomalies.append('high_risk_activity')
        
        # Multiple failed attempts
        if re.search(r'failed.*(\d+).*times?', fields['raw_log'], re.IGNORECASE):
            anomalies.append('multiple_failures')
        
        # Brute force indicators
        if re.search(r'(brute.*force|dictionary.*attack|password.*spray)', fields['raw_log'], re.IGNORECASE):
            anomalies.append('brute_force_attempt')
        
        # Unusual time patterns
        if fields['timestamp']:
            try:
                dt = datetime.fromisoformat(fields['timestamp'].replace('Z', '+00:00'))
                hour = dt.hour
                if hour < 6 or hour > 22:  # Activity outside business hours
                    anomalies.append('off_hours_activity')
            except:
                pass
        
        # Large data transfers
        if 'bytes_sent' in parsed and parsed['bytes_sent'] > self.anomaly_thresholds['large_transfer_threshold']:
            anomalies.append('large_data_transfer')
        
        # Rapid sequential requests
        if hasattr(self, 'last_request_time'):
            current_time = time.time()
            if current_time - self.last_request_time < self.anomaly_thresholds['rapid_request_threshold']:
                anomalies.append('rapid_requests')
        self.last_request_time = time.time()
        
        # Suspicious user agents
        user_agent_patterns = [
            r'(sqlmap|nmap|nikto|dirb|gobuster|wfuzz)',
            r'(bot|crawler|spider)(?!.*google)',
            r'^$',  # Empty user agent
        ]
        for pattern in user_agent_patterns:
            if re.search(pattern, fields['raw_log'], re.IGNORECASE):
                anomalies.append('suspicious_user_agent')
                break
        
        return anomalies

    def store_parsed_log(self, parsed_log: Dict[str, Any]) -> bool:
        """Store parsed log data in ClickHouse"""
        try:
            client = self.get_client()
            
            # Prepare data for insertion
            log_data = {
                'timestamp': parsed_log.get('timestamp', datetime.now().isoformat()),
                'raw_log': parsed_log['raw_log'],
                'log_type': parsed_log['log_type'],
                'risk_score': parsed_log['risk_score'],
                'anomaly_indicators': ','.join(parsed_log['anomaly_indicators']),
                'confidence': parsed_log['confidence'],
                'parsed_fields': json.dumps(parsed_log['parsed_fields']),
                'source_ip': self.extract_source_ip(parsed_log['parsed_fields']),
                'dest_ip': self.extract_dest_ip(parsed_log['parsed_fields']),
                'user_agent': self.extract_user_agent(parsed_log['raw_log']),
                'status_code': parsed_log['parsed_fields'].get('status_code', 0),
                'bytes_sent': parsed_log['parsed_fields'].get('bytes_sent', 0),
                'created_at': datetime.now().isoformat()
            }
            
            # Insert into parsed_logs table
            client.execute(
                """
                INSERT INTO parsed_logs (
                    timestamp, raw_log, log_type, risk_score, anomaly_indicators,
                    confidence, parsed_fields, source_ip, dest_ip, user_agent,
                    status_code, bytes_sent, created_at
                ) VALUES
                """,
                [log_data]
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing parsed log: {e}")
            return False

    def extract_source_ip(self, parsed_fields: Dict) -> str:
        """Extract source IP from parsed fields"""
        if 'client_ip' in parsed_fields:
            return parsed_fields['client_ip']
        elif 'source_ip' in parsed_fields:
            return parsed_fields['source_ip']
        elif 'ip_address' in parsed_fields and parsed_fields['ip_address']:
            return parsed_fields['ip_address'][0]
        return ''

    def extract_dest_ip(self, parsed_fields: Dict) -> str:
        """Extract destination IP from parsed fields"""
        if 'dest_ip' in parsed_fields:
            return parsed_fields['dest_ip']
        elif 'destination_ip' in parsed_fields:
            return parsed_fields['destination_ip']
        return ''

    def extract_user_agent(self, raw_log: str) -> str:
        """Extract user agent from raw log"""
        match = re.search(r'"([^"]*user-agent[^"]*)"', raw_log, re.IGNORECASE)
        if match:
            return match.group(1)
        return ''

    def learn_patterns(self, parsed_logs: List[Dict]) -> None:
        """Learn normal patterns from historical data (ML-like approach)"""
        for log_entry in parsed_logs:
            log_type = log_entry.get('log_type', 'unknown')
            
            # Learn field patterns
            for field, value in log_entry.get('parsed_fields', {}).items():
                if isinstance(value, list):
                    for v in value:
                        self.learned_patterns[f"{log_type}_{field}"][str(v)] += 1
                else:
                    self.learned_patterns[f"{log_type}_{field}"][str(value)] += 1
        
        logger.info(f"Learned patterns from {len(parsed_logs)} log entries")

    def get_parsing_stats(self) -> Dict[str, Any]:
        """Get parsing statistics and learned patterns"""
        return {
            'total_patterns': len(self.learned_patterns),
            'pattern_summary': {
                key: dict(counter.most_common(5))
                for key, counter in self.learned_patterns.items()
            },
            'anomaly_thresholds': self.anomaly_thresholds,
            'supported_log_types': list(self.log_types.keys())
        }

    def get_anomaly_summary(self, time_range: str = '1h') -> Dict[str, Any]:
        """Get anomaly summary from ClickHouse"""
        try:
            client = self.get_client()
            
            # Calculate time range
            hours = {'1h': 1, '6h': 6, '24h': 24, '7d': 168}.get(time_range, 1)
            start_time = datetime.now() - timedelta(hours=hours)
            
            # Query for anomalies
            query = """
            SELECT 
                log_type,
                COUNT(*) as total_logs,
                SUM(CASE WHEN risk_score > 60 THEN 1 ELSE 0 END) as high_risk_count,
                SUM(CASE WHEN anomaly_indicators != '' THEN 1 ELSE 0 END) as anomaly_count,
                AVG(risk_score) as avg_risk_score,
                groupArray(anomaly_indicators) as all_anomalies
            FROM parsed_logs 
            WHERE timestamp >= %s
            GROUP BY log_type
            ORDER BY high_risk_count DESC
            """
            
            result = client.execute(query, [start_time.isoformat()])
            
            summary = {
                'time_range': time_range,
                'log_type_stats': [],
                'top_anomalies': Counter(),
                'total_logs': 0,
                'total_high_risk': 0,
                'total_anomalies': 0
            }
            
            for row in result:
                log_type, total, high_risk, anomalies, avg_risk, all_anomalies = row
                
                summary['log_type_stats'].append({
                    'log_type': log_type,
                    'total_logs': total,
                    'high_risk_count': high_risk,
                    'anomaly_count': anomalies,
                    'avg_risk_score': round(avg_risk, 2)
                })
                
                summary['total_logs'] += total
                summary['total_high_risk'] += high_risk
                summary['total_anomalies'] += anomalies
                
                # Count anomaly types
                for anomaly_list in all_anomalies:
                    if anomaly_list:
                        for anomaly in anomaly_list.split(','):
                            if anomaly.strip():
                                summary['top_anomalies'][anomaly.strip()] += 1
            
            summary['top_anomalies'] = dict(summary['top_anomalies'].most_common(10))
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting anomaly summary: {e}")
            return {'error': str(e)}

# Global parser instance
ai_parser = AILogParser()

@ai_parser_bp.route('/parse', methods=['POST'])
def parse_logs():
    """Parse log entries using AI/ML techniques"""
    try:
        data = request.get_json()
        logs = data.get('logs', [])
        learn_mode = data.get('learn', False)
        store_results = data.get('store', True)
        
        if not logs:
            return jsonify({'error': 'No logs provided'}), 400
        
        results = []
        for log_line in logs:
            if isinstance(log_line, str):
                parsed = ai_parser.extract_fields(log_line)
                results.append(parsed)
                
                # Store in ClickHouse if requested
                if store_results:
                    ai_parser.store_parsed_log(parsed)
        
        # Learn from patterns if requested
        if learn_mode and results:
            ai_parser.learn_patterns(results)
        
        # Calculate summary statistics
        total_logs = len(results)
        high_risk_logs = sum(1 for r in results if r['risk_score'] > 60)
        anomaly_logs = sum(1 for r in results if r['anomaly_indicators'])
        
        log_types = Counter(r['log_type'] for r in results)
        
        response = {
            'parsed_logs': results,
            'summary': {
                'total_logs': total_logs,
                'high_risk_count': high_risk_logs,
                'anomaly_count': anomaly_logs,
                'log_types': dict(log_types),
                'avg_risk_score': statistics.mean(r['risk_score'] for r in results) if results else 0,
                'avg_confidence': statistics.mean(r['confidence'] for r in results) if results else 0
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error parsing logs: {e}")
        return jsonify({'error': str(e)}), 500

@ai_parser_bp.route('/analyze', methods=['POST'])
def analyze_logs():
    """Analyze logs for patterns and anomalies"""
    try:
        data = request.get_json()
        time_range = data.get('time_range', '1h')  # 1h, 6h, 24h, 7d
        
        # Get anomaly summary from ClickHouse
        analysis = ai_parser.get_anomaly_summary(time_range)
        
        # Add recommendations based on findings
        recommendations = []
        if analysis.get('total_high_risk', 0) > 10:
            recommendations.append("High number of risky events detected. Consider implementing additional security measures.")
        
        if 'brute_force_attempt' in analysis.get('top_anomalies', {}):
            recommendations.append("Brute force attempts detected. Consider implementing account lockout policies.")
        
        if 'off_hours_activity' in analysis.get('top_anomalies', {}):
            recommendations.append("Unusual off-hours activity detected. Review user access patterns.")
        
        analysis['recommendations'] = recommendations
        
        return jsonify(analysis)
        
    except Exception as e:
        logger.error(f"Error analyzing logs: {e}")
        return jsonify({'error': str(e)}), 500

@ai_parser_bp.route('/patterns', methods=['GET'])
def get_learned_patterns():
    """Get learned patterns and statistics"""
    try:
        stats = ai_parser.get_parsing_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting patterns: {e}")
        return jsonify({'error': str(e)}), 500

@ai_parser_bp.route('/train', methods=['POST'])
def train_parser():
    """Train parser with sample data"""
    try:
        data = request.get_json()
        training_logs = data.get('logs', [])
        
        if not training_logs:
            return jsonify({'error': 'No training data provided'}), 400
        
        parsed_logs = []
        for log_line in training_logs:
            parsed = ai_parser.extract_fields(log_line)
            parsed_logs.append(parsed)
        
        ai_parser.learn_patterns(parsed_logs)
        
        return jsonify({
            'message': 'Training completed',
            'trained_logs': len(parsed_logs),
            'patterns_learned': len(ai_parser.learned_patterns)
        })
        
    except Exception as e:
        logger.error(f"Error training parser: {e}")
        return jsonify({'error': str(e)}), 500

@ai_parser_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for AI parser"""
    try:
        stats = ai_parser.get_parsing_stats()
        return jsonify({
            'status': 'healthy',
            'patterns_loaded': len(ai_parser.learned_patterns),
            'supported_log_types': len(ai_parser.log_types),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500
