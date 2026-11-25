package store

// State schema versioning.
//
// The state document is a database, and a database that cannot say what shape it
// is in will eventually be read by the wrong version of the code. Two failures
// follow from that, and both are silent:
//
//   - an OLDER dagrun reads a NEWER state and ignores fields it does not know,
//     then writes them back away. The run loses data and reports success.
//   - a state written before a field existed is read as if the field were
//     present, and a default of "" or 0 is interpreted as a real value.
//
// So the version is persisted, a missing version means 1 (that is what every
// state file written before this existed actually is), and a state from a newer
// binary is refused with a reason instead of being half-understood.

import (
	"errors"
	"fmt"
)

// SchemaVersion is the current on-disk schema version. Bump it whenever the
// meaning of an existing field changes or a field becomes required.
const SchemaVersion = 1

// ErrStateTooNew is returned when the state was written by a newer dagrun. It is
// a sentinel so a caller can distinguish "upgrade your binary" from corruption.
var ErrStateTooNew = errors.New("state schema is newer than this binary")

// migration upgrades one schema version to the next.
//
// The chain is currently empty because version 1 is the first explicit version
// and every earlier state file is also version 1. The MECHANISM exists so that
// the next change is an append rather than a redesign: adding a migration is
// how a future field gets a correct value in old documents, and doing it here
// keeps the decision in one ordered list instead of scattered across readers.
type migration struct {
	from, to int
	apply    func(*State) error
}

// migrations must be ordered and contiguous. A gap is a bug, and migrate reports
// it rather than skipping the document past a version nobody can upgrade.
var migrations = []migration{}

// migrate brings a state document up to SchemaVersion.
//
// It mutates st in place. The caller writes the result through the normal atomic
// path, so a migration that fails leaves the on-disk document untouched.
func migrate(st *State) error {
	if st.Version == 0 {
		// Every state file written before schema_version existed is version 1.
		st.Version = 1
	}
	if st.Version > SchemaVersion {
		return fmt.Errorf("%w: state is schema version %d, this binary supports %d; upgrade dagrun or use the dagrun that wrote it",
			ErrStateTooNew, st.Version, SchemaVersion)
	}
	if st.Version == SchemaVersion {
		return nil
	}

	for st.Version < SchemaVersion {
		var next *migration
		for i := range migrations {
			if migrations[i].from == st.Version {
				next = &migrations[i]
				break
			}
		}
		if next == nil {
			return fmt.Errorf("no migration from state schema version %d to %d; refusing to guess",
				st.Version, SchemaVersion)
		}
		if next.to != next.from+1 {
			return fmt.Errorf("migration from version %d targets %d; migrations must advance one version at a time",
				next.from, next.to)
		}
		if next.apply != nil {
			if err := next.apply(st); err != nil {
				return fmt.Errorf("migrate state %d -> %d: %w", next.from, next.to, err)
			}
		}
		st.Version = next.to
	}
	return nil
}
