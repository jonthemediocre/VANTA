"""
Agent: Reflector
Type: introspective
"""
import os
import json
import datetime
import re # For basic keyword extraction
from collections import Counter
from vanta_nextgen import CrossModalMemory # Assuming CrossModalMemory is accessible
from pathlib import Path
import uuid
import logging
import constants # <-- Import constants
from utils import create_task_data # <-- Import the helper function

# ... logger setup ...

class ReflectorAgent:
    """Agent that reflects on memory to identify patterns and suggest self-mutations."""
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.memory_path = self.config.get('memory_path', 'memory_store')
        self.profile_path = self.config.get('profile_path', 'agents/reflector_profile.json')
        # Load thresholds from config with defaults
        self.error_rate_threshold = self.config.get('error_rate_threshold', 0.1)
        self.low_interaction_threshold = self.config.get('low_interaction_threshold', 3)
        
        self.memory = CrossModalMemory(self.memory_path)
        self.profile = self._load_profile()
        print(f"ReflectorAgent initialized. Memory: {self.memory_path}, Profile: {self.profile_path}")
        print(f"  Config: Error Threshold={self.error_rate_threshold}, Low Interaction Threshold={self.low_interaction_threshold}")

    def _load_profile(self):
        if os.path.exists(self.profile_path):
            try:
                with open(self.profile_path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Invalid JSON in profile file {self.profile_path}")
        return {"last_reflection": None, "patterns_identified": []}

    def _save_profile(self):
        try:
            with open(self.profile_path, 'w') as f:
                json.dump(self.profile, f, indent=2)
        except Exception as e:
            print(f"Error saving profile {self.profile_path}: {e}")

    def handle(self, context):
        """Main entrypoint, triggered by orchestrator. Can delegate tasks back."""
        logger.info(f"ReflectorAgent handling task with context intent: {context.get('intent')}")
        orchestrator = context.get('orchestrator') 

        # Perform reflection
        reflection_result = self.reflect()

        if reflection_result.get('suggestions') and orchestrator:
            first_suggestion = reflection_result['suggestions'][0]
            if first_suggestion.get('action') == constants.REVIEW_PROMPT_TEMPLATE:
                delegated_task_payload = {
                    "suggestion": first_suggestion
                }
                delegated_task_context = {
                    "source_task_id": context.get('task_id') # Pass original task ID
                }
                
                # --- Use the helper function --- 
                delegated_task = create_task_data(
                    intent=constants.APPLY_MUTATION_SUGGESTION, 
                    payload=delegated_task_payload,
                    context=delegated_task_context,
                    source_agent="ReflectorAgent"
                )
                # ---------------------------------
                
                orchestrator.add_task(delegated_task)
                logger.info(f"  ReflectorAgent delegated task: {delegated_task.get('intent')}")

        return reflection_result

    def reflect(self):
        """Perform the memory reflection and self-mutation logic."""
        print("ReflectorAgent starting reflection...")
        
        # 1. Query memory for relevant entries
        reflection_days = self.config.get('reflection_depth_days', 7)
        since_timestamp = (datetime.datetime.utcnow() - datetime.timedelta(days=reflection_days)).isoformat() + 'Z'
        
        # --- Ideal CrossModalMemory Query --- 
        # Ideally, search would support structured filters like:
        # relevant_entries = self.memory.search(
        #     filters=[
        #         {"field": "timestamp", "op": ">=", "value": since_timestamp},
        #         {"field": "type", "op": "in", "value": ["outcome", "agent_action", "user_feedback"]}
        #     ]
        # )
        # --- Current Placeholder --- 
        all_recent_entries = self.memory.search(q='', since=since_timestamp) # Fetches broadly
        
        # Manual filtering (less efficient)
        entries_to_analyze = [ 
            e for e in all_recent_entries 
            if e.get('timestamp', '0') >= since_timestamp and 
               e.get('type') in ['outcome', 'text', 'agent_action'] # Example types
        ]
        print(f"  Retrieved {len(all_recent_entries)} total entries since {since_timestamp}.")
        if not entries_to_analyze:
             print("  No relevant entries found for reflection.")
             return {"status": "no_entries", "suggestions": []}
        print(f"  Analyzing {len(entries_to_analyze)} filtered entries.")

        # 2. Analyze entries for patterns
        patterns = self._analyze_patterns(entries_to_analyze)
        print(f"  Identified patterns: {patterns}")

        # 3. Generate self-mutation suggestions
        mutation_suggestions = self._generate_mutations(patterns)
        print(f"  Generated suggestions: {mutation_suggestions}")
        
        # 3.5 Attempt to apply feasible mutations
        self._apply_mutations(mutation_suggestions)

        # 4. Update profile
        self.profile['last_reflection'] = datetime.datetime.utcnow().isoformat() + 'Z'
        self.profile['patterns_identified'].extend(patterns) # Simple append for now
        self._save_profile()
        print("ReflectorAgent reflection complete. Profile updated.")

        # Return suggestions or status
        return {"status": "reflection_complete", "suggestions": mutation_suggestions}

    # --- MoE: Pattern Analysis Experts ---
    def _analyze_interactions(self, entries):
        """Expert for analyzing agent interaction counts."""
        agent_interactions = Counter()
        for entry in entries:
            agent = entry.get('agent')
            if agent:
                agent_interactions[agent] += 1
        return [{"type": "interaction_count", "agent": agent, "count": count} 
                for agent, count in agent_interactions.items()]

    def _analyze_outcomes(self, entries):
        """Expert for analyzing success/error rates from outcome entries."""
        agent_outcomes = Counter()
        agent_successes = Counter()
        agent_errors = Counter()
        patterns = []
        for entry in entries:
            agent = entry.get('agent')
            entry_type = entry.get('type')
            if entry_type == 'outcome' and agent:
                agent_outcomes[agent] += 1
                if entry.get('result', {}).get('success') is True:
                    agent_successes[agent] += 1
                elif entry.get('result', {}).get('error'):
                    error_type = entry['result']['error']
                    agent_errors.setdefault(agent, Counter())[error_type] += 1
        
        for agent, total_outcomes in agent_outcomes.items():
            success_count = agent_successes.get(agent, 0)
            success_rate = success_count / total_outcomes if total_outcomes else 0
            patterns.append({"type": "success_rate", "agent": agent, "rate": round(success_rate, 3), 
                           "successes": success_count, "total_outcomes": total_outcomes})
            if agent in agent_errors:
                for error_type, count in agent_errors[agent].items():
                    error_rate = count / total_outcomes if total_outcomes else 0
                    patterns.append({"type": "error_rate", "agent": agent, "error_type": error_type, 
                                   "count": count, "rate": round(error_rate, 3)})
        return patterns

    def _analyze_topics(self, entries):
        """Expert for basic topic/keyword analysis from text entries."""
        topic_keywords = Counter()
        common_keywords = self.config.get('topic_keywords', 
            ['code', 'test', 'refactor', 'document', 'error', 'config', 'deploy', 'memory'])
        for entry in entries:
            if entry.get('type') == 'text':
                text_data = entry.get('data', '')
                words = re.findall(r'\b\w{4,}\b', text_data.lower())
                for word in words:
                    if word in common_keywords:
                        topic_keywords[word] += 1
        return [{"type": "topic_keyword", "keyword": keyword, "count": count} 
                for keyword, count in topic_keywords.most_common(5)]

    def _analyze_sequences(self, entries):
        """Expert for analyzing basic event sequences."""
        sequences = Counter()
        entries.sort(key=lambda x: x.get('timestamp', ''))
        last_entry = None
        patterns = []
        for entry in entries:
            agent = entry.get('agent')
            entry_type = entry.get('type')
            if entry_type == 'outcome' and agent and entry.get('result', {}).get('error'):
                 error_type = entry['result']['error']
                 if last_entry and last_entry.get('agent') == agent and last_entry.get('type') != 'outcome':
                    seq_key = f"{last_entry.get('type', 'unknown_action')}_then_{error_type}"
                    sequences[(agent, seq_key)] += 1
            last_entry = entry
            
        for (agent, seq_key), count in sequences.most_common(5):
            if count > 2:
                patterns.append({"type": "sequence", "agent": agent, "sequence": seq_key, "count": count})
        return patterns
    # --- End MoE Experts ---

    def _analyze_patterns(self, entries):
        """Orchestrate calls to MoE pattern analysis experts and aggregate results."""
        print("    Analyzing patterns using Mixture of Experts...")
        all_patterns = []
        all_patterns.extend(self._analyze_interactions(entries))
        all_patterns.extend(self._analyze_outcomes(entries))
        all_patterns.extend(self._analyze_topics(entries))
        all_patterns.extend(self._analyze_sequences(entries))
        
        # TODO: Add weighting or fusion logic if experts overlap or conflict
        print(f"    MoE Analyzed patterns: {all_patterns}")
        return all_patterns

    def _generate_mutations(self, patterns):
        """Generate, deduplicate, prioritize, and select best mutation suggestions via Best-of-N."""
        candidate_suggestions = [] # Store all candidates before ranking
        low_success_agents = set()
        suggested_actions = set()
        max_suggestions = self.config.get('max_reflection_suggestions', 5)

        # --- Generate Candidate Suggestions (Allowing multiple per pattern) ---
        for pattern in patterns:
            agent_name = pattern.get('agent')
            current_candidates = [] # Candidates for this specific pattern
            
            # Low success rate -> Suggest review logic
            if pattern.get('type') == 'success_rate' and pattern.get('rate', 1.0) < 0.5:
                low_success_agents.add(agent_name)
                current_candidates.append({
                    "action": "review_logic", "target_agent": agent_name,
                    "reason": f"Low success rate ({pattern['rate']:.1%}).", "priority": 3, "confidence": 0.8
                })

            # High error rate -> Multiple potential suggestions
            elif pattern.get('type') == 'error_rate' and pattern.get('rate', 0) > self.error_rate_threshold:
                error_type = pattern['error_type']
                reason = f"High error rate ({pattern['rate']:.1%}) for '{error_type}' (Count: {pattern['count']})."
                priority = 2

                if error_type == 'timeout':
                    # Candidate 1: Adjust config
                    current_candidates.append({
                        "action": "adjust_config", "target_agent": agent_name,
                        "parameter": "timeout_increase_factor", "suggested_value": 1.1,
                        "reason": reason + " Increase timeout?", "priority": priority, "confidence": 0.7
                    })
                    # Candidate 2: Review logic (maybe timeout is symptom)
                    current_candidates.append({
                        "action": "review_logic", "target_agent": agent_name, "error_type": error_type,
                        "reason": reason + " Underlying issue?", "priority": priority -1 , "confidence": 0.5
                    })
                elif pattern['count'] > 10:
                     # Candidate 1: Propose rule
                    current_candidates.append({
                        "action": "propose_mdc_rule", "target_agent": agent_name, "error_type": error_type,
                        "reason": reason + " Create MDC rule?", "priority": priority, "confidence": 0.6
                    })
                     # Candidate 2: Review logic
                    current_candidates.append({
                        "action": "review_logic", "target_agent": agent_name, "error_type": error_type,
                        "reason": reason + " Fix root cause?", "priority": priority + 1, "confidence": 0.8 # Higher priority
                    })
                else:
                     current_candidates.append({
                        "action": "review_logic", "target_agent": agent_name, "error_type": error_type,
                        "reason": reason + " Review error handling.", "priority": priority, "confidence": 0.7
                     })

            # Low interaction
            elif pattern.get('type') == 'interaction_count' and pattern.get('count', 0) < self.low_interaction_threshold:
                 current_candidates.append({
                    "action": "review_triggers", "target_agent": agent_name,
                    "reason": f"Low interaction ({pattern['count']}) < threshold ({self.low_interaction_threshold}). Check triggers/intents?",
                    "priority": 1, "confidence": 0.6
                 })
            
            # Topic mismatch / low success
            elif pattern.get('type') == 'topic_keyword' and pattern.get('count', 0) > 10:
                topic = pattern['keyword']
                if low_success_agents:
                    current_candidates.append({
                        "action": "review_prompt_template", "topic": topic,
                        "reason": f"Keyword '{topic}' frequent, but low success agents detected. Review prompts?",
                        "priority": 1, "confidence": 0.5
                    })
                    
            # Frequent sequences
            elif pattern.get('type') == 'sequence' and pattern.get('count', 0) > self.low_interaction_threshold:
                current_candidates.append({
                    "action": "review_sequence_logic", "target_agent": agent_name, "sequence": pattern['sequence'],
                    "reason": f"Sequence '{pattern['sequence']}' occurred {pattern['count']} times. Review logic?",
                    "priority": 1, "confidence": 0.6
                })

            # Add candidates if they haven't been suggested already (using a simple key)
            for cand in current_candidates:
                # Use a more specific key for deduplication if needed
                dedup_key = (cand['action'], cand.get('target_agent'), cand.get('topic'), cand.get('parameter'))
                if dedup_key not in suggested_actions:
                    candidate_suggestions.append(cand)
                    suggested_actions.add(dedup_key)
        
        # --- Best-of-N Selection --- 
        # Simple ranking: higher confidence first, then higher priority
        candidate_suggestions.sort(key=lambda x: (x.get('confidence', 0), x.get('priority', 0)), reverse=True)
        
        final_suggestions = candidate_suggestions[:max_suggestions]

        print(f"    Generated {len(final_suggestions)} Best-of-N mutation suggestions (from {len(candidate_suggestions)} candidates).")
        return final_suggestions

    def _apply_mutations(self, suggestions):
        """Attempt to apply feasible mutations (config changes) or trigger CoE for complex ones (rule proposals)."""
        applied_count = 0
        triggered_coe_count = 0
        for suggestion in suggestions:
            action = suggestion.get('action')

            # Apply Config Adjustments (Directly)
            if action == 'adjust_config':
                target_agent = suggestion.get('target_agent')
                parameter = suggestion.get('parameter')
                new_value = suggestion.get('suggested_value')
                reason = suggestion.get('reason', 'No reason provided')

                if not all([target_agent, parameter, new_value]):
                    print(f"Warning: Skipping incomplete adjust_config suggestion: {suggestion}")
                    continue

                # Construct path to target agent's config
                # Assumes a standard naming convention (e.g., agents/<agent_name>.json)
                target_config_path = Path('agents') / f"{target_agent}.json"
                if not target_config_path.exists():
                     print(f"Warning: Config file not found for target agent '{target_agent}' at {target_config_path}. Cannot apply mutation.")
                     continue

                try:
                    with open(target_config_path, 'r') as f:
                        config_data = json.load(f)
                    
                    # Apply change (simple key update, assumes flat structure for 'parameter')
                    # More robust logic would handle nested keys or specific parameter types
                    config_data['config'] = config_data.get('config', {})
                    config_data['config'][parameter] = new_value
                    
                    # Write back atomically (using temp file)
                    temp_path = target_config_path.with_suffix('.json.tmp')
                    with open(temp_path, 'w') as f:
                        json.dump(config_data, f, indent=2)
                    os.replace(temp_path, target_config_path)
                    
                    print(f"Applied mutation: Adjusted '{parameter}' for agent '{target_agent}' to {new_value}. Reason: {reason}")
                    applied_count += 1
                    # Mark suggestion as applied?
                    suggestion['_applied'] = True 
                    
                except json.JSONDecodeError:
                    print(f"Error: Could not parse JSON for agent '{target_agent}' at {target_config_path}.")
                except Exception as e:
                    print(f"Error applying mutation to agent '{target_agent}': {e}")
            
            # Propose New MDC Rule (Trigger CoE)
            elif action == 'propose_mdc_rule':
                target_agent = suggestion.get('target_agent')
                error_type = suggestion.get('error_type')
                reason = suggestion.get('reason', 'No reason provided')
                
                if not all([target_agent, error_type]):
                    print(f"Warning: Skipping incomplete propose_mdc_rule suggestion: {suggestion}")
                    continue
                
                print(f"Triggering CoE for MDC rule proposal: Target={target_agent}, Error={error_type}")
                # --- CoE / Chain-of-Thought Simulation --- 
                # 1. Draft initial rule structure (similar to previous implementation)
                rule_draft_content = self._draft_mdc_rule(target_agent, error_type, reason)
                
                # 2. (Simulated) Invoke RuleSmithAgent / ConfigValidator / Human Review
                # In a real system, this would involve message passing or API calls
                coe_context = {
                    "proposal_type": "new_mdc_rule",
                    "draft_content": rule_draft_content,
                    "triggering_agent": "ReflectorAgent",
                    "target_agent": target_agent,
                    "error_type": error_type,
                    "reason": reason
                }
                # Example: send to orchestrator to route to CoE
                # self.orchestrator.trigger_coe("mdc_rule_review", coe_context)
                print(f"  -> CoE Context: {coe_context}")
                
                # 3. Assume CoE approves and provides final path/content (Placeholder)
                coe_approved = True # Simulate approval for now
                if coe_approved:
                    # Simulate CoE providing final details
                    final_rule_filename = f"1101-coe_approved_{target_agent}_{error_type}.mdc" 
                    final_rule_path = Path('.cursor/rules') / final_rule_filename
                    final_rule_content = rule_draft_content # Use draft for now
                    
                    try:
                        if not final_rule_path.exists():
                            final_rule_path.parent.mkdir(parents=True, exist_ok=True)
                            with open(final_rule_path, 'w') as f:
                                f.write(final_rule_content)
                            print(f"CoE Approved: Created new MDC rule: {final_rule_path}")
                            triggered_coe_count += 1
                            suggestion['_applied'] = True # Mark as applied (via CoE)
                        else:
                            print(f"Note: CoE-approved rule {final_rule_path} already exists. Skipping.")
                    except Exception as e:
                        print(f"Error creating CoE-approved MDC rule {final_rule_path}: {e}")
                else:
                    print(f"CoE Rejected rule proposal for {target_agent}/{error_type}.")
                # --- End CoE Simulation ---

            # Handle other actions (review_logic, etc.) - trigger CoE or log for review
            elif action in ["review_logic", "review_triggers", "review_prompt_template", "review_sequence_logic"]:
                 print(f"Triggering CoE/Review for action '{action}': {suggestion}")
                 # Similar CoE trigger or logging for manual review
                 # self.orchestrator.trigger_review_task(suggestion)
                 triggered_coe_count += 1 # Count as handled by CoE/Review process
                 suggestion['_handled_by_review'] = True
            
        print(f"Mutation application complete. Applied {applied_count} config changes, triggered {triggered_coe_count} CoE/Review processes.")
        return {"applied_configs": applied_count, "triggered_reviews": triggered_coe_count}

    def _draft_mdc_rule(self, target_agent, error_type, reason):
        """Helper to generate the initial draft content for a proposed MDC rule."""
        # Basic template (can be made more sophisticated)
        return f"""---
description: "[Auto-Proposed] Prevent {error_type} errors in {target_agent}"
globs:
  - "agents/{target_agent}.py" # Adjust glob as needed
type: always
---
# RULE TYPE: Always
# FILE PATTERNS: agents/{target_agent}.py

## Prevent {error_type} Errors for {target_agent}

# Triggered Reason: {reason}

# TODO (CoE Review): Define specific patterns, examples, and prevention guidelines.

""" 