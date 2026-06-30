"""
Telegram scraper for medical-telegram-warehouse.
Extracts messages and images from public Telegram channels into a
partitioned raw data lake:
  data/raw/telegram_messages/YYYY-MM-DD/channel_name.json
  data/raw/images/{channel_name}/{message_id}.jpg
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path

from telethon.sync import TelegramClient
from telethon.tl.types import MessageMediaPhoto
from dotenv import load_dotenv

# ---------- Config ----------
load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
PHONE = os.getenv("TELEGRAM_PHONE")

CHANNELS = [
    "CheMed123",       # CheMed Telegram Channel
    "lobelia4cosmetics",  # Lobelia Cosmetics
    "tikvahpharma1",    # Tikvah Pharma
]

DATA_ROOT = Path("data/raw")
LOG_ROOT = Path("logs")
LOG_ROOT.mkdir(exist_ok=True)
DATA_ROOT.mkdir(parents=True, exist_ok=True)

# ---------- Logging ----------
log_file = LOG_ROOT / f"scrape_{datetime.now().strftime('%Y-%m-%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def serialize_message(msg, channel_name, has_media, image_path):
    """Convert a Telethon message object into a JSON-serializable dict,
    preserving the original structure as much as possible."""
    return {
        "message_id": msg.id,
        "channel_name": channel_name,
        "message_date": msg.date.isoformat() if msg.date else None,
        "message_text": msg.message or "",
        "has_media": has_media,
        "image_path": image_path,
        "views": getattr(msg, "views", None),
        "forwards": getattr(msg, "forwards", None),
        "raw": msg.to_dict(),  # preserve original API structure
    }


def scrape_channel(client, channel_name, today_str):
    logger.info(f"Starting scrape for channel: {channel_name}")
    messages_out = []

    image_dir = DATA_ROOT / "images" / channel_name
    image_dir.mkdir(parents=True, exist_ok=True)

    try:
        for msg in client.iter_messages(channel_name, limit=200):
            has_media = msg.media is not None
            image_path = None

            if has_media and isinstance(msg.media, MessageMediaPhoto):
                try:
                    image_path_obj = image_dir / f"{msg.id}.jpg"
                    client.download_media(msg, file=str(image_path_obj))
                    image_path = str(image_path_obj)
                    logger.info(f"Downloaded image for message {msg.id} in {channel_name}")
                except Exception as e:
                    logger.error(f"Failed to download image for message {msg.id} in {channel_name}: {e}")

            messages_out.append(
                serialize_message(msg, channel_name, has_media, image_path)
            )

        # Write JSON for this channel, partitioned by date
        out_dir = DATA_ROOT / "telegram_messages" / today_str
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{channel_name}.json"

        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(messages_out, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"Saved {len(messages_out)} messages from {channel_name} to {out_file}")

    except Exception as e:
        logger.error(f"Error scraping channel {channel_name}: {e}")


def main():
    today_str = datetime.now().strftime("%Y-%m-%d")
    logger.info("=== Scrape run started ===")

    with TelegramClient("medwarehouse_session", API_ID, API_HASH) as client:
        for channel in CHANNELS:
            scrape_channel(client, channel, today_str)

    logger.info("=== Scrape run finished ===")


if __name__ == "__main__":
    main()