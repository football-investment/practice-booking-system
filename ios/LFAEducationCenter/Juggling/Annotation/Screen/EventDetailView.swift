import SwiftUI

// MARK: — EventDetailView

// Sheet displayed when the user taps an event pin or list row.
// Shows the event's fields and sync status, with Edit and Delete actions.
// Edit opens ContactPickerView in edit mode; Delete is confirmation-gated.
// Swipe-to-delete is also available from the event list in JugglingAnnotationScreen.

struct EventDetailView: View {

    let draft:    ContactEventDraft
    let taxonomy: TaxonomyDocument?
    var onEdit:   (String, String?, String, String?, String?) -> Void
    var onDelete: () -> Void

    @Environment(\.presentationMode) private var presentationMode
    @State private var showEditPicker     = false
    @State private var showDeleteConfirm  = false

    var body: some View {
        NavigationView {
            List {
                eventFieldsSection
                syncStatusSection
                actionsSection
            }
            .listStyle(.insetGrouped)
            .navigationTitle("Esemény")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Kész") { presentationMode.wrappedValue.dismiss() }
                }
            }
            .sheet(isPresented: $showEditPicker) { editPickerSheet }
            .actionSheet(isPresented: $showDeleteConfirm) {
                ActionSheet(
                    title: Text("Esemény törlése?"),
                    message: Text("Az esemény eltávolításra kerül a szerverről is a következő szinkronizáció során."),
                    buttons: [
                        .destructive(Text("Törlés")) {
                            onDelete()
                            presentationMode.wrappedValue.dismiss()
                        },
                        .cancel(Text("Mégsem"))
                    ]
                )
            }
        }
    }

    // MARK: — Sections

    private var eventFieldsSection: some View {
        Section {
            labeledRow("Idő",        PlaybackControlBar.formatTimestamp(ms: draft.timestampMs))
            labeledRow("Típus",      typeLabel(for: draft.contactType))
            if let side = draft.side {
                labeledRow("Oldal",  sideLabel(side))
            }
            labeledRow("Bizonyosság", confidenceLabel(draft.annotationConfidence))
            if let label = draft.customLabel {
                labeledRow("Label",  label)
            }
            if let desc = draft.customDescription {
                labeledRow("Leírás", desc)
            }
        }
    }

    private var syncStatusSection: some View {
        Section(header: Text("Szinkron")) {
            HStack(spacing: 8) {
                Circle()
                    .fill(EventTimelineView.pinColor(for: draft.syncStatus))
                    .frame(width: 8, height: 8)
                Text(statusLabel)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
            .accessibilityLabel("Szinkron állapot: \(statusLabel)")
        }
    }

    private var actionsSection: some View {
        Section {
            Button("Szerkesztés") {
                showEditPicker = true
            }
            .disabled(!canEdit)
            .accessibilityLabel(canEdit ? "Szerkesztés" : "Szerkesztés nem elérhető jelenleg")

            Button("Törlés") {
                showDeleteConfirm = true
            }
            .foregroundColor(canDelete ? .red : .secondary)
            .disabled(!canDelete)
            .accessibilityLabel(canDelete ? "Törlés" : "Törlés nem elérhető jelenleg")
        }
    }

    @ViewBuilder
    private var editPickerSheet: some View {
        ContactPickerView(
            taxonomy:            taxonomy,
            currentMs:           draft.timestampMs,
            editMode:            true,
            initialType:         draft.contactType,
            initialSide:         draft.side,
            initialConfidence:   draft.annotationConfidence,
            initialCustomLabel:  draft.customLabel,
            initialCustomDescription: draft.customDescription,
            onSave: { type, side, confidence, label, desc in
                onEdit(type, side, confidence, label, desc)
                showEditPicker = false
                presentationMode.wrappedValue.dismiss()
            },
            onCancel: { showEditPicker = false }
        )
    }

    // MARK: — iOS 14-compatible two-column row (replaces LabeledContent)

    private func labeledRow(_ label: String, _ value: String) -> some View {
        HStack {
            Text(label)
                .foregroundColor(.secondary)
            Spacer()
            Text(value)
        }
    }

    // MARK: — State guards

    private var canEdit: Bool {
        switch draft.syncStatus {
        case .syncing, .updating, .deleting, .conflicted, .needsReconciliation: return false
        default: return true
        }
    }

    private var canDelete: Bool {
        switch draft.syncStatus {
        case .syncing, .updating, .deleting: return false
        default: return true
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

    private var statusLabel: String {
        switch draft.syncStatus {
        case .synced:               return "Szinkronizálva"
        case .localOnly:            return "Helyi — feltöltés folyamatban"
        case .retryPending:         return "Újrapróbálás várakozik (\(draft.retryCount)/3)"
        case .syncing:              return "Szinkronizálás…"
        case .updating:             return "Frissítés…"
        case .deleting:             return "Törlés…"
        case .conflicted:           return "Ütközés — döntés szükséges"
        case .failedPermanent:      return "Hiba: \(draft.failureReason ?? "ismeretlen")"
        case .needsReconciliation:  return "Egyeztetés szükséges"
        case .deleted:              return "Törölve"
        }
    }
}
