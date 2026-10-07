#!/usr/bin/env node
// Loads the shipped extension detectors in Node and prints their predictions
// as JSON, so scripts/check_parity.py can diff them against the Python
// implementations the eval harness scores. Reads a JSON array of
// {id, prompt, prior_turns} on stdin.
//
// The detector files are browser IIFEs that hang their exports off `window`,
// so they're run in a vm context with a `window` shim rather than required as
// modules. Nothing here may transform the detector source: the point is to
// exercise the exact bytes that ship.
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const SRC = path.join(path.resolve(__dirname, ".."), "extension", "src");

// `window` has to be the context's global object, not a property on it: the
// detectors assign to `window.HowToChat` and then read bare `HowToChat`,
// which only resolves if the two are the same object, as they are in a page.
const sandbox = {};
sandbox.window = sandbox;
vm.createContext(sandbox);
for (const file of ["detector.js", "safety-detector.js"]) {
  const code = fs.readFileSync(path.join(SRC, file), "utf8");
  vm.runInContext(code, sandbox, { filename: file });
}

const { detector, safetyDetector } = sandbox.HowToChat;

const records = JSON.parse(fs.readFileSync(0, "utf8"));
const out = records.map((r) => {
  const framing = detector.predict(r.prompt, r.prior_turns || []);
  const safety = safetyDetector.predict(r.prompt);
  return {
    id: r.id,
    framing: { should_flag: framing.shouldFlag, cues: framing.cues },
    safety: { should_flag: safety.shouldFlag, signals: safety.signals },
  };
});

process.stdout.write(JSON.stringify(out));
