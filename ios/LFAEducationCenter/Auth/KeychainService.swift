import Foundation
import Security

// Keychain read/write/delete for auth tokens.
// Service: com.lovas-zoltan.lfa-education-center
// Access:  kSecAttrAccessibleAfterFirstUnlock — background refresh supported.
enum KeychainService {

    static let service         = "com.lovas-zoltan.lfa-education-center"
    static let accessTokenKey  = "lfa_access_token"
    static let refreshTokenKey = "lfa_refresh_token"

    @discardableResult
    static func save(_ value: String, account: String) -> Bool {
        guard let data = value.data(using: .utf8) else { return false }

        let query: [String: Any] = [
            kSecClass          as String: kSecClassGenericPassword,
            kSecAttrService    as String: service,
            kSecAttrAccount    as String: account,
            kSecValueData      as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlock,
        ]

        SecItemDelete(query as CFDictionary)
        return SecItemAdd(query as CFDictionary, nil) == errSecSuccess
    }

    static func load(account: String) -> String? {
        let query: [String: Any] = [
            kSecClass       as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData  as String: kCFBooleanTrue as Any,
            kSecMatchLimit  as String: kSecMatchLimitOne,
        ]

        var item: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &item) == errSecSuccess,
              let data   = item as? Data,
              let string = String(data: data, encoding: .utf8)
        else { return nil }
        return string
    }

    static func delete(account: String) {
        let query: [String: Any] = [
            kSecClass       as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
        SecItemDelete(query as CFDictionary)
    }

    static func clearAll() {
        delete(account: accessTokenKey)
        delete(account: refreshTokenKey)
    }
}
