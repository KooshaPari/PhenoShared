Feature: AgilePlus gRPC service
  As a remote client
  I want a tonic-based gRPC service
  So that I can call AgilePlus from non-Rust runtimes

  Background:
    Given a running AgilePlusService over tonic

  Scenario: Health check reports SERVING
    When the gRPC Health/Check is invoked
    Then the response status is SERVING

  Scenario: Domain errors map to canonical codes
    Given a request that triggers NotFound in the domain
    When the call is made
    Then the gRPC status code is NOT_FOUND
