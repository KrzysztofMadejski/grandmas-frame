#!/bin/bash
# Creates per-app database users, databases, and required extensions.
# Runs once on first postgres startup (skipped if data volume already exists).
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE USER immich WITH PASSWORD '$IMMICH_DB_PASSWORD';
    CREATE DATABASE immich OWNER immich;

    CREATE USER evolution WITH PASSWORD '$EVOLUTION_DB_PASSWORD';
    CREATE DATABASE evolution OWNER evolution;
EOSQL

# Extensions must be created by a superuser, so we do it here before Immich starts.
# We also grant the immich user access to the schemas the extensions create.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname immich <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS vectors;
    CREATE EXTENSION IF NOT EXISTS earthdistance CASCADE;
    GRANT ALL ON SCHEMA vectors TO immich;
    GRANT ALL ON ALL TABLES IN SCHEMA vectors TO immich;
    GRANT ALL ON ALL FUNCTIONS IN SCHEMA vectors TO immich;
EOSQL
