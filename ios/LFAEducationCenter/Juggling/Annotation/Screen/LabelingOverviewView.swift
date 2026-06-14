import SwiftUI
import AVFoundation

// MARK: — ThumbnailSession (AN-3B2A P2B-5B)
//
// Owns the shared EventStillFrameGenerator for the overview sheet lifetime.
// Per-event load tasks are tracked by UUID so they can be cancelled individually.
// clearAll() is called when the sheet is dismissed.

@MainActor
private final class ThumbnailSession: ObservableObject {
    let generator = EventStillFrameGenerator(maxCacheSize: 20)
    var loadTasks: [UUID: Task<Void, Never>] = [:]

    func clearAll() {
        loadTasks.values.forEach { $0.cancel() }
        loadTasks = [:]
        generator.clearCache()
    }
}

// MARK: — LabelingOverviewView (AN-3B2A P2B-5B)
//
// Shows ALL active events in chronological order regardless of sync state.
// Each row: still-frame thumbnail, timestamp, type label or "Nincs címkézve",
// status badge, and a per-event CTA button.
//
// Progress bar: labeledCount / activeEvents.count.
// "Következő címkézetlen" bottom CTA when nextUnlabeledId != nil.
//
// Navigation callbacks (onOpenEvent, onNextUnlabeled) are wired in P2B-5D.
// Main screen integration is P2B-5E.
// No backend sync, no Finish flow.

struct LabelingOverviewView: View {

    @ObservedObject var vm: JugglingAnnotationViewModel
    var videoURL: URL?
    var onClose: () -> Void

    // P2B-5D will supply these; nil = stub (no-op) for P2B-5B.
    var onOpenEvent:     ((UUID) -> Void)? = nil
    var onNextUnlabeled: (() -> Void)?     = nil

    @StateObject private var thumbSession = ThumbnailSession()
    @State private var thumbnails: [UUID: UIImage] = [:]
    @State private var loadingIds: Set<UUID>       = []

    // MARK: — Body

    var body: some View {
        NavigationView {
            VStack(spacing: 0) {
                progressSection
                Divider()
                eventScrollView
                Divider()
                bottomCTA
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Címkézés — \(vm.activeEvents.count) esemény")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button {
                        thumbSession.clearAll()
                        onClose()
                    } label: {
                        Image(systemName: "xmark")
                            .font(.system(size: 16, weight: .medium))
                    }
                    .accessibilityLabel("Bezárás")
                }
            }
        }
        .navigationViewStyle(.stack)
    }

    // MARK: — Progress section

    private var progressSection: some View {
        let total = vm.activeEvents.count
        let done  = vm.labeledCount
        let frac  = total > 0 ? Double(done) / Double(total) : 0.0

        return VStack(spacing: 4) {
            ProgressView(value: frac)
                .progressViewStyle(.linear)
                .padding(.horizontal, 16)
            Text("\(done) / \(total) kész")
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .padding(.vertical, 10)
        .background(Color(.systemBackground))
    }

    // MARK: — Event list

    private var sortedEvents: [ContactEventDraft] {
        vm.activeEvents.sorted { $0.timestampMs < $1.timestampMs }
    }

    @ViewBuilder
    private var eventScrollView: some View {
        if vm.activeEvents.isEmpty {
            emptyState
        } else {
            List {
                ForEach(sortedEvents) { draft in
                    EventOverviewCard(
                        draft:              draft,
                        taxonomy:           vm.taxonomy,
                        thumbnail:          thumbnails[draft.deviceEventId],
                        isLoadingThumbnail: loadingIds.contains(draft.deviceEventId)
                    ) {
                        onOpenEvent?(draft.deviceEventId)
                    }
                    .onAppear { loadThumbnail(for: draft) }
                    .listRowInsets(EdgeInsets(top: 6, leading: 16, bottom: 6, trailing: 16))
                    .listRowBackground(Color(.systemBackground))
                }
            }
            .listStyle(.plain)
        }
    }

    private var emptyState: some View {
        VStack(spacing: 10) {
            Image(systemName: "clock.badge.questionmark")
                .font(.system(size: 40))
                .foregroundColor(.secondary)
            Text("Nincs jelölt esemény")
                .font(.headline)
                .foregroundColor(.secondary)
            Text("Nyomj a + gombra az annotációs képernyőn egy kontakt jelöléséhez.")
                .font(.caption)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: — Bottom CTA

    @ViewBuilder
    private var bottomCTA: some View {
        if vm.nextUnlabeledId != nil {
            Button {
                onNextUnlabeled?()
            } label: {
                Text("Következő címkézetlen")
                    .font(.body.weight(.semibold))
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 10)
                    .foregroundColor(.white)
                    .background(Color.accentColor)
                    .clipShape(RoundedRectangle(cornerRadius: 10))
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 10)
            .background(Color(.systemBackground))
            .accessibilityLabel("Következő megcímkézetlen esemény megnyitása")
        } else if !vm.activeEvents.isEmpty {
            HStack(spacing: 6) {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundColor(.green)
                Text("Minden esemény megcímkézve")
                    .font(.subheadline.weight(.semibold))
                    .foregroundColor(.green)
            }
            .padding(.vertical, 14)
            .frame(maxWidth: .infinity)
            .background(Color(.systemBackground))
        }
    }

    // MARK: — Thumbnail loading (lazy, on card appear)

    private func loadThumbnail(for draft: ContactEventDraft) {
        guard let videoURL else { return }
        let id = draft.deviceEventId
        guard thumbnails[id] == nil, !loadingIds.contains(id) else { return }

        loadingIds.insert(id)
        let asset   = AVAsset(url: videoURL)
        let ms      = draft.timestampMs
        let videoId = vm.videoId

        let task = Task {
            let img = await thumbSession.generator.image(for: asset, videoId: videoId, timestampMs: ms)
            guard !Task.isCancelled else { return }
            thumbnails[id] = img
            loadingIds.remove(id)
        }
        thumbSession.loadTasks[id] = task
    }
}

// MARK: — EventOverviewCard

private struct EventOverviewCard: View {

    let draft:              ContactEventDraft
    let taxonomy:           TaxonomyDocument?
    let thumbnail:          UIImage?
    let isLoadingThumbnail: Bool
    let onCTA:              () -> Void

    var body: some View {
        HStack(alignment: .center, spacing: 12) {
            thumbnailView
            infoStack
            Spacer(minLength: 4)
            ctaButton
        }
        .frame(minHeight: 72)
        .accessibilityElement(children: .combine)
        .accessibilityLabel(cardAccessibilityLabel)
    }

    // MARK: — Thumbnail (80×60 pt)

    private var thumbnailView: some View {
        ZStack {
            Color.black

            if let img = thumbnail {
                Image(uiImage: img)
                    .resizable()
                    .scaledToFill()
            } else if isLoadingThumbnail {
                ProgressView()
                    .progressViewStyle(CircularProgressViewStyle(tint: .white))
                    .scaleEffect(0.75)
            } else {
                Image(systemName: "photo.slash")
                    .foregroundColor(Color(.systemGray3))
                    .font(.system(size: 16))
            }
        }
        .frame(width: 80, height: 60)
        .clipShape(RoundedRectangle(cornerRadius: 6))
        .overlay(
            RoundedRectangle(cornerRadius: 6)
                .stroke(Color(.systemGray5), lineWidth: 1)
        )
        .accessibilityHidden(true)
    }

    // MARK: — Info stack

    private var infoStack: some View {
        VStack(alignment: .leading, spacing: 4) {
            // Timestamp row
            HStack(spacing: 4) {
                Image(systemName: "clock")
                    .font(.caption2)
                    .foregroundColor(.secondary)
                Text(PlaybackControlBar.formatTimestamp(ms: draft.timestampMs))
                    .font(.caption2.monospacedDigit())
                    .foregroundColor(.secondary)
            }

            // Type label
            Text(typeLabel)
                .font(.subheadline)
                .foregroundColor(draft.contactType != nil ? .primary : Color(.tertiaryLabel))
                .lineLimit(1)

            // Status badge
            HStack(spacing: 4) {
                Circle()
                    .fill(EventTimelineView.pinColor(for: draft.syncStatus))
                    .frame(width: 6, height: 6)
                Text(statusLabel)
                    .font(.caption2)
                    .foregroundColor(.secondary)
                if let side = draft.side {
                    Text("·")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                    Text(side == "left" ? "Bal" : side == "right" ? "Jobb" : side)
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
            }
        }
    }

    private var typeLabel: String {
        guard let key = draft.contactType else { return "Nincs címkézve" }
        return taxonomy?.groups
            .flatMap { $0.contactTypes }
            .first { $0.key == key }?
            .labelHu ?? key
    }

    private var statusLabel: String {
        switch draft.syncStatus {
        case .unlabeled:           return "Nem jelölt"
        case .labelPending:        return "Folyamatban"
        case .localOnly:           return "Helyi"
        case .syncing:             return "Szinkronizálás…"
        case .synced:              return "Szinkronizálva"
        case .updating:            return "Frissítés…"
        case .deleting:            return "Törlés…"
        case .deleted:             return "Törölve"
        case .failedPermanent:     return "Hiba"
        case .retryPending:        return "Újrapróbálás"
        case .conflicted:          return "Konfliktus"
        case .needsReconciliation: return "Ellenőrzés szükséges"
        }
    }

    // MARK: — CTA button

    @ViewBuilder
    private var ctaButton: some View {
        let (label, enabled) = ctaConfig
        if case .inFlight = ctaState {
            ProgressView()
                .progressViewStyle(CircularProgressViewStyle(tint: Color(.systemGray3)))
                .scaleEffect(0.75)
                .frame(width: 56, height: 32)
        } else {
            Button(label) {
                if enabled { onCTA() }
            }
            .font(.caption.weight(.semibold))
            .foregroundColor(enabled ? .accentColor : Color(.systemGray3))
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .frame(minWidth: 56)
            .background(Color(.systemGray6))
            .clipShape(RoundedRectangle(cornerRadius: 8))
            .disabled(!enabled)
            .accessibilityLabel("\(label), \(typeLabel)")
        }
    }

    private enum CTAState { case action, inFlight }
    private var ctaState: CTAState {
        switch draft.syncStatus {
        case .syncing, .updating, .deleting: return .inFlight
        default:                             return .action
        }
    }

    private var ctaConfig: (label: String, enabled: Bool) {
        switch draft.syncStatus {
        case .unlabeled:           return ("Címkézés",    true)
        case .labelPending:        return ("Folytatás",   true)
        case .localOnly:           return ("Szerkesztés", true)
        case .synced:              return ("Szerkesztés", true)
        case .retryPending:        return ("Szerkesztés", true)
        case .failedPermanent:     return ("Újra",        true)
        case .needsReconciliation: return ("Szerkesztés", true)
        case .conflicted:          return ("Feloldás",    false) // AN-3C scope
        case .syncing, .updating, .deleting, .deleted:
                                   return ("…",           false)
        }
    }

    // MARK: — Accessibility

    private var cardAccessibilityLabel: String {
        let time = PlaybackControlBar.formatTimestamp(ms: draft.timestampMs)
        return "\(time), \(typeLabel), \(statusLabel)"
    }
}
