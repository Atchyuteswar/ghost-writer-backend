"""Ghost-Writer Backend — Chat Parser Service.

Parses WhatsApp, Discord, and Email exports into ParsedMessage objects.
Handles malformed input gracefully — never crashes, always logs and skips bad lines.
"""
import re
import json
import csv
import io
import uuid
import logging
from datetime import datetime
from typing import Tuple

from models.schemas import ParsedMessage

logger = logging.getLogger(__name__)

# ─── System messages to skip in WhatsApp ──────────────────────
WHATSAPP_SKIP_PATTERNS = [
    "messages and calls are end-to-end encrypted",
    "you deleted this message",
    "this message was deleted",
    "null",
    "media omitted",
    "image omitted",
    "video omitted",
    "audio omitted",
    "sticker omitted",
    "document omitted",
    "gif omitted",
    "missed voice call",
    "missed video call",
    "waiting for this message",
]

# WhatsApp timestamp regex patterns
WA_PATTERNS = [
    # [DD/MM/YYYY, HH:MM:SS] Sender: message
    re.compile(r"^\[(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?)\]\s+(.+?):\s(.+)$"),
    # DD/MM/YYYY, HH:MM:SS - Sender: message
    re.compile(r"^(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?)\s*-\s+(.+?):\s(.+)$"),
]

# Date parse formats for WhatsApp
WA_DATE_FORMATS = [
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%y %H:%M:%S",
    "%d/%m/%y %H:%M",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M",
    "%m/%d/%y %I:%M %p",
    "%m/%d/%y %I:%M:%S %p",
    "%d/%m/%Y %I:%M %p",
    "%d/%m/%y %I:%M %p",
]


class ChatParser:
    """Unified parser for WhatsApp, Discord, and Email exports."""

    @staticmethod
    def parse_whatsapp(content: str) -> Tuple[list[ParsedMessage], list[str]]:
        """Parse a WhatsApp .txt chat export."""
        messages: list[ParsedMessage] = []
        warnings: list[str] = []
        lines = content.strip().split("\n")

        current_msg = None

        for line_num, raw_line in enumerate(lines, 1):
            line = raw_line.strip()
            if not line:
                continue

            # Check if this line should be skipped
            lower = line.lower()
            if any(skip in lower for skip in WHATSAPP_SKIP_PATTERNS):
                continue

            # Try to match against timestamp patterns
            matched = False
            for pattern in WA_PATTERNS:
                m = pattern.match(raw_line.strip())
                if m:
                    # If we had a pending message, save it
                    if current_msg:
                        messages.append(current_msg)

                    date_str = m.group(1)
                    time_str = m.group(2).strip()
                    sender = m.group(3).strip()
                    text = m.group(4).strip()

                    # Skip system messages in the text
                    if any(skip in text.lower() for skip in WHATSAPP_SKIP_PATTERNS):
                        current_msg = None
                        matched = True
                        break

                    # Parse timestamp
                    timestamp = _parse_wa_datetime(date_str, time_str, warnings, line_num)

                    current_msg = ParsedMessage(
                        id=str(uuid.uuid4()),
                        timestamp=timestamp,
                        sender=sender,
                        text=text,
                        platform="whatsapp",
                        word_count=len(text.split()),
                        char_count=len(text),
                    )
                    matched = True
                    break

            if not matched:
                # This is a continuation of the previous message (multi-bubble)
                if current_msg:
                    current_msg = current_msg.model_copy(update={
                        "text": current_msg.text + " " + line,
                        "word_count": len((current_msg.text + " " + line).split()),
                        "char_count": len(current_msg.text + " " + line),
                    })

        # Don't forget the last message
        if current_msg:
            messages.append(current_msg)

        return messages, warnings

    @staticmethod
    def parse_discord(content: str) -> Tuple[list[ParsedMessage], list[str]]:
        """Parse a Discord JSON chat export."""
        messages: list[ParsedMessage] = []
        warnings: list[str] = []

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            warnings.append(f"Invalid JSON: {e}")
            return messages, warnings

        # Handle both root-level and nested formats
        msg_list = data.get("messages", [])
        if not msg_list and "channel" in data:
            msg_list = data["channel"].get("messages", [])
        if not msg_list and isinstance(data, list):
            msg_list = data

        for msg in msg_list:
            try:
                author = msg.get("author", {})

                # Skip bots
                if author.get("bot", False) or author.get("isBot", False):
                    continue

                content_text = (msg.get("content") or "").strip()

                # Skip empty content
                if not content_text:
                    # If there are attachments, use placeholder
                    if msg.get("attachments"):
                        content_text = "[attachment]"
                    else:
                        continue

                # Skip URL-only messages
                if re.match(r"^https?://\S+$", content_text):
                    continue

                timestamp = msg.get("timestamp", datetime.now().isoformat())
                sender = author.get("name", author.get("username", "Unknown"))

                messages.append(ParsedMessage(
                    id=str(uuid.uuid4()),
                    timestamp=timestamp,
                    sender=sender,
                    text=content_text,
                    platform="discord",
                    word_count=len(content_text.split()),
                    char_count=len(content_text),
                ))
            except Exception as e:
                warnings.append(f"Skipped Discord message: {e}")

        return messages, warnings

    @staticmethod
    def parse_email(content: str) -> Tuple[list[ParsedMessage], list[str]]:
        """Parse an Email CSV or mbox export."""
        messages: list[ParsedMessage] = []
        warnings: list[str] = []

        lines = content.strip().split("\n")

        # Try to detect mbox format
        if lines and lines[0].startswith("From "):
            return ChatParser._parse_mbox(content, warnings)

        # CSV format
        try:
            reader = csv.DictReader(io.StringIO(content))
            fieldnames = reader.fieldnames or []

            # Normalize field names (handle case variations)
            field_map = {}
            for f in fieldnames:
                fl = f.lower().strip()
                if fl in ("date", "timestamp"):
                    field_map["date"] = f
                elif fl in ("sender", "from"):
                    field_map["sender"] = f
                elif fl in ("subject",):
                    field_map["subject"] = f
                elif fl in ("body", "content", "message"):
                    field_map["body"] = f

            for row_num, row in enumerate(reader, 2):
                try:
                    body = (row.get(field_map.get("body", "body")) or "").strip()
                    if len(body) < 5:
                        continue

                    # Strip email signatures
                    body = _strip_email_signature(body)
                    # Strip quoted replies
                    body = _strip_quoted_replies(body)

                    if len(body.strip()) < 5:
                        continue

                    sender_raw = (row.get(field_map.get("sender", "sender")) or "Unknown").strip()
                    sender = _extract_sender_name(sender_raw)

                    date_str = (row.get(field_map.get("date", "date")) or "").strip()
                    timestamp = _parse_email_date(date_str, warnings, row_num)

                    messages.append(ParsedMessage(
                        id=str(uuid.uuid4()),
                        timestamp=timestamp,
                        sender=sender,
                        text=body.strip(),
                        platform="email",
                        word_count=len(body.split()),
                        char_count=len(body.strip()),
                    ))
                except Exception as e:
                    warnings.append(f"Skipped email row {row_num}: {e}")

        except Exception as e:
            warnings.append(f"CSV parse error: {e}")

        return messages, warnings

    @staticmethod
    def _parse_mbox(content: str, warnings: list[str]) -> Tuple[list[ParsedMessage], list[str]]:
        """Parse mbox format."""
        messages: list[ParsedMessage] = []
        current_sender = ""
        current_date = ""
        current_body_lines: list[str] = []
        in_body = False

        for line in content.split("\n"):
            if line.startswith("From "):
                # Save previous message
                if current_body_lines:
                    body = "\n".join(current_body_lines).strip()
                    body = _strip_email_signature(body)
                    body = _strip_quoted_replies(body)
                    if len(body) >= 5:
                        messages.append(ParsedMessage(
                            id=str(uuid.uuid4()),
                            timestamp=current_date or datetime.now().isoformat(),
                            sender=_extract_sender_name(current_sender),
                            text=body,
                            platform="email",
                            word_count=len(body.split()),
                            char_count=len(body),
                        ))

                current_body_lines = []
                in_body = False
                parts = line.split(" ", 2)
                current_sender = parts[1] if len(parts) > 1 else "Unknown"
                current_date = parts[2].strip() if len(parts) > 2 else ""
            elif line.startswith("From:"):
                current_sender = line[5:].strip()
            elif line.startswith("Date:"):
                current_date = line[5:].strip()
            elif line == "":
                in_body = True
            elif in_body:
                current_body_lines.append(line)

        # Last message
        if current_body_lines:
            body = "\n".join(current_body_lines).strip()
            body = _strip_email_signature(body)
            body = _strip_quoted_replies(body)
            if len(body) >= 5:
                messages.append(ParsedMessage(
                    id=str(uuid.uuid4()),
                    timestamp=current_date or datetime.now().isoformat(),
                    sender=_extract_sender_name(current_sender),
                    text=body,
                    platform="email",
                    word_count=len(body.split()),
                    char_count=len(body),
                ))

        return messages, warnings

    @staticmethod
    def parse_file(filename: str, content: bytes) -> Tuple[list[ParsedMessage], list[str]]:
        """Main dispatcher — detect file type and call the appropriate parser."""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        # Decode content
        text = None
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                text = content.decode(encoding)
                break
            except (UnicodeDecodeError, AttributeError):
                continue

        if text is None:
            return [], ["Could not decode file content"]

        if ext == "json":
            return ChatParser.parse_discord(text)
        elif ext == "txt":
            return ChatParser.parse_whatsapp(text)
        elif ext == "csv":
            return ChatParser.parse_email(text)
        else:
            return [], [f"Unsupported file extension: .{ext}"]


# ─── Helpers ──────────────────────────────────────────────────

def _parse_wa_datetime(date_str: str, time_str: str, warnings: list[str], line_num: int) -> str:
    """Parse WhatsApp date+time strings into ISO 8601."""
    combined = f"{date_str} {time_str}"
    for fmt in WA_DATE_FORMATS:
        try:
            return datetime.strptime(combined, fmt).isoformat()
        except ValueError:
            continue
    warnings.append(f"Line {line_num}: Could not parse date '{combined}', using current time")
    return datetime.now().isoformat()


def _parse_email_date(date_str: str, warnings: list[str], row_num: int) -> str:
    """Parse email date string into ISO 8601."""
    if not date_str:
        return datetime.now().isoformat()
    common_formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%d/%m/%Y %H:%M",
        "%B %d, %Y",
        "%b %d, %Y %H:%M",
        "%a, %d %b %Y %H:%M:%S",
    ]
    for fmt in common_formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).isoformat()
        except ValueError:
            continue
    warnings.append(f"Row {row_num}: Could not parse date '{date_str}'")
    return datetime.now().isoformat()


def _strip_email_signature(body: str) -> str:
    """Remove email signatures."""
    sig_patterns = [
        r"^--\s*$",
        r"^Best regards",
        r"^Kind regards",
        r"^Thanks,",
        r"^Thank you,",
        r"^Regards,",
        r"^Cheers,",
        r"^Sent from my iPhone",
        r"^Sent from my iPad",
        r"^Get Outlook for",
        r"^Sent from Mail for",
    ]
    lines = body.split("\n")
    result = []
    for line in lines:
        if any(re.match(p, line.strip(), re.IGNORECASE) for p in sig_patterns):
            break
        result.append(line)
    return "\n".join(result)


def _strip_quoted_replies(body: str) -> str:
    """Remove quoted reply content."""
    lines = body.split("\n")
    result = []
    skip_rest = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(">"):
            continue
        if re.match(r"^On .+ wrote:$", stripped):
            skip_rest = True
            continue
        if skip_rest:
            continue
        result.append(line)
    return "\n".join(result)


def _extract_sender_name(sender: str) -> str:
    """Extract name from email-style sender like 'Aryan <aryan@example.com>'."""
    m = re.match(r"^(.+?)\s*<.+>$", sender)
    if m:
        return m.group(1).strip().strip('"')
    return sender.strip()
