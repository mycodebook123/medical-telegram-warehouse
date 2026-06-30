"""
Loads YOLO detection results CSV into PostgreSQL raw schema,
so dbt can build fct_image_detections on top of it.
"""

import os
import csv
import psycopg2
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

cur.execute("""
    CREATE TABLE IF NOT EXISTS raw.yolo_detections (
        id SERIAL PRIMARY KEY,
        channel_name TEXT,
        message_id BIGINT,
        image_path TEXT,
        detected_class TEXT,
        confidence_score FLOAT,
        image_category TEXT,
        loaded_at TIMESTAMP DEFAULT NOW()
    );
""")
conn.commit()

with open("data/yolo_detections.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = [
        (
            row["channel_name"],
            int(row["message_id"]),
            row["image_path"],
            row["detected_class"],
            float(row["confidence_score"]),
            row["image_category"],
        )
        for row in reader
    ]

cur.executemany("""
    INSERT INTO raw.yolo_detections
        (channel_name, message_id, image_path, detected_class, confidence_score, image_category)
    VALUES (%s, %s, %s, %s, %s, %s)
""", rows)

conn.commit()
cur.close()
conn.close()

print(f"Loaded {len(rows)} detection rows into raw.yolo_detections.")