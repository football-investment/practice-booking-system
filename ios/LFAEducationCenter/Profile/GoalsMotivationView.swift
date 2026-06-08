import SwiftUI

// Goals & Motivation — LFA Football Player self-assessment.
//
// Collects preferred position + 7 skill self-ratings (1–10) and
// POSTs to /api/v1/licenses/motivation-assessment as lfa_player data.
// On success: onSuccess() → dashboardVM.reload() → ProfileCompletionScore +15%.
struct GoalsMotivationView: View {

    @EnvironmentObject private var authManager: AuthManager
    @Environment(\.presentationMode) private var presentationMode

    let onSuccess: () -> Void

    @StateObject private var vm = GoalsMotivationViewModel()

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(alignment: .leading, spacing: Theme.Spacing.lg) {
                    positionSection
                    Divider()
                    skillSection
                    saveButton
                    Spacer(minLength: Theme.Spacing.xl)
                }
                .padding(Theme.Spacing.md)
            }
            .background(Color(UIColor.systemBackground).ignoresSafeArea())
            .navigationTitle("Goals & Motivation")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button {
                        presentationMode.wrappedValue.dismiss()
                    } label: {
                        Image(systemName: "xmark")
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundColor(Theme.Color.onSurface)
                    }
                    .disabled(isSaving)
                }
            }
        }
        .navigationViewStyle(.stack)
        .onChange(of: successTriggered) { triggered in
            if triggered {
                onSuccess()
                presentationMode.wrappedValue.dismiss()
            }
        }
    }

    // MARK: — Position section

    private var positionSection: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
            sectionHeader("PREFERRED POSITION")
            LazyVGrid(
                columns: [GridItem(.flexible()), GridItem(.flexible())],
                spacing: Theme.Spacing.sm
            ) {
                ForEach(vm.positions, id: \.self) { pos in
                    Button { vm.selectedPosition = pos } label: {
                        Text(pos)
                            .font(.subheadline.weight(.semibold))
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 12)
                            .background(
                                vm.selectedPosition == pos
                                    ? Theme.Color.primary
                                    : Theme.Color.surface
                            )
                            .foregroundColor(
                                vm.selectedPosition == pos ? .white : Theme.Color.onSurface
                            )
                            .cornerRadius(Theme.Radius.sm)
                            .overlay(
                                RoundedRectangle(cornerRadius: Theme.Radius.sm)
                                    .stroke(
                                        vm.selectedPosition == pos
                                            ? Theme.Color.primary
                                            : Theme.Color.muted.opacity(0.3),
                                        lineWidth: 1
                                    )
                            )
                    }
                    .disabled(isSaving)
                }
            }
        }
    }

    // MARK: — Skill section

    private var skillSection: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
            sectionHeader("SKILL SELF-ASSESSMENT  (1 – 10)")
            VStack(spacing: 2) {
                skillRow(label: "Heading",      binding: $vm.heading)
                skillRow(label: "Shooting",     binding: $vm.shooting)
                skillRow(label: "Crossing",     binding: $vm.crossing)
                skillRow(label: "Passing",      binding: $vm.passing)
                skillRow(label: "Dribbling",    binding: $vm.dribbling)
                skillRow(label: "Ball Control", binding: $vm.ballControl)
                skillRow(label: "Defending",    binding: $vm.defending)
            }
            .background(Theme.Color.surface)
            .cornerRadius(Theme.Radius.md)
        }
    }

    private func skillRow(label: String, binding: Binding<Double>) -> some View {
        HStack(spacing: Theme.Spacing.sm) {
            Text(label)
                .font(.subheadline)
                .foregroundColor(Theme.Color.onSurface)
                .frame(width: 100, alignment: .leading)
            Slider(value: binding, in: 1...10, step: 1)
                .accentColor(Theme.Color.primary)
                .disabled(isSaving)
            Text("\(Int(binding.wrappedValue.rounded()))")
                .font(.system(size: 14, weight: .bold, design: .monospaced))
                .foregroundColor(Theme.Color.primary)
                .frame(width: 22, alignment: .trailing)
        }
        .padding(.horizontal, Theme.Spacing.md)
        .padding(.vertical, 10)
    }

    // MARK: — Save button

    @ViewBuilder
    private var saveButton: some View {
        switch vm.state {
        case .idle:
            primaryButton(title: "Save Assessment") {
                Task { await vm.save(using: authManager) }
            }

        case .saving:
            HStack {
                Spacer()
                ProgressView()
                    .padding(.vertical, 12)
                Spacer()
            }
            .frame(maxWidth: .infinity)
            .background(Theme.Color.primary.opacity(0.08))
            .cornerRadius(Theme.Radius.sm)

        case .success:
            HStack(spacing: 8) {
                Spacer()
                Image(systemName: "checkmark.circle.fill")
                    .foregroundColor(Color(red: 0.18, green: 0.80, blue: 0.44))
                Text("Saved!")
                    .font(.subheadline.weight(.semibold))
                    .foregroundColor(Color(red: 0.18, green: 0.80, blue: 0.44))
                Spacer()
            }
            .padding(.vertical, 12)
            .background(Color(red: 0.18, green: 0.80, blue: 0.44).opacity(0.10))
            .cornerRadius(Theme.Radius.sm)

        case .error(let message):
            VStack(spacing: Theme.Spacing.sm) {
                Text(message)
                    .font(.subheadline)
                    .foregroundColor(Theme.Color.error)
                    .multilineTextAlignment(.center)
                    .fixedSize(horizontal: false, vertical: true)
                primaryButton(title: "Try Again") {
                    vm.reset()
                }
            }
        }
    }

    // MARK: — Helpers

    private func sectionHeader(_ title: String) -> some View {
        Text(title)
            .font(.system(size: 10, weight: .semibold))
            .foregroundColor(Theme.Color.muted)
            .kerning(0.8)
    }

    private func primaryButton(title: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(title)
                .font(.body.weight(.semibold))
                .frame(maxWidth: .infinity)
                .frame(height: 48)
                .background(Theme.Color.primary)
                .foregroundColor(.white)
                .cornerRadius(Theme.Radius.sm)
        }
    }

    private var isSaving: Bool {
        if case .saving = vm.state { return true }
        return false
    }

    private var successTriggered: Bool {
        if case .success = vm.state { return true }
        return false
    }
}
