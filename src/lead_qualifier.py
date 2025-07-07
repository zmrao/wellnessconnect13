import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import json
import re
from dataclasses import dataclass
from enum import Enum

from .database import DatabaseManager
from .utils import ValidationHelper

class TreatmentType(Enum):
    BLOOD_TESTING = "blood_testing"
    PRP = "prp"
    WEIGHT_MANAGEMENT = "weight_management"
    IV_THERAPY = "iv_therapy"
    HORMONE_THERAPY = "hormone_therapy"
    GENERAL_WELLNESS = "general_wellness"

class UrgencyLevel(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4

@dataclass
class QualificationResult:
    user_id: str
    treatment_type: TreatmentType
    urgency_level: UrgencyLevel
    urgency_score: int
    confidence_score: float
    key_symptoms: List[str]
    recommended_actions: List[str]
    notes: str
    qualified: bool

class LeadQualifier:
    """Categorizes and scores potential clients based on health assessments"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.validator = ValidationHelper()
        self.logger = logging.getLogger(__name__)
        
        # Keywords for treatment categorization
        self.treatment_keywords = {
            TreatmentType.BLOOD_TESTING: [
                'blood test', 'blood work', 'lab results', 'cholesterol', 'diabetes',
                'thyroid', 'vitamin deficiency', 'hormone levels', 'health check',
                'screening', 'biomarkers', 'lipid panel'
            ],
            TreatmentType.PRP: [
                'hair loss', 'baldness', 'thinning hair', 'prp', 'platelet rich plasma',
                'hair restoration', 'hair growth', 'alopecia', 'scalp treatment',
                'hair transplant alternative'
            ],
            TreatmentType.WEIGHT_MANAGEMENT: [
                'weight loss', 'obesity', 'overweight', 'diet', 'metabolism',
                'fat loss', 'body composition', 'bmi', 'weight gain', 'nutrition',
                'appetite', 'metabolic syndrome', 'bariatric'
            ],
            TreatmentType.IV_THERAPY: [
                'iv therapy', 'vitamin drip', 'hydration', 'energy boost',
                'immune support', 'hangover', 'fatigue', 'vitamin infusion',
                'myers cocktail', 'glutathione', 'nad+'
            ],
            TreatmentType.HORMONE_THERAPY: [
                'hormone', 'testosterone', 'estrogen', 'menopause', 'andropause',
                'hrt', 'hormone replacement', 'low t', 'hormonal imbalance',
                'bioidentical hormones', 'thyroid hormone'
            ]
        }
        
        # Urgency indicators
        self.urgency_keywords = {
            UrgencyLevel.URGENT: [
                'severe', 'emergency', 'urgent', 'critical', 'immediate',
                'chest pain', 'difficulty breathing', 'severe pain'
            ],
            UrgencyLevel.HIGH: [
                'worsening', 'getting worse', 'concerning', 'worried',
                'significant', 'major', 'serious', 'persistent pain'
            ],
            UrgencyLevel.MEDIUM: [
                'moderate', 'noticeable', 'bothering', 'affecting daily',
                'ongoing', 'recurring', 'mild pain'
            ],
            UrgencyLevel.LOW: [
                'mild', 'occasional', 'preventive', 'maintenance',
                'general wellness', 'routine', 'check-up'
            ]
        }

    def analyze_responses(self, user_id: str, responses: Dict[str, str]) -> QualificationResult:
        """Process health assessment answers and generate qualification result"""
        try:
            self.logger.info(f"Analyzing responses for user {user_id}")
            
            # Combine all response text for analysis
            combined_text = " ".join(responses.values()).lower()
            
            # Categorize treatment type
            treatment_type = self.categorize_treatment(combined_text)
            
            # Calculate urgency score
            urgency_score = self.calculate_urgency_score(combined_text)
            urgency_level = self._score_to_urgency_level(urgency_score)
            
            # Extract key symptoms
            key_symptoms = self._extract_symptoms(combined_text)
            
            # Generate recommendations
            recommended_actions = self._generate_recommendations(treatment_type, urgency_level)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence(responses, treatment_type)
            
            # Determine if lead is qualified
            qualified = self._is_qualified(urgency_score, confidence_score, responses)
            
            # Generate notes
            notes = self._generate_notes(responses, treatment_type, urgency_level)
            
            result = QualificationResult(
                user_id=user_id,
                treatment_type=treatment_type,
                urgency_level=urgency_level,
                urgency_score=urgency_score,
                confidence_score=confidence_score,
                key_symptoms=key_symptoms,
                recommended_actions=recommended_actions,
                notes=notes,
                qualified=qualified
            )
            
            # Save qualification result to database
            self._save_qualification_result(result)
            
            self.logger.info(f"Qualification completed for user {user_id}: {treatment_type.value}, urgency: {urgency_level.value}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error analyzing responses for user {user_id}: {str(e)}")
            raise

    def categorize_treatment(self, text: str) -> TreatmentType:
        """Determine appropriate treatment type based on text analysis"""
        try:
            text = text.lower()
            treatment_scores = {}
            
            for treatment_type, keywords in self.treatment_keywords.items():
                score = 0
                for keyword in keywords:
                    if keyword in text:
                        # Weight longer, more specific keywords higher
                        score += len(keyword.split())
                treatment_scores[treatment_type] = score
            
            # Return treatment type with highest score
            if treatment_scores and max(treatment_scores.values()) > 0:
                return max(treatment_scores, key=treatment_scores.get)
            
            return TreatmentType.GENERAL_WELLNESS
            
        except Exception as e:
            self.logger.error(f"Error categorizing treatment: {str(e)}")
            return TreatmentType.GENERAL_WELLNESS

    def calculate_urgency_score(self, text: str) -> int:
        """Assess priority level for follow-up based on text content"""
        try:
            text = text.lower()
            urgency_score = 0
            
            # Check for urgency keywords
            for urgency_level, keywords in self.urgency_keywords.items():
                for keyword in keywords:
                    if keyword in text:
                        urgency_score += urgency_level.value
            
            # Additional scoring based on specific patterns
            if re.search(r'\b(pain|hurt|ache)\b.*\b(severe|bad|terrible|unbearable)\b', text):
                urgency_score += 3
            
            if re.search(r'\b(can\'t|cannot)\b.*\b(sleep|work|function)\b', text):
                urgency_score += 2
            
            if re.search(r'\b(getting worse|worsening|deteriorating)\b', text):
                urgency_score += 2
            
            # Time-based urgency
            if re.search(r'\b(today|now|immediately|asap)\b', text):
                urgency_score += 3
            elif re.search(r'\b(this week|soon|quickly)\b', text):
                urgency_score += 2
            
            return min(urgency_score, 20)  # Cap at 20
            
        except Exception as e:
            self.logger.error(f"Error calculating urgency score: {str(e)}")
            return 1

    def generate_qualification_report(self, user_id: str) -> Dict:
        """Create summary for staff review"""
        try:
            # Get user profile and conversation history
            user_profile = self.db.get_user_profile(user_id)
            if not user_profile:
                raise ValueError(f"User profile not found for {user_id}")
            
            # Get latest qualification result
            qualification = self._get_latest_qualification(user_id)
            if not qualification:
                raise ValueError(f"No qualification found for {user_id}")
            
            # Get conversation history
            conversations = self.db.get_conversation_history(user_id)
            
            report = {
                'user_id': user_id,
                'generated_at': datetime.now().isoformat(),
                'contact_info': {
                    'phone': user_profile.get('phone'),
                    'name': user_profile.get('name', 'Unknown'),
                    'email': user_profile.get('email')
                },
                'qualification': {
                    'treatment_type': qualification['treatment_type'],
                    'urgency_level': qualification['urgency_level'],
                    'urgency_score': qualification['urgency_score'],
                    'confidence_score': qualification['confidence_score'],
                    'qualified': qualification['qualified'],
                    'key_symptoms': qualification['key_symptoms'],
                    'recommended_actions': qualification['recommended_actions'],
                    'notes': qualification['notes']
                },
                'conversation_summary': self._summarize_conversations(conversations),
                'next_steps': self._determine_next_steps(qualification),
                'priority_ranking': self._calculate_priority_ranking(qualification)
            }
            
            self.logger.info(f"Generated qualification report for user {user_id}")
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating qualification report for {user_id}: {str(e)}")
            raise

    def get_qualified_leads(self, limit: int = 50) -> List[Dict]:
        """Get list of qualified leads sorted by priority"""
        try:
            query = """
                SELECT user_id, treatment_type, urgency_level, urgency_score, 
                       confidence_score, qualified, created_at
                FROM lead_qualifications 
                WHERE qualified = 1 
                ORDER BY urgency_score DESC, confidence_score DESC, created_at DESC
                LIMIT ?
            """
            
            results = self.db.execute_query(query, (limit,))
            
            qualified_leads = []
            for row in results:
                user_profile = self.db.get_user_profile(row['user_id'])
                lead = {
                    'user_id': row['user_id'],
                    'name': user_profile.get('name', 'Unknown') if user_profile else 'Unknown',
                    'phone': user_profile.get('phone') if user_profile else None,
                    'treatment_type': row['treatment_type'],
                    'urgency_level': row['urgency_level'],
                    'urgency_score': row['urgency_score'],
                    'confidence_score': row['confidence_score'],
                    'created_at': row['created_at']
                }
                qualified_leads.append(lead)
            
            return qualified_leads
            
        except Exception as e:
            self.logger.error(f"Error getting qualified leads: {str(e)}")
            return []

    def _score_to_urgency_level(self, score: int) -> UrgencyLevel:
        """Convert numeric urgency score to urgency level enum"""
        if score >= 10:
            return UrgencyLevel.URGENT
        elif score >= 6:
            return UrgencyLevel.HIGH
        elif score >= 3:
            return UrgencyLevel.MEDIUM
        else:
            return UrgencyLevel.LOW

    def _extract_symptoms(self, text: str) -> List[str]:
        """Extract key symptoms mentioned in the text"""
        symptoms = []
        
        # Common symptom patterns
        symptom_patterns = [
            r'\b(pain|ache|hurt|sore|tender)\b',
            r'\b(tired|fatigue|exhausted|weak)\b',
            r'\b(nausea|nauseous|sick)\b',
            r'\b(dizzy|dizziness|lightheaded)\b',
            r'\b(headache|migraine)\b',
            r'\b(insomnia|sleep problems|can\'t sleep)\b',
            r'\b(anxiety|anxious|stressed|stress)\b',
            r'\b(depression|depressed|sad)\b',
            r'\b(weight gain|weight loss)\b',
            r'\b(hair loss|balding|thinning hair)\b'
        ]
        
        for pattern in symptom_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            symptoms.extend(matches)
        
        return list(set(symptoms))  # Remove duplicates

    def _generate_recommendations(self, treatment_type: TreatmentType, urgency_level: UrgencyLevel) -> List[str]:
        """Generate recommended actions based on treatment type and urgency"""
        recommendations = []
        
        # Base recommendations by treatment type
        treatment_recommendations = {
            TreatmentType.BLOOD_TESTING: [
                "Schedule comprehensive blood panel",
                "Review current medications and supplements",
                "Prepare fasting instructions if needed"
            ],
            TreatmentType.PRP: [
                "Schedule hair loss consultation",
                "Discuss PRP treatment options",
                "Review before/after photos"
            ],
            TreatmentType.WEIGHT_MANAGEMENT: [
                "Schedule metabolic assessment",
                "Discuss nutrition and lifestyle factors",
                "Consider body composition analysis"
            ],
            TreatmentType.IV_THERAPY: [
                "Schedule IV therapy consultation",
                "Discuss vitamin deficiencies",
                "Review hydration needs"
            ],
            TreatmentType.HORMONE_THERAPY: [
                "Schedule hormone evaluation",
                "Order hormone panel blood work",
                "Discuss symptoms and treatment options"
            ],
            TreatmentType.GENERAL_WELLNESS: [
                "Schedule general wellness consultation",
                "Discuss health goals and concerns",
                "Consider preventive care options"
            ]
        }
        
        recommendations.extend(treatment_recommendations.get(treatment_type, []))
        
        # Add urgency-based recommendations
        if urgency_level == UrgencyLevel.URGENT:
            recommendations.insert(0, "PRIORITY: Schedule within 24-48 hours")
        elif urgency_level == UrgencyLevel.HIGH:
            recommendations.insert(0, "Schedule within 1 week")
        elif urgency_level == UrgencyLevel.MEDIUM:
            recommendations.insert(0, "Schedule within 2 weeks")
        
        return recommendations

    def _calculate_confidence(self, responses: Dict[str, str], treatment_type: TreatmentType) -> float:
        """Calculate confidence score for the qualification"""
        confidence = 0.0
        
        # Base confidence on response completeness
        total_questions = len(responses)
        answered_questions = sum(1 for response in responses.values() if response.strip())
        completeness_score = answered_questions / total_questions if total_questions > 0 else 0
        
        # Boost confidence if treatment type keywords are strongly present
        combined_text = " ".join(responses.values()).lower()
        keyword_matches = sum(1 for keyword in self.treatment_keywords.get(treatment_type, []) 
                             if keyword in combined_text)
        keyword_score = min(keyword_matches / 5, 1.0)  # Normalize to 0-1
        
        # Calculate final confidence
        confidence = (completeness_score * 0.6) + (keyword_score * 0.4)
        
        return round(confidence, 2)

    def _is_qualified(self, urgency_score: int, confidence_score: float, responses: Dict[str, str]) -> bool:
        """Determine if lead is qualified based on various factors"""
        # Minimum thresholds
        min_confidence = 0.3
        min_urgency = 1
        
        # Check if responses contain enough information
        combined_text = " ".join(responses.values())
        has_sufficient_info = len(combined_text.strip()) > 20
        
        # Qualification criteria
        qualified = (
            confidence_score >= min_confidence and
            urgency_score >= min_urgency and
            has_sufficient_info
        )
        
        return qualified

    def _generate_notes(self, responses: Dict[str, str], treatment_type: TreatmentType, urgency_level: UrgencyLevel) -> str:
        """Generate summary notes for the qualification"""
        notes = []
        
        # Add treatment type note
        notes.append(f"Categorized as: {treatment_type.value.replace('_', ' ').title()}")
        
        # Add urgency note
        notes.append(f"Urgency level: {urgency_level.value}")
        
        # Add key response highlights
        for question, response in responses.items():
            if response and len(response.strip()) > 10:
                notes.append(f"{question}: {response[:100]}...")
        
        return " | ".join(notes)

    def _save_qualification_result(self, result: QualificationResult):
        """Save qualification result to database"""
        try:
            query = """
                INSERT OR REPLACE INTO lead_qualifications 
                (user_id, treatment_type, urgency_level, urgency_score, confidence_score,
                 key_symptoms, recommended_actions, notes, qualified, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            params = (
                result.user_id,
                result.treatment_type.value,
                result.urgency_level.value,
                result.urgency_score,
                result.confidence_score,
                json.dumps(result.key_symptoms),
                json.dumps(result.recommended_actions),
                result.notes,
                result.qualified,
                datetime.now().isoformat()
            )
            
            self.db.execute_query(query, params)
            
        except Exception as e:
            self.logger.error(f"Error saving qualification result: {str(e)}")
            raise

    def _get_latest_qualification(self, user_id: str) -> Optional[Dict]:
        """Get the most recent qualification for a user"""
        try:
            query = """
                SELECT * FROM lead_qualifications 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            """
            
            result = self.db.execute_query(query, (user_id,))
            if result:
                row = result[0]
                return {
                    'treatment_type': row['treatment_type'],
                    'urgency_level': row['urgency_level'],
                    'urgency_score': row['urgency_score'],
                    'confidence_score': row['confidence_score'],
                    'qualified': row['qualified'],
                    'key_symptoms': json.loads(row['key_symptoms']) if row['key_symptoms'] else [],
                    'recommended_actions': json.loads(row['recommended_actions']) if row['recommended_actions'] else [],
                    'notes': row['notes'],
                    'created_at': row['created_at']
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting latest qualification: {str(e)}")
            return None

    def _summarize_conversations(self, conversations: List[Dict]) -> str:
        """Create a summary of conversation history"""
        if not conversations:
            return "No conversation history available"
        
        summary_parts = []
        for conv in conversations[-5:]:  # Last 5 conversations
            timestamp = conv.get('timestamp', 'Unknown time')
            message = conv.get('message', '')[:100]  # First 100 chars
            summary_parts.append(f"{timestamp}: {message}...")
        
        return " | ".join(summary_parts)

    def _determine_next_steps(self, qualification: Dict) -> List[str]:
        """Determine recommended next steps based on qualification"""
        next_steps = []
        
        if qualification['qualified']:
            if qualification['urgency_level'] in ['urgent', 'high']:
                next_steps.append("Contact within 24 hours")
            else:
                next_steps.append("Schedule follow-up call")
            
            next_steps.extend(qualification['recommended_actions'])
        else:
            next_steps.append("Send educational content")
            next_steps.append("Schedule follow-up in 1 week")
        
        return next_steps

    def _calculate_priority_ranking(self, qualification: Dict) -> int:
        """Calculate priority ranking for lead sorting"""
        priority = 0
        
        # Urgency score contributes most to priority
        priority += qualification['urgency_score'] * 10
        
        # Confidence score adds to priority
        priority += int(qualification['confidence_score'] * 50)
        
        # Qualified leads get bonus points
        if qualification['qualified']:
            priority += 100
        
        return priority