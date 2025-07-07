import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json
from dataclasses import dataclass
from enum import Enum

from .database import DatabaseManager
from .whatsapp_handler import WhatsAppHandler
from .utils import setup_logger

class ContentType(Enum):
    WELLNESS_TIP = "wellness_tip"
    TREATMENT_INFO = "treatment_info"
    POST_CARE = "post_care"
    FOLLOW_UP = "follow_up"
    EDUCATIONAL = "educational"

class TreatmentCategory(Enum):
    BLOOD_TESTING = "blood_testing"
    PRP = "prp"
    WEIGHT_MANAGEMENT = "weight_management"
    GENERAL_WELLNESS = "general_wellness"

@dataclass
class ContentItem:
    id: str
    title: str
    content: str
    content_type: ContentType
    treatment_category: TreatmentCategory
    urgency_level: int
    tags: List[str]
    created_at: datetime

class ContentManager:
    """Manages personalized wellness content delivery and follow-up communications"""
    
    def __init__(self, db_manager: DatabaseManager, whatsapp_handler: WhatsAppHandler):
        self.db = db_manager
        self.whatsapp = whatsapp_handler
        self.logger = setup_logger(__name__)
        self._content_library = self._initialize_content_library()
        
    def _initialize_content_library(self) -> Dict[str, ContentItem]:
        """Initialize the wellness content library with predefined content"""
        content_data = {
            "blood_test_prep": ContentItem(
                id="blood_test_prep",
                title="Blood Test Preparation Guide",
                content="🩸 *Preparing for Your Blood Test*\n\n"
                       "• Fast for 8-12 hours before your appointment\n"
                       "• Stay hydrated with water only\n"
                       "• Avoid alcohol 24 hours prior\n"
                       "• Take medications as prescribed unless advised otherwise\n"
                       "• Wear comfortable clothing with loose sleeves\n\n"
                       "Questions? Reply to this message!",
                content_type=ContentType.TREATMENT_INFO,
                treatment_category=TreatmentCategory.BLOOD_TESTING,
                urgency_level=3,
                tags=["preparation", "blood_test", "fasting"],
                created_at=datetime.now()
            ),
            "prp_aftercare": ContentItem(
                id="prp_aftercare",
                title="PRP Treatment Aftercare",
                content="✨ *Your PRP Treatment Aftercare Plan*\n\n"
                       "First 24 hours:\n"
                       "• Avoid touching or washing the treated area\n"
                       "• No makeup or skincare products\n"
                       "• Stay hydrated and rest well\n\n"
                       "Next 48 hours:\n"
                       "• Gentle cleansing with mild soap\n"
                       "• Apply recommended moisturizer\n"
                       "• Avoid direct sunlight\n\n"
                       "You may experience mild redness - this is normal!",
                content_type=ContentType.POST_CARE,
                treatment_category=TreatmentCategory.PRP,
                urgency_level=4,
                tags=["aftercare", "prp", "recovery"],
                created_at=datetime.now()
            ),
            "weight_management_tips": ContentItem(
                id="weight_management_tips",
                title="Weekly Weight Management Tips",
                content="🎯 *This Week's Wellness Focus*\n\n"
                       "💧 Hydration Goal: 8 glasses of water daily\n"
                       "🥗 Nutrition Tip: Fill half your plate with vegetables\n"
                       "🚶 Movement Goal: 10,000 steps or 30 minutes activity\n"
                       "😴 Sleep Target: 7-9 hours quality sleep\n\n"
                       "Small changes lead to big results! How are you feeling this week?",
                content_type=ContentType.WELLNESS_TIP,
                treatment_category=TreatmentCategory.WEIGHT_MANAGEMENT,
                urgency_level=2,
                tags=["weight_loss", "lifestyle", "weekly_tips"],
                created_at=datetime.now()
            ),
            "general_wellness": ContentItem(
                id="general_wellness",
                title="Daily Wellness Reminder",
                content="🌟 *Your Daily Wellness Moment*\n\n"
                       "Remember: Wellness is a journey, not a destination.\n\n"
                       "Today's focus:\n"
                       "• Take 5 deep breaths\n"
                       "• Drink a glass of water\n"
                       "• Move your body for 10 minutes\n"
                       "• Practice gratitude\n\n"
                       "You're investing in the best version of yourself! 💪",
                content_type=ContentType.WELLNESS_TIP,
                treatment_category=TreatmentCategory.GENERAL_WELLNESS,
                urgency_level=1,
                tags=["daily_wellness", "mindfulness", "motivation"],
                created_at=datetime.now()
            ),
            "appointment_reminder": ContentItem(
                id="appointment_reminder",
                title="Appointment Reminder",
                content="📅 *Appointment Reminder*\n\n"
                       "Hello! This is a friendly reminder about your upcoming appointment at The Wellness London.\n\n"
                       "📍 Location: [CLINIC_ADDRESS]\n"
                       "🕐 Time: [APPOINTMENT_TIME]\n"
                       "👩‍⚕️ Treatment: [TREATMENT_TYPE]\n\n"
                       "Please arrive 15 minutes early. If you need to reschedule, reply to this message.\n\n"
                       "Looking forward to seeing you!",
                content_type=ContentType.FOLLOW_UP,
                treatment_category=TreatmentCategory.GENERAL_WELLNESS,
                urgency_level=5,
                tags=["reminder", "appointment", "clinic"],
                created_at=datetime.now()
            )
        }
        return content_data
    
    def get_targeted_content(self, user_phone: str, content_type: Optional[ContentType] = None) -> Optional[ContentItem]:
        """Select personalized content based on user profile and treatment history"""
        try:
            # Get user profile and treatment history
            user_profile = self.db.get_user_profile(user_phone)
            if not user_profile:
                self.logger.warning(f"No user profile found for {user_phone}")
                return self._content_library["general_wellness"]
            
            # Determine user's treatment category
            treatment_category = self._determine_treatment_category(user_profile)
            
            # Filter content based on treatment category and type
            suitable_content = []
            for content_item in self._content_library.values():
                if content_item.treatment_category == treatment_category:
                    if content_type is None or content_item.content_type == content_type:
                        suitable_content.append(content_item)
            
            if not suitable_content:
                return self._content_library["general_wellness"]
            
            # Select content based on user's engagement history
            best_content = self._select_best_content(user_phone, suitable_content)
            
            # Track content selection
            self._track_content_selection(user_phone, best_content.id)
            
            return best_content
            
        except Exception as e:
            self.logger.error(f"Error getting targeted content for {user_phone}: {str(e)}")
            return self._content_library["general_wellness"]
    
    def send_wellness_tips(self, user_phone: str, custom_message: Optional[str] = None) -> bool:
        """Send personalized wellness tips to user"""
        try:
            if custom_message:
                message = custom_message
            else:
                content_item = self.get_targeted_content(user_phone, ContentType.WELLNESS_TIP)
                if not content_item:
                    return False
                message = content_item.content
            
            # Send via WhatsApp
            success = self.whatsapp.send_message(user_phone, message)
            
            if success:
                # Log the interaction
                self.db.save_conversation(
                    user_phone=user_phone,
                    message=message,
                    sender="system",
                    message_type="wellness_tip"
                )
                self.logger.info(f"Wellness tip sent to {user_phone}")
                return True
            else:
                self.logger.error(f"Failed to send wellness tip to {user_phone}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending wellness tips to {user_phone}: {str(e)}")
            return False
    
    def schedule_follow_up(self, user_phone: str, follow_up_type: str, delay_hours: int = 24) -> bool:
        """Schedule follow-up messages for post-treatment care"""
        try:
            follow_up_time = datetime.now() + timedelta(hours=delay_hours)
            
            # Get appropriate follow-up content
            content_item = None
            if follow_up_type == "post_treatment":
                content_item = self.get_targeted_content(user_phone, ContentType.POST_CARE)
            elif follow_up_type == "appointment_reminder":
                content_item = self._content_library["appointment_reminder"]
            else:
                content_item = self.get_targeted_content(user_phone, ContentType.FOLLOW_UP)
            
            if not content_item:
                self.logger.warning(f"No follow-up content found for type: {follow_up_type}")
                return False
            
            # Store follow-up in database
            follow_up_data = {
                'user_phone': user_phone,
                'content_id': content_item.id,
                'follow_up_type': follow_up_type,
                'scheduled_time': follow_up_time.isoformat(),
                'status': 'scheduled',
                'created_at': datetime.now().isoformat()
            }
            
            # Save to database (assuming we have a follow_ups table)
            query = """
                INSERT INTO follow_ups (user_phone, content_id, follow_up_type, scheduled_time, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            
            self.db.execute_query(query, (
                follow_up_data['user_phone'],
                follow_up_data['content_id'],
                follow_up_data['follow_up_type'],
                follow_up_data['scheduled_time'],
                follow_up_data['status'],
                follow_up_data['created_at']
            ))
            
            self.logger.info(f"Follow-up scheduled for {user_phone} at {follow_up_time}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error scheduling follow-up for {user_phone}: {str(e)}")
            return False
    
    def track_engagement(self, user_phone: str, content_id: str, engagement_type: str) -> bool:
        """Track user engagement with content"""
        try:
            engagement_data = {
                'user_phone': user_phone,
                'content_id': content_id,
                'engagement_type': engagement_type,  # 'viewed', 'clicked', 'replied'
                'timestamp': datetime.now().isoformat()
            }
            
            # Save engagement data
            query = """
                INSERT INTO content_engagement (user_phone, content_id, engagement_type, timestamp)
                VALUES (?, ?, ?, ?)
            """
            
            self.db.execute_query(query, (
                engagement_data['user_phone'],
                engagement_data['content_id'],
                engagement_data['engagement_type'],
                engagement_data['timestamp']
            ))
            
            self.logger.info(f"Engagement tracked: {user_phone} - {engagement_type} - {content_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error tracking engagement: {str(e)}")
            return False
    
    def process_scheduled_follow_ups(self) -> int:
        """Process and send scheduled follow-up messages"""
        try:
            current_time = datetime.now()
            
            # Get due follow-ups
            query = """
                SELECT * FROM follow_ups 
                WHERE status = 'scheduled' AND scheduled_time <= ?
                ORDER BY scheduled_time ASC
            """
            
            due_follow_ups = self.db.fetch_all(query, (current_time.isoformat(),))
            
            processed_count = 0
            for follow_up in due_follow_ups:
                try:
                    user_phone = follow_up['user_phone']
                    content_id = follow_up['content_id']
                    
                    # Get content
                    content_item = self._content_library.get(content_id)
                    if not content_item:
                        self.logger.warning(f"Content not found: {content_id}")
                        continue
                    
                    # Customize content if needed
                    message = self._customize_follow_up_message(content_item, follow_up)
                    
                    # Send message
                    if self.whatsapp.send_message(user_phone, message):
                        # Update follow-up status
                        update_query = """
                            UPDATE follow_ups 
                            SET status = 'sent', sent_at = ? 
                            WHERE id = ?
                        """
                        self.db.execute_query(update_query, (current_time.isoformat(), follow_up['id']))
                        
                        # Log conversation
                        self.db.save_conversation(
                            user_phone=user_phone,
                            message=message,
                            sender="system",
                            message_type="follow_up"
                        )
                        
                        processed_count += 1
                        self.logger.info(f"Follow-up sent to {user_phone}")
                    else:
                        # Mark as failed
                        update_query = """
                            UPDATE follow_ups 
                            SET status = 'failed', attempted_at = ? 
                            WHERE id = ?
                        """
                        self.db.execute_query(update_query, (current_time.isoformat(), follow_up['id']))
                        
                except Exception as e:
                    self.logger.error(f"Error processing follow-up {follow_up.get('id', 'unknown')}: {str(e)}")
                    continue
            
            self.logger.info(f"Processed {processed_count} follow-up messages")
            return processed_count
            
        except Exception as e:
            self.logger.error(f"Error processing scheduled follow-ups: {str(e)}")
            return 0
    
    def get_engagement_stats(self, days: int = 30) -> Dict:
        """Get content engagement statistics"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # Get engagement stats
            query = """
                SELECT 
                    content_id,
                    engagement_type,
                    COUNT(*) as count
                FROM content_engagement 
                WHERE timestamp >= ?
                GROUP BY content_id, engagement_type
            """
            
            engagement_data = self.db.fetch_all(query, (start_date.isoformat(),))
            
            # Process stats
            stats = {
                'total_engagements': 0,
                'by_content': {},
                'by_type': {'viewed': 0, 'clicked': 0, 'replied': 0}
            }
            
            for row in engagement_data:
                content_id = row['content_id']
                engagement_type = row['engagement_type']
                count = row['count']
                
                stats['total_engagements'] += count
                
                if content_id not in stats['by_content']:
                    stats['by_content'][content_id] = {}
                stats['by_content'][content_id][engagement_type] = count
                
                if engagement_type in stats['by_type']:
                    stats['by_type'][engagement_type] += count
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting engagement stats: {str(e)}")
            return {}
    
    def _determine_treatment_category(self, user_profile: Dict) -> TreatmentCategory:
        """Determine user's primary treatment category from profile"""
        try:
            # Check qualification data
            qualification_data = user_profile.get('qualification_data', {})
            if isinstance(qualification_data, str):
                qualification_data = json.loads(qualification_data)
            
            treatment_type = qualification_data.get('treatment_type', '').lower()
            
            if 'blood' in treatment_type or 'test' in treatment_type:
                return TreatmentCategory.BLOOD_TESTING
            elif 'prp' in treatment_type or 'platelet' in treatment_type:
                return TreatmentCategory.PRP
            elif 'weight' in treatment_type or 'management' in treatment_type:
                return TreatmentCategory.WEIGHT_MANAGEMENT
            else:
                return TreatmentCategory.GENERAL_WELLNESS
                
        except Exception as e:
            self.logger.error(f"Error determining treatment category: {str(e)}")
            return TreatmentCategory.GENERAL_WELLNESS
    
    def _select_best_content(self, user_phone: str, content_options: List[ContentItem]) -> ContentItem:
        """Select the best content based on user engagement history"""
        try:
            # Get user's recent engagement
            query = """
                SELECT content_id, COUNT(*) as engagement_count
                FROM content_engagement 
                WHERE user_phone = ? AND timestamp >= ?
                GROUP BY content_id
            """
            
            recent_date = datetime.now() - timedelta(days=7)
            recent_engagement = self.db.fetch_all(query, (user_phone, recent_date.isoformat()))
            
            engaged_content_ids = {row['content_id'] for row in recent_engagement}
            
            # Prefer content user hasn't seen recently
            fresh_content = [c for c in content_options if c.id not in engaged_content_ids]
            
            if fresh_content:
                # Sort by urgency level (higher first)
                fresh_content.sort(key=lambda x: x.urgency_level, reverse=True)
                return fresh_content[0]
            else:
                # If all content has been seen, return highest urgency
                content_options.sort(key=lambda x: x.urgency_level, reverse=True)
                return content_options[0]
                
        except Exception as e:
            self.logger.error(f"Error selecting best content: {str(e)}")
            return content_options[0] if content_options else self._content_library["general_wellness"]
    
    def _track_content_selection(self, user_phone: str, content_id: str):
        """Track when content is selected for a user"""
        try:
            self.track_engagement(user_phone, content_id, 'selected')
        except Exception as e:
            self.logger.error(f"Error tracking content selection: {str(e)}")
    
    def _customize_follow_up_message(self, content_item: ContentItem, follow_up_data: Dict) -> str:
        """Customize follow-up message with user-specific data"""
        try:
            message = content_item.content
            
            # Replace placeholders if this is an appointment reminder
            if content_item.id == "appointment_reminder":
                # Get user's appointment details (would need to be implemented)
                # For now, return generic message
                message = message.replace("[CLINIC_ADDRESS]", "123 Wellness Street, London")
                message = message.replace("[APPOINTMENT_TIME]", "Tomorrow at 2:00 PM")
                message = message.replace("[TREATMENT_TYPE]", "Wellness Consultation")
            
            return message
            
        except Exception as e:
            self.logger.error(f"Error customizing follow-up message: {str(e)}")
            return content_item.content