"""
Pydantic models defining request/response shapes for the analytical API.
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class TopProduct(BaseModel):
    term: str
    mention_count: int


class ChannelActivity(BaseModel):
    channel_name: str
    channel_type: str
    total_posts: int
    avg_views: float
    first_post_date: Optional[datetime]
    last_post_date: Optional[datetime]


class MessageSearchResult(BaseModel):
    message_id: int
    channel_name: str
    message_text: str
    views: int
    forwards: int
    message_date: Optional[date]


class VisualContentStats(BaseModel):
    channel_name: str
    total_images: int
    promotional_count: int
    product_display_count: int
    lifestyle_count: int
    other_count: int