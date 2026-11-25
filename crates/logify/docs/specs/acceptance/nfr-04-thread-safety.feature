# status: pending
# maps-to: Logger: Send+Sync, Sink: Send+Sync
@nfr-4
Feature: Thread-safe shared loggers
  Logger and Sink traits permit shared ownership across threads.

  Scenario: Arc<dyn Logger> is Send and Sync
  # PENDING: compile-time assert_send_sync::<Arc<dyn Logger>>()

  Scenario: Arc<dyn Sink> is Send and Sync
  # PENDING: compile-time assert_send_sync::<Arc<dyn Sink>>()
