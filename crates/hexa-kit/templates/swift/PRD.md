# Product Requirements Document — template-lang-swift

**Product:** Phenotype Swift Language Templates
**Template Version:** 0.1.0
**Date:** 2026-04-02

## Purpose

Provide production-ready Swift project templates that follow Phenotype platform conventions, Apple platform best practices, and modern Swift patterns.

## Target Users

1. **iOS Developers** - Building iOS/macOS applications
2. **Swift Engineers** - Creating command-line tools
3. **Platform Engineers** - Integrating with Phenotype platform

## Problem Statement

Starting a new Swift project requires:
- Xcode project configuration
- Package dependencies setup
- Architecture scaffolding
- Testing infrastructure
- CI/CD configuration

This template accelerates onboarding.

## Solution

### Core Templates

1. **phenotype-swift-kit**
   - iOS/macOS development foundation
   - SwiftUI and UIKit patterns
   - Network layer
   - Persistence

2. **phenotype-swift-cli**
   - Command-line tools
   - Cross-platform Swift
   - Shell integration

### Key Features

- **Swift 5.9+** - Modern concurrency
- **Swift Concurrency** - async/await, actors
- **SPM** - Native package management
- **XcodeGen** - Code generation
- **MVVM + Coordinators** - Architecture pattern

## User Stories

### US-SWIFT-001: Generate New iOS App
**As an** iOS developer
**I want to** generate a new iOS project
**So that** I can start coding immediately

### US-SWIFT-002: Use Modern Swift
**As a** Swift engineer
**I want to** use async/await and actors
**So that** my code is safe and modern

## Success Metrics

| Metric | Target |
|--------|--------|
| Project generation | < 30 seconds |
| Build time | < 2 minutes |
| Test suite passing | 100% |

## Constraints

- Must use Swift 5.9+
- Must target iOS 16+ / macOS 13+
- Swift Concurrency required
- SPM for dependencies
