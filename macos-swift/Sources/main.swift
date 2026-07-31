import AppKit
import Darwin

if CommandLine.arguments.contains("--self-test") { fputs("native-self-test: main entered\n", stderr) }
let application = NSApplication.shared
if CommandLine.arguments.contains("--self-test") { fputs("native-self-test: application created\n", stderr) }
let applicationDelegate = AppDelegate()
application.delegate = applicationDelegate
if CommandLine.arguments.contains("--self-test") { fputs("native-self-test: delegate assigned\n", stderr) }
application.run()
