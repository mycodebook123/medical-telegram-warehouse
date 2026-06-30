"""
FastAPI analytical API exposing insights from the medical Telegram data warehouse.
Run with: uvicorn api.main:app --reload
"""

import re
from collections import Counter
from typing import List

from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from api.database import get_db
from api.schemas import (
    TopProduct,
    ChannelActivity,
    MessageSearchResult,
    VisualContentStats,
)

app = FastAPI(
    title="Medical Telegram Warehouse API",
    description="Analytical API exposing insights about Ethiopian medical Telegram channels.",
    version="1.0.0",
)

# Common English/medical stopwords to exclude from "top products" term extraction
STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "from", "have", "has",
    "are", "you", "your", "our", "all", "can", "will", "not", "but",
    "price", "available", "call", "order", "now", "new", "free", "more",
}


@app.get("/")
def root():
    return {"message": "Medical Telegram Warehouse API is running. Visit /docs for documentation."}


@app.get("/api/reports/top-products", response_model=List[TopProduct], tags=["Reports"])
def top_products(
    limit: int = Query(10, ge=1, le=100, description="Number of top terms to return"),
    db: Session = Depends(get_db),
):
    """
    Returns the most frequently mentioned terms/products across all channels,
    derived from message text (simple word-frequency analysis).
    """
    rows = db.execute(text("SELECT message_text FROM marts.fct_messages")).fetchall()

    counter = Counter()
    for row in rows:
        text_value = row[0] or ""
        words = re.findall(r"[a-zA-Z]{4,}", text_value.lower())
        for w in words:
            if w not in STOPWORDS:
                counter[w] += 1

    top = counter.most_common(limit)
    return [TopProduct(term=term, mention_count=count) for term, count in top]


@app.get("/api/channels/{channel_name}/activity", response_model=ChannelActivity, tags=["Channels"])
def channel_activity(channel_name: str, db: Session = Depends(get_db)):
    """
    Returns posting activity and stats for a specific channel.
    """
    row = db.execute(
        text("""
            SELECT channel_name, channel_type, total_posts, avg_views,
                   first_post_date, last_post_date
            FROM marts.dim_channels
            WHERE channel_name = :channel_name
        """),
        {"channel_name": channel_name},
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"Channel '{channel_name}' not found.")

    return ChannelActivity(
        channel_name=row[0],
        channel_type=row[1],
        total_posts=row[2],
        avg_views=float(row[3]) if row[3] is not None else 0.0,
        first_post_date=row[4],
        last_post_date=row[5],
    )


@app.get("/api/search/messages", response_model=List[MessageSearchResult], tags=["Search"])
def search_messages(
    query: str = Query(..., min_length=1, description="Keyword to search for in message text"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Searches for messages containing a specific keyword (case-insensitive).
    """
    rows = db.execute(
        text("""
            SELECT f.message_id, c.channel_name, f.message_text, f.views, f.forwards, d.full_date
            FROM marts.fct_messages f
            JOIN marts.dim_channels c ON f.channel_key = c.channel_key
            JOIN marts.dim_dates d ON f.date_key = d.date_key
            WHERE f.message_text ILIKE :pattern
            ORDER BY f.views DESC
            LIMIT :limit
        """),
        {"pattern": f"%{query}%", "limit": limit},
    ).fetchall()

    return [
        MessageSearchResult(
            message_id=row[0],
            channel_name=row[1],
            message_text=row[2],
            views=row[3],
            forwards=row[4],
            message_date=row[5],
        )
        for row in rows
    ]


@app.get("/api/reports/visual-content", response_model=List[VisualContentStats], tags=["Reports"])
def visual_content_stats(db: Session = Depends(get_db)):
    """
    Returns statistics about image usage and content category across channels.
    """
    rows = db.execute(
        text("""
            SELECT
                c.channel_name,
                COUNT(*) AS total_images,
                COUNT(*) FILTER (WHERE i.image_category = 'promotional') AS promotional_count,
                COUNT(*) FILTER (WHERE i.image_category = 'product_display') AS product_display_count,
                COUNT(*) FILTER (WHERE i.image_category = 'lifestyle') AS lifestyle_count,
                COUNT(*) FILTER (WHERE i.image_category = 'other') AS other_count
            FROM marts.fct_image_detections i
            JOIN marts.dim_channels c ON i.channel_key = c.channel_key
            GROUP BY c.channel_name
            ORDER BY total_images DESC
        """)
    ).fetchall()

    return [
        VisualContentStats(
            channel_name=row[0],
            total_images=row[1],
            promotional_count=row[2],
            product_display_count=row[3],
            lifestyle_count=row[4],
            other_count=row[5],
        )
        for row in rows
    ]