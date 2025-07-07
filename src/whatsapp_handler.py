import os
import json
import hmac
import hashlib
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
from src.database import DatabaseManager
from src.ai_assistant import AIAssistant
from src.lead_qualifier import LeadQualifier
from src.utils import validate_phone_number, setup_logger

class WhatsAppHandler:
    """
    Manages WhatsApp Business API integration for the WellnessConnect platform.
    Handles sending messages, receiving webhooks, and processing incoming messages.
    """
    
    def __init__(self):
        """Initialize WhatsApp handler with API credentials and dependencies."""
        self.access_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
        self.phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
        self.webhook_verify_token = os.getenv('WHATSAPP_WEBHOOK_VERIFY_TOKEN')
        self.app_secret = os.getenv('WHATSAPP_APP_SECRET')
        self.api_base_url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}"
        
        # Initialize dependencies
        self.db = DatabaseManager()
        self.ai_assistant = AIAssistant()
        self.lead_qualifier = LeadQualifier()
        self.logger = setup_logger('whatsapp_handler')
        
        # Validate required configuration
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate that all required WhatsApp API configuration is present."""
        required_vars = [
            'WHATSAPP_ACCESS_TOKEN',
            'WHATSAPP_PHONE_NUMBER_ID', 
            'WHATSAPP_WEBHOOK_VERIFY_TOKEN',
            'WHATSAPP_APP_SECRET'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    def send_message(self, to_number: str, message: str, message_type: str = "text") -> Dict[str, Any]:
        """
        Send a message to a WhatsApp contact.
        
        Args:
            to_number: Recipient's phone number in international format
            message: Message content to send
            message_type: Type of message (text, template, etc.)
            
        Returns:
            Dict containing API response or error information
        """
        try:
            # Validate phone number format
            if not validate_phone_number(to_number):
                raise ValueError(f"Invalid phone number format: {to_number}")
            
            # Prepare message payload
            payload = {
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": message_type,
                message_type: {
                    "body": message
                }
            }
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            # Send message via WhatsApp API
            response = requests.post(
                f"{self.api_base_url}/messages",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Log successful message
            self.logger.info(f"Message sent successfully to {to_number}")
            
            # Save message to database
            self.db.save_conversation(
                phone_number=to_number,
                message=message,
                sender='assistant',
                timestamp=datetime.now()
            )
            
            return {
                "success": True,
                "message_id": result.get("messages", [{}])[0].get("id"),
                "response": result
            }
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"WhatsApp API error: {str(e)}")
            return {
                "success": False,
                "error": f"API request failed: {str(e)}"
            }
        except Exception as e:
            self.logger.error(f"Error sending message: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def receive_webhook(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming WhatsApp webhook data.
        
        Args:
            request_data: Webhook payload from WhatsApp
            
        Returns:
            Dict containing processing results
        """
        try:
            # Extract entry data
            entry = request_data.get("entry", [])
            if not entry:
                return {"success": False, "error": "No entry data found"}
            
            # Process each webhook entry
            results = []
            for entry_item in entry:
                changes = entry_item.get("changes", [])
                for change in changes:
                    if change.get("field") == "messages":
                        result = self._process_message_change(change.get("value", {}))
                        results.append(result)
            
            return {
                "success": True,
                "processed_messages": len(results),
                "results": results
            }
            
        except Exception as e:
            self.logger.error(f"Error processing webhook: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _process_message_change(self, value: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process individual message change from webhook.
        
        Args:
            value: Message change data
            
        Returns:
            Dict containing processing result
        """
        try:
            messages = value.get("messages", [])
            contacts = value.get("contacts", [])
            
            # Create contact lookup
            contact_lookup = {contact["wa_id"]: contact for contact in contacts}
            
            results = []
            for message in messages:
                result = self._handle_incoming_message(message, contact_lookup)
                results.append(result)
            
            return {
                "success": True,
                "messages_processed": len(results)
            }
            
        except Exception as e:
            self.logger.error(f"Error processing message change: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _handle_incoming_message(self, message: Dict[str, Any], contact_lookup: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle individual incoming message.
        
        Args:
            message: Message data from webhook
            contact_lookup: Contact information lookup
            
        Returns:
            Dict containing handling result
        """
        try:
            from_number = message.get("from")
            message_id = message.get("id")
            timestamp = datetime.fromtimestamp(int(message.get("timestamp", 0)))
            
            # Extract message text
            message_text = ""
            if message.get("type") == "text":
                message_text = message.get("text", {}).get("body", "")
            
            # Get contact info
            contact = contact_lookup.get(from_number, {})
            contact_name = contact.get("profile", {}).get("name", "Unknown")
            
            self.logger.info(f"Received message from {from_number}: {message_text}")
            
            # Save incoming message to database
            self.db.save_conversation(
                phone_number=from_number,
                message=message_text,
                sender='user',
                timestamp=timestamp,
                message_id=message_id
            )
            
            # Generate AI response
            ai_response = self.ai_assistant.generate_response(
                user_message=message_text,
                phone_number=from_number
            )
            
            # Send AI response back to user
            if ai_response.get("success"):
                response_text = ai_response.get("response", "")
                send_result = self.send_message(from_number, response_text)
                
                # Check if this interaction qualifies the lead
                self._check_lead_qualification(from_number, message_text, response_text)
                
                return {
                    "success": True,
                    "message_id": message_id,
                    "response_sent": send_result.get("success", False)
                }
            else:
                # Send fallback message if AI fails
                fallback_message = "I apologize, but I'm having trouble processing your message right now. Please try again or contact us directly at The Wellness London."
                self.send_message(from_number, fallback_message)
                
                return {
                    "success": False,
                    "error": "AI response generation failed",
                    "fallback_sent": True
                }
                
        except Exception as e:
            self.logger.error(f"Error handling incoming message: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _check_lead_qualification(self, phone_number: str, user_message: str, ai_response: str) -> None:
        """
        Check if the conversation qualifies the user as a lead.
        
        Args:
            phone_number: User's phone number
            user_message: User's latest message
            ai_response: AI's response
        """
        try:
            # Get conversation history
            conversation_history = self.db.get_conversation_history(phone_number)
            
            # Analyze responses for lead qualification
            qualification_result = self.lead_qualifier.analyze_responses(
                phone_number=phone_number,
                conversation_history=conversation_history
            )
            
            if qualification_result.get("qualified"):
                # Update lead status in database
                self.db.update_lead_status(
                    phone_number=phone_number,
                    status="qualified",
                    treatment_type=qualification_result.get("treatment_type"),
                    urgency_score=qualification_result.get("urgency_score")
                )
                
                self.logger.info(f"Lead qualified: {phone_number} - {qualification_result.get('treatment_type')}")
                
        except Exception as e:
            self.logger.error(f"Error checking lead qualification: {str(e)}")
    
    def validate_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """
        Validate webhook verification request from WhatsApp.
        
        Args:
            mode: Verification mode
            token: Verification token
            challenge: Challenge string to echo back
            
        Returns:
            Challenge string if validation successful, None otherwise
        """
        try:
            if mode == "subscribe" and token == self.webhook_verify_token:
                self.logger.info("Webhook verification successful")
                return challenge
            else:
                self.logger.warning("Webhook verification failed")
                return None
                
        except Exception as e:
            self.logger.error(f"Error validating webhook: {str(e)}")
            return None
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify webhook signature for security.
        
        Args:
            payload: Raw webhook payload
            signature: X-Hub-Signature-256 header value
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            if not signature.startswith('sha256='):
                return False
            
            expected_signature = hmac.new(
                self.app_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            received_signature = signature[7:]  # Remove 'sha256=' prefix
            
            return hmac.compare_digest(expected_signature, received_signature)
            
        except Exception as e:
            self.logger.error(f"Error verifying webhook signature: {str(e)}")
            return False
    
    def send_template_message(self, to_number: str, template_name: str, language_code: str = "en", parameters: List[str] = None) -> Dict[str, Any]:
        """
        Send a WhatsApp template message.
        
        Args:
            to_number: Recipient's phone number
            template_name: Name of the approved template
            language_code: Language code for the template
            parameters: Template parameter values
            
        Returns:
            Dict containing API response or error information
        """
        try:
            if not validate_phone_number(to_number):
                raise ValueError(f"Invalid phone number format: {to_number}")
            
            # Prepare template payload
            template_payload = {
                "name": template_name,
                "language": {
                    "code": language_code
                }
            }
            
            # Add parameters if provided
            if parameters:
                template_payload["components"] = [{
                    "type": "body",
                    "parameters": [{"type": "text", "text": param} for param in parameters]
                }]
            
            payload = {
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": "template",
                "template": template_payload
            }
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{self.api_base_url}/messages",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            self.logger.info(f"Template message sent successfully to {to_number}")
            
            return {
                "success": True,
                "message_id": result.get("messages", [{}])[0].get("id"),
                "response": result
            }
            
        except Exception as e:
            self.logger.error(f"Error sending template message: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_message_status(self, message_id: str) -> Dict[str, Any]:
        """
        Get the delivery status of a sent message.
        
        Args:
            message_id: ID of the message to check
            
        Returns:
            Dict containing message status information
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}"
            }
            
            response = requests.get(
                f"https://graph.facebook.com/v18.0/{message_id}",
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": True,
                "status": result
            }
            
        except Exception as e:
            self.logger.error(f"Error getting message status: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }