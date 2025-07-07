import os
from typing import Dict, Any, Optional
import logging
from pathlib import Path

class Config:
    """Application configuration management class"""
    
    def __init__(self):
        self.config = {}
        self.load_environment_vars()
        self.validate_api_keys()
        
    def load_environment_vars(self) -> Dict[str, Any]:
        """Import settings from .env file and environment variables"""
        try:
            # Flask Configuration
            self.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'wellness-connect-secret-key-2024')
            self.config['DEBUG'] = os.getenv('DEBUG', 'False').lower() == 'true'
            self.config['HOST'] = os.getenv('HOST', '0.0.0.0')
            self.config['PORT'] = int(os.getenv('PORT', 5000))
            
            # Database Configuration
            self.config['DATABASE_URL'] = self.get_database_url()
            self.config['DATABASE_POOL_SIZE'] = int(os.getenv('DATABASE_POOL_SIZE', 10))
            
            # WhatsApp Business API Configuration
            self.config['WHATSAPP_TOKEN'] = os.getenv('WHATSAPP_TOKEN')
            self.config['WHATSAPP_PHONE_NUMBER_ID'] = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
            self.config['WHATSAPP_WEBHOOK_VERIFY_TOKEN'] = os.getenv('WHATSAPP_WEBHOOK_VERIFY_TOKEN')
            self.config['WHATSAPP_BUSINESS_ACCOUNT_ID'] = os.getenv('WHATSAPP_BUSINESS_ACCOUNT_ID')
            
            # Claude AI Configuration
            self.config['CLAUDE_API_KEY'] = os.getenv('CLAUDE_API_KEY')
            self.config['CLAUDE_MODEL'] = os.getenv('CLAUDE_MODEL', 'claude-3-sonnet-20240229')
            self.config['CLAUDE_MAX_TOKENS'] = int(os.getenv('CLAUDE_MAX_TOKENS', 1000))
            self.config['CLAUDE_TEMPERATURE'] = float(os.getenv('CLAUDE_TEMPERATURE', 0.7))
            
            # Business Configuration
            self.config['BUSINESS_NAME'] = os.getenv('BUSINESS_NAME', 'The Wellness London')
            self.config['BUSINESS_PHONE'] = os.getenv('BUSINESS_PHONE', '+44 20 7123 4567')
            self.config['BUSINESS_EMAIL'] = os.getenv('BUSINESS_EMAIL', 'info@thewellnesslondon.com')
            self.config['BUSINESS_ADDRESS'] = os.getenv('BUSINESS_ADDRESS', 'London, UK')
            
            # Appointment Configuration
            self.config['APPOINTMENT_DURATION'] = int(os.getenv('APPOINTMENT_DURATION', 60))  # minutes
            self.config['BUSINESS_HOURS_START'] = os.getenv('BUSINESS_HOURS_START', '09:00')
            self.config['BUSINESS_HOURS_END'] = os.getenv('BUSINESS_HOURS_END', '18:00')
            self.config['BUSINESS_DAYS'] = os.getenv('BUSINESS_DAYS', 'Monday,Tuesday,Wednesday,Thursday,Friday').split(',')
            
            # Lead Qualification Configuration
            self.config['URGENCY_THRESHOLD_HIGH'] = int(os.getenv('URGENCY_THRESHOLD_HIGH', 80))
            self.config['URGENCY_THRESHOLD_MEDIUM'] = int(os.getenv('URGENCY_THRESHOLD_MEDIUM', 50))
            self.config['AUTO_BOOK_THRESHOLD'] = int(os.getenv('AUTO_BOOK_THRESHOLD', 90))
            
            # Content Management Configuration
            self.config['CONTENT_DELIVERY_ENABLED'] = os.getenv('CONTENT_DELIVERY_ENABLED', 'True').lower() == 'true'
            self.config['FOLLOW_UP_DELAY_HOURS'] = int(os.getenv('FOLLOW_UP_DELAY_HOURS', 24))
            self.config['MAX_FOLLOW_UPS'] = int(os.getenv('MAX_FOLLOW_UPS', 3))
            
            # Security Configuration
            self.config['ENCRYPTION_KEY'] = os.getenv('ENCRYPTION_KEY')
            self.config['SESSION_TIMEOUT'] = int(os.getenv('SESSION_TIMEOUT', 3600))  # seconds
            self.config['MAX_LOGIN_ATTEMPTS'] = int(os.getenv('MAX_LOGIN_ATTEMPTS', 5))
            
            # Logging Configuration
            self.config['LOG_LEVEL'] = os.getenv('LOG_LEVEL', 'INFO')
            self.config['LOG_FILE'] = os.getenv('LOG_FILE', 'logs/wellness_connect.log')
            self.config['LOG_MAX_BYTES'] = int(os.getenv('LOG_MAX_BYTES', 10485760))  # 10MB
            self.config['LOG_BACKUP_COUNT'] = int(os.getenv('LOG_BACKUP_COUNT', 5))
            
            # Rate Limiting Configuration
            self.config['RATE_LIMIT_ENABLED'] = os.getenv('RATE_LIMIT_ENABLED', 'True').lower() == 'true'
            self.config['RATE_LIMIT_PER_MINUTE'] = int(os.getenv('RATE_LIMIT_PER_MINUTE', 60))
            self.config['RATE_LIMIT_PER_HOUR'] = int(os.getenv('RATE_LIMIT_PER_HOUR', 1000))
            
            # Treatment Types Configuration
            self.config['TREATMENT_TYPES'] = {
                'blood_testing': {
                    'name': 'Blood Testing',
                    'duration': 30,
                    'price_range': '£150-£300',
                    'description': 'Comprehensive blood analysis and health screening'
                },
                'prp': {
                    'name': 'PRP Treatment',
                    'duration': 90,
                    'price_range': '£400-£800',
                    'description': 'Platelet-Rich Plasma therapy for regenerative medicine'
                },
                'weight_management': {
                    'name': 'Weight Management',
                    'duration': 60,
                    'price_range': '£200-£500',
                    'description': 'Personalized weight loss and nutrition programs'
                },
                'general_wellness': {
                    'name': 'General Wellness',
                    'duration': 45,
                    'price_range': '£100-£250',
                    'description': 'Overall health assessment and wellness planning'
                }
            }
            
            return self.config
            
        except Exception as e:
            logging.error(f"Error loading environment variables: {str(e)}")
            raise
    
    def validate_api_keys(self) -> bool:
        """Verify required API credentials are present"""
        required_keys = [
            'WHATSAPP_TOKEN',
            'WHATSAPP_PHONE_NUMBER_ID',
            'WHATSAPP_WEBHOOK_VERIFY_TOKEN',
            'CLAUDE_API_KEY'
        ]
        
        missing_keys = []
        for key in required_keys:
            if not self.config.get(key):
                missing_keys.append(key)
        
        if missing_keys:
            error_msg = f"Missing required API keys: {', '.join(missing_keys)}"
            logging.error(error_msg)
            raise ValueError(error_msg)
        
        # Validate API key formats
        if not self.config['CLAUDE_API_KEY'].startswith('sk-'):
            logging.warning("Claude API key format may be incorrect")
        
        if len(self.config['WHATSAPP_TOKEN']) < 50:
            logging.warning("WhatsApp token appears to be too short")
        
        return True
    
    def get_database_url(self) -> str:
        """Return database connection string"""
        db_url = os.getenv('DATABASE_URL')
        if db_url:
            return db_url
        
        # Default to SQLite database in data directory
        base_dir = Path(__file__).parent.parent
        db_path = base_dir / 'data' / 'wellness.db'
        
        # Ensure data directory exists
        db_path.parent.mkdir(exist_ok=True)
        
        return f'sqlite:///{db_path}'
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""
        self.config[key] = value
    
    def get_whatsapp_config(self) -> Dict[str, str]:
        """Get WhatsApp-specific configuration"""
        return {
            'token': self.config['WHATSAPP_TOKEN'],
            'phone_number_id': self.config['WHATSAPP_PHONE_NUMBER_ID'],
            'webhook_verify_token': self.config['WHATSAPP_WEBHOOK_VERIFY_TOKEN'],
            'business_account_id': self.config['WHATSAPP_BUSINESS_ACCOUNT_ID']
        }
    
    def get_claude_config(self) -> Dict[str, Any]:
        """Get Claude AI-specific configuration"""
        return {
            'api_key': self.config['CLAUDE_API_KEY'],
            'model': self.config['CLAUDE_MODEL'],
            'max_tokens': self.config['CLAUDE_MAX_TOKENS'],
            'temperature': self.config['CLAUDE_TEMPERATURE']
        }
    
    def get_business_config(self) -> Dict[str, str]:
        """Get business-specific configuration"""
        return {
            'name': self.config['BUSINESS_NAME'],
            'phone': self.config['BUSINESS_PHONE'],
            'email': self.config['BUSINESS_EMAIL'],
            'address': self.config['BUSINESS_ADDRESS']
        }
    
    def get_appointment_config(self) -> Dict[str, Any]:
        """Get appointment scheduling configuration"""
        return {
            'duration': self.config['APPOINTMENT_DURATION'],
            'hours_start': self.config['BUSINESS_HOURS_START'],
            'hours_end': self.config['BUSINESS_HOURS_END'],
            'business_days': self.config['BUSINESS_DAYS']
        }
    
    def get_treatment_types(self) -> Dict[str, Dict[str, Any]]:
        """Get available treatment types configuration"""
        return self.config['TREATMENT_TYPES']
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return os.getenv('ENVIRONMENT', 'development').lower() == 'production'
    
    def is_debug(self) -> bool:
        """Check if debug mode is enabled"""
        return self.config.get('DEBUG', False)

# Global configuration instance
config = Config()

def load_environment_vars() -> Dict[str, Any]:
    """Load environment variables - wrapper function for backward compatibility"""
    return config.load_environment_vars()

def validate_api_keys() -> bool:
    """Validate API keys - wrapper function for backward compatibility"""
    return config.validate_api_keys()

def get_database_url() -> str:
    """Get database URL - wrapper function for backward compatibility"""
    return config.get_database_url()