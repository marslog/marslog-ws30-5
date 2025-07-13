#!/usr/bin/env python3
"""
Test script for MARSLOG AI Log Parser
Tests parsing functionality with sample log entries
"""

import requests
import json
import time

# Sample log entries for testing
sample_logs = [
    # Apache access logs
    '192.168.1.100 - - [11/Jul/2025:14:55:23 +0000] "GET /admin/login.php HTTP/1.1" 200 1234',
    '10.0.0.50 - - [11/Jul/2025:14:55:24 +0000] "POST /api/users HTTP/1.1" 401 567',
    '203.0.113.15 - - [11/Jul/2025:14:55:25 +0000] "GET /../../etc/passwd HTTP/1.1" 404 0',
    
    # Syslog entries
    'Jul 11 14:55:26 webapp-01 sshd[12345]: Failed password for root from 192.168.1.200 port 22 ssh2',
    'Jul 11 14:55:27 database-01 mysqld[5678]: Access denied for user \'admin\'@\'192.168.1.150\' (using password: YES)',
    'Jul 11 14:55:28 firewall-01 kernel: iptables: DROPPED: SRC=203.0.113.20 DST=10.0.0.1 PROTO=TCP SPT=1234 DPT=80',
    
    # Error logs
    '[11/Jul/2025:14:55:29 +0000] [error] [client 192.168.1.75] File does not exist: /var/www/html/admin/backup.sql',
    '[11/Jul/2025:14:55:30 +0000] [warn] [client 10.0.0.25] mod_rewrite: redirect to login attempted',
    
    # Security events
    'Jul 11 14:55:31 security-server auth: FAILED LOGIN ATTEMPT - User: admin, IP: 203.0.113.25, Attempts: 5',
    'Jul 11 14:55:32 ids-sensor snort[9999]: ATTACK DETECTED: SQL injection attempt from 203.0.113.30',
    
    # Normal activity
    'Jul 11 14:55:33 webapp-02 httpd[1111]: User authentication successful for user john@company.com',
    'Jul 11 14:55:34 backup-server rsync[2222]: backup completed successfully - 2.3GB transferred',
]

def test_ai_parser():
    """Test the AI log parser endpoints"""
    base_url = "http://localhost:5000/api/ai-parser"
    
    print("🧠 Testing MARSLOG AI Log Parser")
    print("=" * 50)
    
    # Test 1: Health check
    print("\n1. Testing health check...")
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            health_data = response.json()
            print(f"   ✅ Health check passed")
            print(f"   Status: {health_data.get('status')}")
            print(f"   Supported log types: {health_data.get('supported_log_types')}")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
    
    # Test 2: Parse sample logs
    print("\n2. Testing log parsing...")
    try:
        payload = {
            "logs": sample_logs,
            "learn": True,
            "store": True
        }
        
        response = requests.post(f"{base_url}/parse", json=payload)
        if response.status_code == 200:
            parse_data = response.json()
            print(f"   ✅ Parsing successful")
            print(f"   Total logs processed: {parse_data['summary']['total_logs']}")
            print(f"   High risk logs: {parse_data['summary']['high_risk_count']}")
            print(f"   Anomaly logs: {parse_data['summary']['anomaly_count']}")
            print(f"   Average risk score: {parse_data['summary']['avg_risk_score']:.2f}")
            print(f"   Average confidence: {parse_data['summary']['avg_confidence']:.2f}")
            
            # Show some parsed examples
            print("\n   📋 Sample parsed logs:")
            for i, log in enumerate(parse_data['parsed_logs'][:3]):
                print(f"   Log {i+1}:")
                print(f"     Type: {log['log_type']}")
                print(f"     Risk Score: {log['risk_score']}")
                print(f"     Anomalies: {', '.join(log['anomaly_indicators']) if log['anomaly_indicators'] else 'None'}")
                print(f"     Confidence: {log['confidence']:.2f}")
                print()
        else:
            print(f"   ❌ Parsing failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Parsing error: {e}")
    
    # Test 3: Get learned patterns
    print("\n3. Testing learned patterns...")
    try:
        response = requests.get(f"{base_url}/patterns")
        if response.status_code == 200:
            patterns_data = response.json()
            print(f"   ✅ Patterns retrieved")
            print(f"   Total patterns: {patterns_data['total_patterns']}")
            print(f"   Supported log types: {len(patterns_data['supported_log_types'])}")
        else:
            print(f"   ❌ Patterns retrieval failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Patterns error: {e}")
    
    # Test 4: Analyze logs
    print("\n4. Testing log analysis...")
    try:
        payload = {
            "time_range": "1h"
        }
        
        response = requests.post(f"{base_url}/analyze", json=payload)
        if response.status_code == 200:
            analysis_data = response.json()
            print(f"   ✅ Analysis successful")
            print(f"   Time range: {analysis_data.get('time_range')}")
            print(f"   Total logs: {analysis_data.get('total_logs', 0)}")
            print(f"   High risk events: {analysis_data.get('total_high_risk', 0)}")
            print(f"   Total anomalies: {analysis_data.get('total_anomalies', 0)}")
            
            if analysis_data.get('recommendations'):
                print(f"   💡 Recommendations:")
                for rec in analysis_data['recommendations']:
                    print(f"     • {rec}")
        else:
            print(f"   ❌ Analysis failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Analysis error: {e}")
    
    # Test 5: Training
    print("\n5. Testing parser training...")
    try:
        payload = {
            "logs": sample_logs[:5]  # Use subset for training
        }
        
        response = requests.post(f"{base_url}/train", json=payload)
        if response.status_code == 200:
            train_data = response.json()
            print(f"   ✅ Training successful")
            print(f"   Message: {train_data['message']}")
            print(f"   Trained logs: {train_data['trained_logs']}")
            print(f"   Patterns learned: {train_data['patterns_learned']}")
        else:
            print(f"   ❌ Training failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Training error: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 AI Log Parser testing completed!")

def test_individual_parsing():
    """Test individual log parsing with detailed output"""
    print("\n🔍 Individual Log Parsing Test")
    print("=" * 50)
    
    base_url = "http://localhost:5000/api/ai-parser"
    
    test_logs = [
        '203.0.113.100 - - [11/Jul/2025:15:00:00 +0000] "GET /admin/../../etc/passwd HTTP/1.1" 404 0',
        'Jul 11 15:00:01 server-01 sshd[1234]: Failed password for root from 203.0.113.150 port 22 ssh2',
        'Jul 11 15:00:02 security snort[9999]: ATTACK DETECTED: SQL injection from 203.0.113.200'
    ]
    
    for i, log in enumerate(test_logs, 1):
        print(f"\nTest Log {i}: {log}")
        try:
            payload = {"logs": [log], "store": False}
            response = requests.post(f"{base_url}/parse", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                parsed_log = data['parsed_logs'][0]
                
                print(f"  🏷️  Type: {parsed_log['log_type']}")
                print(f"  ⚠️  Risk Score: {parsed_log['risk_score']}/100")
                print(f"  🎯 Confidence: {parsed_log['confidence']:.2f}")
                print(f"  🚨 Anomalies: {', '.join(parsed_log['anomaly_indicators']) if parsed_log['anomaly_indicators'] else 'None'}")
                
                if parsed_log['parsed_fields']:
                    print(f"  📊 Parsed Fields:")
                    for field, value in parsed_log['parsed_fields'].items():
                        if isinstance(value, list):
                            value = ', '.join(str(v) for v in value)
                        print(f"     {field}: {value}")
            else:
                print(f"  ❌ Failed: {response.status_code}")
        except Exception as e:
            print(f"  ❌ Error: {e}")

if __name__ == "__main__":
    print("Starting AI Log Parser Tests...")
    test_ai_parser()
    test_individual_parsing()
