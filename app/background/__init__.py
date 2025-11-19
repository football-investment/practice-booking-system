"""
Background Jobs Module

Handles scheduled tasks and background processing:
- Progress-License synchronization
- Data integrity checks
- Automated maintenance tasks
"""

from .scheduler import start_scheduler, stop_scheduler

__all__ = ['start_scheduler', 'stop_scheduler']
