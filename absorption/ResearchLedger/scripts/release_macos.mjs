#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repositoryDirectory = path.resolve(scriptDirectory, "..");
const tauriDirectory = path.join(repositoryDirectory, "apps", "desktop", "src-tauri");
const releaseConfigurationPath = path.join(repositoryDirectory, "config", "release", "macos.json");
const notarizationEnvironmentVariables = [
  "APPLE_API_ISSUER",
  "APPLE_API_KEY",
  "APPLE_API_KEY_PATH",
  "APPLE_ID",
  "APPLE_PASSWORD",
  "APPLE_TEAM_ID",
];

function fail(message) {
  throw new Error(`macOS release preflight failed: ${message}`);
}

function commandText(executable, arguments_) {
  return [executable, ...arguments_].join(" ");
}

function run(executable, arguments_, options = {}) {
  process.stdout.write(`$ ${commandText(executable, arguments_)}\n`);
  const result = spawnSync(executable, arguments_, {
    cwd: repositoryDirectory,
    encoding: "utf8",
    ...options,
  });
  if (result.error) {
    throw result.error;
  }
  if (result.status !== 0) {
    throw new Error(`${commandText(executable, arguments_)} failed:\n${result.stderr ?? ""}`);
  }
  return `${result.stdout ?? ""}${result.stderr ?? ""}`;
}

function readReleaseConfiguration() {
  let configuration;
  try {
    configuration = JSON.parse(readFileSync(releaseConfigurationPath, "utf8"));
  } catch (error) {
    fail(`cannot read ${path.relative(repositoryDirectory, releaseConfigurationPath)}: ${error.message}`);
  }

  const environmentVariable = configuration.signingIdentityEnvironmentVariable;
  const profile = configuration.notarytoolKeychainProfile;
  if (!/^[A-Z][A-Z0-9_]*$/.test(environmentVariable ?? "")) {
    fail("signingIdentityEnvironmentVariable must name one environment variable");
  }
  if (typeof profile !== "string" || profile.length === 0 || /[\r\n]/.test(profile)) {
    fail("notarytoolKeychainProfile must be a non-empty, single-line Keychain profile name");
  }

  const signingIdentity = process.env[environmentVariable];
  if (typeof signingIdentity !== "string" || signingIdentity.length === 0) {
    fail(`${environmentVariable} is required and must name a Developer ID Application identity`);
  }
  if (!signingIdentity.startsWith("Developer ID Application:")) {
    fail(`${environmentVariable} must start with "Developer ID Application:"`);
  }
  if (/[\r\n]/.test(signingIdentity)) {
    fail(`${environmentVariable} must be a single-line Keychain identity name`);
  }

  return { profile, signingIdentity };
}

function assertNoTauriNotarizationCredentials() {
  const configured = notarizationEnvironmentVariables.filter((name) => process.env[name]);
  if (configured.length > 0) {
    fail(
      `manual notarytool profile workflow forbids Tauri notarization credentials: ${configured.join(", ")}`,
    );
  }
}

function assertCommandAvailable(name) {
  run("xcrun", ["--find", name]);
}

function assertMacOS() {
  if (process.platform !== "darwin") {
    fail("must run on macOS because Developer ID signing and notarization require Apple tooling");
  }
}

function assertIdentityAvailable(signingIdentity) {
  const identities = run("security", ["find-identity", "-v", "-p", "codesigning"]);
  if (!identities.includes(signingIdentity)) {
    fail(`Keychain does not contain the configured identity: ${signingIdentity}`);
  }
}

function verifyNotaryProfile(profile) {
  run("xcrun", ["notarytool", "history", "--keychain-profile", profile]);
}

function readTauriConfiguration() {
  const configurationPath = path.join(tauriDirectory, "tauri.conf.json");
  return JSON.parse(readFileSync(configurationPath, "utf8"));
}

function findReleaseArtifacts() {
  const configuration = readTauriConfiguration();
  const bundleDirectory = path.join(tauriDirectory, "target", "release", "bundle");
  const applicationPath = path.join(bundleDirectory, "macos", `${configuration.productName}.app`);
  const dmgDirectory = path.join(bundleDirectory, "dmg");
  const dmgPrefix = `${configuration.productName}_${configuration.version}_`;
  const dmgArtifacts = existsSync(dmgDirectory)
    ? readdirSync(dmgDirectory)
        .filter((entry) => entry.startsWith(dmgPrefix) && entry.endsWith(".dmg"))
        .map((entry) => path.join(dmgDirectory, entry))
    : [];

  if (!existsSync(applicationPath)) {
    fail(`Tauri build did not produce ${path.relative(repositoryDirectory, applicationPath)}`);
  }
  if (dmgArtifacts.length !== 1) {
    fail(`expected exactly one release DMG matching ${dmgPrefix}*.dmg, found ${dmgArtifacts.length}`);
  }
  return { applicationPath, dmgPath: dmgArtifacts[0] };
}

export function validateSignatureMetadata(signature, signingIdentity) {
  if (!signature.includes(`Authority=${signingIdentity}`)) {
    fail("application is not signed by the configured Developer ID identity");
  }
  if (!signature.includes("runtime")) {
    fail("application signature does not enable the hardened runtime");
  }
  if (!signature.includes("Timestamp=")) {
    fail("application signature does not contain a secure timestamp");
  }
}

function verifySignedApplication(applicationPath, signingIdentity) {
  run("codesign", ["--verify", "--deep", "--strict", "--verbose=4", applicationPath]);
  const signature = run("codesign", ["-d", "--verbose=4", applicationPath]);
  validateSignatureMetadata(signature, signingIdentity);
  const entitlements = run("codesign", ["-d", "--entitlements", ":-", applicationPath]);
  if (entitlements.includes("com.apple.security.get-task-allow")) {
    fail("distribution application contains the forbidden get-task-allow entitlement");
  }
}

function release(configuration) {
  assertMacOS();
  assertNoTauriNotarizationCredentials();
  for (const command of ["codesign", "notarytool", "stapler", "spctl"]) {
    assertCommandAvailable(command);
  }
  assertIdentityAvailable(configuration.signingIdentity);
  verifyNotaryProfile(configuration.profile);

  run("bunx", ["tauri", "build", "--bundles", "app,dmg"], {
    env: { ...process.env, APPLE_SIGNING_IDENTITY: configuration.signingIdentity },
  });

  const { applicationPath, dmgPath } = findReleaseArtifacts();
  verifySignedApplication(applicationPath, configuration.signingIdentity);
  run("xcrun", ["notarytool", "submit", dmgPath, "--keychain-profile", configuration.profile, "--wait"]);
  run("xcrun", ["stapler", "staple", dmgPath]);
  run("xcrun", ["stapler", "validate", dmgPath]);
  run("spctl", ["--assess", "--type", "execute", "--verbose=4", applicationPath]);
  run("spctl", ["--assess", "--type", "open", "--context", "context:primary-signature", "--verbose=4", dmgPath]);
}

function printDryRun() {
  process.stdout.write("Dry run only: no credentials, signing, notarization, or stapling occurs.\n");
  process.stdout.write("Release configuration: config/release/macos.json\n");
  process.stdout.write("Required identity environment variable: RESEARCHLEDGER_DEVELOPER_IDENTITY\n");
  for (const command of [
    "security find-identity -v -p codesigning",
    "xcrun notarytool history --keychain-profile ResearchLedger-Notary",
    "bunx tauri build --bundles app,dmg",
    "codesign --verify --deep --strict --verbose=4 <ResearchLedger.app>",
    "xcrun notarytool submit <ResearchLedger.dmg> --keychain-profile ResearchLedger-Notary --wait",
    "xcrun stapler staple <ResearchLedger.dmg>",
    "xcrun stapler validate <ResearchLedger.dmg>",
    "spctl --assess --type execute --verbose=4 <ResearchLedger.app>",
    "spctl --assess --type open --context context:primary-signature --verbose=4 <ResearchLedger.dmg>",
  ]) {
    process.stdout.write(`$ ${command}\n`);
  }
}

function main() {
  const arguments_ = process.argv.slice(2);
  if (arguments_.length === 1 && arguments_[0] === "--dry-run") {
    printDryRun();
    return;
  }
  if (arguments_.length !== 1 || arguments_[0] !== "--confirm-release") {
    throw new Error(`Unknown argument: ${arguments_.join(" ") || "(none)"}. Use --dry-run or --confirm-release.`);
  }
  release(readReleaseConfiguration());
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    main();
  } catch (error) {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  }
}
