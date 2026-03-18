"""Ghost-Writer Backend — NLP Analyzer Service.

Performs sentiment analysis, vocabulary analysis, slang detection, and activity pattern analysis.
"""
import json
import os
import logging
from collections import Counter
from datetime import datetime
from statistics import mean

import nltk
from nltk.corpus import stopwords
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from models.schemas import (
    ParsedMessage, AnalyzeResponse, WordFrequency,
    SocialContact, SocialMapResponse, SentimentDay, SentimentHistoryResponse
)

logger = logging.getLogger(__name__)

# Load slang list
_slang_path = os.path.join(os.path.dirname(__file__), "..", "data", "slang_list.json")
try:
    with open(_slang_path, "r", encoding="utf-8") as f:
        SLANG_LIST = set(json.load(f))
except Exception:
    logger.warning("Could not load slang_list.json, using empty set")
    SLANG_LIST = set()


class NLPAnalyzer:
    """Performs linguistic analysis on parsed messages."""

    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()
        try:
            self.stop_words = set(stopwords.words("english"))
        except Exception:
            nltk.download("stopwords", quiet=True)
            self.stop_words = set(stopwords.words("english"))

    def analyze(self, messages: list[ParsedMessage]) -> AnalyzeResponse:
        """Run full NLP analysis on a list of messages."""

        # ─── Sentiment Analysis ──────────────────────────
        sentiments: list[float] = []
        sentiment_by_day: dict[str, list[float]] = {}
        sentiment_by_hour: dict[int, list[float]] = {}

        for msg in messages:
            score = self.vader.polarity_scores(msg.text)["compound"]
            sentiments.append(score)

            # Group by day
            try:
                dt = datetime.fromisoformat(msg.timestamp.replace("Z", "+00:00"))
                day_key = dt.strftime("%Y-%m-%d")
                hour_key = dt.hour
            except Exception:
                day_key = "unknown"
                hour_key = 0

            sentiment_by_day.setdefault(day_key, []).append(score)
            sentiment_by_hour.setdefault(hour_key, []).append(score)

        avg_sentiment = round(mean(sentiments), 4) if sentiments else 0.0
        sent_day_avg = {k: round(mean(v), 4) for k, v in sentiment_by_day.items()}
        sent_hour_avg = {k: round(mean(v), 4) for k, v in sentiment_by_hour.items()}

        # ─── Vocabulary Analysis ─────────────────────────
        all_text = " ".join(msg.text for msg in messages)
        try:
            tokens = nltk.word_tokenize(all_text.lower())
        except Exception:
            nltk.download("punkt", quiet=True)
            nltk.download("punkt_tab", quiet=True)
            tokens = nltk.word_tokenize(all_text.lower())

        clean_tokens = [
            t for t in tokens
            if t.isalpha() and t not in self.stop_words and len(t) >= 2
        ]

        total_clean = len(clean_tokens)
        unique_clean = len(set(clean_tokens))
        vocabulary_richness = round(unique_clean / total_clean, 4) if total_clean > 0 else 0.0

        avg_message_length = round(mean(msg.char_count for msg in messages), 2) if messages else 0.0
        avg_word_count = round(mean(msg.word_count for msg in messages), 2) if messages else 0.0

        # ─── Top Words ───────────────────────────────────
        word_counter = Counter(clean_tokens)
        top_words = [
            WordFrequency(
                word=word,
                count=count,
                frequency=round(count / total_clean, 6) if total_clean > 0 else 0.0,
            )
            for word, count in word_counter.most_common(20)
        ]

        # ─── Slang Detection ─────────────────────────────
        slang_tokens = [t for t in clean_tokens if t in SLANG_LIST]
        slang_frequency = round(len(slang_tokens) / total_clean, 4) if total_clean > 0 else 0.0
        slang_counter = Counter(slang_tokens)
        top_slang = [
            WordFrequency(
                word=word,
                count=count,
                frequency=round(count / total_clean, 6) if total_clean > 0 else 0.0,
            )
            for word, count in slang_counter.most_common(10)
        ]

        # ─── Platform Stats ──────────────────────────────
        platform_stats: dict[str, int] = {}
        for msg in messages:
            platform_stats[msg.platform] = platform_stats.get(msg.platform, 0) + 1

        # ─── Activity Patterns ───────────────────────────
        hour_counts: dict[int, int] = {}
        day_counts: dict[str, int] = {}
        for msg in messages:
            try:
                dt = datetime.fromisoformat(msg.timestamp.replace("Z", "+00:00"))
                h = dt.hour
                d = dt.strftime("%A")
            except Exception:
                h = 0
                d = "Monday"
            hour_counts[h] = hour_counts.get(h, 0) + 1
            day_counts[d] = day_counts.get(d, 0) + 1

        most_active_hour = max(hour_counts, key=hour_counts.get, default=0)  # type: ignore
        most_active_day = max(day_counts, key=day_counts.get, default="Monday")  # type: ignore

        return AnalyzeResponse(
            total_messages=len(messages),
            avg_sentiment=avg_sentiment,
            sentiment_by_day=sent_day_avg,
            sentiment_by_hour=sent_hour_avg,
            vocabulary_richness=vocabulary_richness,
            avg_message_length=avg_message_length,
            avg_word_count=avg_word_count,
            slang_frequency=slang_frequency,
            top_words=top_words,
            top_slang=top_slang,
            platform_stats=platform_stats,
            most_active_hour=most_active_hour,
            most_active_day=most_active_day,
        )

    def analyze_social(self, messages: list[ParsedMessage]) -> SocialMapResponse:
        """Analyze message distribution and style per contact."""
        contacts_data: dict[str, list[ParsedMessage]] = {}
        for msg in messages:
            contacts_data.setdefault(msg.sender, []).append(msg)

        contacts: list[SocialContact] = []
        for name, msgs in contacts_data.items():
            if len(msgs) < 2:
                continue

            sentiments = [self.vader.polarity_scores(m.text)["compound"] for m in msgs]
            avg_sent = round(mean(sentiments), 4) if sentiments else 0.0

            text = " ".join(m.text for m in msgs)
            tokens = text.lower().split()
            clean = [t for t in tokens if t.isalpha() and t not in self.stop_words and len(t) >= 2]
            top_words = [word for word, count in Counter(clean).most_common(5)]

            avg_len = mean(m.char_count for m in msgs)
            if avg_sent > 0.4:
                style = "highly positive & energetic" if avg_len > 50 else "brief & cheerful"
            elif avg_sent < -0.2:
                style = "serious or transactional"
            else:
                style = "casual & balanced"

            contacts.append(SocialContact(
                name=name,
                message_count=len(msgs),
                avg_sentiment=avg_sent,
                top_words=top_words,
                style_description=style
            ))

        contacts.sort(key=lambda x: x.message_count, reverse=True)
        return SocialMapResponse(contacts=contacts[:15])

    def analyze_sentiment(self, messages: list[ParsedMessage]) -> SentimentHistoryResponse:
        """Analyze daily sentiment trends and pick mood tags."""
        daily_msgs: dict[str, list[ParsedMessage]] = {}
        for msg in messages:
            try:
                day = datetime.fromisoformat(msg.timestamp.replace("Z", "+00:00")).strftime("%Y-%m-%d")
            except Exception:
                day = "unknown"
            daily_msgs.setdefault(day, []).append(msg)

        days: list[SentimentDay] = []
        all_scores: list[float] = []

        for date, msgs in daily_msgs.items():
            if date == "unknown": continue
            
            sentiments = [self.vader.polarity_scores(m.text)["compound"] for m in msgs]
            avg_score = mean(sentiments) if sentiments else 0.0
            all_scores.append(avg_score)

            if avg_score > 0.6: tag = "Euphoric"
            elif avg_score > 0.2: tag = "Chill"
            elif avg_score >= -0.1: tag = "Neutral"
            elif avg_score > -0.5: tag = "Annoyed"
            else: tag = "Chaotic"

            excerpts = [m.text[:100] for m in msgs[:3]]

            days.append(SentimentDay(
                date=date,
                score=round(avg_score, 4),
                mood_tag=tag,
                message_count=len(msgs),
                excerpts=excerpts
            ))

        days.sort(key=lambda x: x.date, reverse=True)
        avg_total = round(mean(all_scores), 1) if all_scores else 0.0
        
        return SentimentHistoryResponse(days=days, avg_score=avg_total)
