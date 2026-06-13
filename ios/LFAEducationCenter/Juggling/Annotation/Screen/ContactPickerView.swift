import SwiftUI

// MARK: — ContactPickerView

// Bottom-sheet contact-type picker used for both adding new events and editing
// existing ones. Explicit Save button is always required — no auto-submit on tap.
//
// sidePolicy handling:
//   "fixed"            → side is auto-set from type.side; no buttons shown
//   "center"           → side is auto-set to type.side ("center"); no buttons shown
//   "explicit_required"→ L / R toggle buttons shown; Save blocked until side is chosen
//
// canSave:
//   - A type must be selected
//   - If explicit_required side policy: selectedSide must be non-nil
//   - If requiresCustomLabel == true: customLabel must be non-empty

struct ContactPickerView: View {

    let taxonomy:            TaxonomyDocument?
    let currentMs:           Int
    var editMode:            Bool    = false
    var initialType:         String? = nil
    var initialSide:         String? = nil
    var initialConfidence:   String  = "certain"
    var initialCustomLabel:  String? = nil
    var initialCustomDescription: String? = nil
    var onSave:   (String, String?, String, String?, String?) -> Void
    var onCancel: () -> Void

    @State private var selectedKey:         String?  = nil
    @State private var selectedSide:        String?  = nil
    @State private var confidence:          String   = "certain"
    @State private var customLabel:         String   = ""
    @State private var customDescription:   String   = ""

    var body: some View {
        NavigationView {
            List {
                timestampSection
                if let doc = taxonomy {
                    ForEach(
                        doc.groups.sorted { $0.groupSortOrder < $1.groupSortOrder }
                    ) { group in
                        Section(header: groupHeader(group)) {
                            ForEach(
                                group.contactTypes.sorted { $0.sortOrder < $1.sortOrder }
                            ) { type in
                                typeRow(type, in: doc)
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
            }
            .listStyle(.insetGrouped)
            .navigationTitle(editMode ? "Szerkesztés" : "Kontakt típus")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Mégsem", action: onCancel)
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Mentés") { submit() }
                        .disabled(!canSave)
                        .font(.body.weight(.semibold))
                        .accessibilityLabel(canSave ? "Mentés" : "Mentés — hiányzó mezők")
                }
            }
            .onAppear { applyInitialValues() }
        }
    }

    // MARK: — Sections

    private var timestampSection: some View {
        Section {
            HStack(spacing: 8) {
                Image(systemName: "clock")
                    .foregroundColor(.secondary)
                Text(PlaybackControlBar.formatTimestamp(ms: currentMs))
                    .font(.headline.monospacedDigit())
                    .accessibilityLabel("Időpont: \(PlaybackControlBar.formatTimestamp(ms: currentMs))")
            }
        }
    }

    @ViewBuilder
    private func groupHeader(_ group: TaxonomyGroup) -> some View {
        Label(group.groupLabelHu, systemImage: group.iosIcon ?? "circle")
            .accessibilityLabel(group.groupLabelHu)
    }

    @ViewBuilder
    private func typeRow(_ type: TaxonomyContactType, in doc: TaxonomyDocument) -> some View {
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

                // Side buttons — only for explicit_required, only when this row is selected
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

    // MARK: — Validation

    var canSave: Bool {
        ContactPickerValidation.canSave(
            selectedKey:   selectedKey,
            selectedSide:  selectedSide,
            sidePolicy:    currentType?.sidePolicy,
            customLabel:   customLabel,
            requiresLabel: currentType?.requiresCustomLabel == true
        )
    }

    private var needsCustomLabel: Bool {
        currentType?.requiresCustomLabel == true
    }

    private var needsCustomDescription: Bool {
        currentType?.requiresCustomDescription == true
    }

    private var currentType: TaxonomyContactType? {
        guard let key = selectedKey else { return nil }
        return taxonomy?.groups.flatMap { $0.contactTypes }.first { $0.key == key }
    }

    // MARK: — Interaction

    private func toggleType(_ type: TaxonomyContactType) {
        if selectedKey == type.key {
            selectedKey  = nil
            selectedSide = nil
        } else {
            selectedKey  = type.key
            selectedSide = ContactPickerValidation.autoSide(for: type)
        }
    }

    private func submit() {
        guard canSave, let key = selectedKey else { return }
        let label = customLabel.trimmingCharacters(in: .whitespaces)
        let desc  = customDescription.trimmingCharacters(in: .whitespaces)
        onSave(
            key,
            selectedSide,
            confidence,
            label.isEmpty ? nil : label,
            desc.isEmpty  ? nil : desc
        )
    }

    private func applyInitialValues() {
        guard editMode else { return }
        selectedKey   = initialType
        selectedSide  = initialSide
        confidence    = initialConfidence
        customLabel   = initialCustomLabel  ?? ""
        customDescription = initialCustomDescription ?? ""
        // Auto-set side for fixed/center types even in edit mode
        if let type = currentType, selectedSide == nil {
            selectedSide = ContactPickerValidation.autoSide(for: type)
        }
    }

    private func accessibilityLabel(for type: TaxonomyContactType) -> String {
        var parts = [type.labelHu, type.labelEn]
        if type.sidePolicy == "explicit_required" { parts.append("Oldal szükséges") }
        if type.requiresCustomLabel == true { parts.append("Egyedi label szükséges") }
        return parts.joined(separator: ", ")
    }
}

// MARK: — ContactPickerValidation (static — unit-testable without SwiftUI)

struct ContactPickerValidation {

    static func canSave(
        selectedKey:   String?,
        selectedSide:  String?,
        sidePolicy:    String?,
        customLabel:   String,
        requiresLabel: Bool
    ) -> Bool {
        guard selectedKey != nil else { return false }
        if sidePolicy == "explicit_required" && selectedSide == nil { return false }
        if requiresLabel && customLabel.trimmingCharacters(in: .whitespaces).isEmpty { return false }
        return true
    }

    // Returns the auto-applied side for fixed/center policies; nil for explicit_required.
    static func autoSide(for type: TaxonomyContactType) -> String? {
        switch type.sidePolicy {
        case "fixed", "center": return type.side
        default:                 return nil
        }
    }
}
