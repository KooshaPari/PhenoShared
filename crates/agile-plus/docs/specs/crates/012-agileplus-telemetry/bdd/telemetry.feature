Feature: AgilePlus telemetry port
  As a platform operator
  I want a stable TelemetrySink port
  So that backends can be swapped without caller changes

  Background:
    Given a TelemetrySink wired with the in-memory recorder

  Scenario: Span emission is observable
    When a span "agileplus.op" with attrs is emitted
    Then the recorder contains one span named "agileplus.op"

  Scenario: No-op adapter never panics
    Given a NoopTelemetrySink
    When any span, counter, or log is emitted
    Then the call returns Ok(())
