import sqlite3
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import json
from contextlib import contextmanager

class DatabaseManager:
    """SQLite database operations handler for WellnessConnect platform"""
    
    def __init__(self, db_path: str = "data/wellness.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._ensure_data_directory()
        self.init_db()
    
    def _ensure_data_directory(self):
        """Ensure the data directory exists"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def init_db(self):
        """Create database tables and schema"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        phone_number TEXT UNIQUE NOT NULL,
                        name TEXT,
                        email TEXT,
                        age INTEGER,
                        gender TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Conversations table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS conversations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        message_type TEXT NOT NULL,
                        message_content TEXT NOT NULL,
                        response_content TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                # Health assessments table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS health_assessments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        assessment_data TEXT NOT NULL,
                        symptoms TEXT,
                        medical_history TEXT,
                        current_medications TEXT,
                        health_goals TEXT,
                        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                # Leads table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS leads (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        qualification_status TEXT DEFAULT 'new',
                        treatment_category TEXT,
                        urgency_score INTEGER DEFAULT 0,
                        qualification_notes TEXT,
                        assigned_staff TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                # Appointments table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS appointments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        lead_id INTEGER,
                        appointment_datetime TIMESTAMP,
                        treatment_type TEXT,
                        status TEXT DEFAULT 'scheduled',
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id),
                        FOREIGN KEY (lead_id) REFERENCES leads (id)
                    )
                ''')
                
                # Content delivery table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS content_delivery (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        content_type TEXT NOT NULL,
                        content_title TEXT,
                        content_body TEXT,
                        delivery_status TEXT DEFAULT 'pending',
                        scheduled_at TIMESTAMP,
                        delivered_at TIMESTAMP,
                        engagement_score INTEGER DEFAULT 0,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                # Follow-up reminders table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS follow_up_reminders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        appointment_id INTEGER,
                        reminder_type TEXT NOT NULL,
                        reminder_content TEXT,
                        scheduled_at TIMESTAMP,
                        sent_at TIMESTAMP,
                        status TEXT DEFAULT 'pending',
                        FOREIGN KEY (user_id) REFERENCES users (id),
                        FOREIGN KEY (appointment_id) REFERENCES appointments (id)
                    )
                ''')
                
                conn.commit()
                self.logger.info("Database initialized successfully")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    def save_conversation(self, phone_number: str, message_type: str, 
                         message_content: str, response_content: str = None) -> bool:
        """Store chat history and user responses"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get or create user
                user_id = self._get_or_create_user(cursor, phone_number)
                
                cursor.execute('''
                    INSERT INTO conversations (user_id, message_type, message_content, response_content)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, message_type, message_content, response_content))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to save conversation: {e}")
            return False
    
    def get_user_profile(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Retrieve user health profile data"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT u.*, ha.assessment_data, ha.symptoms, ha.medical_history,
                           ha.current_medications, ha.health_goals, l.qualification_status,
                           l.treatment_category, l.urgency_score
                    FROM users u
                    LEFT JOIN health_assessments ha ON u.id = ha.user_id
                    LEFT JOIN leads l ON u.id = l.user_id
                    WHERE u.phone_number = ?
                    ORDER BY ha.completed_at DESC, l.updated_at DESC
                    LIMIT 1
                ''', (phone_number,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get user profile: {e}")
            return None
    
    def update_lead_status(self, phone_number: str, status: str, 
                          treatment_category: str = None, urgency_score: int = None,
                          notes: str = None) -> bool:
        """Modify lead qualification status"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                user_id = self._get_or_create_user(cursor, phone_number)
                
                # Check if lead exists
                cursor.execute('SELECT id FROM leads WHERE user_id = ?', (user_id,))
                lead = cursor.fetchone()
                
                if lead:
                    # Update existing lead
                    cursor.execute('''
                        UPDATE leads 
                        SET qualification_status = ?, treatment_category = COALESCE(?, treatment_category),
                            urgency_score = COALESCE(?, urgency_score),
                            qualification_notes = COALESCE(?, qualification_notes),
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ?
                    ''', (status, treatment_category, urgency_score, notes, user_id))
                else:
                    # Create new lead
                    cursor.execute('''
                        INSERT INTO leads (user_id, qualification_status, treatment_category, 
                                         urgency_score, qualification_notes)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (user_id, status, treatment_category, urgency_score, notes))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to update lead status: {e}")
            return False
    
    def save_health_assessment(self, phone_number: str, assessment_data: Dict[str, Any]) -> bool:
        """Save health assessment responses"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                user_id = self._get_or_create_user(cursor, phone_number)
                
                cursor.execute('''
                    INSERT INTO health_assessments 
                    (user_id, assessment_data, symptoms, medical_history, 
                     current_medications, health_goals)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    json.dumps(assessment_data),
                    assessment_data.get('symptoms', ''),
                    assessment_data.get('medical_history', ''),
                    assessment_data.get('current_medications', ''),
                    assessment_data.get('health_goals', '')
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to save health assessment: {e}")
            return False
    
    def get_conversation_history(self, phone_number: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation history for a user"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT c.message_type, c.message_content, c.response_content, c.timestamp
                    FROM conversations c
                    JOIN users u ON c.user_id = u.id
                    WHERE u.phone_number = ?
                    ORDER BY c.timestamp DESC
                    LIMIT ?
                ''', (phone_number, limit))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Failed to get conversation history: {e}")
            return []
    
    def save_appointment(self, phone_number: str, appointment_datetime: datetime,
                        treatment_type: str, notes: str = None) -> Optional[int]:
        """Save appointment booking"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                user_id = self._get_or_create_user(cursor, phone_number)
                
                # Get lead_id if exists
                cursor.execute('SELECT id FROM leads WHERE user_id = ?', (user_id,))
                lead = cursor.fetchone()
                lead_id = lead['id'] if lead else None
                
                cursor.execute('''
                    INSERT INTO appointments 
                    (user_id, lead_id, appointment_datetime, treatment_type, notes)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, lead_id, appointment_datetime, treatment_type, notes))
                
                appointment_id = cursor.lastrowid
                conn.commit()
                return appointment_id
                
        except Exception as e:
            self.logger.error(f"Failed to save appointment: {e}")
            return None
    
    def schedule_content_delivery(self, phone_number: str, content_type: str,
                                 content_title: str, content_body: str,
                                 scheduled_at: datetime = None) -> bool:
        """Schedule content delivery to user"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                user_id = self._get_or_create_user(cursor, phone_number)
                
                cursor.execute('''
                    INSERT INTO content_delivery 
                    (user_id, content_type, content_title, content_body, scheduled_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, content_type, content_title, content_body, scheduled_at))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to schedule content delivery: {e}")
            return False
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get statistics for dashboard display"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Total users
                cursor.execute('SELECT COUNT(*) as count FROM users')
                stats['total_users'] = cursor.fetchone()['count']
                
                # Leads by status
                cursor.execute('''
                    SELECT qualification_status, COUNT(*) as count 
                    FROM leads 
                    GROUP BY qualification_status
                ''')
                stats['leads_by_status'] = {row['qualification_status']: row['count'] 
                                          for row in cursor.fetchall()}
                
                # Appointments by status
                cursor.execute('''
                    SELECT status, COUNT(*) as count 
                    FROM appointments 
                    GROUP BY status
                ''')
                stats['appointments_by_status'] = {row['status']: row['count'] 
                                                 for row in cursor.fetchall()}
                
                # Recent activity
                cursor.execute('''
                    SELECT COUNT(*) as count 
                    FROM conversations 
                    WHERE timestamp >= datetime('now', '-24 hours')
                ''')
                stats['recent_conversations'] = cursor.fetchone()['count']
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Failed to get dashboard stats: {e}")
            return {}
    
    def _get_or_create_user(self, cursor, phone_number: str) -> int:
        """Get existing user or create new one"""
        cursor.execute('SELECT id FROM users WHERE phone_number = ?', (phone_number,))
        user = cursor.fetchone()
        
        if user:
            return user['id']
        else:
            cursor.execute('''
                INSERT INTO users (phone_number) VALUES (?)
            ''', (phone_number,))
            return cursor.lastrowid
    
    def update_user_info(self, phone_number: str, name: str = None, 
                        email: str = None, age: int = None, gender: str = None) -> bool:
        """Update user information"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                user_id = self._get_or_create_user(cursor, phone_number)
                
                cursor.execute('''
                    UPDATE users 
                    SET name = COALESCE(?, name),
                        email = COALESCE(?, email),
                        age = COALESCE(?, age),
                        gender = COALESCE(?, gender),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (name, email, age, gender, user_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to update user info: {e}")
            return False

def init_db():
    """Initialize database - convenience function"""
    db_manager = DatabaseManager()
    return db_manager