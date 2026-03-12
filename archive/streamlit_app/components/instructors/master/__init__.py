"""Master Instructor Component - Modular structure with multiple pathways"""

from .master_card import render_master_card
from .pending_offers import render_pending_offers_admin_view
from .hiring_interface import render_hiring_interface
from .pathway_a import render_direct_hire_tab
from .pathway_b import render_post_opening_tab, render_master_position_applications

__all__ = [
    'render_master_card',
    'render_pending_offers_admin_view',
    'render_hiring_interface',
    'render_direct_hire_tab',
    'render_post_opening_tab',
    'render_master_position_applications',
]
