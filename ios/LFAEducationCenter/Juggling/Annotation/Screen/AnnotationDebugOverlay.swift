#if DEBUG
import SwiftUI

// MARK: — AnnotationDebugOverlay (AN-3B2A P0)
//
// DEBUG-only diagnostic sheet for JugglingAnnotationScreen. Read-only: never
// mutates vm.session, never touches the local store beyond the existing
// read-only diagnostics accessors (sessionFileURL / sessionFileExists /
// quarantineDirectory — none of which create or modify files).
//
// Presentation: a toolbar bug icon, visible only in DEBUG builds, opens this
// as a sheet. There is no equivalent UI in RELEASE builds.

struct AnnotationDebugOverlay: View {
    @ObservedObject var vm: JugglingAnnotationViewModel
    let authManager: AuthManager
    let videoId: String

    @Environment(\.presentationMode) private var presentationMode

    var body: some View {
        NavigationView {
            List {
                Section(header: Text("Build")) {
                    row("Build tag", AnnotationBuildInfo.tag)
                }

                Section(header: Text("Identity")) {
                    row("authManager.currentUserId", authManager.currentUserId.map(String.init) ?? "nil")
                    row("vm.userId", String(vm.userId))
                    row("videoId", videoId)
                }

                Section(header: Text("Local session file")) {
                    row("Path", vm.diagSessionFilePath.path)
                    row("File exists", String(vm.diagSessionFileExists))
                    row("Quarantine dir", vm.diagQuarantineDirectory.path)
                }

                Section(header: Text("Last load")) {
                    row("Result", vm.diagnostics.loadResult.description)
                    row("At", formatted(vm.diagnostics.lastLoadAt))
                    if let qPath = vm.diagnostics.quarantinePath {
                        row("Quarantine path", qPath.path)
                    }
                }

                Section(header: Text("Session counts")) {
                    row("Active events", String(vm.activeEvents.count))
                    row("Unlabeled", String(vm.unlabeledCount))
                    row("Label pending", String(vm.labelPendingCount))
                }

                Section(header: Text("Last save")) {
                    row("Result", vm.diagnostics.lastSaveResult.description)
                    row("At", formatted(vm.diagnostics.lastSaveAt))
                }

                Section(header: Text("Errors / warnings")) {
                    row("saveError", vm.saveError ?? "—")
                    row("loadWarning", vm.loadWarning ?? "—")
                }
            }
            .navigationTitle("AN-3B2A Diagnostics")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Bezárás") {
                        presentationMode.wrappedValue.dismiss()
                    }
                }
            }
        }
        .navigationViewStyle(.stack)
    }

    private func row(_ label: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label)
                .font(.caption)
                .foregroundColor(.secondary)
            Text(value)
                .font(.system(.footnote, design: .monospaced))
        }
    }

    private func formatted(_ date: Date?) -> String {
        guard let date = date else { return "—" }
        let f = DateFormatter()
        f.dateFormat = "HH:mm:ss.SSS"
        return f.string(from: date)
    }
}
#endif
