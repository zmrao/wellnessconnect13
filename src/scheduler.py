import sqlite3
import datetime
from typing import Dict, List, Optional, Tuple
import json
import logging
from dataclasses import dataclass
from enum import Enum

from .database import DatabaseManager
from .whatsapp_handler import WhatsAppHandler
from .utils import setup_logger, format_datetime

class AppointmentStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    RESCHEDULED = "rescheduled"

@dataclass
class TimeSlot:
    date: str
    time: str
    duration: int
    available: bool
    treatment_type: str

@dataclass
class Appointment:
    id: Optional[int]
    user_id: int
    phone_number: str
    date: str
    time: str
    treatment_type: str
    duration: int
    status: AppointmentStatus
    notes: str
    created_at: str
    updated_at: str

class AppointmentScheduler:
    def __init__(self, db_manager: DatabaseManager, whatsapp_handler: WhatsAppHandler):
        self.db = db_manager
        self.whatsapp = whatsapp_handler
        self.logger = setup_logger(__name__)
        
        # Business hours configuration
        self.business_hours = {
            'monday': {'start': '09:00', 'end': '18:00'},
            'tuesday': {'start': '09:00', 'end': '18:00'},
            'wednesday': {'start': '09:00', 'end': '18:00'},
            'thursday': {'start': '09:00', 'end': '18:00'},
            'friday': {'start': '09:00', 'end': '18:00'},
            'saturday': {'start': '10:00', 'end': '16:00'},
            'sunday': {'start': '10:00', 'end': '16:00'}
        }
        
        # Treatment duration mapping (in minutes)
        self.treatment_durations = {
            'blood_testing': 30,
            'prp_therapy': 60,
            'weight_management': 45,
            'consultation': 30,
            'iv_therapy': 45,
            'wellness_check': 30
        }
        
        self._init_scheduler_tables()

    def _init_scheduler_tables(self):
        """Initialize scheduler-specific database tables"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            # Create appointments table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS appointments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    phone_number TEXT NOT NULL,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    treatment_type TEXT NOT NULL,
                    duration INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Create availability table for custom schedules
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS availability (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    duration INTEGER NOT NULL,
                    available BOOLEAN DEFAULT TRUE,
                    treatment_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            self.logger.info("Scheduler tables initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing scheduler tables: {str(e)}")
            raise

    def check_availability(self, date: str, treatment_type: str = None) -> List[TimeSlot]:
        """Query available appointment slots for a given date"""
        try:
            available_slots = []
            
            # Parse date and get day of week
            appointment_date = datetime.datetime.strptime(date, '%Y-%m-%d')
            day_name = appointment_date.strftime('%A').lower()
            
            # Check if date is in business hours
            if day_name not in self.business_hours:
                return available_slots
            
            business_start = self.business_hours[day_name]['start']
            business_end = self.business_hours[day_name]['end']
            
            # Get treatment duration
            duration = self.treatment_durations.get(treatment_type, 30)
            
            # Generate time slots
            current_time = datetime.datetime.strptime(business_start, '%H:%M')
            end_time = datetime.datetime.strptime(business_end, '%H:%M')
            
            while current_time < end_time:
                slot_time = current_time.strftime('%H:%M')
                
                # Check if slot is available
                if self._is_slot_available(date, slot_time, duration):
                    available_slots.append(TimeSlot(
                        date=date,
                        time=slot_time,
                        duration=duration,
                        available=True,
                        treatment_type=treatment_type or 'consultation'
                    ))
                
                # Move to next slot (30-minute intervals)
                current_time += datetime.timedelta(minutes=30)
            
            self.logger.info(f"Found {len(available_slots)} available slots for {date}")
            return available_slots
            
        except Exception as e:
            self.logger.error(f"Error checking availability: {str(e)}")
            return []

    def _is_slot_available(self, date: str, time: str, duration: int) -> bool:
        """Check if a specific time slot is available"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            # Check for existing appointments that would conflict
            cursor.execute('''
                SELECT COUNT(*) FROM appointments 
                WHERE date = ? AND time = ? AND status NOT IN ('cancelled')
            ''', (date, time))
            
            existing_count = cursor.fetchone()[0]
            conn.close()
            
            return existing_count == 0
            
        except Exception as e:
            self.logger.error(f"Error checking slot availability: {str(e)}")
            return False

    def book_appointment(self, user_id: int, phone_number: str, date: str, 
                        time: str, treatment_type: str, notes: str = "") -> Optional[Appointment]:
        """Reserve time slot for qualified leads"""
        try:
            # Validate inputs
            if not self._validate_booking_data(date, time, treatment_type):
                return None
            
            # Check availability one more time
            duration = self.treatment_durations.get(treatment_type, 30)
            if not self._is_slot_available(date, time, duration):
                self.logger.warning(f"Slot {date} {time} no longer available")
                return None
            
            # Create appointment
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO appointments 
                (user_id, phone_number, date, time, treatment_type, duration, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, phone_number, date, time, treatment_type, duration, 
                  AppointmentStatus.PENDING.value, notes))
            
            appointment_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # Create appointment object
            appointment = Appointment(
                id=appointment_id,
                user_id=user_id,
                phone_number=phone_number,
                date=date,
                time=time,
                treatment_type=treatment_type,
                duration=duration,
                status=AppointmentStatus.PENDING,
                notes=notes,
                created_at=datetime.datetime.now().isoformat(),
                updated_at=datetime.datetime.now().isoformat()
            )
            
            # Send confirmation
            self.send_confirmation(appointment)
            
            self.logger.info(f"Appointment booked successfully: ID {appointment_id}")
            return appointment
            
        except Exception as e:
            self.logger.error(f"Error booking appointment: {str(e)}")
            return None

    def _validate_booking_data(self, date: str, time: str, treatment_type: str) -> bool:
        """Validate appointment booking data"""
        try:
            # Validate date format
            datetime.datetime.strptime(date, '%Y-%m-%d')
            
            # Validate time format
            datetime.datetime.strptime(time, '%H:%M')
            
            # Validate treatment type
            if treatment_type not in self.treatment_durations:
                return False
            
            # Check if date is not in the past
            appointment_date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
            if appointment_date < datetime.date.today():
                return False
            
            return True
            
        except ValueError:
            return False

    def send_confirmation(self, appointment: Appointment) -> bool:
        """Deliver booking details via WhatsApp"""
        try:
            # Format appointment details
            formatted_date = format_datetime(f"{appointment.date} {appointment.time}")
            treatment_name = appointment.treatment_type.replace('_', ' ').title()
            
            confirmation_message = f"""
🏥 *Appointment Confirmation*

Hello! Your appointment has been scheduled:

📅 *Date:* {formatted_date}
⏰ *Duration:* {appointment.duration} minutes
🩺 *Treatment:* {treatment_name}
📋 *Booking ID:* #{appointment.id}

📍 *Location:* The Wellness London
📞 *Contact:* Reply to this message for any changes

*Important Notes:*
• Please arrive 10 minutes early
• Bring a valid ID
• Cancel at least 24 hours in advance if needed

We look forward to seeing you! 🌟
            """.strip()
            
            # Send confirmation message
            success = self.whatsapp.send_message(appointment.phone_number, confirmation_message)
            
            if success:
                self.logger.info(f"Confirmation sent for appointment {appointment.id}")
                return True
            else:
                self.logger.error(f"Failed to send confirmation for appointment {appointment.id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending confirmation: {str(e)}")
            return False

    def handle_reschedule(self, appointment_id: int, new_date: str, new_time: str) -> bool:
        """Process appointment changes"""
        try:
            # Get existing appointment
            appointment = self.get_appointment(appointment_id)
            if not appointment:
                return False
            
            # Validate new slot
            if not self._validate_booking_data(new_date, new_time, appointment.treatment_type):
                return False
            
            # Check availability of new slot
            if not self._is_slot_available(new_date, new_time, appointment.duration):
                return False
            
            # Update appointment
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE appointments 
                SET date = ?, time = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_date, new_time, AppointmentStatus.RESCHEDULED.value, appointment_id))
            
            conn.commit()
            conn.close()
            
            # Send reschedule confirmation
            updated_appointment = self.get_appointment(appointment_id)
            if updated_appointment:
                self._send_reschedule_confirmation(updated_appointment)
            
            self.logger.info(f"Appointment {appointment_id} rescheduled successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error rescheduling appointment: {str(e)}")
            return False

    def _send_reschedule_confirmation(self, appointment: Appointment):
        """Send reschedule confirmation message"""
        try:
            formatted_date = format_datetime(f"{appointment.date} {appointment.time}")
            treatment_name = appointment.treatment_type.replace('_', ' ').title()
            
            message = f"""
🔄 *Appointment Rescheduled*

Your appointment has been successfully rescheduled:

📅 *New Date:* {formatted_date}
🩺 *Treatment:* {treatment_name}
📋 *Booking ID:* #{appointment.id}

Thank you for letting us know! See you soon. 🌟
            """.strip()
            
            self.whatsapp.send_message(appointment.phone_number, message)
            
        except Exception as e:
            self.logger.error(f"Error sending reschedule confirmation: {str(e)}")

    def get_appointment(self, appointment_id: int) -> Optional[Appointment]:
        """Get appointment by ID"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, user_id, phone_number, date, time, treatment_type, 
                       duration, status, notes, created_at, updated_at
                FROM appointments WHERE id = ?
            ''', (appointment_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return Appointment(
                    id=row[0],
                    user_id=row[1],
                    phone_number=row[2],
                    date=row[3],
                    time=row[4],
                    treatment_type=row[5],
                    duration=row[6],
                    status=AppointmentStatus(row[7]),
                    notes=row[8] or "",
                    created_at=row[9],
                    updated_at=row[10]
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting appointment: {str(e)}")
            return None

    def get_user_appointments(self, user_id: int) -> List[Appointment]:
        """Get all appointments for a user"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, user_id, phone_number, date, time, treatment_type, 
                       duration, status, notes, created_at, updated_at
                FROM appointments WHERE user_id = ?
                ORDER BY date DESC, time DESC
            ''', (user_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            appointments = []
            for row in rows:
                appointments.append(Appointment(
                    id=row[0],
                    user_id=row[1],
                    phone_number=row[2],
                    date=row[3],
                    time=row[4],
                    treatment_type=row[5],
                    duration=row[6],
                    status=AppointmentStatus(row[7]),
                    notes=row[8] or "",
                    created_at=row[9],
                    updated_at=row[10]
                ))
            
            return appointments
            
        except Exception as e:
            self.logger.error(f"Error getting user appointments: {str(e)}")
            return []

    def cancel_appointment(self, appointment_id: int, reason: str = "") -> bool:
        """Cancel an appointment"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE appointments 
                SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (AppointmentStatus.CANCELLED.value, reason, appointment_id))
            
            conn.commit()
            conn.close()
            
            # Send cancellation confirmation
            appointment = self.get_appointment(appointment_id)
            if appointment:
                self._send_cancellation_confirmation(appointment)
            
            self.logger.info(f"Appointment {appointment_id} cancelled")
            return True
            
        except Exception as e:
            self.logger.error(f"Error cancelling appointment: {str(e)}")
            return False

    def _send_cancellation_confirmation(self, appointment: Appointment):
        """Send cancellation confirmation message"""
        try:
            message = f"""
❌ *Appointment Cancelled*

Your appointment has been cancelled:

📋 *Booking ID:* #{appointment.id}
📅 *Date:* {appointment.date} {appointment.time}

If you'd like to reschedule, please let us know!
            """.strip()
            
            self.whatsapp.send_message(appointment.phone_number, message)
            
        except Exception as e:
            self.logger.error(f"Error sending cancellation confirmation: {str(e)}")

    def get_daily_schedule(self, date: str) -> List[Appointment]:
        """Get all appointments for a specific date"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, user_id, phone_number, date, time, treatment_type, 
                       duration, status, notes, created_at, updated_at
                FROM appointments 
                WHERE date = ? AND status NOT IN ('cancelled')
                ORDER BY time ASC
            ''', (date,))
            
            rows = cursor.fetchall()
            conn.close()
            
            appointments = []
            for row in rows:
                appointments.append(Appointment(
                    id=row[0],
                    user_id=row[1],
                    phone_number=row[2],
                    date=row[3],
                    time=row[4],
                    treatment_type=row[5],
                    duration=row[6],
                    status=AppointmentStatus(row[7]),
                    notes=row[8] or "",
                    created_at=row[9],
                    updated_at=row[10]
                ))
            
            return appointments
            
        except Exception as e:
            self.logger.error(f"Error getting daily schedule: {str(e)}")
            return []

    def send_appointment_reminders(self):
        """Send reminders for upcoming appointments"""
        try:
            # Get appointments for tomorrow
            tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
            appointments = self.get_daily_schedule(tomorrow)
            
            for appointment in appointments:
                if appointment.status == AppointmentStatus.CONFIRMED:
                    self._send_reminder(appointment)
            
            self.logger.info(f"Sent reminders for {len(appointments)} appointments")
            
        except Exception as e:
            self.logger.error(f"Error sending appointment reminders: {str(e)}")

    def _send_reminder(self, appointment: Appointment):
        """Send individual appointment reminder"""
        try:
            formatted_date = format_datetime(f"{appointment.date} {appointment.time}")
            treatment_name = appointment.treatment_type.replace('_', ' ').title()
            
            reminder_message = f"""
⏰ *Appointment Reminder*

This is a friendly reminder about your appointment tomorrow:

📅 *Date:* {formatted_date}
🩺 *Treatment:* {treatment_name}
📋 *Booking ID:* #{appointment.id}

Please remember to:
• Arrive 10 minutes early
• Bring a valid ID
• Reply if you need to reschedule

Looking forward to seeing you! 🌟
            """.strip()
            
            self.whatsapp.send_message(appointment.phone_number, reminder_message)
            
        except Exception as e:
            self.logger.error(f"Error sending reminder: {str(e)}")