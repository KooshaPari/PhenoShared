package applet

// The publish-time gate. It lives in its own file because it is a different
// kind of code from Build: Build composes a document, Validate decides whether
// the result may leave the process at all.

import (
	"fmt"
	"strings"
)

// Validate checks a manifest against the contract's own constraints.
//
// It is the publish-time gate: the manifest is handed to strangers, so a
// malformed one is caught here instead of by whoever trusts it. The schema
// itself is the authority; this mirrors it for the fields where a mistake is
// plausible (ids, enums, required presence, array-not-null).
func (m Manifest) Validate() error {
	check := func(what, v string) error {
		if len(v) < 2 {
			return fmt.Errorf("%s %q is shorter than the contract's minimum of 2", what, v)
		}
		if !idPattern.MatchString(v) {
			return fmt.Errorf("%s %q does not match %s", what, v, idPattern)
		}
		return nil
	}
	for _, f := range []struct{ what, v string }{
		{"id", m.ID}, {"subject_id", m.SubjectID}, {"lifecycle_contract_id", m.LifecycleContractID},
	} {
		if err := check(f.what, f.v); err != nil {
			return err
		}
	}
	if m.Version == "" {
		return fmt.Errorf("version is empty; the contract requires minLength 1")
	}
	if strings.TrimSpace(m.FederationPolicy) == "" {
		return fmt.Errorf("federation_policy is empty; the contract requires minLength 1")
	}
	// A nil slice marshals to null, which the contract's "type": "array"
	// rejects. Every list is therefore required to be non-nil, empty is fine.
	for _, l := range []struct {
		name string
		v    []string
	}{
		{"provided_capabilities", m.ProvidedCapabilities},
		{"required_capabilities", m.RequiredCapabilities},
		{"optional_capabilities", m.OptionalCapabilities},
		{"owned_state_ids", m.OwnedStateIDs},
		{"permission_ids", m.PermissionIDs},
		{"resource_profile_ids", m.ResourceProfileIDs},
		{"surfaces", m.Surfaces},
		{"children", m.Children},
	} {
		if l.v == nil {
			return fmt.Errorf("%s is nil; the contract requires an array (empty is allowed)", l.name)
		}
	}
	if m.Ports == nil {
		return fmt.Errorf("ports is nil; the contract requires an array (empty is allowed)")
	}
	for _, s := range m.Surfaces {
		if !surfaces[s] {
			return fmt.Errorf("surface %q is not in the contract's enum", s)
		}
	}
	for _, p := range m.Ports {
		if p.Name == "" {
			return fmt.Errorf("port with empty name")
		}
		if p.Direction != "provides" && p.Direction != "requires" {
			return fmt.Errorf("port %q has direction %q, want provides or requires", p.Name, p.Direction)
		}
		if err := check("port "+p.Name+" contract_id", p.ContractID); err != nil {
			return err
		}
	}
	return nil
}
