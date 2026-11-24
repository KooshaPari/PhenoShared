/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Barrel export for space app providers
// Dependencies:
//   - react (for React.ReactNode type)
//   - mobx-react (for observer HOC)
//   - react-router (for Link component)
//   - next-themes (for useTheme hook)
//   - swr (for useSWR hook)
//   - @plane/constants (for SPACE_BASE_PATH)
//   - @plane/propel/icons (for PlaneLockup icon)
//   - @plane/propel/toast (for Toast component)
//   - @plane/utils (for resolveGeneralTheme)
//   - @/hooks/store/* (for store hooks)
//   - @/components/* (for UI components)

export { InstanceProvider } from "./instance-provider";
export {
  StoreProvider,
  StoreContext,
  type StoreProviderProps,
  type RootStoreHydrationState,
} from "./store-provider";
export { ToastProvider } from "./toast-provider";
