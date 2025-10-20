from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, SessionStarted, ActionExecuted
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ActionCheckGuardrails(Action):
    """
    Pre-processes user messages to check for guardrail violations
    before the main NLU pipeline processes them.
    """
    
    def name(self) -> Text:
        return "action_check_guardrails"
    
    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        
        user_message = tracker.latest_message.get('text', '')
        intent = tracker.latest_message.get('intent', {}).get('name', '')
        
        logger.info(f"Guardrail check - Intent: {intent}, Message: {user_message}")
        
        # Additional custom guardrail logic can be added here
        # For example, regex patterns, custom entity extraction, etc.
        
        return []


class ActionLogViolation(Action):
    """
    Logs violations for monitoring, auditing, and analytics purposes.
    """
    
    def name(self) -> Text:
        return "action_log_violation"
    
    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        
        # Get violation details
        intent = tracker.latest_message.get('intent', {}).get('name', 'unknown')
        user_message = tracker.latest_message.get('text', '')
        user_id = tracker.sender_id
        timestamp = datetime.now().isoformat()
        
        # Log the violation
        violation_log = {
            'timestamp': timestamp,
            'user_id': user_id,
            'intent': intent,
            'message': user_message,
            'violation_type': self._categorize_violation(intent)
        }
        
        logger.warning(f"VIOLATION LOGGED: {violation_log}")
        
        # In production, you would:
        # 1. Send to a monitoring service (e.g., Elasticsearch, Splunk)
        # 2. Store in database
        # 3. Trigger alerts for severe violations
        # 4. Update user reputation score
        
        # Store last violation type in slot
        return [SlotSet("last_violation_type", intent)]
    
    def _categorize_violation(self, intent: Text) -> Text:
        """Categorize violation severity"""
        severe_violations = [
            'prompt_injection',
            'out_of_scope_technical',
            'share_sensitive_data'
        ]
        moderate_violations = [
            'offensive_language',
            'harassment',
            'sara_topic'
        ]
        
        if intent in severe_violations:
            return 'SEVERE'
        elif intent in moderate_violations:
            return 'MODERATE'
        else:
            return 'MINOR'


class ActionHandleViolation(Action):
    """
    Handles violation counting and determines if escalation is needed.
    """
    
    def name(self) -> Text:
        return "action_handle_violation"
    
    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        
        # Get current violation count
        current_count = tracker.get_slot("violation_count") or 0
        new_count = current_count + 1
        
        intent = tracker.latest_message.get('intent', {}).get('name', '')
        
        logger.info(f"Violation count increased: {current_count} -> {new_count} for intent: {intent}")
        
        events = [SlotSet("violation_count", new_count)]
        
        # Check if we need to escalate
        if new_count == 2:
            # Second violation - this will trigger utter_final_warning in stories
            logger.warning(f"User {tracker.sender_id} reached 2 violations - final warning")
        elif new_count >= 3:
            # Third violation - this will trigger session termination in stories
            logger.error(f"User {tracker.sender_id} reached 3 violations - terminating session")
        
        return events


class ActionEscalateViolation(Action):
    """
    Handles severe violations that require immediate escalation.
    Used for prompt injection, technical threats, etc.
    """
    
    def name(self) -> Text:
        return "action_escalate_violation"
    
    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        
        intent = tracker.latest_message.get('intent', {}).get('name', '')
        user_message = tracker.latest_message.get('text', '')
        user_id = tracker.sender_id
        timestamp = datetime.now().isoformat()
        
        # Log severe violation
        severe_violation = {
            'timestamp': timestamp,
            'user_id': user_id,
            'intent': intent,
            'message': user_message,
            'severity': 'CRITICAL'
        }
        
        logger.error(f"SEVERE VIOLATION - ESCALATED: {severe_violation}")
        
        # In production:
        # 1. Immediately notify security team
        # 2. Flag user account for review
        # 3. Block user temporarily if needed
        # 4. Send alert to monitoring dashboard
        # 5. Store in security incident database
        
        # Increase violation count significantly for severe violations
        current_count = tracker.get_slot("violation_count") or 0
        new_count = current_count + 2  # Severe violations count as 2
        
        return [
            SlotSet("violation_count", new_count),
            SlotSet("last_violation_type", intent)
        ]


class ActionResetViolationCount(Action):
    """
    Resets violation count after successful positive interactions.
    This gives users a fresh start after they've corrected their behavior.
    """
    
    def name(self) -> Text:
        return "action_reset_violation_count"
    
    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        
        user_id = tracker.sender_id
        previous_count = tracker.get_slot("violation_count") or 0
        
        if previous_count > 0:
            logger.info(f"Resetting violation count for user {user_id}: {previous_count} -> 0")
        
        return [
            SlotSet("violation_count", 0),
            SlotSet("last_violation_type", None)
        ]


class ActionDefaultFallback(Action):
    """
    Custom fallback action when the bot doesn't understand the user input.
    """
    
    def name(self) -> Text:
        return "action_default_fallback"
    
    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        
        user_message = tracker.latest_message.get('text', '')
        
        logger.info(f"Fallback triggered for message: {user_message}")
        
        # Provide helpful fallback response
        dispatcher.utter_message(
            text="Maaf, saya tidak mengerti maksud Anda. "
                 "Saya dapat membantu Anda dengan informasi tentang produk dan layanan BRI. "
                 "Apakah ada yang ingin ditanyakan tentang tabungan, kredit, atau layanan BRI lainnya?"
        )
        
        return []


class ActionSessionStart(Action):
    """
    Custom action to execute at the start of each session.
    """
    
    def name(self) -> Text:
        return "action_session_start"
    
    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        
        # Initialize or carry over slots based on configuration
        events = [SessionStarted()]
        
        # Get session configuration
        session_config = domain.get("session_config", {})
        carry_over = session_config.get("carry_over_slots_to_new_session", True)
        
        if carry_over:
            # Preserve certain slots across sessions
            preserved_slots = {
                "user_name": tracker.get_slot("user_name"),
                "user_segment": tracker.get_slot("user_segment"),
            }
            
            events.extend([SlotSet(key, value) for key, value in preserved_slots.items() if value is not None])
        else:
            # Reset violation count for new session
            events.append(SlotSet("violation_count", 0))
            events.append(SlotSet("last_violation_type", None))
        
        # Always add action_listen to ensure the conversation can continue
        events.append(ActionExecuted("action_listen"))
        
        logger.info(f"New session started for user: {tracker.sender_id}")
        
        return events


# Additional utility actions can be added here

class ActionGetUserInfo(Action):
    """
    Retrieves user information for personalization.
    This is a placeholder - integrate with your CRM/database.
    """
    
    def name(self) -> Text:
        return "action_get_user_info"
    
    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        
        user_id = tracker.sender_id
        
        # In production, query your database/CRM
        # Example:
        # user_data = database.get_user(user_id)
        
        # Mock data for demonstration
        user_data = {
            "name": "Valued Customer",
            "segment": "retail"
        }
        
        return [
            SlotSet("user_name", user_data.get("name")),
            SlotSet("user_segment", user_data.get("segment"))
        ]


class ActionTrackAnalytics(Action):
    """
    Tracks user interactions for analytics and insights.
    """
    
    def name(self) -> Text:
        return "action_track_analytics"
    
    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        
        # Track conversation metrics
        analytics_data = {
            'user_id': tracker.sender_id,
            'intent': tracker.latest_message.get('intent', {}).get('name'),
            'timestamp': datetime.now().isoformat(),
            'conversation_length': len(tracker.events),
            'violations': tracker.get_slot("violation_count") or 0
        }
        
        logger.info(f"Analytics: {analytics_data}")
        
        # In production, send to analytics platform
        # e.g., Google Analytics, Mixpanel, custom dashboard
        
        return []