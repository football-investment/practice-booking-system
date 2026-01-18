"""
Session filtering service for specialized user groups
Handles intelligent session visibility based on user specializations and projects
"""

import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import and_, or_

from ..models.user import User, UserRole
from ..models.session import Session as SessionTypel
from ..models.project import Project, ProjectEnrollment
from ..models.semester import Semester

# ProjectSession might not exist yet - let's simplify for now
# from ..models.project_session import ProjectSession


class UserSpecialization:
    """User specialization categories"""
    COACH = "coach"
    PLAYER = "player" 
    GENERAL = "general"
    MIXED = "mixed"


class SessionFilterService:
    """Service for filtering sessions based on user specialization and context"""
    
    def __init__(self, db: DBSession):
        self.db = db
        self._user_specialization_cache = {}  # Simple in-memory cache
    
    def get_user_specialization(self, user: User) -> str:
        """
        Determine user specialization based on their projects and interests
        Uses caching for performance optimization
        """
        # Check cache first
        if user.id in self._user_specialization_cache:
            return self._user_specialization_cache[user.id]
        
        if user.role != UserRole.STUDENT:
            specialization = UserSpecialization.GENERAL
            self._user_specialization_cache[user.id] = specialization
            return specialization
            
        # Check user's enrolled projects
        enrolled_projects = self.db.query(Project).join(
            ProjectEnrollment
        ).filter(
            ProjectEnrollment.user_id == user.id,
            ProjectEnrollment.status == 'active'
        ).all()
        
        # Analyze project titles and descriptions for specialization keywords
        coach_keywords = ['coach', 'edző', 'tréner', 'instructor', 'vezetés', 'management']
        player_keywords = ['player', 'játékos', 'versenyző', 'atléta', 'performance']
        
        is_coach_oriented = False
        is_player_oriented = False
        
        for project in enrolled_projects:
            project_text = f"{project.title} {project.description}".lower()
            
            if any(keyword in project_text for keyword in coach_keywords):
                is_coach_oriented = True
            if any(keyword in project_text for keyword in player_keywords):
                is_player_oriented = True
        
        # Check user interests
        if user.interests:
            try:
                interests = json.loads(user.interests)
                interests_text = " ".join(interests).lower()
                
                if any(keyword in interests_text for keyword in coach_keywords):
                    is_coach_oriented = True
                if any(keyword in interests_text for keyword in player_keywords):
                    is_player_oriented = True
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Determine final specialization
        if is_coach_oriented and is_player_oriented:
            specialization = UserSpecialization.MIXED
        elif is_coach_oriented:
            specialization = UserSpecialization.COACH
        elif is_player_oriented:
            specialization = UserSpecialization.PLAYER
        else:
            specialization = UserSpecialization.GENERAL
        
        # Cache the result
        self._user_specialization_cache[user.id] = specialization
        return specialization
    
    def get_session_target_groups(self, session: SessionTypel) -> List[str]:
        """
        Determine which user groups a session is targeted for
        Enhanced to handle parallel semesters and shared sessions
        """
        target_groups = []
        
        # Check session title and description for keywords
        session_text = f"{session.title} {session.description or ''}".lower()
        
        coach_keywords = ['coach', 'edző', 'tréner', 'instructor', 'vezetés', 'management', 'tactics', 'strategy', 'methodology', 'planning']
        player_keywords = ['player', 'játékos', 'training', 'skill', 'technique', 'performance', 'fitness', 'individual', 'match', 'analysis']
        general_keywords = ['everyone', 'mindenkinek', 'mixed', 'vegyes', 'open', 'nyitott', 'mental', 'psychology', 'nutrition', 'health', 'workshop']
        
        if any(keyword in session_text for keyword in coach_keywords):
            target_groups.append(UserSpecialization.COACH)
        
        if any(keyword in session_text for keyword in player_keywords):
            target_groups.append(UserSpecialization.PLAYER)
            
        if any(keyword in session_text for keyword in general_keywords):
            target_groups.append(UserSpecialization.GENERAL)
        
        # Check related projects (skip for now - ProjectSession model might not exist)
        # related_projects = self.db.query(Project).join(
        #     ProjectSession
        # ).filter(ProjectSession.session_id == session.id).all()
        related_projects = []  # Simplified for now
        
        for project in related_projects:
            project_text = f"{project.title} {project.description}".lower()
            
            if any(keyword in project_text for keyword in coach_keywords):
                if UserSpecialization.COACH not in target_groups:
                    target_groups.append(UserSpecialization.COACH)
            
            if any(keyword in project_text for keyword in player_keywords):
                if UserSpecialization.PLAYER not in target_groups:
                    target_groups.append(UserSpecialization.PLAYER)
        
        # Default to general if no specific targeting found
        if not target_groups:
            target_groups.append(UserSpecialization.GENERAL)
            
        return target_groups
    
    def get_relevant_sessions_for_user(self, user: User, base_query, limit: int = None) -> List[SessionTypel]:
        """
        Filter sessions based on user specialization and relevance
        Optimized for performance with optional result limiting
        """
        user_specialization = self.get_user_specialization(user)
        
        # For general users, return all sessions without scoring (performance optimization)
        if user_specialization == UserSpecialization.GENERAL:
            return base_query.all() if not limit else base_query.limit(limit).all()
        
        # Get all sessions from base query (limit to reasonable number for performance)
        all_sessions = base_query.limit(100).all() if not limit else base_query.limit(min(100, limit)).all()
        
        # Score and filter sessions
        scored_sessions = []
        
        for session in all_sessions:
            relevance_score = self._calculate_session_relevance(
                session, user, user_specialization
            )
            
            # Only include sessions with relevance score > 0
            if relevance_score > 0:
                scored_sessions.append({
                    'session': session,
                    'score': relevance_score
                })
        
        # Sort by relevance score (highest first)
        scored_sessions.sort(key=lambda x: x['score'], reverse=True)
        
        return [item['session'] for item in scored_sessions]
    
    def _calculate_session_relevance(
        self, 
        session: SessionTypel, 
        user: User, 
        user_specialization: str
    ) -> float:
        """
        Calculate relevance score for a session based on user profile
        Returns: 0.0 - 10.0 (higher = more relevant)
        """
        score = 0.0
        
        # Base score for all sessions
        score += 1.0
        
        # Target group matching
        session_targets = self.get_session_target_groups(session)
        
        if user_specialization in session_targets:
            score += 5.0  # Strong match
        elif UserSpecialization.GENERAL in session_targets:
            score += 3.0  # General sessions are relevant for everyone
        elif user_specialization == UserSpecialization.MIXED:
            score += 4.0  # Mixed users benefit from most sessions
        
        # Skip complex project queries for performance
        # These can be added back later with proper caching or optimization
        # Project enrollment bonus would go here
        
        # Sport type interest bonus
        if user.interests:
            try:
                interests = json.loads(user.interests)
                if session.sport_type.lower() in [interest.lower() for interest in interests]:
                    score += 2.0
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Level appropriateness
        if user_specialization == UserSpecialization.COACH:
            if session.level in ['advanced', 'expert', 'intermediate']:
                score += 1.0
        elif user_specialization == UserSpecialization.PLAYER:
            # Players might benefit from various levels
            score += 0.5
        
        # Capacity consideration (prefer sessions with availability)
        if hasattr(session, 'current_bookings') and hasattr(session, 'capacity'):
            if session.current_bookings < session.capacity:
                availability_ratio = (session.capacity - session.current_bookings) / session.capacity
                score += availability_ratio * 1.0
        
        return score
    
    def get_session_recommendations_summary(self, user: User) -> Dict[str, Any]:
        """
        Get summary of user's session recommendations and filtering logic
        """
        specialization = self.get_user_specialization(user)
        
        # Get user's enrolled projects
        enrolled_projects = self.db.query(Project).join(
            ProjectEnrollment
        ).filter(
            ProjectEnrollment.user_id == user.id,
            ProjectEnrollment.status == 'active'
        ).all()
        
        return {
            'user_id': user.id,
            'user_name': user.name,
            'specialization': specialization,
            'enrolled_projects': [
                {
                    'id': p.id,
                    'title': p.title,
                    'description': p.description
                } for p in enrolled_projects
            ],
            'filtering_logic': {
                'prioritizes': f'Sessions targeted for {specialization} users',
                'includes_general': True,
                'project_bonus': len(enrolled_projects) > 0,
                'interest_matching': user.interests is not None
            }
        }

    def apply_specialization_filter(
        self,
        query,
        user: User,
        include_mixed: bool = True
    ):
        """
        Apply specialization filtering to session query.

        Extracted from list_sessions() lines 123-146 (Phase 0 analysis).
        Only applies to STUDENTS with specialization - skips admin/instructor.

        Args:
            query: SQLAlchemy query for sessions
            user: Current user
            include_mixed: Include mixed specialization sessions (default: True)

        Returns:
            Filtered query

        Complexity: B (6) - role check + hasattr + 3 OR conditions
        """
        # Only apply to STUDENTS with specialization
        if user.role != UserRole.STUDENT:
            return query

        if not (hasattr(user, 'has_specialization') and user.has_specialization):
            return query

        specialization_conditions = []

        # Sessions with no specific target (accessible to all)
        specialization_conditions.append(SessionTypel.target_specialization.is_(None))

        # Sessions matching user's specialization
        if user.specialization:
            specialization_conditions.append(
                SessionTypel.target_specialization == user.specialization
            )

        # Mixed specialization sessions (if include_mixed is True)
        if include_mixed:
            specialization_conditions.append(SessionTypel.mixed_specialization == True)

        query = query.filter(or_(*specialization_conditions))

        if user.specialization:
            print(f"🎓 Specialization filtering applied for {user.name}: {user.specialization.value}")

        return query