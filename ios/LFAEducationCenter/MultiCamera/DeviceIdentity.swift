import Foundation
import Security

enum DeviceIdentity {

    static let keychainAccount = "lfa_mc_device_uuid"

    static func stableDeviceUUID() -> String {
        if let stored = load() { return stored }
        let fresh = UUID().uuidString
        save(fresh)
        return fresh
    }

    static func logSafeIdentifier() -> String {
        let full = stableDeviceUUID()
        let suffix = full.suffix(8)
        return "...\(suffix)"
    }

    #if DEBUG
    static func resetForTesting() {
        delete()
    }
    #endif

    // MARK: - Keychain (isolated from KeychainService.clearAll)

    private static let service = "com.lovas-zoltan.lfa-education-center.device"

    private static func save(_ value: String) {
        guard let data = value.data(using: .utf8) else { return }
        let query: [String: Any] = [
            kSecClass          as String: kSecClassGenericPassword,
            kSecAttrService    as String: service,
            kSecAttrAccount    as String: keychainAccount,
            kSecValueData      as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlock,
        ]
        SecItemDelete(query as CFDictionary)
        SecItemAdd(query as CFDictionary, nil)
    }

    private static func load() -> String? {
        let query: [String: Any] = [
            kSecClass       as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: keychainAccount,
            kSecReturnData  as String: kCFBooleanTrue as Any,
            kSecMatchLimit  as String: kSecMatchLimitOne,
        ]
        var item: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &item) == errSecSuccess,
              let data = item as? Data,
              let string = String(data: data, encoding: .utf8)
        else { return nil }
        return string
    }

    private static func delete() {
        let query: [String: Any] = [
            kSecClass       as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: keychainAccount,
        ]
        SecItemDelete(query as CFDictionary)
    }
}
