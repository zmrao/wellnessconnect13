# WellnessConnect - AI-Powered Health Concierge Platform

A WhatsApp-based AI health concierge that pre-qualifies leads, schedules appointments, and provides personalized wellness recommendations for The Wellness London.

## Overview

WellnessConnect streamlines the client acquisition and care process by automating initial health assessments, lead qualification, appointment scheduling, and follow-up care through WhatsApp integration with Claude AI.

## Features

- **AI Chatbot Integration**: WhatsApp Business API with Claude AI for natural health conversations
- **Smart Lead Qualification**: Automatic categorization by treatment type (blood testing, PRP, weight management) and urgency
- **Personalized Content Delivery**: Targeted wellness content based on individual health profiles
- **Automated Scheduling**: Seamless appointment booking for qualified leads
- **Follow-up Care**: Post-treatment reminders and wellness plan delivery
- **Analytics Dashboard**: Real-time insights into lead conversion and engagement metrics

## Technology Stack

- **Backend**: Flask (Python)
- **AI Engine**: Claude API (Anthropic)
- **Database**: SQLite
- **Frontend**: HTML/CSS/JavaScript
- **Messaging**: WhatsApp Business API
- **Deployment**: Python 3.8+

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd wellnessconnect
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   
   Copy `.env.example` to `.env` and configure:
   ```
   CLAUDE_API_KEY=your_claude_api_key
   WHATSAPP_TOKEN=your_whatsapp_business_token
   WHATSAPP_PHONE_ID=your_phone_number_id
   WHATSAPP_VERIFY_TOKEN=your_webhook_verify_token
   FLASK_SECRET_KEY=your_secret_key
   DATABASE_URL=sqlite:///data/wellness.db
   ```

5. **Initialize Database**
   ```bash
   python -c "from src.database import DatabaseManager; DatabaseManager().init_db()"
   ```

## Quick Start

1. **Start the application**
   ```bash
   python main.py
   ```

2. **Access the dashboard**
   - Open browser to `http://localhost:5000`
   - Monitor leads, appointments, and analytics

3. **Configure WhatsApp Webhook**
   - Set webhook URL to `https://your-domain.com/webhook`
   - Verify token matches your `.env` configuration

## API Endpoints

### WhatsApp Integration
- `POST /webhook` - Receive WhatsApp messages
- `GET /webhook` - Webhook verification

### Dashboard
- `GET /` - Main dashboard interface
- `GET /api/leads` - Lead qualification data
- `GET /api/appointments` - Appointment statistics
- `GET /api/analytics` - Engagement metrics

## Project Structure

```
wellnessconnect/
├── main.py                 # Flask application entry point
├── requirements.txt        # Python dependencies
├── .env                   # Environment variables
├── .gitignore            # Git ignore rules
├── src/
│   ├── whatsapp_handler.py    # WhatsApp Business API integration
│   ├── ai_assistant.py        # Claude AI conversation management
│   ├── database.py           # SQLite database operations
│   ├── lead_qualifier.py     # Lead scoring and categorization
│   ├── scheduler.py          # Appointment booking system
│   ├── content_manager.py    # Personalized content delivery
│   └── utils.py              # Utility functions and helpers
├── static/
│   ├── css/style.css         # Dashboard styling
│   └── js/main.js           # Frontend functionality
├── templates/
│   ├── index.html           # Landing page
│   └── dashboard.html       # Analytics dashboard
├── data/
│   └── wellness.db          # SQLite database file
└── config/
    └── settings.py          # Application configuration
```

## Core Components

### AI Assistant
- Conducts initial health assessments
- Provides personalized wellness recommendations
- Maintains conversation context and history
- Integrates with Claude API for natural language processing

### Lead Qualification
- Analyzes health assessment responses
- Categorizes by treatment type and urgency
- Generates qualification scores for staff review
- Automates follow-up scheduling

### WhatsApp Integration
- Handles incoming/outgoing messages
- Validates webhook security
- Manages conversation flow
- Delivers appointment confirmations and reminders

### Content Management
- Delivers targeted wellness content
- Schedules post-treatment care messages
- Tracks engagement metrics
- Personalizes recommendations based on user profiles

## Database Schema

### Users Table
- `id` - Primary key
- `phone_number` - WhatsApp contact
- `name` - Client name
- `created_at` - Registration timestamp
- `profile_data` - JSON health profile

### Conversations Table
- `id` - Primary key
- `user_id` - Foreign key to users
- `message` - Message content
- `sender` - User or AI
- `timestamp` - Message time

### Leads Table
- `id` - Primary key
- `user_id` - Foreign key to users
- `treatment_type` - Categorized treatment
- `urgency_score` - Priority rating
- `status` - Qualification status
- `qualified_at` - Qualification timestamp

### Appointments Table
- `id` - Primary key
- `user_id` - Foreign key to users
- `appointment_time` - Scheduled time
- `treatment_type` - Booked service
- `status` - Booking status
- `created_at` - Booking timestamp

## Configuration

### WhatsApp Business Setup
1. Create WhatsApp Business account
2. Generate access token and phone number ID
3. Configure webhook URL and verify token
4. Add required permissions for messaging

### Claude API Setup
1. Create Anthropic account
2. Generate API key
3. Configure rate limits and usage monitoring
4. Test API connectivity

## Usage Examples

### Health Assessment Flow
1. User messages WhatsApp number
2. AI conducts initial health questionnaire
3. System qualifies lead and categorizes treatment
4. Qualified leads receive appointment booking options
5. Confirmations and follow-ups sent automatically

### Dashboard Monitoring
- View real-time lead qualification metrics
- Track appointment booking conversion rates
- Monitor AI conversation quality
- Export analytics reports

## Deployment

### Production Setup
1. Configure production environment variables
2. Set up SSL certificates for webhook security
3. Configure database backups
4. Set up monitoring and logging
5. Deploy to cloud platform (Heroku, AWS, etc.)

### Environment Variables
```bash
FLASK_ENV=production
CLAUDE_API_KEY=prod_key
WHATSAPP_TOKEN=prod_token
DATABASE_URL=production_db_url
```

## Security Considerations

- All health data encrypted at rest
- WhatsApp webhook validation implemented
- API rate limiting configured
- Sensitive data sanitization
- GDPR compliance measures

## Monitoring & Analytics

- Lead qualification success rates
- Appointment booking conversion
- AI conversation quality metrics
- User engagement tracking
- Treatment type distribution

## Support & Maintenance

### Logging
- Application logs stored in `logs/` directory
- Error tracking and alerting configured
- Performance monitoring enabled

### Database Maintenance
- Regular backup scheduling
- Data retention policies
- Performance optimization

## Contributing

1. Fork the repository
2. Create feature branch
3. Implement changes with tests
4. Submit pull request with documentation

## License

Proprietary software for The Wellness London. All rights reserved.

## Contact

For technical support or feature requests, contact the development team.

---

**Version**: 1.0.0  
**Last Updated**: 2024  
**Maintained by**: WellnessConnect Development Team