import SwiftUI
import WebKit

struct ContentView: View {
    @EnvironmentObject var serverManager: ServerManager

    var body: some View {
        Group {
            if serverManager.isReady {
                BrainWebView(url: URL(string: "http://127.0.0.1:\(serverManager.port)")!)
                    .ignoresSafeArea()
            } else if let error = serverManager.errorMessage {
                ErrorView(message: error)
            } else {
                SplashView()
            }
        }
        .frame(minWidth: 900, minHeight: 650)
    }
}

struct BrainWebView: NSViewRepresentable {
    let url: URL

    func makeNSView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.preferences.setValue(true, forKey: "developerExtrasEnabled")
        config.userContentController.add(context.coordinator, name: "agentKeys")
        config.userContentController.add(context.coordinator, name: "clipboard")
        // Allow WebSocket connections to localhost
        config.limitsNavigationsToAppBoundDomains = false
        let webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = context.coordinator
        webView.load(URLRequest(url: url))
        return webView
    }

    func updateNSView(_ nsView: WKWebView, context: Context) {}

    func makeCoordinator() -> Coordinator { Coordinator() }

    class Coordinator: NSObject, WKNavigationDelegate, WKScriptMessageHandler {
        func webView(
            _ webView: WKWebView,
            decidePolicyFor action: WKNavigationAction,
            decisionHandler: @escaping (WKNavigationActionPolicy) -> Void
        ) {
            if let host = action.request.url?.host, host != "127.0.0.1" {
                NSWorkspace.shared.open(action.request.url!)
                decisionHandler(.cancel)
                return
            }
            decisionHandler(.allow)
        }

        func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
            if message.name == "clipboard", let text = message.body as? String {
                NSPasteboard.general.clearContents()
                NSPasteboard.general.setString(text, forType: .string)
                return
            }
            guard message.name == "agentKeys", let body = message.body as? [String: Any] else { return }
            if let key = body["anthropic_api_key"] as? String, !key.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                KeychainHelper.save(key: "anthropic_api_key", value: key.trimmingCharacters(in: .whitespacesAndNewlines))
            }
            if let key = body["openai_api_key"] as? String, !key.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                KeychainHelper.save(key: "openai_api_key", value: key.trimmingCharacters(in: .whitespacesAndNewlines))
            }
        }
    }
}

struct SplashView: View {
    var body: some View {
        VStack(spacing: 20) {
            BrainLogoView(size: 80)
            Text("Starting brain²...")
                .font(.title3)
                .foregroundColor(.secondary)
            ProgressView()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(NSColor.windowBackgroundColor))
    }
}

struct ErrorView: View {
    let message: String

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 40))
                .foregroundColor(.red)
            Text("Failed to start brain²")
                .font(.title2.bold())
            Text(message)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .frame(maxWidth: 400)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(NSColor.windowBackgroundColor))
    }
}
