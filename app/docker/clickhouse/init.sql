-- init.sql for ClickHouse (MARSLOG)

CREATE DATABASE IF NOT EXISTS marslog;

USE marslog;

CREATE TABLE IF NOT EXISTS logs (
    timestamp DateTime,
    device String,
    severity String,
    message String,
    source_ip IPv4,
    raw_log String
) ENGINE = MergeTree()
ORDER BY timestamp;
