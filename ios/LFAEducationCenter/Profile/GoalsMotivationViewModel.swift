import Foundation

// MARK: — Request / Response

private struct GoalsMotivationRequest: Encodable {
    let lfaPlayer: LFAPlayerMotivationPayload
    enum CodingKeys: String, CodingKey { case lfaPlayer = "lfa_player" }
}

private struct LFAPlayerMotivationPayload: Encodable {
    let preferredPosition:    String
    let headingSelfRating:    Int
    let shootingSelfRating:   Int
    let crossingSelfRating:   Int
    let passingSelfRating:    Int
    let dribblingSelfRating:  Int
    let ballControlSelfRating: Int
    let defendingSelfRating:  Int

    enum CodingKeys: String, CodingKey {
        case preferredPosition    = "preferred_position"
        case headingSelfRating    = "heading_self_rating"
        case shootingSelfRating   = "shooting_self_rating"
        case crossingSelfRating   = "crossing_self_rating"
        case passingSelfRating    = "passing_self_rating"
        case dribblingSelfRating  = "dribbling_self_rating"
        case ballControlSelfRating = "ball_control_self_rating"
        case defendingSelfRating  = "defending_self_rating"
    }
}

private struct GoalsMotivationSaveResponse: Decodable {
    let success: Bool
    let message: String
}

// MARK: — State

enum GoalsMotivationState {
    case idle
    case saving
    case success
    case error(String)
}

// MARK: — ViewModel

@MainActor
final class GoalsMotivationViewModel: ObservableObject {

    // Position picker
    @Published var selectedPosition: String = "Striker"
    let positions = ["Striker", "Midfielder", "Defender", "Goalkeeper"]

    // Skill self-ratings (1–10, stored as Double for Slider compatibility)
    @Published var heading:     Double = 5
    @Published var shooting:    Double = 5
    @Published var crossing:    Double = 5
    @Published var passing:     Double = 5
    @Published var dribbling:   Double = 5
    @Published var ballControl: Double = 5
    @Published var defending:   Double = 5

    @Published private(set) var state: GoalsMotivationState = .idle

    // POST /api/v1/licenses/motivation-assessment
    func save(using authManager: AuthManager) async {
        state = .saving

        let payload = GoalsMotivationRequest(
            lfaPlayer: LFAPlayerMotivationPayload(
                preferredPosition:    selectedPosition,
                headingSelfRating:    Int(heading.rounded()),
                shootingSelfRating:   Int(shooting.rounded()),
                crossingSelfRating:   Int(crossing.rounded()),
                passingSelfRating:    Int(passing.rounded()),
                dribblingSelfRating:  Int(dribbling.rounded()),
                ballControlSelfRating: Int(ballControl.rounded()),
                defendingSelfRating:  Int(defending.rounded())
            )
        )

        do {
            let response: GoalsMotivationSaveResponse = try await authManager.authenticatedPost(
                path: "/api/v1/licenses/motivation-assessment",
                body: payload
            )
            state = response.success ? .success : .error("Could not save. Please try again.")
        } catch APIError.httpError(let code, let detail) {
            switch code {
            case 400: state = .error(detail ?? "Invalid data. Please check your inputs.")
            case 401: state = .error("Your session has expired. Please sign in again.")
            case 404: state = .error("No active LFA Football Player license found.")
            default:  state = .error("Save failed (error \(code)). Please try again.")
            }
        } catch APIError.unauthorized {
            state = .error("Your session has expired. Please sign in again.")
        } catch {
            state = .error("Network error. Check your connection and try again.")
        }
    }

    func reset() { state = .idle }
}
