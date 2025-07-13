-- init_users.sql for ClickHouse (MARSLOG)

-- Create read-write user
CREATE USER IF NOT EXISTS marslog_rw IDENTIFIED BY 'marslog123';
GRANT SELECT, INSERT, ALTER ON marslog.* TO marslog_rw;
