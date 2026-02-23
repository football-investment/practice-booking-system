# Decision Log

Engineering decisions and strategic choices made during development.

---

## 2026-01-31: Location Venue Cleanup - Sprint 4-6 Deferred

**Decision**: DEFER Sprint 4 (Streamlit UI), Sprint 5 (Scripts), and Sprint 6 (Legacy) cleanup

**Context**:
- Sprint 3 (API Schema & Endpoints) completed successfully
- 19/19 API occurrences migrated
- Critical path complete (AttributeError eliminated)
- 33 non-critical occurrences remain (UI: 4, Scripts: 10, Legacy: 12, Migrations: 7)

**Rationale**:

✅ **Critical Path Complete**:
- API layer clean → No more AttributeError
- Backward compatibility maintained (schema field kept)
- Proper FK relationships in place

✅ **No Production Risk**:
- API responses unchanged (backward compatible)
- Frontend still works (schema includes deprecated field)
- No blocking issues for business operations

✅ **Low Impact Remaining**:
- Streamlit UI (4 occurrences): Admin/internal tools only
- Scripts (10 occurrences): Maintenance utilities
- Legacy (12 occurrences): Potentially deletable file

✅ **Higher Priorities Exist**:
- P3 Week 3 sandbox improvements
- Tournament testing workflows
- User-facing feature development

**Trade-offs**:

👍 **Benefits**:
- Focus on business-critical work
- Avoid gold-plating / over-engineering
- Technical debt documented and tracked
- Can revisit when capacity allows

👎 **Costs**:
- 33 occurrences remain in codebase
- Minor code inconsistency (but documented)
- Future cleanup effort required

**Mitigation**:
- Epic paused (not cancelled)
- BACKLOG_LOCATION_VENUE.md maintains complete usage map
- Can resume any time with clear roadmap

**Decision Owner**: User (confirmed deferral)
**Implementation**: Claude Sonnet 4.5
**Status**: ✅ APPROVED and documented

**Related Documents**:
- [EPIC_LOCATION_VENUE_CLEANUP.md](EPIC_LOCATION_VENUE_CLEANUP.md) - Updated to PAUSED status
- [BACKLOG_LOCATION_VENUE.md](BACKLOG_LOCATION_VENUE.md) - Complete remaining usage map
- [.sprints/2026-01-31-api-location-venue/](file://.sprints/2026-01-31-api-location-venue/) - Sprint 3 archive

---

## Template for Future Decisions

**Decision**: [Brief title]

**Context**: [What problem are we solving? What's the situation?]

**Rationale**: [Why this decision? What are the factors?]

**Trade-offs**: [What are we gaining? What are we giving up?]

**Mitigation**: [How do we address the downsides?]

**Decision Owner**: [Who made/approved this decision?]
**Status**: [Proposed / Approved / Implemented / Reversed]

**Related Documents**: [Links to relevant files]

---

**Last Updated**: 2026-01-31
