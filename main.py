from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
import os
import logging
from datetime import datetime
from src.whatsapp_handler import WhatsAppHandler
from src.ai_assistant import AIAssistant
from src.database import DatabaseManager
from src.lead_qualifier import LeadQualifier
from src.scheduler import AppointmentScheduler
from src.content_manager import ContentManager
from src.utils import setup_logger, validate_phone_number
from config.settings import Config

class WellnessConnectApp:
    """Main Flask application class for WellnessConnect AI Health Concierge Platform"""
    
    def __init__(self):
        self.app = None
        self.config = Config()
        self.db_manager = DatabaseManager()
        self.whatsapp_handler = WhatsAppHandler()
        self.ai_assistant = AIAssistant()
        self.lead_qualifier = LeadQualifier()
        self.scheduler = AppointmentScheduler()
        self.content_manager = ContentManager()
        self.logger = setup_logger('wellness_connect')
        
    def create_app(self):
        """Initialize Flask app with routes and configurations"""
        self.app = Flask(__name__)
        self.app.config.from_object(self.config)
        
        # Initialize database
        with self.app.app_context():
            self.db_manager.init_db()
        
        # Register routes
        self._register_routes()
        
        # Setup error handlers
        self._setup_error_handlers()
        
        return self.app
    
    def _register_routes(self):
        """Register all application routes"""
        
        @self.app.route('/')
        def index():
            """Main dashboard page"""
            try:
                # Get dashboard statistics
                total_leads = self.db_manager.get_total_leads()
                qualified_leads = self.db_manager.get_qualified_leads_count()
                pending_appointments = self.db_manager.get_pending_appointments_count()
                active_conversations = self.db_manager.get_active_conversations_count()
                
                stats = {
                    'total_leads': total_leads,
                    'qualified_leads': qualified_leads,
                    'pending_appointments': pending_appointments,
                    'active_conversations': active_conversations
                }
                
                return render_template('index.html', stats=stats)
            except Exception as e:
                self.logger.error(f"Error loading dashboard: {str(e)}")
                flash('Error loading dashboard data', 'error')
                return render_template('index.html', stats={})
        
        @self.app.route('/dashboard')
        def dashboard():
            """Detailed dashboard with lead management"""
            try:
                leads = self.db_manager.get_recent_leads(limit=50)
                appointments = self.db_manager.get_upcoming_appointments()
                
                return render_template('dashboard.html', 
                                     leads=leads, 
                                     appointments=appointments)
            except Exception as e:
                self.logger.error(f"Error loading dashboard: {str(e)}")
                flash('Error loading dashboard data', 'error')
                return render_template('dashboard.html', leads=[], appointments=[])
        
        @self.app.route('/webhook', methods=['GET', 'POST'])
        def webhook():
            """WhatsApp webhook endpoint"""
            if request.method == 'GET':
                # Webhook verification
                return self.whatsapp_handler.validate_webhook(request)
            
            elif request.method == 'POST':
                # Handle incoming messages
                try:
                    data = request.get_json()
                    self.logger.info(f"Received webhook data: {data}")
                    
                    # Process incoming message
                    response = self._process_incoming_message(data)
                    
                    return jsonify({'status': 'success', 'response': response})
                    
                except Exception as e:
                    self.logger.error(f"Error processing webhook: {str(e)}")
                    return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/leads', methods=['GET'])
        def get_leads():
            """API endpoint to get leads data"""
            try:
                page = request.args.get('page', 1, type=int)
                per_page = request.args.get('per_page', 20, type=int)
                status = request.args.get('status', None)
                
                leads = self.db_manager.get_leads_paginated(page, per_page, status)
                
                return jsonify({
                    'status': 'success',
                    'leads': leads,
                    'total': len(leads)
                })
                
            except Exception as e:
                self.logger.error(f"Error fetching leads: {str(e)}")
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/leads/<int:lead_id>/qualify', methods=['POST'])
        def qualify_lead(lead_id):
            """API endpoint to manually qualify a lead"""
            try:
                data = request.get_json()
                qualification_status = data.get('status', 'qualified')
                notes = data.get('notes', '')
                
                # Update lead qualification
                self.db_manager.update_lead_status(lead_id, qualification_status, notes)
                
                # If qualified, trigger follow-up actions
                if qualification_status == 'qualified':
                    lead_data = self.db_manager.get_lead_by_id(lead_id)
                    if lead_data:
                        self._trigger_qualified_lead_actions(lead_data)
                
                return jsonify({'status': 'success', 'message': 'Lead updated successfully'})
                
            except Exception as e:
                self.logger.error(f"Error qualifying lead: {str(e)}")
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/appointments', methods=['GET', 'POST'])
        def appointments():
            """API endpoint for appointment management"""
            if request.method == 'GET':
                try:
                    appointments = self.db_manager.get_all_appointments()
                    return jsonify({
                        'status': 'success',
                        'appointments': appointments
                    })
                except Exception as e:
                    self.logger.error(f"Error fetching appointments: {str(e)}")
                    return jsonify({'status': 'error', 'message': str(e)}), 500
            
            elif request.method == 'POST':
                try:
                    data = request.get_json()
                    appointment_id = self.scheduler.book_appointment(
                        lead_id=data.get('lead_id'),
                        datetime_slot=data.get('datetime'),
                        treatment_type=data.get('treatment_type'),
                        notes=data.get('notes', '')
                    )
                    
                    return jsonify({
                        'status': 'success',
                        'appointment_id': appointment_id,
                        'message': 'Appointment booked successfully'
                    })
                    
                except Exception as e:
                    self.logger.error(f"Error booking appointment: {str(e)}")
                    return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/send-content', methods=['POST'])
        def send_content():
            """API endpoint to send targeted content to leads"""
            try:
                data = request.get_json()
                lead_id = data.get('lead_id')
                content_type = data.get('content_type')
                
                lead_data = self.db_manager.get_lead_by_id(lead_id)
                if not lead_data:
                    return jsonify({'status': 'error', 'message': 'Lead not found'}), 404
                
                # Send targeted content
                success = self.content_manager.send_targeted_content(
                    phone_number=lead_data['phone_number'],
                    content_type=content_type,
                    user_profile=lead_data
                )
                
                if success:
                    return jsonify({'status': 'success', 'message': 'Content sent successfully'})
                else:
                    return jsonify({'status': 'error', 'message': 'Failed to send content'}), 500
                    
            except Exception as e:
                self.logger.error(f"Error sending content: {str(e)}")
                return jsonify({'status': 'error', 'message': str(e)}), 500
    
    def _process_incoming_message(self, webhook_data):
        """Process incoming WhatsApp message and generate response"""
        try:
            # Extract message data
            if 'entry' not in webhook_data:
                return None
            
            for entry in webhook_data['entry']:
                for change in entry.get('changes', []):
                    if change.get('field') == 'messages':
                        value = change.get('value', {})
                        messages = value.get('messages', [])
                        
                        for message in messages:
                            phone_number = message.get('from')
                            message_text = message.get('text', {}).get('body', '')
                            message_id = message.get('id')
                            
                            if not validate_phone_number(phone_number):
                                self.logger.warning(f"Invalid phone number: {phone_number}")
                                continue
                            
                            # Get or create user profile
                            user_profile = self.db_manager.get_user_profile(phone_number)
                            if not user_profile:
                                user_profile = self.db_manager.create_user_profile(phone_number)
                            
                            # Save incoming message
                            self.db_manager.save_conversation(
                                phone_number, message_text, 'user', message_id
                            )
                            
                            # Generate AI response
                            conversation_history = self.db_manager.get_conversation_history(phone_number)
                            ai_response = self.ai_assistant.generate_response(
                                message_text, conversation_history, user_profile
                            )
                            
                            # Send response via WhatsApp
                            if ai_response:
                                success = self.whatsapp_handler.send_message(phone_number, ai_response)
                                
                                if success:
                                    # Save AI response
                                    self.db_manager.save_conversation(
                                        phone_number, ai_response, 'assistant'
                                    )
                                    
                                    # Check if health assessment is complete
                                    self._check_assessment_completion(phone_number, user_profile)
                            
                            return ai_response
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error processing incoming message: {str(e)}")
            return None
    
    def _check_assessment_completion(self, phone_number, user_profile):
        """Check if health assessment is complete and trigger qualification"""
        try:
            conversation_history = self.db_manager.get_conversation_history(phone_number)
            
            # Check if assessment is complete
            if self.ai_assistant.is_assessment_complete(conversation_history):
                # Qualify the lead
                qualification_result = self.lead_qualifier.analyze_responses(
                    conversation_history, user_profile
                )
                
                # Update lead status
                lead_id = self.db_manager.get_lead_id_by_phone(phone_number)
                if lead_id:
                    self.db_manager.update_lead_qualification(lead_id, qualification_result)
                    
                    # Trigger follow-up actions for qualified leads
                    if qualification_result.get('status') == 'qualified':
                        self._trigger_qualified_lead_actions(user_profile)
                
        except Exception as e:
            self.logger.error(f"Error checking assessment completion: {str(e)}")
    
    def _trigger_qualified_lead_actions(self, lead_data):
        """Trigger actions for qualified leads"""
        try:
            phone_number = lead_data.get('phone_number')
            treatment_type = lead_data.get('recommended_treatment')
            
            # Send personalized content
            self.content_manager.send_targeted_content(
                phone_number, 'treatment_info', lead_data
            )
            
            # Schedule follow-up
            self.content_manager.schedule_follow_up(
                phone_number, treatment_type, days_delay=1
            )
            
            # Check availability and suggest appointments
            available_slots = self.scheduler.check_availability(treatment_type)
            if available_slots:
                appointment_message = self.scheduler.format_availability_message(available_slots)
                self.whatsapp_handler.send_message(phone_number, appointment_message)
            
        except Exception as e:
            self.logger.error(f"Error triggering qualified lead actions: {str(e)}")
    
    def _setup_error_handlers(self):
        """Setup application error handlers"""
        
        @self.app.errorhandler(404)
        def not_found(error):
            return render_template('index.html'), 404
        
        @self.app.errorhandler(500)
        def internal_error(error):
            self.logger.error(f"Internal server error: {str(error)}")
            return render_template('index.html'), 500
        
        @self.app.errorhandler(Exception)
        def handle_exception(e):
            self.logger.error(f"Unhandled exception: {str(e)}")
            return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

def create_app():
    """Initialize Flask app with routes and configurations"""
    wellness_app = WellnessConnectApp()
    return wellness_app.create_app()

def run_app():
    """Start the Flask development server"""
    app = create_app()
    
    # Get configuration
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Setup logging
    if not debug:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(levelname)s %(name)s %(message)s'
        )
    
    print(f"Starting WellnessConnect AI Health Concierge Platform...")
    print(f"Server running on http://{host}:{port}")
    print(f"Debug mode: {debug}")
    
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    run_app()