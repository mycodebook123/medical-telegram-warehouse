"""
Loads raw Telegram JSON files from the data lake into PostgreSQL,
into raw.telegram_messages, preserving the original message structure.
"""

import os
import json
import glob
from pathlib import Path

import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST"),
    port=os.getenv("POSTGRES_PORT"),
    dbname=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
)
cur = conn.cursor()

# Create raw table if it doesn't exist
cur.execute("""
    CREATE TABLE IF NOT EXISTS raw.telegram_messages (
        id SERIAL PRIMARY KEY,
        message_id BIGINT,
        channel_name TEXT,
        message_date TIMESTAMP,
        message_text TEXT,
        has_media BOOLEAN,
        image_path TEXT,
        views INTEGER,
        forwards INTEGER,
        raw_json JSONB,
        loaded_at TIMESTAMP DEFAULT NOW()
    );
""")
conn.commit()

json_files = glob.glob("data/raw/telegram_messages/*/*.json")
print(f"Found {len(json_files)} JSON files to load.")

total_inserted = 0

for file_path in json_files:
    with open(file_path, "r", encoding="utf-8") as f:
        messages = json.load(f)

    for msg in messages:
        cur.execute("""
            INSERT INTO raw.telegram_messages
                (message_id, channel_name, message_date, message_text,
                 has_media, image_path, views, forwards, raw_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            msg.get("message_id"),
            msg.get("channel_name"),
            msg.get("message_date"),
            msg.get("message_text"),
            msg.get("has_media"),
            msg.get("image_path"),
            msg.get("views"),
            msg.get("forwards"),
            Json(msg.get("raw", {})),
        ))
        total_inserted += 1

conn.commit()
cur.close()
conn.close()

print(f"Loaded {total_inserted} messages into raw.telegram_messages.")