from typing import List
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
# import numpy as np  # Temporarily disabled for deployment

from app.db.models import User, Event

def recommend_events_for_user(user: User, all_events: List[Event]) -> List[Event]:
    """
    Recommends events to a user based on the content of clubs they've joined
    and events they've registered for.
    """
    # 1. Gather text descriptions from the user's current interests (clubs and events)
    user_interest_docs = []
    for club in user.clubs:
        user_interest_docs.append(club.description)
    for event in user.events_attending:
        user_interest_docs.append(f"{event.name} {event.description}")
    
    # If the user has no activity, we can't make personalized recommendations
    if not user_interest_docs:
        # Fallback: maybe return the most recent events or popular ones
        return sorted(all_events, key=lambda x: x.date, reverse=True)[:5]

    # 2. Identify candidate events (those the user hasn't registered for yet)
    user_event_ids = {event.id for event in user.events_attending}
    candidate_events = [event for event in all_events if event.id not in user_event_ids]
    
    if not candidate_events:
        return [] # No new events to recommend

    candidate_event_docs = [f"{event.name} {event.description}" for event in candidate_events]

    # 3. Vectorize all text documents using TF-IDF
    # We combine user docs and candidate docs to create a shared vocabulary
    all_docs = user_interest_docs + candidate_event_docs
    tfidf_vectorizer = TfidfVectorizer(stop_words='english', max_features=500)
    tfidf_matrix = tfidf_vectorizer.fit_transform(all_docs)

    # 4. Create a "user profile" vector by averaging their interest vectors
    num_user_docs = len(user_interest_docs)
    user_profile_vector = np.mean(tfidf_matrix[:num_user_docs], axis=0)

    # 5. Calculate the cosine similarity between the user profile and all candidate events
    candidate_vectors = tfidf_matrix[num_user_docs:]
    similarities = cosine_similarity(user_profile_vector, candidate_vectors)

    # 6. Sort events by similarity and return the top N
    num_recommendations = 5
    # Get the indices of the most similar events
    recommended_indices = similarities[0].argsort()[-num_recommendations:][::-1]
    
    recommendations = [candidate_events[i] for i in recommended_indices if similarities[0][i] > 0]

    return recommendations