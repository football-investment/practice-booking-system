import SwiftUI

// Academy ID colour picker sheet — Phase 1 (free colours only).
//
// Shows the three free swatches: Official / Ivory / Charcoal.
// Tap → optimistic select via AcademyIDColorViewModel.
// Active colour has a checkmark overlay.
// No premium section, no crown icon, no locked state — Phase 2 only.
//
// Reduce Motion: colour change is always a crossfade in the card;
// the sheet itself uses the system sheet animation.

struct AcademyIDColorPickerView: View {

    @EnvironmentObject private var authManager: AuthManager
    @ObservedObject var colorVM: AcademyIDColorViewModel
    @Environment(\.presentationMode) private var presentationMode
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    private let swatchSize: CGFloat = 44

    var body: some View {
        NavigationView {
            VStack(alignment: .leading, spacing: 0) {

                // Error banner (non-intrusive, dismissible)
                if let err = colorVM.errorMessage {
                    HStack(spacing: Theme.Spacing.sm) {
                        Image(systemName: "exclamationmark.circle")
                            .font(.system(size: 13))
                        Text(err)
                            .font(.system(size: 12))
                        Spacer()
                        Button { colorVM.errorMessage = nil } label: {
                            Image(systemName: "xmark")
                                .font(.system(size: 11))
                        }
                    }
                    .foregroundColor(.red)
                    .padding(.horizontal, Theme.Spacing.md)
                    .padding(.vertical, Theme.Spacing.sm)
                    .background(Color.red.opacity(0.08))
                }

                // Swatch grid
                if colorVM.colors.isEmpty {
                    Spacer()
                    if colorVM.isLoading {
                        ProgressView()
                            .frame(maxWidth: .infinity)
                    } else {
                        Text("No styles available.")
                            .font(.subheadline)
                            .foregroundColor(Theme.Color.muted)
                            .frame(maxWidth: .infinity)
                    }
                    Spacer()
                } else {
                    swatchRow
                        .padding(.horizontal, Theme.Spacing.md)
                        .padding(.top, Theme.Spacing.lg)
                }

                Spacer()
            }
            .navigationTitle("ID Card Style")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") { presentationMode.wrappedValue.dismiss() }
                        .font(.system(size: 15, weight: .semibold))
                        .foregroundColor(Theme.Color.primary)
                }
            }
        }
        .navigationViewStyle(.stack)
    }

    // MARK: — Swatch row

    private var swatchRow: some View {
        HStack(spacing: Theme.Spacing.lg) {
            ForEach(colorVM.colors) { theme in
                swatchButton(theme)
            }
            Spacer()
        }
    }

    @ViewBuilder
    private func swatchButton(_ theme: AcademyIDColorTheme) -> some View {
        let isActive = colorVM.activeColorId == theme.id

        Button {
            let animation: Animation = reduceMotion
                ? .easeInOut(duration: 0.20)
                : .spring(response: 0.30, dampingFraction: 0.75)
            withAnimation(animation) {
                Task { await colorVM.select(colorId: theme.id, using: authManager) }
            }
        } label: {
            VStack(spacing: 6) {
                ZStack {
                    // Dot colour circle
                    Circle()
                        .fill(Color(hex: theme.dotColor))
                        .frame(width: swatchSize, height: swatchSize)
                        .overlay(
                            Circle()
                                .stroke(
                                    isActive ? Theme.Color.primary : Color.clear,
                                    lineWidth: 2.5
                                )
                        )
                        .shadow(
                            color: isActive ? Theme.Color.primary.opacity(0.30) : .clear,
                            radius: 4
                        )

                    // Checkmark for active colour
                    if isActive {
                        Image(systemName: "checkmark")
                            .font(.system(size: 14, weight: .bold))
                            .foregroundColor(checkmarkColor(for: theme.dotColor))
                            .transition(.scale.combined(with: .opacity))
                    }
                }
                .animation(.spring(response: 0.25, dampingFraction: 0.70), value: isActive)

                Text(theme.label)
                    .font(.system(size: 11, weight: isActive ? .semibold : .regular))
                    .foregroundColor(isActive ? Theme.Color.primary : Theme.Color.muted)
            }
        }
        .buttonStyle(.plain)
        .disabled(colorVM.isLoading)
    }

    // MARK: — Checkmark colour (white on dark swatches, dark on light)

    private func checkmarkColor(for hexColor: String) -> Color {
        // Charcoal swatch is near-black → white checkmark; others → dark
        let h = hexColor.trimmingCharacters(in: .init(charactersIn: "#"))
        var rgb: UInt64 = 0
        Scanner(string: h).scanHexInt64(&rgb)
        let r = Double((rgb >> 16) & 0xFF) * 299
        let g = Double((rgb >>  8) & 0xFF) * 587
        let b = Double( rgb        & 0xFF) * 114
        let brightness = (r + g + b) / (255 * 1000)
        return brightness < 0.40 ? .white : .black.opacity(0.75)
    }
}
