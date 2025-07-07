import os
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import anthropic
from src.database import DatabaseManager
from src.utils import setup_logger

class AIAssistant:
    """Claude API integration for health conversations and assessments."""
    
    def __init__(self):
        """Initialize AI Assistant with Claude API client."""
        self.client = anthropic.Anthropic(
            api_key=os.getenv('CLAUDE_API_KEY')
        )
        self.db = DatabaseManager()
        self.logger = setup_logger(__name__)
        
        # Health assessment questions structure
        self.assessment_questions = {
            'basic_info': [
                "What's your age range? (18-30, 31-45, 46-60, 60+)",
                "What's your primary health goal? (Weight management, Energy boost, Preventive care, Specific concern)",
                "Have you had any blood tests in the last 6 months? (Yes/No)"
            ],
            'symptoms': [
                "Are you experiencing any of these symptoms? (Fatigue, Sleep issues, Digestive problems, Joint pain, Mood changes, None)",
                "How would you rate your current energy levels? (1-10 scale)",
                "Any current medications or supplements? (Please list or say None)"
            ],
            'lifestyle': [
                "How often do you exercise? (Daily, 3-4 times/week, 1-2 times/week, Rarely)",
                "How would you describe your diet? (Very healthy, Mostly healthy, Average, Needs improvement)",
                "What's your stress level? (Low, Moderate, High, Very high)"
            ]
        }
        
        # System prompt for health conversations
        self.system_prompt = """You are a professional health concierge assistant for The Wellness London, a premium wellness clinic. Your role is to:

1. Conduct friendly, professional health assessments
2. Gather information about symptoms, health goals, and lifestyle
3. Provide general wellness guidance (not medical advice)
4. Qualify leads for appropriate treatments (blood testing, PRP, weight management)
5. Maintain a warm, supportive tone while being informative

Key guidelines:
- Always clarify you're not providing medical diagnosis or treatment
- Focus on wellness optimization and preventive care
- Ask follow-up questions to better understand client needs
- Suggest appropriate next steps based on responses
- Keep responses concise but informative
- Show empathy and understanding for health concerns

Available treatments to recommend:
- Comprehensive blood testing and analysis
- PRP (Platelet-Rich Plasma) therapy
- Weight management programs
- Nutritional consultations
- Hormone optimization
- IV therapy and supplements"""

    def generate_response(self, user_input: str, phone_number: str, conversation_history: List[Dict] = None) -> str:
        """
        Process user input and generate AI response using Claude API.
        
        Args:
            user_input: User's message
            phone_number: User's WhatsApp number
            conversation_history: Previous conversation messages
            
        Returns:
            AI-generated response string
        """
        try:
            # Get user profile for context
            user_profile = self.db.get_user_profile(phone_number)
            
            # Format conversation for Claude
            formatted_conversation = self.format_conversation(
                user_input, conversation_history, user_profile
            )
            
            # Generate response using Claude
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=500,
                temperature=0.7,
                system=self.system_prompt,
                messages=formatted_conversation
            )
            
            ai_response = response.content[0].text
            
            # Save conversation to database
            self.db.save_conversation(
                phone_number=phone_number,
                user_message=user_input,
                ai_response=ai_response,
                timestamp=datetime.now()
            )
            
            self.logger.info(f"Generated AI response for {phone_number}")
            return ai_response
            
        except Exception as e:
            self.logger.error(f"Error generating AI response: {str(e)}")
            return "I apologize, but I'm experiencing technical difficulties. Please try again in a moment, or feel free to call The Wellness London directly for immediate assistance."

    def conduct_health_assessment(self, phone_number: str, current_step: str = 'start') -> Tuple[str, str]:
        """
        Guide users through initial health questionnaire.
        
        Args:
            phone_number: User's WhatsApp number
            current_step: Current assessment step
            
        Returns:
            Tuple of (response_message, next_step)
        """
        try:
            user_profile = self.db.get_user_profile(phone_number)
            
            if current_step == 'start':
                response = """Welcome to The Wellness London! 🌟

I'm here to help you discover the best wellness solutions for your needs. Let's start with a quick health assessment to personalize your experience.

This will take just 2-3 minutes and help us recommend the most suitable treatments for you.

Ready to begin? Please reply 'yes' to start, or ask me any questions you might have!"""
                return response, 'basic_info_0'
                
            elif current_step.startswith('basic_info'):
                question_index = int(current_step.split('_')[-1])
                if question_index < len(self.assessment_questions['basic_info']):
                    question = self.assessment_questions['basic_info'][question_index]
                    response = f"Great! Let's start with some basic information:\n\n{question}"
                    next_step = f"basic_info_{question_index + 1}" if question_index + 1 < len(self.assessment_questions['basic_info']) else "symptoms_0"
                    return response, next_step
                    
            elif current_step.startswith('symptoms'):
                question_index = int(current_step.split('_')[-1])
                if question_index < len(self.assessment_questions['symptoms']):
                    question = self.assessment_questions['symptoms'][question_index]
                    response = f"Now, let's talk about any symptoms you might be experiencing:\n\n{question}"
                    next_step = f"symptoms_{question_index + 1}" if question_index + 1 < len(self.assessment_questions['symptoms']) else "lifestyle_0"
                    return response, next_step
                    
            elif current_step.startswith('lifestyle'):
                question_index = int(current_step.split('_')[-1])
                if question_index < len(self.assessment_questions['lifestyle']):
                    question = self.assessment_questions['lifestyle'][question_index]
                    response = f"Finally, let's understand your lifestyle:\n\n{question}"
                    next_step = f"lifestyle_{question_index + 1}" if question_index + 1 < len(self.assessment_questions['lifestyle']) else "complete"
                    return response, next_step
                    
            elif current_step == 'complete':
                response = """Thank you for completing the health assessment! 🎉

Based on your responses, I'll analyze your needs and provide personalized recommendations for The Wellness London's services.

Give me just a moment to review your information and I'll share some tailored suggestions for your wellness journey."""
                return response, 'analysis'
                
            else:
                # Default fallback
                return self.generate_response("Let's continue with your health assessment.", phone_number), 'basic_info_0'
                
        except Exception as e:
            self.logger.error(f"Error in health assessment: {str(e)}")
            return "I apologize for the technical issue. Let me help you in a different way. What brings you to The Wellness London today?", 'conversation'

    def format_conversation(self, current_input: str, history: List[Dict] = None, user_profile: Dict = None) -> List[Dict]:
        """
        Structure conversation history for Claude API.
        
        Args:
            current_input: Current user message
            history: Previous conversation messages
            user_profile: User's stored profile data
            
        Returns:
            Formatted conversation list for Claude API
        """
        try:
            messages = []
            
            # Add user profile context if available
            if user_profile:
                context = f"User profile context: {json.dumps(user_profile, default=str)}"
                messages.append({
                    "role": "user",
                    "content": f"Context: {context}"
                })
                messages.append({
                    "role": "assistant", 
                    "content": "I understand the user's profile context and will provide personalized assistance."
                })
            
            # Add conversation history
            if history:
                for msg in history[-10:]:  # Limit to last 10 messages
                    if msg.get('user_message'):
                        messages.append({
                            "role": "user",
                            "content": msg['user_message']
                        })
                    if msg.get('ai_response'):
                        messages.append({
                            "role": "assistant",
                            "content": msg['ai_response']
                        })
            
            # Add current user input
            messages.append({
                "role": "user",
                "content": current_input
            })
            
            return messages
            
        except Exception as e:
            self.logger.error(f"Error formatting conversation: {str(e)}")
            return [{"role": "user", "content": current_input}]

    def analyze_health_responses(self, phone_number: str) -> Dict:
        """
        Analyze completed health assessment responses.
        
        Args:
            phone_number: User's WhatsApp number
            
        Returns:
            Analysis results dictionary
        """
        try:
            # Get user's conversation history
            user_profile = self.db.get_user_profile(phone_number)
            
            if not user_profile or not user_profile.get('assessment_responses'):
                return {'error': 'No assessment data found'}
            
            # Use Claude to analyze responses
            analysis_prompt = f"""Please analyze this health assessment data and provide recommendations:

Assessment Responses: {json.dumps(user_profile.get('assessment_responses', {}), indent=2)}

Please provide:
1. Key health insights
2. Recommended treatments from our services
3. Urgency level (Low/Medium/High)
4. Suggested next steps

Our available treatments:
- Comprehensive blood testing
- PRP therapy
- Weight management programs
- Nutritional consultations
- Hormone optimization
- IV therapy"""

            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=400,
                temperature=0.5,
                system="You are a health analysis expert. Provide structured, actionable insights based on assessment data.",
                messages=[{"role": "user", "content": analysis_prompt}]
            )
            
            analysis = response.content[0].text
            
            return {
                'analysis': analysis,
                'timestamp': datetime.now().isoformat(),
                'phone_number': phone_number
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing health responses: {str(e)}")
            return {'error': 'Analysis failed', 'message': str(e)}

    def get_wellness_recommendation(self, symptoms: List[str], goals: List[str]) -> str:
        """
        Generate personalized wellness recommendations.
        
        Args:
            symptoms: List of reported symptoms
            goals: List of health goals
            
        Returns:
            Personalized recommendation string
        """
        try:
            recommendation_prompt = f"""Based on these symptoms and goals, provide wellness recommendations:

Symptoms: {', '.join(symptoms) if symptoms else 'None reported'}
Goals: {', '.join(goals) if goals else 'General wellness'}

Please recommend appropriate treatments from:
- Blood testing and analysis
- PRP therapy
- Weight management
- Nutritional consultation
- Hormone optimization
- IV therapy

Keep recommendations specific and actionable."""

            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=300,
                temperature=0.6,
                system="You are a wellness consultant providing treatment recommendations.",
                messages=[{"role": "user", "content": recommendation_prompt}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            self.logger.error(f"Error generating wellness recommendation: {str(e)}")
            return "I recommend starting with our comprehensive blood testing to get a complete picture of your health, followed by a consultation to discuss personalized treatment options."

    def handle_appointment_request(self, phone_number: str, message: str) -> str:
        """
        Process appointment booking requests.
        
        Args:
            phone_number: User's WhatsApp number
            message: User's appointment request message
            
        Returns:
            Response about appointment booking
        """
        try:
            appointment_prompt = f"""The user is requesting an appointment. Their message: "{message}"

Please provide a helpful response that:
1. Acknowledges their appointment request
2. Explains the next steps for booking
3. Asks for preferred dates/times if not provided
4. Mentions any preparation needed

Keep the tone professional and helpful."""

            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=200,
                temperature=0.5,
                system="You are an appointment booking assistant for a wellness clinic.",
                messages=[{"role": "user", "content": appointment_prompt}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            self.logger.error(f"Error handling appointment request: {str(e)}")
            return "I'd be happy to help you book an appointment! Please let me know your preferred dates and times, and I'll check our availability for you."