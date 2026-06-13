import SwiftUI

// MARK: — EventLabelDetailView (AN-3B2A P2)
//
// Step-by-step Phase 2 labeling flow, presented after enterLabelingMode()
// transitions every .unlabeled draft to .labelPending.
//
// The queue is captured once on appear (deviceEventIds of all .labelPending
// drafts, sorted by timestamp). Stepping through it:
//   .labelPending → pick contact type / side / confidence → labelEvent()
//                  → persisted immediately → .localOnly
// "Vissza" revisits a previous queue entry (now .localOnly) so its current
// values can be reviewed or changed — labelEvent() accepts both
// .labelPending and .localOnly as a starting state.
//
// Closing (X or "Kész") never needs an extra save: every successful step
// already persisted via labelEvent(). onClose() just returns to the marking
// screen (exitLabelingMode()).
//
// NOT in scope: backend sync, Finish, conflict resolution (AN-3C+).

struct EventLabelDetailView: View {
    @ObservedObject var vm: JugglingAnnotationViewModel
    var onClose: () -> Void

    @State private var queue: [UUID] = []
    @State private var currentIndex: Int = 0

    @State private var selectedKey:       String? = nil
    @State private var selectedSide:      String? = nil
    @State private var confidence:        String  = "certain"
    @State private var customLabel:       String  = ""
    @State private var customDescription: String  = ""

    @State private var showSaveErrorAlert = false

    var body: some View {
        NavigationView {
            Group {
                if currentDraft != nil {
                    formView
                } else {
                    completionView
                }
            }
            .navigationTitle(navigationTitle)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button {
                        close()
                    } label: {
                        Image(systemName: "xmark")
                            .font(.system(size: 16, weight: .medium))
                    }
                    .accessibilityLabel("Bezárás")
                }
            }
            .alert(isPresented: $showSaveErrorAlert) {
                Alert(
                    title: Text("Mentési hiba"),
                    message: Text(vm.saveError ?? "A mentés sikertelen."),
                    dismissButton: .default(Text("OK")) { vm.clearSaveError() }
                )
            }
        }
        .navigationViewStyle(.stack)
        .onAppear { setUpQueue() }
    }

    // MARK: — Queue / current draft

    private var navigationTitle: String {
        guard !queue.isEmpty, currentIndex < queue.count else { return "Címkézés kész" }
        return "Címkézés (\(currentIndex + 1)/\(queue.count))"
    }

    private var currentDraft: ContactEventDraft? {
        guard currentIndex >= 0, currentIndex < queue.count else { return nil }
        let id = queue[currentIndex]
        return vm.activeEvents.first { $0.deviceEventId == id }
    }

    private func setUpQueue() {
        guard queue.isEmpty else { return }
        queue = vm.activeEvents
            .filter { $0.syncStatus == .labelPending || $0.syncStatus == .localOnly }
            .sorted { $0.timestampMs < $1.timestampMs }
            .map { $0.deviceEventId }
        loadFormState()
    }

    private func loadFormState() {
        guard let draft = currentDraft else { return }
        selectedKey       = draft.contactType
        selectedSide      = draft.side
        confidence        = draft.annotationConfidence
        customLabel       = draft.customLabel ?? ""
        customDescription = draft.customDescription ?? ""
        if selectedSide == nil, let type = currentType {
            selectedSide = Self.autoSide(for: type)
        }
    }

    // MARK: — Form

    @ViewBuilder
    private var formView: some View {
        List {
            timestampSection
            if let doc = vm.taxonomy {
                ForEach(doc.groups.sorted { $0.groupSortOrder < $1.groupSortOrder }) { group in
                    Section(header: groupHeader(group)) {
                        ForEach(group.contactTypes.sorted { $0.sortOrder < $1.sortOrder }) { type in
                            typeRow(type)
                        }
                    }
                }
            } else {
                Section {
                    Text("Taxonomy betöltése…")
                        .foregroundColor(.secondary)
                }
            }
            confidenceSection
            if needsCustomLabel { customLabelSection }
            if needsCustomDescription { customDescSection }
            navigationSection
        }
        .listStyle(.insetGrouped)
    }

    private var timestampSection: some View {
        Section {
            HStack(spacing: 8) {
                Image(systemName: "clock")
                    .foregroundColor(.secondary)
                Text(PlaybackControlBar.formatTimestamp(ms: currentDraft?.timestampMs ?? 0))
                    .font(.headline.monospacedDigit())
                Spacer()
                statusBadge
            }
        }
    }

    @ViewBuilder
    private var statusBadge: some View {
        let status = currentDraft?.syncStatus ?? .labelPending
        Text(status == .localOnly ? "Címkézve" : "Címkézésre vár")
            .font(.caption.weight(.semibold))
            .foregroundColor(.white)
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .background(status == .localOnly ? Color.green : Color(.systemGray))
            .clipShape(Capsule())
    }

    @ViewBuilder
    private func groupHeader(_ group: TaxonomyGroup) -> some View {
        Label(group.groupLabelHu, systemImage: group.iosIcon ?? "circle")
            .accessibilityLabel(group.groupLabelHu)
    }

    @ViewBuilder
    private func typeRow(_ type: TaxonomyContactType) -> some View {
        let isSelected = selectedKey == type.key
        Button {
            toggleType(type)
        } label: {
            HStack(spacing: 12) {
                Image(systemName: type.iosIcon ?? "circle.fill")
                    .frame(width: 24)
                    .foregroundColor(isSelected ? .accentColor : .secondary)

                VStack(alignment: .leading, spacing: 2) {
                    Text(type.labelHu)
                        .foregroundColor(.primary)
                    Text(type.labelEn)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }

                Spacer()

                if isSelected && type.sidePolicy == "explicit_required" {
                    sideToggleButtons
                        .padding(.trailing, 4)
                }

                if isSelected {
                    Image(systemName: "checkmark")
                        .foregroundColor(.accentColor)
                        .font(.caption.weight(.bold))
                }
            }
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .frame(minHeight: 52)
        .accessibilityLabel(accessibilityLabel(for: type))
        .accessibilityAddTraits(isSelected ? .isSelected : [])
    }

    private var sideToggleButtons: some View {
        HStack(spacing: 6) {
            sideButton(label: "B", value: "left",  accessLabel: "Bal")
            sideButton(label: "J", value: "right", accessLabel: "Jobb")
        }
    }

    private func sideButton(label: String, value: String, accessLabel: String) -> some View {
        Button(label) {
            selectedSide = (selectedSide == value) ? nil : value
        }
        .font(.caption.weight(.bold))
        .frame(width: 36, height: 36)
        .background(selectedSide == value ? Color.accentColor : Color(.systemGray5))
        .foregroundColor(selectedSide == value ? .white : .primary)
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .accessibilityLabel(accessLabel)
        .accessibilityAddTraits(selectedSide == value ? .isSelected : [])
    }

    private var confidenceSection: some View {
        Section(header: Text("Bizonyosság")) {
            Picker("Bizonyosság", selection: $confidence) {
                Text("Biztos").tag("certain")
                Text("Valószínű").tag("probable")
                Text("Bizonytalan").tag("uncertain")
            }
            .pickerStyle(.segmented)
            .padding(.vertical, 4)
            .accessibilityLabel("Bizonyosság szint")
        }
    }

    private var customLabelSection: some View {
        Section(header: Text("Egyedi label (kötelező)")) {
            TextField("pl. belső csüd", text: $customLabel)
                .accessibilityLabel("Egyedi label szöveges mező")
        }
    }

    private var customDescSection: some View {
        Section(header: Text("Leírás")) {
            TextField("Rövid leírás (opcionális)", text: $customDescription)
                .accessibilityLabel("Leírás szöveges mező")
        }
    }

    // MARK: — Navigation row (Vissza / Mentés és tovább)

    @ViewBuilder
    private var navigationSection: some View {
        Section {
            HStack(spacing: 12) {
                Button("Vissza") {
                    goToPrevious()
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 8)
                .foregroundColor(currentIndex > 0 ? Color.accentColor : .secondary)
                .disabled(currentIndex == 0)
                .accessibilityLabel("Előző esemény")

                Button(isLastInQueue ? "Mentés és befejezés" : "Mentés és tovább") {
                    saveAndAdvance()
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 8)
                .foregroundColor(canSave ? .white : .secondary)
                .background(canSave ? Color.accentColor : Color(.systemGray5))
                .clipShape(RoundedRectangle(cornerRadius: 8))
                .disabled(!canSave)
                .accessibilityLabel(isLastInQueue ? "Mentés és befejezés" : "Mentés és a következő esemény")
            }
            .listRowInsets(EdgeInsets())
            .padding(.horizontal, 16)
            .padding(.vertical, 4)
        }
    }

    private var isLastInQueue: Bool {
        currentIndex >= queue.count - 1
    }

    // MARK: — Completion

    @ViewBuilder
    private var completionView: some View {
        VStack(spacing: 16) {
            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 48))
                .foregroundColor(.green)
            Text(queue.isEmpty ? "Nincs címkézendő esemény" : "Minden esemény megcímkézve")
                .font(.headline)
            Button("Vissza a videóhoz") {
                close()
            }
            .font(.body.weight(.semibold))
            .foregroundColor(.white)
            .padding(.horizontal, 24)
            .padding(.vertical, 10)
            .background(Color.accentColor)
            .clipShape(RoundedRectangle(cornerRadius: 8))
            .accessibilityLabel("Vissza a videóhoz")
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: — Validation (mirrors taxonomy sidePolicy / requiresCustomLabel)

    private var currentType: TaxonomyContactType? {
        guard let key = selectedKey else { return nil }
        return vm.taxonomy?.groups.flatMap { $0.contactTypes }.first { $0.key == key }
    }

    private var needsCustomLabel: Bool {
        currentType?.requiresCustomLabel == true
    }

    private var needsCustomDescription: Bool {
        currentType?.requiresCustomDescription == true
    }

    private var canSave: Bool {
        guard selectedKey != nil else { return false }
        if currentType?.sidePolicy == "explicit_required" && selectedSide == nil { return false }
        if needsCustomLabel && customLabel.trimmingCharacters(in: .whitespaces).isEmpty { return false }
        return true
    }

    // Returns the auto-applied side for fixed/center policies; nil for explicit_required.
    private static func autoSide(for type: TaxonomyContactType) -> String? {
        switch type.sidePolicy {
        case "fixed", "center": return type.side
        default:                 return nil
        }
    }

    // MARK: — Interaction

    private func toggleType(_ type: TaxonomyContactType) {
        if selectedKey == type.key {
            selectedKey  = nil
            selectedSide = nil
        } else {
            selectedKey  = type.key
            selectedSide = Self.autoSide(for: type)
        }
    }

    private func saveAndAdvance() {
        guard let draft = currentDraft, let key = selectedKey else { return }
        let label = customLabel.trimmingCharacters(in: .whitespaces)
        let desc  = customDescription.trimmingCharacters(in: .whitespaces)

        let ok = vm.labelEvent(
            deviceEventId:        draft.deviceEventId,
            contactType:          key,
            side:                 selectedSide,
            annotationConfidence: confidence,
            customLabel:          label.isEmpty ? nil : label,
            customDescription:    desc.isEmpty  ? nil : desc
        )
        guard ok else {
            showSaveErrorAlert = true
            return
        }
        if isLastInQueue {
            currentIndex += 1   // out of range → completionView
        } else {
            currentIndex += 1
            loadFormState()
        }
    }

    private func goToPrevious() {
        guard currentIndex > 0 else { return }
        currentIndex -= 1
        loadFormState()
    }

    private func close() {
        vm.exitLabelingMode()
        onClose()
    }

    private func accessibilityLabel(for type: TaxonomyContactType) -> String {
        var parts = [type.labelHu, type.labelEn]
        if type.sidePolicy == "explicit_required" { parts.append("Oldal szükséges") }
        if type.requiresCustomLabel == true { parts.append("Egyedi label szükséges") }
        return parts.joined(separator: ", ")
    }
}
