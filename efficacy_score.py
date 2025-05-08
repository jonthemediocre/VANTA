"""
VANTA Kernel - Efficacy Scorer

This module is responsible for calculating an efficacy score for different
strategies, protocols, or responses used within the VANTA ecosystem.
The score can be influenced by time decay, explicit caregiver feedback,
and contextual factors.

This is a foundational scaffold; the actual scoring logic will evolve with
the Reinforcement Learning (RL) system integration.
"""
import time
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants for decay calculation (example values)
HALFLIFE_SECONDS = 7 * 24 * 60 * 60  # Score halves in 7 days
INITIAL_SCORE = 1.0
MIN_SCORE = 0.01

class EfficacyScorer:
    @staticmethod
    def calculate_score(
        strategy_id: str,
        child_id: str, 
        last_used_timestamp: float = None, 
        initial_score: float = INITIAL_SCORE,
        caregiver_feedback: dict = None, 
        positive_interactions: int = 0,
        negative_interactions: int = 0,
        context: dict = None
    ) -> float:
        """
        Calculates an efficacy score for a given strategy.

        Args:
            strategy_id (str): Unique identifier for the strategy/protocol/response.
            child_id (str): Identifier for the child this score pertains to.
            last_used_timestamp (float, optional): Unix timestamp of when the strategy was last used.
                                                 If None, time decay is not applied from a past point.
            initial_score (float): The base score to start from before decay or feedback.
            caregiver_feedback (dict, optional): Explicit feedback from a caregiver.
                                               Example: {"rating": "positive" | "neutral" | "negative", "weight": 0.8}
            positive_interactions (int): Count of recent positive interactions/outcomes with this strategy.
            negative_interactions (int): Count of recent negative interactions/outcomes with this strategy.
            context (dict, optional): Additional contextual factors that might influence the score.

        Returns:
            float: The calculated efficacy score, typically between 0.0 and 1.0.
        """
        logging.info(f"Calculating efficacy for strategy '{strategy_id}' for child '{child_id}'.")

        current_score = float(initial_score)

        # 1. Apply Time Decay (if last_used_timestamp is provided)
        if last_used_timestamp is not None:
            time_since_last_use = time.time() - last_used_timestamp
            # Exponential decay: score = initial_score * (0.5 ^ (time_elapsed / half_life))
            decay_factor = (0.5) ** (time_since_last_use / HALFLIFE_SECONDS)
            current_score *= decay_factor
            logging.debug(f"  Time decay applied. Time since last use: {time_since_last_use:.2f}s. Decay factor: {decay_factor:.4f}. Score after decay: {current_score:.4f}")

        # 2. Incorporate Implicit Feedback (interaction counts)
        # Simple adjustment; more sophisticated Bayesian updating could be used.
        interaction_modifier = 0.0
        total_interactions = positive_interactions + negative_interactions
        if total_interactions > 0:
            interaction_modifier = (positive_interactions - negative_interactions) / total_interactions * 0.2 # Max +/- 20% impact
            current_score += interaction_modifier
            logging.debug(f"  Interaction feedback applied. Pos: {positive_interactions}, Neg: {negative_interactions}. Modifier: {interaction_modifier:.4f}. Score: {current_score:.4f}")

        # 3. Incorporate Explicit Caregiver Feedback
        if caregiver_feedback and isinstance(caregiver_feedback, dict):
            rating = caregiver_feedback.get("rating")
            weight = float(caregiver_feedback.get("weight", 1.0)) # How much this feedback should influence
            
            feedback_modifier = 0.0
            if rating == "positive":
                feedback_modifier = 0.25 * weight # Boost score
            elif rating == "negative":
                feedback_modifier = -0.35 * weight # Penalize score more heavily
            elif rating == "neutral":
                feedback_modifier = 0.0
            
            current_score += feedback_modifier
            logging.debug(f"  Caregiver feedback '{rating}' (weight {weight}) applied. Modifier: {feedback_modifier:.4f}. Score: {current_score:.4f}")

        # 4. Apply Contextual Adjustments (placeholder)
        if context and isinstance(context, dict):
            # Example: if context suggests high stress, certain strategies might be less effective
            if context.get("child_stress_level") == "high" and strategy_id == "complex_reasoning_prompt":
                current_score *= 0.8 # Reduce score by 20% for this context
                logging.debug(f"  Contextual adjustment for high stress applied. Score: {current_score:.4f}")

        # Ensure score is within bounds [MIN_SCORE, INITIAL_SCORE (as max for this model)]
        current_score = max(MIN_SCORE, min(current_score, INITIAL_SCORE))
        
        logging.info(f"Final efficacy score for strategy '{strategy_id}' for child '{child_id}': {current_score:.4f}")
        return round(current_score, 4)

if __name__ == "__main__":
    print("Testing EfficacyScorer Module...")

    child1 = "child_alex"
    strategy_tbri_connect = "tbri_connect_first_v1"

    # Test Case 1: New strategy, no feedback
    score1 = EfficacyScorer.calculate_score(strategy_tbri_connect, child1)
    print(f"\nTest 1 (New Strategy): Score = {score1}")
    assert score1 == INITIAL_SCORE

    # Test Case 2: Strategy used 3.5 days ago, no other feedback
    three_half_days_ago = time.time() - (3.5 * 24 * 60 * 60)
    score2 = EfficacyScorer.calculate_score(strategy_tbri_connect, child1, last_used_timestamp=three_half_days_ago)
    print(f"Test 2 (3.5 days decay): Score = {score2}") # Should be INITIAL_SCORE / sqrt(2) = ~0.7071
    # Check if close, allowing for float precision
    assert abs(score2 - INITIAL_SCORE * (0.5**(3.5/7.0))) < 0.0001 

    # Test Case 3: Strategy used 7 days ago (should be half score)
    seven_days_ago = time.time() - HALFLIFE_SECONDS
    score3 = EfficacyScorer.calculate_score(strategy_tbri_connect, child1, last_used_timestamp=seven_days_ago)
    print(f"Test 3 (7 days decay): Score = {score3}")
    assert abs(score3 - INITIAL_SCORE * 0.5) < 0.0001

    # Test Case 4: Positive caregiver feedback
    feedback_pos = {"rating": "positive", "weight": 0.5}
    score4 = EfficacyScorer.calculate_score(strategy_tbri_connect, child1, caregiver_feedback=feedback_pos)
    print(f"Test 4 (Positive Feedback, weight 0.5): Score = {score4}")
    # Expected: INITIAL_SCORE + 0.25 * 0.5 = 1.0 + 0.125. Max is INITIAL_SCORE for this simple model.
    # This will be INITIAL_SCORE because current_score is capped at INITIAL_SCORE. 
    # If INITIAL_SCORE = 1.0, 1.0 + 0.125 = 1.125, capped to 1.0
    assert score4 == INITIAL_SCORE 

    # Test Case 5: Negative caregiver feedback
    feedback_neg = {"rating": "negative", "weight": 1.0}
    score5 = EfficacyScorer.calculate_score(strategy_tbri_connect, child1, caregiver_feedback=feedback_neg)
    print(f"Test 5 (Negative Feedback, weight 1.0): Score = {score5}")
    # Expected: INITIAL_SCORE - 0.35 * 1.0 = 1.0 - 0.35 = 0.65
    assert abs(score5 - (INITIAL_SCORE - 0.35)) < 0.0001

    # Test Case 6: Combined decay and negative feedback
    score6 = EfficacyScorer.calculate_score(strategy_tbri_connect, child1, 
                                          last_used_timestamp=seven_days_ago, 
                                          caregiver_feedback=feedback_neg)
    print(f"Test 6 (7 days decay + Negative Feedback): Score = {score6}")
    # Expected: (INITIAL_SCORE * 0.5) - 0.35 = 0.5 - 0.35 = 0.15
    assert abs(score6 - ( (INITIAL_SCORE * 0.5) - 0.35) ) < 0.0001

    # Test Case 7: Positive and negative interactions
    score7 = EfficacyScorer.calculate_score(strategy_tbri_connect, child1,
                                          positive_interactions=10,
                                          negative_interactions=2)
    print(f"Test 7 (Interactions P10, N2): Score = {score7}")
    # Expected: INITIAL_SCORE + ((10-2)/12 * 0.2) = 1.0 + (8/12 * 0.2) = 1.0 + (0.666 * 0.2) = 1.0 + 0.1333. Capped at 1.0.
    assert score7 == INITIAL_SCORE

    # Test Case 8: Contextual adjustment
    context_high_stress = {"child_stress_level": "high"}
    score8 = EfficacyScorer.calculate_score("complex_reasoning_prompt", child1, context=context_high_stress)
    print(f"Test 8 (Contextual adjustment): Score = {score8}")
    # Expected: INITIAL_SCORE * 0.8 = 0.8
    assert abs(score8 - (INITIAL_SCORE * 0.8)) < 0.0001
    
    # Test Case 9: Score hitting min boundary
    very_old_ts = time.time() - (HALFLIFE_SECONDS * 10) # Very old
    strong_neg_feedback = {"rating": "negative", "weight": 2.0} # Stronger than normal weight
    score9 = EfficacyScorer.calculate_score(strategy_tbri_connect, child1, 
                                          last_used_timestamp=very_old_ts,
                                          caregiver_feedback=strong_neg_feedback,
                                          negative_interactions=5)
    print(f"Test 9 (Hitting MIN_SCORE boundary): Score = {score9}")
    assert score9 == MIN_SCORE

    print("\nAll EfficacyScorer tests passed (basic assertions).") 