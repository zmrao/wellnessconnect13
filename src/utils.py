import logging
import re
import hashlib
import os
from datetime import datetime
from typing import Optional, Any, Dict
from cryptography.fernet import Fernet
import phonenumbers
from phonenumbers import NumberParseException


class Logger:
    """Application logging utility for WellnessConnect platform"""
    
    def __init__(self, name: str = 'WellnessConnect'):
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """Configure logging settings with appropriate handlers and formatters"""
        if not self.logger.handlers:
            # Create logs directory if it doesn't exist
            os.makedirs('logs', exist_ok=True)
            
            # File handler
            file_handler = logging.FileHandler('logs/wellness_connect.log')
            file_handler.setLevel(logging.INFO)
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            
            # Formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            # Add handlers to logger
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
            self.logger.setLevel(logging.DEBUG)
    
    def info(self, message: str, extra: Dict = None):
        """Log info level message"""
        self.logger.info(message, extra=extra or {})
    
    def error(self, message: str, extra: Dict = None):
        """Log error level message"""
        self.logger.error(message, extra=extra or {})
    
    def warning(self, message: str, extra: Dict = None):
        """Log warning level message"""
        self.logger.warning(message, extra=extra or {})
    
    def debug(self, message: str, extra: Dict = None):
        """Log debug level message"""
        self.logger.debug(message, extra=extra or {})


class ValidationHelper:
    """Input validation and sanitization utilities"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email address format"""
        if not email or not isinstance(email, str):
            return False
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email.strip()))
    
    @staticmethod
    def validate_name(name: str) -> bool:
        """Validate name contains only letters, spaces, hyphens, and apostrophes"""
        if not name or not isinstance(name, str):
            return False
        
        name = name.strip()
        if len(name) < 2 or len(name) > 50:
            return False
        
        name_pattern = r"^[a-zA-Z\s\-']+$"
        return bool(re.match(name_pattern, name))
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Sanitize user input by removing potentially harmful characters"""
        if not text or not isinstance(text, str):
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove script tags and content
        text = re.sub(r'<script.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove potentially harmful characters
        text = re.sub(r'[<>"\']', '', text)
        
        return text.strip()
    
    @staticmethod
    def validate_age(age: Any) -> bool:
        """Validate age is a reasonable number"""
        try:
            age_int = int(age)
            return 16 <= age_int <= 120
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_treatment_type(treatment: str) -> bool:
        """Validate treatment type is one of the accepted options"""
        valid_treatments = [
            'blood_testing',
            'prp_therapy',
            'weight_management',
            'general_wellness',
            'consultation'
        ]
        return treatment.lower() in valid_treatments


def setup_logger(name: str = 'WellnessConnect', level: str = 'INFO') -> Logger:
    """Configure and return a logger instance"""
    logger = Logger(name)
    
    # Set log level based on environment
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.logger.setLevel(log_level)
    
    return logger


def validate_phone_number(phone: str, region: str = 'GB') -> bool:
    """Verify WhatsApp contact format using phonenumbers library"""
    if not phone or not isinstance(phone, str):
        return False
    
    try:
        # Parse the phone number
        parsed_number = phonenumbers.parse(phone, region)
        
        # Check if the number is valid
        if not phonenumbers.is_valid_number(parsed_number):
            return False
        
        # Check if it's a mobile number (WhatsApp requirement)
        number_type = phonenumbers.number_type(parsed_number)
        valid_types = [
            phonenumbers.PhoneNumberType.MOBILE,
            phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE
        ]
        
        return number_type in valid_types
        
    except NumberParseException:
        return False


def format_phone_number(phone: str, region: str = 'GB') -> Optional[str]:
    """Format phone number for WhatsApp API"""
    if not validate_phone_number(phone, region):
        return None
    
    try:
        parsed_number = phonenumbers.parse(phone, region)
        # Format as E164 (international format without + sign for WhatsApp)
        formatted = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
        return formatted.lstrip('+')
    except NumberParseException:
        return None


def encrypt_sensitive_data(data: str, key: Optional[bytes] = None) -> str:
    """Secure personal health information using Fernet encryption"""
    if not data:
        return ""
    
    try:
        # Use provided key or generate from environment
        if key is None:
            encryption_key = os.getenv('ENCRYPTION_KEY')
            if not encryption_key:
                # Generate a new key if none exists (should be stored securely)
                encryption_key = Fernet.generate_key().decode()
                # In production, this should be stored securely
            key = encryption_key.encode() if isinstance(encryption_key, str) else encryption_key
        
        fernet = Fernet(key)
        encrypted_data = fernet.encrypt(data.encode())
        return encrypted_data.decode()
        
    except Exception as e:
        logger = setup_logger()
        logger.error(f"Encryption failed: {str(e)}")
        return ""


def decrypt_sensitive_data(encrypted_data: str, key: Optional[bytes] = None) -> str:
    """Decrypt personal health information"""
    if not encrypted_data:
        return ""
    
    try:
        # Use provided key or get from environment
        if key is None:
            encryption_key = os.getenv('ENCRYPTION_KEY')
            if not encryption_key:
                return ""
            key = encryption_key.encode() if isinstance(encryption_key, str) else encryption_key
        
        fernet = Fernet(key)
        decrypted_data = fernet.decrypt(encrypted_data.encode())
        return decrypted_data.decode()
        
    except Exception as e:
        logger = setup_logger()
        logger.error(f"Decryption failed: {str(e)}")
        return ""


def format_datetime(dt: datetime, format_type: str = 'display') -> str:
    """Standardize date/time display across the application"""
    if not isinstance(dt, datetime):
        return ""
    
    formats = {
        'display': '%d/%m/%Y %H:%M',
        'date_only': '%d/%m/%Y',
        'time_only': '%H:%M',
        'iso': '%Y-%m-%dT%H:%M:%S',
        'filename': '%Y%m%d_%H%M%S',
        'whatsapp': '%d %b %Y at %H:%M'
    }
    
    format_string = formats.get(format_type, formats['display'])
    return dt.strftime(format_string)


def generate_hash(data: str, salt: Optional[str] = None) -> str:
    """Generate SHA-256 hash for data integrity"""
    if not data:
        return ""
    
    # Add salt if provided
    if salt:
        data = f"{data}{salt}"
    
    return hashlib.sha256(data.encode()).hexdigest()


def validate_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    """Validate webhook signature for security"""
    if not all([payload, signature, secret]):
        return False
    
    try:
        # Generate expected signature
        expected_signature = hashlib.sha256(
            f"{secret}{payload}".encode()
        ).hexdigest()
        
        # Compare signatures
        return signature == expected_signature
        
    except Exception:
        return False


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length with suffix"""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def extract_keywords(text: str) -> list:
    """Extract keywords from text for content matching"""
    if not text:
        return []
    
    # Convert to lowercase and split
    words = re.findall(r'\b\w+\b', text.lower())
    
    # Filter out common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
        'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
    }
    
    keywords = [word for word in words if word not in stop_words and len(word) > 2]
    
    # Return unique keywords
    return list(set(keywords))


def calculate_similarity_score(text1: str, text2: str) -> float:
    """Calculate similarity between two texts based on common keywords"""
    if not text1 or not text2:
        return 0.0
    
    keywords1 = set(extract_keywords(text1))
    keywords2 = set(extract_keywords(text2))
    
    if not keywords1 or not keywords2:
        return 0.0
    
    # Calculate Jaccard similarity
    intersection = len(keywords1.intersection(keywords2))
    union = len(keywords1.union(keywords2))
    
    return intersection / union if union > 0 else 0.0


def format_currency(amount: float, currency: str = 'GBP') -> str:
    """Format currency amounts for display"""
    if currency == 'GBP':
        return f"£{amount:.2f}"
    elif currency == 'USD':
        return f"${amount:.2f}"
    elif currency == 'EUR':
        return f"€{amount:.2f}"
    else:
        return f"{amount:.2f} {currency}"


def is_business_hours(dt: Optional[datetime] = None) -> bool:
    """Check if current time or provided datetime is within business hours"""
    if dt is None:
        dt = datetime.now()
    
    # Business hours: Monday-Friday 9:00-18:00, Saturday 9:00-13:00
    weekday = dt.weekday()  # 0 = Monday, 6 = Sunday
    hour = dt.hour
    
    if weekday < 5:  # Monday to Friday
        return 9 <= hour < 18
    elif weekday == 5:  # Saturday
        return 9 <= hour < 13
    else:  # Sunday
        return False


def generate_reference_number(prefix: str = 'WC') -> str:
    """Generate unique reference number for appointments/leads"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return f"{prefix}{timestamp}"