#!/usr/bin/env python3
"""
MARSLOG-ClickHouse Flask API Server
Main Flask application for MARSLOG with ClickHouse integration
"""

import os
import sys
import json
import traceback
import warnings
import threading
import time
from datetime import datetime, timedelta

# Suppress warnings
warnings.filterwarnings("ignore", message=".*TripleDES.*", category=DeprecationWarning)

from flask import Flask, request, jsonify, g
from flask_cors import CORS
import jwt
import clickhouse_connect
import redis
import logging
from logging.handlers import RotatingFileHandler

# Import custom modules
from utils import (
    hash_password, verify_password, find_user_by_username,
    add_user_to_json, get_ip_info
)
from ai_log_parser import ai_parser_bp

# Initialize Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "your_super_secret_key_change_me_in_prod")

# Enable CORS
CORS(app, origins=["*"], methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# Configure logging
if not app.debug:
    if not os.path.exists('/app/logs'):
        os.makedirs('/app/logs')
    
    file_handler = RotatingFileHandler('/app/logs/marslog.log', 
                                       maxBytes=10240000, backupCount=5)
    file_handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('MARSLOG startup')

# Database configurations
CLICKHOUSE_HOST = os.getenv('CLICKHOUSE_HOST', 'clickhouse')
CLICKHOUSE_PORT = int(os.getenv('CLICKHOUSE_PORT', 9000))
CLICKHOUSE_USER = os.getenv('CLICKHOUSE_USER', 'default')
CLICKHOUSE_PASSWORD = os.getenv('CLICKHOUSE_PASSWORD', '')
CLICKHOUSE_DATABASE = os.getenv('CLICKHOUSE_DATABASE', 'marslog')

REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

# Global connections
clickhouse_client = None
redis_client = None

def get_clickhouse_client():
    """Get ClickHouse client connection"""
    global clickhouse_client
    if clickhouse_client is None:
        try:
            clickhouse_client = clickhouse_connect.get_client(
                host=CLICKHOUSE_HOST,
                port=CLICKHOUSE_PORT,
                username=CLICKHOUSE_USER,
                password=CLICKHOUSE_PASSWORD,
                database=CLICKHOUSE_DATABASE
            )
            app.logger.info(f"Connected to ClickHouse at {CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}")
        except Exception as e:
            app.logger.error(f"Failed to connect to ClickHouse: {e}")
            clickhouse_client = None
    return clickhouse_client

def get_redis_client():
    """Get Redis client connection"""
    global redis_client
    if redis_client is None:
        try:
            redis_client = redis.Redis(
                host=REDIS_HOST, 
                port=REDIS_PORT, 
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            redis_client.ping()
            app.logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        except Exception as e:
            app.logger.error(f"Failed to connect to Redis: {e}")
            redis_client = None
    return redis_client

# Initialize database connections
@app.before_first_request
def initialize_connections():
    """Initialize database connections and create tables"""
    # Initialize ClickHouse
    ch_client = get_clickhouse_client()
    if ch_client:
        try:
            # Create database if not exists
            ch_client.command(f"CREATE DATABASE IF NOT EXISTS {CLICKHOUSE_DATABASE}")
            
            # Create logs table
            ch_client.command(f"""
                CREATE TABLE IF NOT EXISTS {CLICKHOUSE_DATABASE}.logs (
                    timestamp DateTime64(3),
                    level String,
                    message String,
                    source String,
                    host String,
                    facility String,
                    severity Int32,
                    program String,
                    pid Int32,
                    raw_message String,
                    parsed_fields Map(String, String),
                    created_at DateTime DEFAULT now()
                ) ENGINE = MergeTree()
                ORDER BY (timestamp, host, source)
                PARTITION BY toYYYYMM(timestamp)
                TTL timestamp + INTERVAL 90 DAY
            """)
            
            # Create metrics table
            ch_client.command(f"""
                CREATE TABLE IF NOT EXISTS {CLICKHOUSE_DATABASE}.system_metrics (
                    timestamp DateTime64(3),
                    host String,
                    metric_name String,
                    metric_value Float64,
                    tags Map(String, String),
                    created_at DateTime DEFAULT now()
                ) ENGINE = MergeTree()
                ORDER BY (timestamp, host, metric_name)
                PARTITION BY toYYYYMM(timestamp)
                TTL timestamp + INTERVAL 30 DAY
            """)
            
            # Create alerts table
            ch_client.command(f"""
                CREATE TABLE IF NOT EXISTS {CLICKHOUSE_DATABASE}.alerts (
                    id String,
                    timestamp DateTime64(3),
                    level String,
                    title String,
                    message String,
                    source String,
                    host String,
                    status String DEFAULT 'open',
                    acknowledged Boolean DEFAULT false,
                    acknowledged_by String DEFAULT '',
                    acknowledged_at DateTime DEFAULT '1970-01-01 00:00:00',
                    resolved_at DateTime DEFAULT '1970-01-01 00:00:00',
                    metadata Map(String, String),
                    created_at DateTime DEFAULT now()
                ) ENGINE = MergeTree()
                ORDER BY (timestamp, level, host)
                PARTITION BY toYYYYMM(timestamp)
                TTL timestamp + INTERVAL 365 DAY
            """)
            
            # Create parsed logs table for AI parser
            ch_client.command(f"""
                CREATE TABLE IF NOT EXISTS {CLICKHOUSE_DATABASE}.parsed_logs (
                    timestamp DateTime64(3),
                    raw_log String,
                    log_type String,
                    risk_score Int32,
                    anomaly_indicators String,
                    confidence Float64,
                    parsed_fields String,
                    source_ip String,
                    dest_ip String,
                    user_agent String,
                    status_code Int32,
                    bytes_sent Int64,
                    created_at DateTime DEFAULT now()
                ) ENGINE = MergeTree()
                ORDER BY (timestamp, log_type, risk_score)
                PARTITION BY toYYYYMM(timestamp)
                TTL timestamp + INTERVAL 90 DAY
            """)
            
            app.logger.info("ClickHouse tables created successfully")
        except Exception as e:
            app.logger.error(f"Failed to create ClickHouse tables: {e}")
    
    # Initialize Redis
    redis_client = get_redis_client()

# Authentication decorator
def jwt_required(f):
    """JWT authentication decorator"""
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            g.current_user = data
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid'}), 401
        
        return f(*args, **kwargs)
    
    decorated_function.__name__ = f.__name__
    return decorated_function

# ================================
# AUTHENTICATION ROUTES
# ================================

@app.route("/api/login", methods=["POST"])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        username = data.get("username", "")
        password = data.get("password", "")
        
        if not username or not password:
            return jsonify({"message": "Username and password required"}), 400
        
        user = find_user_by_username(username)
        if not user or not verify_password(password, user["password"]):
            return jsonify({"message": "Invalid credentials"}), 401
        
        # Generate JWT token
        token = jwt.encode({
            'user_id': user.get('id', username),
            'username': username,
            'role': user.get('role', 'user'),
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'token': token,
            'user': {
                'username': username,
                'role': user.get('role', 'user')
            }
        })
        
    except Exception as e:
        app.logger.error(f"Login error: {e}")
        return jsonify({"message": "Internal server error"}), 500

@app.route("/api/user", methods=["GET"])
@jwt_required
def get_user():
    """Get current user info"""
    return jsonify(g.current_user)

# ================================
# LOG MANAGEMENT ROUTES
# ================================

@app.route("/api/logs", methods=["GET"])
@jwt_required
def get_logs():
    """Get logs with filtering and pagination"""
    try:
        ch_client = get_clickhouse_client()
        if not ch_client:
            return jsonify({"error": "Database connection failed"}), 500
        
        # Get query parameters
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 100)), 1000)  # Max 1000 logs per request
        offset = (page - 1) * limit
        
        level = request.args.get('level')
        host = request.args.get('host')
        source = request.args.get('source')
        search = request.args.get('search')
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        
        # Build query
        where_conditions = []
        params = {}
        
        if level:
            where_conditions.append("level = %(level)s")
            params['level'] = level
        
        if host:
            where_conditions.append("host = %(host)s")
            params['host'] = host
        
        if source:
            where_conditions.append("source = %(source)s")
            params['source'] = source
        
        if search:
            where_conditions.append("(message ILIKE %(search)s OR raw_message ILIKE %(search)s)")
            params['search'] = f"%{search}%"
        
        if start_time:
            where_conditions.append("timestamp >= %(start_time)s")
            params['start_time'] = start_time
        
        if end_time:
            where_conditions.append("timestamp <= %(end_time)s")
            params['end_time'] = end_time
        
        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Get total count
        count_query = f"SELECT count() FROM {CLICKHOUSE_DATABASE}.logs{where_clause}"
        total_count = ch_client.command(count_query, parameters=params)
        
        # Get logs
        query = f"""
            SELECT 
                timestamp,
                level,
                message,
                source,
                host,
                facility,
                severity,
                program,
                pid,
                raw_message,
                parsed_fields
            FROM {CLICKHOUSE_DATABASE}.logs
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT {limit} OFFSET {offset}
        """
        
        result = ch_client.query(query, parameters=params)
        logs = []
        for row in result.result_rows:
            logs.append({
                'timestamp': row[0].isoformat() if row[0] else None,
                'level': row[1],
                'message': row[2],
                'source': row[3],
                'host': row[4],
                'facility': row[5],
                'severity': row[6],
                'program': row[7],
                'pid': row[8],
                'raw_message': row[9],
                'parsed_fields': dict(row[10]) if row[10] else {}
            })
        
        return jsonify({
            'logs': logs,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
            }
        })
        
    except Exception as e:
        app.logger.error(f"Get logs error: {e}")
        return jsonify({"error": "Failed to retrieve logs"}), 500

@app.route("/api/logs", methods=["POST"])
@jwt_required
def insert_log():
    """Insert new log entry"""
    try:
        ch_client = get_clickhouse_client()
        if not ch_client:
            return jsonify({"error": "Database connection failed"}), 500
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['timestamp', 'level', 'message']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Insert log
        ch_client.insert(f"{CLICKHOUSE_DATABASE}.logs", [data])
        
        return jsonify({"message": "Log inserted successfully"}), 201
        
    except Exception as e:
        app.logger.error(f"Insert log error: {e}")
        return jsonify({"error": "Failed to insert log"}), 500

# ================================
# METRICS ROUTES
# ================================

@app.route("/api/metrics", methods=["GET"])
@jwt_required
def get_metrics():
    """Get system metrics"""
    try:
        ch_client = get_clickhouse_client()
        if not ch_client:
            return jsonify({"error": "Database connection failed"}), 500
        
        # Get query parameters
        host = request.args.get('host')
        metric_name = request.args.get('metric_name')
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        
        # Build query
        where_conditions = []
        params = {}
        
        if host:
            where_conditions.append("host = %(host)s")
            params['host'] = host
        
        if metric_name:
            where_conditions.append("metric_name = %(metric_name)s")
            params['metric_name'] = metric_name
        
        if start_time:
            where_conditions.append("timestamp >= %(start_time)s")
            params['start_time'] = start_time
        
        if end_time:
            where_conditions.append("timestamp <= %(end_time)s")
            params['end_time'] = end_time
        
        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        query = f"""
            SELECT 
                timestamp,
                host,
                metric_name,
                metric_value,
                tags
            FROM {CLICKHOUSE_DATABASE}.system_metrics
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT 1000
        """
        
        result = ch_client.query(query, parameters=params)
        metrics = []
        for row in result.result_rows:
            metrics.append({
                'timestamp': row[0].isoformat() if row[0] else None,
                'host': row[1],
                'metric_name': row[2],
                'metric_value': row[3],
                'tags': dict(row[4]) if row[4] else {}
            })
        
        return jsonify({'metrics': metrics})
        
    except Exception as e:
        app.logger.error(f"Get metrics error: {e}")
        return jsonify({"error": "Failed to retrieve metrics"}), 500

# ================================
# HEALTH CHECK ROUTES
# ================================

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'services': {}
    }
    
    # Check ClickHouse
    try:
        ch_client = get_clickhouse_client()
        if ch_client:
            ch_client.command("SELECT 1")
            status['services']['clickhouse'] = 'healthy'
        else:
            status['services']['clickhouse'] = 'unhealthy'
            status['status'] = 'degraded'
    except:
        status['services']['clickhouse'] = 'unhealthy'
        status['status'] = 'degraded'
    
    # Check Redis
    try:
        redis_client = get_redis_client()
        if redis_client:
            redis_client.ping()
            status['services']['redis'] = 'healthy'
        else:
            status['services']['redis'] = 'unhealthy'
    except:
        status['services']['redis'] = 'unhealthy'
    
    return jsonify(status)

# ================================
# ERROR HANDLERS
# ================================
# BLUEPRINT REGISTRATION
# ================================

# Register AI parser blueprint
app.register_blueprint(ai_parser_bp, url_prefix="/api/ai-parser")

# ================================
# ERROR HANDLERS
# ================================
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# ================================
# MAIN
# ================================

if __name__ == "__main__":
    # Initialize connections
    with app.app_context():
        initialize_connections()
    
    # Run the application
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    
    app.run(host="0.0.0.0", port=port, debug=debug)
