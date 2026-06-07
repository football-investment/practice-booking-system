import Foundation

// MARK: — Base URL

// Simulator: localhost works directly.
// Physical iPhone: replace with your Mac's local IP, e.g. http://192.168.1.100:8000
// Production:      replace with the production domain.
private let kBaseURL = "http://localhost:8000"

// MARK: — APIClient

// Minimal URLSession wrapper for Phase B (login only).
// Phase C adds: Authorization header injection, 401 refresh/retry, GET support.
enum APIClient {

    static func post<B: Encodable, T: Decodable>(
        path:  String,
        body:  B,
        token: String? = nil
    ) async throws -> T {
        guard let url = URL(string: kBaseURL + path) else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.httpBody = try JSONEncoder().encode(body)

        if let token = token {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let (data, response) = try await perform(request)

        guard let http = response as? HTTPURLResponse else {
            throw APIError.networkError(URLError(.badServerResponse))
        }

        guard (200...299).contains(http.statusCode) else {
            let detail = try? JSONDecoder().decode(ErrorBody.self, from: data)
            throw APIError.httpError(statusCode: http.statusCode, detail: detail?.detail)
        }

        do {
            return try JSONDecoder().decode(T.self, from: data)
        } catch {
            throw APIError.decodingError
        }
    }

    // URLSession.data(for:) async is iOS 15+.
    // This continuation wrapper is iOS 13+ compatible.
    private static func perform(_ request: URLRequest) async throws -> (Data, URLResponse) {
        try await withCheckedThrowingContinuation { continuation in
            URLSession.shared.dataTask(with: request) { data, response, error in
                if let error = error {
                    continuation.resume(throwing: APIError.networkError(error))
                } else if let data = data, let response = response {
                    continuation.resume(returning: (data, response))
                } else {
                    continuation.resume(throwing: APIError.networkError(URLError(.unknown)))
                }
            }.resume()
        }
    }
}

// MARK: — APIError

enum APIError: Error {
    case invalidURL
    case httpError(statusCode: Int, detail: String?)
    case decodingError
    case networkError(Error)
}

private struct ErrorBody: Decodable {
    let detail: String?
}
