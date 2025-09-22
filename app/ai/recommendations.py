from typing import List
# from sklearn.feature_extraction.text import TfidfVectorizer  # Temporarily disabled for deployment
# from sklearn.metrics.pairwise import cosine_similarity  # Temporarily disabled for deployment
# import numpy as np  # Temporarily disabled for deployment

from app.db.models import User, Event

# AI recommendations temporarily disabled for deployment
def recommend_events_for_user(user: User, all_events: List[Event]) -> List[Event]:
    """
    Simple fallback recommendation - returns recent events
    (AI-based recommendations temporarily disabled for deployment)
    """
    # Simple fallback: return recent events that user hasn't registered for
    user_event_ids = {event.id for event in user.events_attending}
    candidate_events = [event for event in all_events if event.id not in user_event_ids]
    
    # Return most recent events
    return sorted(candidate_events, key=lambda x: x.date, reverse=True)[:5]