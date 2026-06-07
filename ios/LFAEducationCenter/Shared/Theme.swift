import SwiftUI

// LFA Education Center design tokens.
// All views import Theme — no magic numbers in view code.
enum Theme {

    enum Color {
        static let primary    = SwiftUI.Color.green
        static let secondary  = SwiftUI.Color.orange
        static let background = SwiftUI.Color(UIColor.systemBackground)
        static let surface    = SwiftUI.Color(UIColor.secondarySystemBackground)
        static let onSurface  = SwiftUI.Color(UIColor.label)
        static let muted      = SwiftUI.Color(UIColor.secondaryLabel)
        static let warning    = SwiftUI.Color.yellow
        static let error      = SwiftUI.Color.red
    }

    enum Spacing {
        static let xs: CGFloat = 4
        static let sm: CGFloat = 8
        static let md: CGFloat = 16
        static let lg: CGFloat = 24
        static let xl: CGFloat = 32
    }

    enum Radius {
        static let sm: CGFloat = 8
        static let md: CGFloat = 12
        static let lg: CGFloat = 20
    }

    enum FontSize {
        static let caption: CGFloat  = 12
        static let body: CGFloat     = 16
        static let title3: CGFloat   = 20
        static let title2: CGFloat   = 22
        static let title: CGFloat    = 28
    }
}
