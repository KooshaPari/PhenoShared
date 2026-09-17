package ports

import "github.com/KooshaPari/nanovms/internal/domain"

// VMTier represents the VM tier level.
type VMTier = domain.VMFlavor

const (
	VMTierNative VMTier = "native"
	VMTierLimaVZ VMTier = "lima"
	VMTierMicroVM VMTier = "microvm"
)
