import SwiftUI

// iOS-side rendering tokens for the Academy ID card colour system.
//
// The backend returns colour IDs (e.g. "ivory"), not CSS variables.
// This struct maps those IDs to SwiftUI Color values and derived text tones,
// keeping the card rendering fully native and independent of the backend's
// web-card CSS variable system.
//
// Phase 1: official / ivory / charcoal (all flat colours, no gradient).
// Phase 2: will add gradient-capable colours (surfaceEnd non-nil).

struct AcademyIDColorConfig {

    let id:            String
    let surfaceColor:  Color    // card background (flat in Phase 1)
    let borderColor:   Color
    let borderOpacity: Double
    let isLightSurface: Bool   // true = dark text; false = white text

    // MARK: — Derived text tones

    /// Primary value text (field values, full name, etc.)
    var valueColor:  Color { isLightSurface ? Color(UIColor.label) : .white }

    /// Secondary label text (field name caps: "FULL NAME", "AGE"…)
    var labelColor:  Color { isLightSurface ? Color(UIColor.secondaryLabel) : Color.white.opacity(0.55) }

    /// Faint placeholder text ("———", spec "—")
    var mutedColor:  Color { isLightSurface ? Color(UIColor.secondaryLabel).opacity(0.4) : Color.white.opacity(0.28) }

    /// Brand accent (header "LION FOOTBALL ACADEMY")
    var brandAccent: Color { isLightSurface ? Color(hex: "#b8a06a") : Color.white.opacity(0.80) }

    /// Photo panel / QR border tint
    var panelBorder: Color { isLightSurface ? Color(hex: "#b8a06a").opacity(0.30) : Color.white.opacity(0.15) }

    // MARK: — Static resolver

    /// Map a backend colour ID to the iOS rendering config.
    /// Unknown IDs fall back to "official" (the default white card appearance).
    static func resolve(_ colorId: String) -> AcademyIDColorConfig {
        switch colorId {

        case "ivory":
            return AcademyIDColorConfig(
                id:            "ivory",
                surfaceColor:  Color(red: 253/255, green: 250/255, blue: 244/255),
                borderColor:   Color(hex: "#b8a06a"),
                borderOpacity: 0.40,
                isLightSurface: true
            )

        case "charcoal":
            return AcademyIDColorConfig(
                id:            "charcoal",
                surfaceColor:  Color(red: 28/255, green: 28/255, blue: 30/255),
                borderColor:   .white,
                borderOpacity: 0.18,
                isLightSurface: false
            )

        default: // "official" and unknown → existing system appearance
            return AcademyIDColorConfig(
                id:            "official",
                surfaceColor:  Color(UIColor.secondarySystemBackground),
                borderColor:   Color(hex: "#b8a06a"),
                borderOpacity: 0.28,
                isLightSurface: true
            )
        }
    }
}

// MARK: — Hex colour initialiser (iOS 14 compatible)

extension Color {
    init(hex: String) {
        let h = hex.trimmingCharacters(in: .init(charactersIn: "#"))
        var rgb: UInt64 = 0
        Scanner(string: h).scanHexInt64(&rgb)
        let r = Double((rgb >> 16) & 0xFF) / 255
        let g = Double((rgb >>  8) & 0xFF) / 255
        let b = Double( rgb        & 0xFF) / 255
        self.init(red: r, green: g, blue: b)
    }
}
