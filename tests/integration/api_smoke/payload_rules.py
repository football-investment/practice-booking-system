"""
Domain-specific payload generation rules for tournament endpoints.

This module provides explicit rules for endpoints that have:
1. XOR constraints (either field A or field B must be provided)
2. Complex validation logic not visible in OpenAPI schema
3. Context-dependent required fields
"""

from typing import Dict, Any, Optional


class PayloadRules:
    """Domain-specific payload generation rules."""

    @staticmethod
    def apply_rules(method: str, path: str, payload: Dict, context: Dict) -> Dict:
        """
        Apply domain-specific rules to a generated payload.

        Uses pattern matching to handle both placeholder and literal paths.

        Args:
            method: HTTP method (POST, PUT, PATCH)
            path: API endpoint path (may contain literals or placeholders)
            payload: Base payload from factory
            context: Context with fixture values

        Returns:
            Enhanced payload with domain rules applied
        """
        import re

        # Normalize path - replace any {...} or {test_...[...]} with generic placeholder
        normalized_path = re.sub(r'\{[^}]+\}', '{ID}', path)

        # Route to specific rule handlers using normalized paths
        if "/tournaments/create" in path:
            return PayloadRules._rule_create_tournament(payload, context)
        elif "/ops/run-scenario" in path:
            return PayloadRules._rule_ops_scenario(payload, context)
        elif re.search(r'/tournaments/\{ID\}/status', normalized_path):
            return PayloadRules._rule_transition_status(payload, context)
        elif re.search(r'/tournaments/\{ID\}/admin/batch-enroll', normalized_path):
            return PayloadRules._rule_batch_enroll(payload, context)
        elif re.search(r'/tournaments/\{ID\}/assign-instructor', normalized_path):
            return PayloadRules._rule_assign_instructor(payload, context)
        elif re.search(r'/tournaments/\{ID\}/direct-assign-instructor', normalized_path):
            return PayloadRules._rule_direct_assign_instructor(payload, context)
        elif re.search(r'/tournaments/\{ID\}/cancel', normalized_path):
            return PayloadRules._rule_cancel_tournament(payload, context)
        elif re.search(r'/tournaments/\{ID\}/send-instructor-request', normalized_path):
            return PayloadRules._rule_send_instructor_request(payload, context)
        elif re.search(r'/tournaments/\{ID\}/skill-mappings', normalized_path):
            return PayloadRules._rule_create_skill_mapping(payload, context)
        elif re.search(r'/tournaments/\{ID\}/rankings', normalized_path):
            return PayloadRules._rule_submit_rankings(payload, context)
        elif re.search(r'/tournaments/\{ID\}/distribute-rewards-v2', normalized_path):
            return PayloadRules._rule_distribute_rewards(payload, context)
        elif re.search(r'/tournaments/\{ID\}/campus-schedules', normalized_path):
            return PayloadRules._rule_upsert_campus_schedule(payload, context)
        elif re.search(r'/tournaments/\{ID\}/reward-config', normalized_path):
            return PayloadRules._rule_reward_config(payload, context)
        elif "/requests/" in path and ("/accept" in path or "/decline" in path):
            return PayloadRules._rule_request_action(payload, context)

        # Phase A: Global date format validation (applies to ALL payloads)
        payload = PayloadRules._apply_date_format_validation(payload)

        return payload

    @staticmethod
    def _rule_create_tournament(payload: Dict, context: Dict) -> Dict:
        """
        Rule: Either 'game_preset_id' or 'skills_to_test' must be provided.
        Rule: tournament_type must be one of [league, knockout, hybrid]

        Strategy: Always use game_preset_id (simpler, deterministic)
        """
        import random

        # Remove skills_to_test if present (factory might generate it)
        payload.pop("skills_to_test", None)

        # Add game_preset_id (use 1 as default - assumes at least one preset exists)
        payload["game_preset_id"] = 1

        # Phase A: Validate tournament_type enum
        valid_types = ["league", "knockout", "hybrid"]
        if "tournament_type" in payload:
            if payload["tournament_type"] not in valid_types:
                payload["tournament_type"] = random.choice(valid_types)

        return payload

    @staticmethod
    def _rule_transition_status(payload: Dict, context: Dict) -> Dict:
        """
        Rule: new_status is required for status transitions.
        Rule: Only allow valid status transitions.

        Strategy: Use deterministic status (ACTIVE) or first valid transition
        """
        # Phase A: Valid transition validation
        valid_transitions = {
            "DRAFT": ["ENROLLMENT_OPEN", "SEEKING_INSTRUCTOR", "CANCELLED"],
            "ENROLLMENT_OPEN": ["IN_PROGRESS", "CANCELLED"],
            "IN_PROGRESS": ["COMPLETED", "CANCELLED"],
            "COMPLETED": ["REWARDS_DISTRIBUTED"],
        }

        if "new_status" not in payload:
            payload["new_status"] = "ENROLLMENT_OPEN"  # First valid DRAFT transition
        else:
            # Validate transition from current tournament status
            current_status = context.get("tournament_status", "DRAFT")
            new_status = payload["new_status"]

            if current_status in valid_transitions:
                if new_status not in valid_transitions[current_status]:
                    # Use first valid transition instead
                    payload["new_status"] = valid_transitions[current_status][0]

        return payload

    @staticmethod
    def _rule_batch_enroll(payload: Dict, context: Dict) -> Dict:
        """
        Rule: player_ids array is required.

        Strategy: Use test_student_id from context if available
        """
        if "player_ids" not in payload or not payload.get("player_ids"):
            student_id = context.get("student_id", 1)
            payload["player_ids"] = [student_id]

        return payload

    @staticmethod
    def _rule_assign_instructor(payload: Dict, context: Dict) -> Dict:
        """
        Rule: instructor_id is required.

        Strategy: Use test_instructor_id from context
        """
        if "instructor_id" not in payload:
            instructor_id = context.get("instructor_id", 1)
            payload["instructor_id"] = instructor_id

        return payload

    @staticmethod
    def _rule_direct_assign_instructor(payload: Dict, context: Dict) -> Dict:
        """Same as assign_instructor."""
        return PayloadRules._rule_assign_instructor(payload, context)

    @staticmethod
    def _rule_cancel_tournament(payload: Dict, context: Dict) -> Dict:
        """
        Rule: reason is required for cancellation.

        Strategy: Use deterministic reason
        """
        if "reason" not in payload:
            payload["reason"] = "Test cancellation"

        return payload

    @staticmethod
    def _rule_send_instructor_request(payload: Dict, context: Dict) -> Dict:
        """
        Rule: instructor_id is required.

        Strategy: Use test_instructor_id from context
        """
        return PayloadRules._rule_assign_instructor(payload, context)

    @staticmethod
    def _rule_create_skill_mapping(payload: Dict, context: Dict) -> Dict:
        """
        Rule: tournament_id, skill_name, skill_category are required.

        Strategy: Ensure all required fields are present
        """
        if "tournament_id" not in payload:
            payload["tournament_id"] = context.get("tournament_id", 1)

        if "skill_name" not in payload:
            payload["skill_name"] = "Test Skill"

        if "skill_category" not in payload:
            payload["skill_category"] = "TECHNICAL"

        return payload

    @staticmethod
    def _rule_submit_rankings(payload: Dict, context: Dict) -> Dict:
        """
        Rule: rankings array is required with user_id (not player_id).

        Strategy: Create minimal valid ranking
        """
        if "rankings" not in payload or not payload.get("rankings"):
            student_id = context.get("student_id", 1)
            payload["rankings"] = [
                {
                    "user_id": student_id,  # Correct field: user_id, not player_id
                    "rank": 1,
                    "score": 100
                }
            ]

        return payload

    @staticmethod
    def _rule_distribute_rewards(payload: Dict, context: Dict) -> Dict:
        """
        Rule: tournament_id is required in body.

        Strategy: Use tournament_id from context
        """
        if "tournament_id" not in payload:
            payload["tournament_id"] = context.get("tournament_id", 1)

        return payload

    @staticmethod
    def _rule_upsert_campus_schedule(payload: Dict, context: Dict) -> Dict:
        """
        Rule: campus_id is required.

        Strategy: Use test_campus_id from context
        """
        if "campus_id" not in payload:
            payload["campus_id"] = context.get("campus_id", 1)

        return payload

    @staticmethod
    def _rule_request_action(payload: Dict, context: Dict) -> Dict:
        """
        Rule: Request accept/decline endpoints may need empty payload.

        Strategy: Keep payload minimal (empty is OK)
        """
        # These endpoints typically don't need payload
        return payload or {}

    @staticmethod
    def _rule_ops_scenario(payload: Dict, context: Dict) -> Dict:
        """
        Rule: OPS scenario requires confirmed=True + explicit player_ids.

        Strategy:
        - Set confirmed=True to bypass safety check
        - Use explicit player_ids to bypass @lfa-seed.hu pool requirement
        - Set player_count=0 (ignored when player_ids provided)
        """
        payload["confirmed"] = True

        # Use enrolled students from context to bypass @lfa-seed.hu requirement
        if "enrolled_student_ids" in context and context["enrolled_student_ids"]:
            payload["player_ids"] = context["enrolled_student_ids"]
            payload["player_count"] = 0  # Ignored when player_ids provided

        return payload

    @staticmethod
    def _rule_reward_config(payload: Dict, context: Dict) -> Dict:
        """
        Rule: At least 1 skill must be enabled for tournament rewards.

        Strategy: Ensure skill_config has at least one enabled skill
        """
        if "skill_config" in payload and isinstance(payload["skill_config"], dict):
            # Check if at least one skill is enabled
            if not any(payload["skill_config"].values()):
                # Enable first skill
                first_skill = next(iter(payload["skill_config"].keys()))
                payload["skill_config"][first_skill] = True

        return payload

    @staticmethod
    def _apply_date_format_validation(payload: Dict) -> Dict:
        """
        Global rule: Date fields must be YYYY-MM-DD format.

        Applies to ALL payloads with date fields.
        """
        date_fields = ["start_date", "end_date", "tournament_date", "date", "deadline"]

        for field in date_fields:
            if field in payload and isinstance(payload[field], str):
                # Extract YYYY-MM-DD if longer format (e.g., "2026-02-25T13:00:00")
                if len(payload[field]) > 10:
                    payload[field] = payload[field][:10]

        return payload
