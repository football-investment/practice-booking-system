import Foundation

// Decoded from GET /api/v1/licenses/dashboard.
//
// All top-level fields and nested structs are Optional.
// The backend returns a complex Dict[str, Any] — we decode only what we display.
// Graceful degradation: DashboardView shows progress card only if decode succeeds.
struct LicenseDashboard: Decodable {
    let user:            DashboardUser?
    let overallProgress: OverallProgress?
    let recentActivity:  [ActivityEntry]?

    struct DashboardUser: Decodable {
        let id:             Int?
        let name:           String?
        let specialization: String?
    }

    struct OverallProgress: Decodable {
        let percentage:    Double
        let currentLevels: Int?
        let totalPossible: Int?

        enum CodingKeys: String, CodingKey {
            case percentage
            case currentLevels = "current_levels"
            case totalPossible = "total_possible"
        }
    }

    // ActivityEntry keeps only the specialization string.
    // The nested from_level/to_level dicts are complex — omitted until Phase E.
    struct ActivityEntry: Decodable {
        let specialization: String?
    }

    enum CodingKeys: String, CodingKey {
        case user
        case overallProgress = "overall_progress"
        case recentActivity  = "recent_activity"
    }
}
