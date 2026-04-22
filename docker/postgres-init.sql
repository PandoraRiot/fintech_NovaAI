-- postgres-init.sql
-- Crea las bases de datos necesarias para la app y Frankfurter

CREATE DATABASE fintechdb;
CREATE DATABASE frankfurterdb;

-- Tablas del Gold Layer para persistencia
\c fintechdb;

CREATE TABLE IF NOT EXISTS user_360 (
    user_id           TEXT PRIMARY KEY,
    name              TEXT,
    age               INTEGER,
    email             TEXT,
    segment           TEXT,
    city              TEXT,
    country           TEXT,
    total_spent       FLOAT,
    avg_transaction   FLOAT,
    n_transactions    INTEGER,
    fail_ratio        FLOAT,
    current_balance   FLOAT,
    cluster           INTEGER,
    segment_name      TEXT,
    is_high_value     INTEGER,
    is_low_balance    INTEGER,
    is_high_risk      INTEGER,
    financial_stress  INTEGER,
    updated_at        TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS anomalies (
    event_id       TEXT PRIMARY KEY,
    user_id        TEXT,
    event_type     TEXT,
    amount         FLOAT,
    merchant       TEXT,
    category       TEXT,
    anomaly_score  FLOAT,
    detected_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id             SERIAL PRIMARY KEY,
    run_at         TIMESTAMP DEFAULT NOW(),
    n_events       INTEGER,
    n_users        INTEGER,
    n_anomalies    INTEGER,
    silhouette     FLOAT,
    duration_sec   FLOAT
);

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO fintech;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO fintech;
