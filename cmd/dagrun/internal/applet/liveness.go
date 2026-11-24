package applet

// Liveness is what a pid probe could establish, not a guess about what the
// answer means for a registry record.
//
// The distinction exists because a bool cannot carry it. On Windows, "you may
// not open this process" and "this pid is free" arrive as different errors, and
// on Unix the same split is EPERM against ESRCH. A probe that collapses them
// reports one answer for two opposite situations, and the caller then has to
// decide whether to delete a record on evidence it no longer has.
//
// Measured cost of the collapsed form: `dagrun instances --prune` deleted the
// advertisement of live pid 4 on the desk.
type Liveness int

const (
	// LivenessUnknown means the probe could not establish anything: the process
	// exists but refuses to be queried (ERROR_ACCESS_DENIED, EPERM), or the
	// query failed for a reason that says nothing about the pid. A record in
	// this state must be kept. A pid you cannot ask about is not a pid that is
	// gone, and age is not evidence about a process.
	LivenessUnknown Liveness = iota

	// LivenessAlive means a running process holds the pid. It does not prove the
	// process is the one that wrote the record: pids are recycled, and a
	// recycled pid can point at an unrelated live process.
	LivenessAlive

	// LivenessDead means the pid is free. This is the only state in which
	// deleting a record is founded on proof rather than on a guess.
	LivenessDead
)

// String keeps test failures and log lines readable without a lookup table at
// every call site.
func (l Liveness) String() string {
	switch l {
	case LivenessAlive:
		return "alive"
	case LivenessDead:
		return "dead"
	default:
		return "unknown"
	}
}
