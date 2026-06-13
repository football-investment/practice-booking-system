import SwiftUI

// MARK: — ConflictResolutionView

// Shown as an overlay when JugglingAnnotationViewModel.pendingConflictId != nil.
// Presents the server version (from pendingServerSnapshot) and the local version
// side-by-side so the user can make an informed decision.
//
// Two outcomes:
//   Accept server  → vm.acceptServerVersion(deviceEventId:) → draft becomes .synced
//   Keep local     → vm.keepLocalVersion(deviceEventId:)   → draft becomes .localOnly,
//                    caller must trigger flushPending() to re-POST

struct ConflictResolutionView: View {

    let draft:          ContactEventDraft
    let taxonomy:       TaxonomyDocument?
    var onAcceptServer: () -> Void
    var onKeepLocal:    () -> Void

    var body: some View {
        VStack(spacing: 0) {
            header
            Divider()
            versions
            Divider()
            actionButtons
        }
        .background(Color(.systemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .shadow(color: .black.opacity(0.2), radius: 12, x: 0, y: -4)
        .accessibilityElement(children: .contain)
    }

    // MARK: — Header

    private var header: some View {
        HStack(spacing: 8) {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundColor(.red)
            Text("Szinkronizációs ütközés")
                .font(.headline)
            Spacer()
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 14)
        .background(Color.red.opacity(0.07))
        .accessibilityAddTraits(.isHeader)
    }

    // MARK: — Version comparison

    private var versions: some View {
        HStack(alignment: .top, spacing: 0) {
            versionColumn(title: "Szerver", icon: "cloud.fill", color: .blue) {
                if let snap = draft.pendingServerSnapshot {
                    serverVersionContent(snap)
                } else {
                    Text("Nem elérhető")
                        .foregroundColor(.secondary)
                        .font(.caption)
                }
            }
            Divider()
            versionColumn(title: "Helyi", icon: "iphone", color: .orange) {
                localVersionContent
            }
        }
        .padding(.vertical, 12)
    }

    @ViewBuilder
    private func versionColumn<Content: View>(
        title: String,
        icon:  String,
        color: Color,
        @ViewBuilder content: () -> Content
    ) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Label(title, systemImage: icon)
                .font(.caption.weight(.semibold))
                .foregroundColor(color)
            content()
        }
        .padding(.horizontal, 16)
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    @ViewBuilder
    private func serverVersionContent(_ snap: ContactEventOut) -> some View {
        fieldRow("Típus",      typeLabel(for: snap.contactType))
        if let side = snap.side { fieldRow("Oldal", sideLabel(side)) }
        fieldRow("Bizonyosság", confidenceLabel(snap.annotationConfidence))
        fieldRow("Verzió",     "v\(snap.version)")
    }

    private var localVersionContent: some View {
        Group {
            fieldRow("Típus",      typeLabel(for: draft.contactType))
            if let side = draft.side { fieldRow("Oldal", sideLabel(side)) }
            fieldRow("Bizonyosság", confidenceLabel(draft.annotationConfidence))
            fieldRow("Verzió",     "v\(draft.version)")
        }
    }

    private func fieldRow(_ label: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 1) {
            Text(label)
                .font(.caption2)
                .foregroundColor(.secondary)
            Text(value)
                .font(.subheadline)
        }
    }

    // MARK: — Action buttons

    private var actionButtons: some View {
        VStack(spacing: 0) {
            Button {
                onAcceptServer()
            } label: {
                Label("Szerver verziót megtartom", systemImage: "cloud.fill")
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
            }
            .accessibilityLabel("Szerver verzió elfogadása")

            Divider()

            Button {
                onKeepLocal()
            } label: {
                Label("Saját verzióm marad (újraküldés)", systemImage: "arrow.up.circle")
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
            }
            .foregroundColor(.accentColor)
            .accessibilityLabel("Helyi verzió megtartása és újraküldés")
        }
    }

    // MARK: — Display helpers

    private func typeLabel(for key: String) -> String {
        taxonomy?.groups.flatMap { $0.contactTypes }.first { $0.key == key }?.labelHu ?? key
    }

    private func sideLabel(_ side: String) -> String {
        switch side {
        case "left":   return "Bal"
        case "right":  return "Jobb"
        case "center": return "Középső"
        default:       return side
        }
    }

    private func confidenceLabel(_ c: String) -> String {
        switch c {
        case "certain":   return "Biztos"
        case "probable":  return "Valószínű"
        case "uncertain": return "Bizonytalan"
        default:          return c
        }
    }
}
