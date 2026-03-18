# routers/insights.py

from fastapi import APIRouter
from models.schemas import ParsedMessage, AnalyzeRequest
from pydantic import BaseModel
from collections import defaultdict
import re

router = APIRouter(prefix="/insights", tags=["insights"])

class ContactStat(BaseModel):
    name: str
    initials: str
    message_count: int
    avg_sentiment: float
    sentiment_label: str
    top_words: list[str]
    communication_style: str
    node_size: int  # 28-48 based on frequency

class RelationshipMapResponse(BaseModel):
    contacts: list[ContactStat]
    total_contacts: int
    most_active_contact: str
    most_positive_contact: str

@router.post("/relationship-map")
async def generate_relationship_map(request: AnalyzeRequest) -> RelationshipMapResponse:
    """
    Analyze uploaded messages and return relationship network data.
    Groups messages by sender, calculates per-contact sentiment and stats.
    """
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    import nltk
    from nltk.corpus import stopwords

    analyzer = SentimentIntensityAnalyzer()
    stop_words = set(stopwords.words('english'))

    # Group messages by sender
    by_sender: dict[str, list[ParsedMessage]] = defaultdict(list)
    for msg in request.messages:
        by_sender[msg.sender].append(msg)

    # Sort by message count descending, take top 8
    sorted_senders = sorted(by_sender.items(), key=lambda x: len(x[1]), reverse=True)[:8]
    max_count = sorted_senders[0][1].__len__() if sorted_senders else 1

    contacts = []
    for sender, messages in sorted_senders:
        # Sentiment
        scores = [analyzer.polarity_scores(m.text)["compound"] for m in messages]
        avg_score = round(sum(scores) / len(scores), 3) if scores else 0.0

        sentiment_label = (
            "very positive" if avg_score > 0.5 else
            "positive" if avg_score > 0.2 else
            "neutral-positive" if avg_score > 0.0 else
            "neutral" if avg_score > -0.2 else
            "negative"
        )

        # Top words unique to this contact
        all_words = " ".join(m.text for m in messages).lower().split()
        clean_words = [
            w for w in all_words
            if w.isalpha() and w not in stop_words and len(w) > 2
        ]
        from collections import Counter
        word_freq = Counter(clean_words)
        top_words = [w for w, _ in word_freq.most_common(5)]

        # Communication style heuristic
        avg_length = sum(len(m.text.split()) for m in messages) / len(messages)
        if avg_score > 0.4 and avg_length > 15:
            style = "warm and frequent"
        elif avg_score > 0.1 and avg_length < 10:
            style = "casual and consistent"
        elif avg_score < -0.1:
            style = "tense and infrequent"
        elif avg_length < 8:
            style = "brief and transactional"
        else:
            style = "warm and sporadic"

        # Node size: 28 to 48 based on relative message count
        node_size = round(28 + (len(messages) / max_count) * 20)

        # Initials
        parts = sender.strip().split()
        initials = "".join(p[0].upper() for p in parts[:2]) if parts else "??"

        contacts.append(ContactStat(
            name=sender,
            initials=initials,
            message_count=len(messages),
            avg_sentiment=avg_score,
            sentiment_label=sentiment_label,
            top_words=top_words,
            communication_style=style,
            node_size=node_size
        ))

    most_active = contacts[0].name if contacts else ""
    most_positive = max(contacts, key=lambda c: c.avg_sentiment).name if contacts else ""

    return RelationshipMapResponse(
        contacts=contacts,
        total_contacts=len(contacts),
        most_active_contact=most_active,
        most_positive_contact=most_positive
    )