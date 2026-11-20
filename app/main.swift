// Macquarium helper app.
// Keeps a live aquarium window directly behind every Terminal.app window, and
// brings it forward as an interactive "care mode" on request (macquarium://care).
//
// Build:  swiftc -O main.swift -framework AppKit -framework WebKit -o Macquarium

import Cocoa
import WebKit

let terminalBundleID = "com.apple.Terminal"
let stateDir = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent(".macquarium/state")

// MARK: - Logging (~/.macquarium/state/app.log, shown by `macquarium doctor`)
func mqlog(_ msg: String) {
    let url = stateDir.appendingPathComponent("app.log")
    let line = "\(ISO8601DateFormatter().string(from: Date()))  \(msg)\n"
    if let h = try? FileHandle(forWritingTo: url) {
        h.seekToEndOfFile(); h.write(line.data(using: .utf8)!); h.closeFile()
    } else {
        try? line.write(to: url, atomically: true, encoding: .utf8)
    }
}

// MARK: - A borderless window that can still take keyboard focus in care mode
final class TankWindow: NSWindow {
    override var canBecomeKey: Bool { return true }
    override var canBecomeMain: Bool { return true }
}

// MARK: - Weak wrapper so WKUserContentController doesn't retain the tank forever
final class WeakHandler: NSObject, WKScriptMessageHandler {
    weak var target: WKScriptMessageHandler?
    init(_ target: WKScriptMessageHandler) { self.target = target }
    func userContentController(_ c: WKUserContentController, didReceive m: WKScriptMessage) {
        target?.userContentController(c, didReceive: m)
    }
}

// MARK: - One tank per Terminal window
final class Tank: NSObject, WKScriptMessageHandler, WKNavigationDelegate {
    let window: TankWindow
    let web: WKWebView
    weak var app: AppDelegate?
    private var loaded = false
    private var pending: [String] = []

    init(app: AppDelegate, frame: NSRect, dim: Double) {
        self.app = app
        window = TankWindow(contentRect: frame, styleMask: [.borderless], backing: .buffered, defer: false)
        let config = WKWebViewConfiguration()
        let saved = (try? String(contentsOf: stateDir.appendingPathComponent("tank.json"), encoding: .utf8)) ?? "null"
        let boot = WKUserScript(source: "window.__mqSaved = \(saved); window.__mqDim = \(dim);", injectionTime: .atDocumentStart, forMainFrameOnly: true)
        config.userContentController.addUserScript(boot)
        web = WKWebView(frame: NSRect(origin: .zero, size: frame.size), configuration: config)
        super.init()
        config.userContentController.add(WeakHandler(self), name: "mq")
        web.navigationDelegate = self
        web.autoresizingMask = [.width, .height]

        // rounded corners that match Terminal's, so no square corners poke out
        let corner = UserDefaults.standard.object(forKey: "corner") as? Double ?? 16
        let box = NSView(frame: NSRect(origin: .zero, size: frame.size))
        box.wantsLayer = true
        box.layer?.cornerRadius = CGFloat(corner)
        box.layer?.masksToBounds = true
        box.layer?.backgroundColor = NSColor(calibratedRed: 0.01, green: 0.09, blue: 0.17, alpha: 1).cgColor
        box.autoresizingMask = [.width, .height]
        web.frame = box.bounds
        box.addSubview(web)
        window.isOpaque = false
        window.backgroundColor = .clear
        window.hasShadow = false
        window.ignoresMouseEvents = true
        window.isReleasedWhenClosed = false
        window.level = .normal
        // .transient = hidden in Mission Control / Exposé instead of floating on its own
        window.collectionBehavior = [.canJoinAllSpaces, .transient, .fullScreenAuxiliary, .ignoresCycle]
        window.contentView = box

        if let dir = Bundle.main.resourceURL?.appendingPathComponent("tank") {
            let index = dir.appendingPathComponent("index.html")
            mqlog("tank window created \(Int(frame.width))x\(Int(frame.height)); loading \(index.path) exists=\(FileManager.default.fileExists(atPath: index.path))")
            // plain file URL only: WebKit rejects file URLs with a query string (that crashed v2.0)
            web.loadFileURL(index, allowingReadAccessTo: dir)
        }
    }

    func js(_ code: String) {
        if loaded { web.evaluateJavaScript(code, completionHandler: nil) } else { pending.append(code) }
    }

    func setMode(_ mode: String) {
        js("window.__pendingMode = '\(mode)'; if (window.mq) mq.setMode('\(mode)');")
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        mqlog("page failed: \(error.localizedDescription)")
    }
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        mqlog("page failed to start: \(error.localizedDescription)")
    }
    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
        mqlog("web content process crashed; reloading"); webView.reload()
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        mqlog("page loaded")
        loaded = true
        for code in pending { web.evaluateJavaScript(code, completionHandler: nil) }
        pending.removeAll()
    }

    func userContentController(_ c: WKUserContentController, didReceive message: WKScriptMessage) {
        guard let body = message.body as? [String: Any], let type = body["type"] as? String else { return }
        if type == "back" { app?.endCare() }
        if type == "log" { mqlog("js: \(body["msg"] as? String ?? "")") }
        if type == "stats" { app?.saveStats(body) }
    }

    func close() {
        web.configuration.userContentController.removeScriptMessageHandler(forName: "mq")
        window.orderOut(nil)
        window.close()
    }
}

// MARK: - App
final class AppDelegate: NSObject, NSApplicationDelegate {
    var tanks: [Int: Tank] = [:]
    var careTank: Tank?
    var statusItem: NSStatusItem!
    var pauseItem: NSMenuItem!
    var paused = false
    var timer: Timer?

    var dim: Double {
        get { return UserDefaults.standard.object(forKey: "dim") as? Double ?? 0.35 }
        set { UserDefaults.standard.set(newValue, forKey: "dim") }
    }

    func applicationWillFinishLaunching(_ notification: Notification) {
        NSAppleEventManager.shared().setEventHandler(self, andSelector: #selector(handleURL(_:reply:)),
            forEventClass: AEEventClass(kInternetEventClass), andEventID: AEEventID(kAEGetURL))
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        // only one Macquarium at a time
        let me = NSRunningApplication.current
        if NSRunningApplication.runningApplications(withBundleIdentifier: Bundle.main.bundleIdentifier ?? "").contains(where: { $0 != me }) {
            NSApp.terminate(nil); return
        }
        NSApp.setActivationPolicy(.accessory)
        try? FileManager.default.createDirectory(at: stateDir, withIntermediateDirectories: true)
        try? "".write(to: stateDir.appendingPathComponent("app.log"), atomically: true, encoding: .utf8)
        mqlog("Macquarium started (macOS \(ProcessInfo.processInfo.operatingSystemVersionString)); resources=\(Bundle.main.resourceURL?.path ?? "nil")")
        buildMenu()
        let t = Timer(timeInterval: 1.0 / 30.0, repeats: true) { [weak self] _ in self?.sync() }
        RunLoop.main.add(t, forMode: .common)
        timer = t
    }

    @objc func handleURL(_ event: NSAppleEventDescriptor, reply: NSAppleEventDescriptor) {
        guard let s = event.paramDescriptor(forKeyword: keyDirectObject)?.stringValue, let url = URL(string: s) else { return }
        switch url.host ?? "" {
        case "care": DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) { self.startCare(tries: 0) }
        case "quit": NSApp.terminate(nil)
        default: break
        }
    }

    // MARK: menu bar
    func buildMenu() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        // hand-drawn fish sketch; template image so it turns white/black with the menu bar
        if let icon = Bundle.main.image(forResource: "MenuIcon") {
            icon.isTemplate = true
            icon.size = NSSize(width: 18, height: 18)
            statusItem.button?.image = icon
        } else {
            statusItem.button?.title = "🐠"
        }
        let menu = NSMenu()
        let care = NSMenuItem(title: "Take care of the aquarium", action: #selector(careFromMenu), keyEquivalent: "")
        care.target = self
        menu.addItem(care)
        let bright = NSMenuItem(title: "Tank brightness", action: nil, keyEquivalent: "")
        let sub = NSMenu()
        for (name, value) in [("Bright", 0.1), ("Normal", 0.35), ("Dim", 0.55), ("Very dim", 0.72)] {
            let item = NSMenuItem(title: name, action: #selector(setBrightness(_:)), keyEquivalent: "")
            item.representedObject = value
            item.target = self
            item.state = abs(value - dim) < 0.01 ? .on : .off
            sub.addItem(item)
        }
        bright.submenu = sub
        menu.addItem(bright)
        pauseItem = NSMenuItem(title: "Hide the tank", action: #selector(togglePause), keyEquivalent: "")
        pauseItem.target = self
        menu.addItem(pauseItem)
        menu.addItem(.separator())
        menu.addItem(NSMenuItem(title: "Quit Macquarium", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q"))
        statusItem.menu = menu
    }

    @objc func careFromMenu() { startCare(tries: 0) }

    @objc func setBrightness(_ sender: NSMenuItem) {
        guard let v = sender.representedObject as? Double else { return }
        dim = v
        sender.menu?.items.forEach { $0.state = ($0 === sender) ? .on : .off }
        for t in tanks.values { t.js("if (window.mq) mq.setDim(\(v));") }
    }

    @objc func togglePause() {
        paused.toggle()
        pauseItem.title = paused ? "Show the tank" : "Hide the tank"
        for t in tanks.values {
            t.js("if (window.mq) mq.pause(\(paused));")
            if paused { t.window.orderOut(nil) }
        }
    }

    // MARK: following Terminal windows
    func terminalPIDs() -> Set<Int32> {
        return Set(NSRunningApplication.runningApplications(withBundleIdentifier: terminalBundleID).map { $0.processIdentifier })
    }

    /// On-screen Terminal windows, front to back, plus the full on-screen window order.
    func terminalWindows() -> (wins: [(num: Int, rect: CGRect)], order: [Int]) {
        guard let list = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] else { return ([], []) }
        let pids = terminalPIDs()
        var wins: [(num: Int, rect: CGRect)] = []
        var order: [Int] = []
        for w in list {
            guard let num = w[kCGWindowNumber as String] as? Int else { continue }
            order.append(num)
            guard let pid = w[kCGWindowOwnerPID as String] as? Int32, pids.contains(pid),
                  (w[kCGWindowLayer as String] as? Int) == 0,
                  let b = w[kCGWindowBounds as String] as? NSDictionary,
                  let rect = CGRect(dictionaryRepresentation: b as CFDictionary),
                  rect.width > 120, rect.height > 80 else { continue }
            wins.append((num: num, rect: rect))
        }
        return (wins, order)
    }

    func cocoaRect(_ r: CGRect) -> NSRect {
        let mainHeight = NSScreen.screens.first?.frame.height ?? (r.origin.y + r.height)
        return NSRect(x: r.origin.x, y: mainHeight - r.origin.y - r.height, width: r.width, height: r.height)
    }

    var lastReport = ""
    func report(_ s: String) { if s != lastReport { lastReport = s; mqlog(s) } }

    func sync() {
        if paused { return }
        let (wins, order) = terminalWindows()
        var stack: [String] = []
        for (num, _) in wins {
            if let t = tanks[num], let i = order.firstIndex(of: num) {
                let next = i + 1 < order.count ? order[i + 1] : -1
                var where_ = "offscreen"
                if let ti = order.firstIndex(of: t.window.windowNumber) { where_ = String(ti) }
                stack.append(next == t.window.windowNumber ? "behind" : "NOT behind (tank at index \(where_), terminal at \(i))")
            }
        }
        report("terminal windows: \(wins.count) (pids \(terminalPIDs().sorted())), tanks: \(tanks.count), stacking: \(stack)")
        var seen = Set<Int>()
        for (num, rect) in wins {
            seen.insert(num)
            let frame = cocoaRect(rect)
            let tank: Tank
            if let existing = tanks[num] { tank = existing } else {
                tank = Tank(app: self, frame: frame, dim: dim)
                tanks[num] = tank
            }
            let old = tank.window.frame
            if old != frame {
                // moved without resizing = the window is being dragged: slosh the tank
                if old.size == frame.size && tank.window.isVisible {
                    let dx = frame.origin.x - old.origin.x, dy = -(frame.origin.y - old.origin.y)
                    tank.js("if (window.mq) mq.shake(\(Double(dx)), \(Double(dy)));")
                }
                tank.window.setFrame(frame, display: true)
            }
            if tank === careTank { continue }
            // keep the tank directly behind its Terminal window
            if let i = order.firstIndex(of: num) {
                let next = i + 1 < order.count ? order[i + 1] : -1
                if next != tank.window.windowNumber || !tank.window.isVisible {
                    tank.window.order(.below, relativeTo: num)
                }
            }
        }
        for (num, tank) in tanks where !seen.contains(num) {
            if tank === careTank { continue }
            if windowExists(num) { tank.window.orderOut(nil) }   // minimised / hidden / other Space
            else { tank.close(); tanks[num] = nil }               // window closed
        }
    }

    func windowExists(_ num: Int) -> Bool {
        guard let list = CGWindowListCopyWindowInfo([.optionIncludingWindow], CGWindowID(num)) as? [[String: Any]] else { return false }
        return !list.isEmpty
    }

    // MARK: care mode
    func startCare(tries: Int) {
        if paused { togglePause() }
        sync()
        guard let front = terminalWindows().wins.first, let tank = tanks[front.num] else {
            if tries < 10 { DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) { self.startCare(tries: tries + 1) } }
            return
        }
        if let old = careTank, old !== tank { endCare() }
        careTank = tank
        tank.window.ignoresMouseEvents = false
        tank.window.level = .floating
        NSApp.activate(ignoringOtherApps: true)
        tank.window.makeKeyAndOrderFront(nil)
        tank.window.makeFirstResponder(tank.web)
        tank.setMode("care")
    }

    func endCare() {
        guard let tank = careTank else { return }
        tank.setMode("ambient")
        tank.window.ignoresMouseEvents = true
        tank.window.level = .normal
        careTank = nil
        NSRunningApplication.runningApplications(withBundleIdentifier: terminalBundleID).first?.activate(options: [])
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.15) { self.sync() }
    }

    func saveStats(_ body: [String: Any]) {
        let full = body["full"] as? Int ?? 0, joy = body["joy"] as? Int ?? 0
        let t = (body["t"] as? Double) ?? Date().timeIntervalSince1970 * 1000
        let json = "{\"full\": \(full), \"joy\": \(joy), \"t\": \(Int64(t))}\n"
        try? json.write(to: stateDir.appendingPathComponent("tank.json"), atomically: true, encoding: .utf8)
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()
