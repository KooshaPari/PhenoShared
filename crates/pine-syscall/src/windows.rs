//! Windows-specific syscall translator.
//!
//! Maps common Windows NT syscalls to their NTAPI numbers and provides a
//! [`WindowsSyscallTranslator`] for translating raw Windows syscall numbers.
//!
//! # Note on syscall numbers
//!
//! NT syscall numbers vary across Windows versions and architectures. The
//! numbers in this module correspond to **Windows 10/11 x64** (build 19041+)
//! and are the most common reference values for modern Windows systems.

use std::collections::HashMap;
use std::fmt;

/// Error returned when a Windows syscall translation fails.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum WindowsSyscallError {
    /// `UnknownSyscall`
    UnknownSyscall(u32),
    /// `InvalidArgument`
    InvalidArgument,
}

impl fmt::Display for WindowsSyscallError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            WindowsSyscallError::UnknownSyscall(num) => {
                write!(f, "Unknown Windows syscall number: {}", num)
            }
            WindowsSyscallError::InvalidArgument => write!(f, "Invalid argument"),
        }
    }
}

impl std::error::Error for WindowsSyscallError {}

/// Named identifier for a Windows NT syscall.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum WindowsSyscallName {
    /// `NtAccessCheck`
    NtAccessCheck,
    /// `NtAllocateVirtualMemory`
    NtAllocateVirtualMemory,
    /// `NtClose`
    NtClose,
    /// `NtCreateEvent`
    NtCreateEvent,
    /// `NtCreateFile`
    NtCreateFile,
    /// `NtCreateKey`
    NtCreateKey,
    /// `NtCreateSection`
    NtCreateSection,
    /// `NtCreateThread`
    NtCreateThread,
    /// `NtCreateThreadEx`
    NtCreateThreadEx,
    /// `NtCreateUserProcess`
    NtCreateUserProcess,
    /// `NtDelayExecution`
    NtDelayExecution,
    /// `NtDeleteKey`
    NtDeleteKey,
    /// `NtDeviceIoControlFile`
    NtDeviceIoControlFile,
    /// `NtDuplicateObject`
    NtDuplicateObject,
    /// `NtFlushBuffersFile`
    NtFlushBuffersFile,
    /// `NtFreeVirtualMemory`
    NtFreeVirtualMemory,
    /// `NtFsControlFile`
    NtFsControlFile,
    /// `NtGetContextThread`
    NtGetContextThread,
    /// `NtMapViewOfSection`
    NtMapViewOfSection,
    /// `NtOpenEvent`
    NtOpenEvent,
    /// `NtOpenFile`
    NtOpenFile,
    /// `NtOpenKey`
    NtOpenKey,
    /// `NtOpenProcess`
    NtOpenProcess,
    /// `NtOpenSection`
    NtOpenSection,
    /// `NtOpenThread`
    NtOpenThread,
    /// `NtProtectVirtualMemory`
    NtProtectVirtualMemory,
    /// `NtQueryDirectoryFile`
    NtQueryDirectoryFile,
    /// `NtQueryInformationFile`
    NtQueryInformationFile,
    /// `NtQueryInformationProcess`
    NtQueryInformationProcess,
    /// `NtQueryInformationThread`
    NtQueryInformationThread,
    /// `NtQuerySystemInformation`
    NtQuerySystemInformation,
    /// `NtQueryValueKey`
    NtQueryValueKey,
    /// `NtQueryVirtualMemory`
    NtQueryVirtualMemory,
    /// `NtReadFile`
    NtReadFile,
    /// `NtReadVirtualMemory`
    NtReadVirtualMemory,
    /// `NtResetEvent`
    NtResetEvent,
    /// `NtResumeThread`
    NtResumeThread,
    /// `NtSetContextThread`
    NtSetContextThread,
    /// `NtSetEvent`
    NtSetEvent,
    /// `NtSetInformationFile`
    NtSetInformationFile,
    /// `NtSetInformationProcess`
    NtSetInformationProcess,
    /// `NtSetValueKey`
    NtSetValueKey,
    /// `NtSuspendThread`
    NtSuspendThread,
    /// `NtTerminateProcess`
    NtTerminateProcess,
    /// `NtTerminateThread`
    NtTerminateThread,
    /// `NtUnmapViewOfSection`
    NtUnmapViewOfSection,
    /// `NtWaitForMultipleObjects`
    NtWaitForMultipleObjects,
    /// `NtWaitForSingleObject`
    NtWaitForSingleObject,
    /// `NtWriteFile`
    NtWriteFile,
    /// `NtWriteVirtualMemory`
    NtWriteVirtualMemory,
    /// `NtYieldExecution`
    NtYieldExecution,
}

/// Result of a successful Windows syscall translation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WindowsSyscallResult {
    pub name: WindowsSyscallName,
    pub number: u32,
    pub args: [u64; 6],
}

/// Trait for translating raw Windows syscall numbers into structured results.
pub trait WindowsSyscallTranslator {
    fn translate(
        &self,
        syscall_num: u32,
        args: [u64; 6],
    ) -> Result<WindowsSyscallResult, WindowsSyscallError>;
}

/// Windows NT syscall translator backed by a lookup table.
///
/// The default instance is populated with the standard NT syscall numbers for
/// Windows 10/11 x64.
#[derive(Debug, Clone)]
pub struct WindowsNtSyscallTranslator {
    table: HashMap<u32, WindowsSyscallName>,
}

/// Common Windows NT x64 syscall numbers (Windows 10/11, build 19041+).
impl WindowsNtSyscallTranslator {
    /// `NtClose` — close an object handle
    pub const NT_CLOSE: u32 = 0x0F;
    /// `NtCreateFile` — create or open a file
    pub const NT_CREATE_FILE: u32 = 0x55;
    /// `NtCreateSection` — create a section object
    pub const NT_CREATE_SECTION: u32 = 0x4A;
    /// `NtDeviceIoControlFile` — perform device I/O control
    pub const NT_DEVICE_IO_CONTROL_FILE: u32 = 0x07;
    /// `NtDuplicateObject` — duplicate an object handle
    pub const NT_DUPLICATE_OBJECT: u32 = 0x57;
    /// `NtFlushBuffersFile` — flush buffers for a file
    pub const NT_FLUSH_BUFFERS_FILE: u32 = 0x41;
    /// `NtFreeVirtualMemory` — free virtual memory
    pub const NT_FREE_VIRTUAL_MEMORY: u32 = 0x1E;
    /// `NtFsControlFile` — perform file system control
    pub const NT_FS_CONTROL_FILE: u32 = 0x09;
    /// `NtMapViewOfSection` — map a view of a section
    pub const NT_MAP_VIEW_OF_SECTION: u32 = 0x28;
    /// `NtOpenFile` — open a file
    pub const NT_OPEN_FILE: u32 = 0x33;
    /// `NtOpenProcess` — open a process object
    pub const NT_OPEN_PROCESS: u32 = 0x26;
    /// `NtOpenSection` — open a section object
    pub const NT_OPEN_SECTION: u32 = 0x4B;
    /// `NtOpenThread` — open a thread object
    pub const NT_OPEN_THREAD: u32 = 0x4D;
    /// `NtProtectVirtualMemory` — change virtual memory protection
    pub const NT_PROTECT_VIRTUAL_MEMORY: u32 = 0x50;
    /// `NtQueryDirectoryFile` — query a directory
    pub const NT_QUERY_DIRECTORY_FILE: u32 = 0x91;
    /// `NtQueryInformationFile` — query file information
    pub const NT_QUERY_INFORMATION_FILE: u32 = 0x11;
    /// `NtQueryInformationProcess` — query process information
    pub const NT_QUERY_INFORMATION_PROCESS: u32 = 0x19;
    /// `NtQueryInformationThread` — query thread information
    pub const NT_QUERY_INFORMATION_THREAD: u32 = 0x25;
    /// `NtQuerySystemInformation` — query system information
    pub const NT_QUERY_SYSTEM_INFORMATION: u32 = 0x24;
    /// `NtQueryVirtualMemory` — query virtual memory
    pub const NT_QUERY_VIRTUAL_MEMORY: u32 = 0x23;
    /// `NtReadFile` — read from a file
    pub const NT_READ_FILE: u32 = 0x06;
    /// `NtReadVirtualMemory` — read virtual memory
    pub const NT_READ_VIRTUAL_MEMORY: u32 = 0x3D;
    /// `NtResumeThread` — resume a thread
    pub const NT_RESUME_THREAD: u32 = 0x4F;
    /// `NtSetEvent` — set an event to signaled state
    pub const NT_SET_EVENT: u32 = 0x0E;
    /// `NtSetInformationFile` — set file information
    pub const NT_SET_INFORMATION_FILE: u32 = 0x27;
    /// `NtSuspendThread` — suspend a thread
    pub const NT_SUSPEND_THREAD: u32 = 0x36;
    /// `NtTerminateProcess` — terminate a process
    pub const NT_TERMINATE_PROCESS: u32 = 0x2C;
    /// `NtTerminateThread` — terminate a thread
    pub const NT_TERMINATE_THREAD: u32 = 0x53;
    /// `NtUnmapViewOfSection` — unmap a view of a section
    pub const NT_UNMAP_VIEW_OF_SECTION: u32 = 0x2A;
    /// `NtWaitForMultipleObjects` — wait for multiple objects
    pub const NT_WAIT_FOR_MULTIPLE_OBJECTS: u32 = 0x05;
    /// `NtWaitForSingleObject` — wait for a single object
    pub const NT_WAIT_FOR_SINGLE_OBJECT: u32 = 0x04;
    /// `NtWriteFile` — write to a file
    pub const NT_WRITE_FILE: u32 = 0x08;
    /// `NtWriteVirtualMemory` — write virtual memory
    pub const NT_WRITE_VIRTUAL_MEMORY: u32 = 0x3A;
    /// `NtYieldExecution` — yield execution
    pub const NT_YIELD_EXECUTION: u32 = 0x46;
    /// `NtDelayExecution` — delay execution
    pub const NT_DELAY_EXECUTION: u32 = 0x34;
    /// `NtAllocateVirtualMemory` — allocate virtual memory
    pub const NT_ALLOCATE_VIRTUAL_MEMORY: u32 = 0x18;
    /// `NtCreateEvent` — create an event object
    pub const NT_CREATE_EVENT: u32 = 0x48;
    /// `NtOpenEvent` — open an event object
    pub const NT_OPEN_EVENT: u32 = 0x49;
    /// `NtOpenKey` — open a registry key
    pub const NT_OPEN_KEY: u32 = 0x78;
    /// `NtCreateKey` — create a registry key
    pub const NT_CREATE_KEY: u32 = 0x77;
    /// `NtQueryValueKey` — query a registry value
    pub const NT_QUERY_VALUE_KEY: u32 = 0x79;
    /// `NtSetValueKey` — set a registry value
    pub const NT_SET_VALUE_KEY: u32 = 0x5D;
    /// `NtDeleteKey` — delete a registry key
    pub const NT_DELETE_KEY: u32 = 0x63;
    /// `NtCreateThread` — create a thread
    pub const NT_CREATE_THREAD: u32 = 0xA6;
    /// `NtCreateThreadEx` — create a thread (extended)
    pub const NT_CREATE_THREAD_EX: u32 = 0xB9;
    /// `NtCreateUserProcess` — create a user process
    pub const NT_CREATE_USER_PROCESS: u32 = 0xC1;
    /// `NtGetContextThread` — get thread context
    pub const NT_GET_CONTEXT_THREAD: u32 = 0xD4;
    /// `NtSetContextThread` — set thread context
    pub const NT_SET_CONTEXT_THREAD: u32 = 0xD5;
    /// `NtAccessCheck` — check access rights
    pub const NT_ACCESS_CHECK: u32 = 0x00;
    /// `NtResetEvent` — reset an event to non-signaled state
    pub const NT_RESET_EVENT: u32 = 0xD1;

    /// Create a new translator with the standard Windows NT syscall table.
    pub fn new() -> Self {
        let mut table = HashMap::new();
        table.insert(0x00, WindowsSyscallName::NtAccessCheck);
        table.insert(0x04, WindowsSyscallName::NtWaitForSingleObject);
        table.insert(0x05, WindowsSyscallName::NtWaitForMultipleObjects);
        table.insert(0x06, WindowsSyscallName::NtReadFile);
        table.insert(0x07, WindowsSyscallName::NtDeviceIoControlFile);
        table.insert(0x08, WindowsSyscallName::NtWriteFile);
        table.insert(0x09, WindowsSyscallName::NtFsControlFile);
        table.insert(0x0E, WindowsSyscallName::NtSetEvent);
        table.insert(0x0F, WindowsSyscallName::NtClose);
        table.insert(0x11, WindowsSyscallName::NtQueryInformationFile);
        table.insert(0x18, WindowsSyscallName::NtAllocateVirtualMemory);
        table.insert(0x19, WindowsSyscallName::NtQueryInformationProcess);
        table.insert(0x1E, WindowsSyscallName::NtFreeVirtualMemory);
        table.insert(0x23, WindowsSyscallName::NtQueryVirtualMemory);
        table.insert(0x24, WindowsSyscallName::NtQuerySystemInformation);
        table.insert(0x25, WindowsSyscallName::NtQueryInformationThread);
        table.insert(0x26, WindowsSyscallName::NtOpenProcess);
        table.insert(0x27, WindowsSyscallName::NtSetInformationFile);
        table.insert(0x28, WindowsSyscallName::NtMapViewOfSection);
        table.insert(0x2A, WindowsSyscallName::NtUnmapViewOfSection);
        table.insert(0x2C, WindowsSyscallName::NtTerminateProcess);
        table.insert(0x33, WindowsSyscallName::NtOpenFile);
        table.insert(0x34, WindowsSyscallName::NtDelayExecution);
        table.insert(0x36, WindowsSyscallName::NtSuspendThread);
        table.insert(0x3A, WindowsSyscallName::NtWriteVirtualMemory);
        table.insert(0x3D, WindowsSyscallName::NtReadVirtualMemory);
        table.insert(0x41, WindowsSyscallName::NtFlushBuffersFile);
        table.insert(0x46, WindowsSyscallName::NtYieldExecution);
        table.insert(0x48, WindowsSyscallName::NtCreateEvent);
        table.insert(0x49, WindowsSyscallName::NtOpenEvent);
        table.insert(0x4A, WindowsSyscallName::NtCreateSection);
        table.insert(0x4B, WindowsSyscallName::NtOpenSection);
        table.insert(0x4D, WindowsSyscallName::NtOpenThread);
        table.insert(0x4F, WindowsSyscallName::NtResumeThread);
        table.insert(0x50, WindowsSyscallName::NtProtectVirtualMemory);
        table.insert(0x53, WindowsSyscallName::NtTerminateThread);
        table.insert(0x55, WindowsSyscallName::NtCreateFile);
        table.insert(0x57, WindowsSyscallName::NtDuplicateObject);
        table.insert(0x5D, WindowsSyscallName::NtSetValueKey);
        table.insert(0x63, WindowsSyscallName::NtDeleteKey);
        table.insert(0x77, WindowsSyscallName::NtCreateKey);
        table.insert(0x78, WindowsSyscallName::NtOpenKey);
        table.insert(0x79, WindowsSyscallName::NtQueryValueKey);
        table.insert(0x91, WindowsSyscallName::NtQueryDirectoryFile);
        table.insert(0xA6, WindowsSyscallName::NtCreateThread);
        table.insert(0xB9, WindowsSyscallName::NtCreateThreadEx);
        table.insert(0xC1, WindowsSyscallName::NtCreateUserProcess);
        table.insert(0xD4, WindowsSyscallName::NtGetContextThread);
        table.insert(0xD5, WindowsSyscallName::NtSetContextThread);
        table.insert(0xD1, WindowsSyscallName::NtResetEvent);
        Self { table }
    }

    /// Look up the syscall name for a given number.
    pub fn lookup_name(&self, number: u32) -> Option<&WindowsSyscallName> {
        self.table.get(&number)
    }

    /// Look up the syscall number for a given name.
    pub fn lookup_number(&self, name: WindowsSyscallName) -> Option<u32> {
        self.table
            .iter()
            .find(|(_, n)| **n == name)
            .map(|(num, _)| *num)
    }
}

impl Default for WindowsNtSyscallTranslator {
    fn default() -> Self {
        Self::new()
    }
}

impl WindowsSyscallTranslator for WindowsNtSyscallTranslator {
    fn translate(
        &self,
        syscall_num: u32,
        args: [u64; 6],
    ) -> Result<WindowsSyscallResult, WindowsSyscallError> {
        match self.table.get(&syscall_num) {
            Some(&name) => Ok(WindowsSyscallResult {
                name,
                number: syscall_num,
                args,
            }),
            None => Err(WindowsSyscallError::UnknownSyscall(syscall_num)),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{
        WindowsNtSyscallTranslator, WindowsSyscallError, WindowsSyscallName,
        WindowsSyscallTranslator,
    };

    #[test]
    fn windows_translator_translates_nt_create_file() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(
                WindowsNtSyscallTranslator::NT_CREATE_FILE,
                [1, 2, 3, 4, 5, 6],
            )
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtCreateFile);
        assert_eq!(result.number, 0x55);
        assert_eq!(result.args, [1, 2, 3, 4, 5, 6]);
    }

    #[test]
    fn windows_translator_translates_nt_read_file() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_READ_FILE, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtReadFile);
        assert_eq!(result.number, 0x06);
    }

    #[test]
    fn windows_translator_translates_nt_write_file() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_WRITE_FILE, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtWriteFile);
        assert_eq!(result.number, 0x08);
    }

    #[test]
    fn windows_translator_translates_nt_close() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_CLOSE, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtClose);
        assert_eq!(result.number, 0x0F);
    }

    #[test]
    fn windows_translator_translates_nt_open_file() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_OPEN_FILE, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtOpenFile);
    }

    #[test]
    fn windows_translator_translates_nt_allocate_virtual_memory() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(
                WindowsNtSyscallTranslator::NT_ALLOCATE_VIRTUAL_MEMORY,
                [0; 6],
            )
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtAllocateVirtualMemory);
    }

    #[test]
    fn windows_translator_translates_nt_free_virtual_memory() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_FREE_VIRTUAL_MEMORY, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtFreeVirtualMemory);
    }

    #[test]
    fn windows_translator_translates_nt_protect_virtual_memory() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(
                WindowsNtSyscallTranslator::NT_PROTECT_VIRTUAL_MEMORY,
                [0; 6],
            )
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtProtectVirtualMemory);
    }

    #[test]
    fn windows_translator_translates_nt_map_view_of_section() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_MAP_VIEW_OF_SECTION, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtMapViewOfSection);
    }

    #[test]
    fn windows_translator_translates_nt_unmap_view_of_section() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_UNMAP_VIEW_OF_SECTION, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtUnmapViewOfSection);
    }

    #[test]
    fn windows_translator_translates_nt_query_system_information() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(
                WindowsNtSyscallTranslator::NT_QUERY_SYSTEM_INFORMATION,
                [0; 6],
            )
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtQuerySystemInformation);
    }

    #[test]
    fn windows_translator_translates_nt_query_information_process() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(
                WindowsNtSyscallTranslator::NT_QUERY_INFORMATION_PROCESS,
                [0; 6],
            )
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtQueryInformationProcess);
    }

    #[test]
    fn windows_translator_translates_nt_wait_for_single_object() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(
                WindowsNtSyscallTranslator::NT_WAIT_FOR_SINGLE_OBJECT,
                [0; 6],
            )
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtWaitForSingleObject);
    }

    #[test]
    fn windows_translator_translates_nt_wait_for_multiple_objects() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(
                WindowsNtSyscallTranslator::NT_WAIT_FOR_MULTIPLE_OBJECTS,
                [0; 6],
            )
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtWaitForMultipleObjects);
    }

    #[test]
    fn windows_translator_translates_nt_set_event() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_SET_EVENT, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtSetEvent);
    }

    #[test]
    fn windows_translator_translates_nt_create_event() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_CREATE_EVENT, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtCreateEvent);
    }

    #[test]
    fn windows_translator_translates_nt_open_event() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_OPEN_EVENT, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtOpenEvent);
    }

    #[test]
    fn windows_translator_translates_nt_terminate_process() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_TERMINATE_PROCESS, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtTerminateProcess);
    }

    #[test]
    fn windows_translator_translates_nt_terminate_thread() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_TERMINATE_THREAD, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtTerminateThread);
    }

    #[test]
    fn windows_translator_translates_nt_suspend_thread() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_SUSPEND_THREAD, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtSuspendThread);
    }

    #[test]
    fn windows_translator_translates_nt_resume_thread() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_RESUME_THREAD, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtResumeThread);
    }

    #[test]
    fn windows_translator_translates_nt_create_thread() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_CREATE_THREAD, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtCreateThread);
    }

    #[test]
    fn windows_translator_translates_nt_create_thread_ex() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_CREATE_THREAD_EX, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtCreateThreadEx);
    }

    #[test]
    fn windows_translator_translates_nt_create_user_process() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_CREATE_USER_PROCESS, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtCreateUserProcess);
    }

    #[test]
    fn windows_translator_translates_nt_create_key() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_CREATE_KEY, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtCreateKey);
    }

    #[test]
    fn windows_translator_translates_nt_open_key() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_OPEN_KEY, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtOpenKey);
    }

    #[test]
    fn windows_translator_translates_nt_set_value_key() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_SET_VALUE_KEY, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtSetValueKey);
    }

    #[test]
    fn windows_translator_translates_nt_query_value_key() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_QUERY_VALUE_KEY, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtQueryValueKey);
    }

    #[test]
    fn windows_translator_translates_nt_delete_key() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_DELETE_KEY, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtDeleteKey);
    }

    #[test]
    fn windows_translator_translates_nt_duplicate_object() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_DUPLICATE_OBJECT, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtDuplicateObject);
    }

    #[test]
    fn windows_translator_translates_nt_query_directory_file() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_QUERY_DIRECTORY_FILE, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtQueryDirectoryFile);
    }

    #[test]
    fn windows_translator_translates_nt_flush_buffers_file() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_FLUSH_BUFFERS_FILE, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtFlushBuffersFile);
    }

    #[test]
    fn windows_translator_translates_nt_device_io_control_file() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(
                WindowsNtSyscallTranslator::NT_DEVICE_IO_CONTROL_FILE,
                [0; 6],
            )
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtDeviceIoControlFile);
    }

    #[test]
    fn windows_translator_translates_nt_fs_control_file() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_FS_CONTROL_FILE, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtFsControlFile);
    }

    #[test]
    fn windows_translator_translates_nt_yield_execution() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_YIELD_EXECUTION, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtYieldExecution);
    }

    #[test]
    fn windows_translator_translates_nt_delay_execution() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_DELAY_EXECUTION, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtDelayExecution);
    }

    #[test]
    fn windows_translator_translates_nt_query_information_file() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(
                WindowsNtSyscallTranslator::NT_QUERY_INFORMATION_FILE,
                [0; 6],
            )
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtQueryInformationFile);
    }

    #[test]
    fn windows_translator_translates_nt_set_information_file() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_SET_INFORMATION_FILE, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtSetInformationFile);
    }

    #[test]
    fn windows_translator_translates_nt_query_virtual_memory() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_QUERY_VIRTUAL_MEMORY, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtQueryVirtualMemory);
    }

    #[test]
    fn windows_translator_translates_nt_read_virtual_memory() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_READ_VIRTUAL_MEMORY, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtReadVirtualMemory);
    }

    #[test]
    fn windows_translator_translates_nt_write_virtual_memory() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_WRITE_VIRTUAL_MEMORY, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtWriteVirtualMemory);
    }

    #[test]
    fn windows_translator_translates_nt_open_process() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_OPEN_PROCESS, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtOpenProcess);
    }

    #[test]
    fn windows_translator_translates_nt_open_thread() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_OPEN_THREAD, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtOpenThread);
    }

    #[test]
    fn windows_translator_translates_nt_create_section() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_CREATE_SECTION, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtCreateSection);
    }

    #[test]
    fn windows_translator_translates_nt_open_section() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_OPEN_SECTION, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtOpenSection);
    }

    #[test]
    fn windows_translator_translates_nt_query_information_thread() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(
                WindowsNtSyscallTranslator::NT_QUERY_INFORMATION_THREAD,
                [0; 6],
            )
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtQueryInformationThread);
    }

    #[test]
    fn windows_translator_translates_nt_get_context_thread() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_GET_CONTEXT_THREAD, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtGetContextThread);
    }

    #[test]
    fn windows_translator_translates_nt_set_context_thread() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_SET_CONTEXT_THREAD, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtSetContextThread);
    }

    #[test]
    fn windows_translator_translates_nt_reset_event() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_RESET_EVENT, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtResetEvent);
    }

    #[test]
    fn windows_translator_translates_nt_access_check() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_ACCESS_CHECK, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::NtAccessCheck);
    }

    #[test]
    fn windows_translator_returns_error_for_unknown() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator.translate(0xFFFF, [0; 6]);
        assert!(result.is_err());
        assert_eq!(
            result.unwrap_err(),
            WindowsSyscallError::UnknownSyscall(0xFFFF)
        );
    }

    #[test]
    fn windows_translator_lookup_name() {
        let translator = WindowsNtSyscallTranslator::new();
        assert_eq!(
            translator.lookup_name(0x55),
            Some(&WindowsSyscallName::NtCreateFile)
        );
        assert_eq!(
            translator.lookup_name(0x06),
            Some(&WindowsSyscallName::NtReadFile)
        );
        assert_eq!(
            translator.lookup_name(0x08),
            Some(&WindowsSyscallName::NtWriteFile)
        );
        assert_eq!(translator.lookup_name(0xFFFF), None);
    }

    #[test]
    fn windows_translator_lookup_number() {
        let translator = WindowsNtSyscallTranslator::new();
        assert_eq!(
            translator.lookup_number(WindowsSyscallName::NtCreateFile),
            Some(0x55)
        );
        assert_eq!(
            translator.lookup_number(WindowsSyscallName::NtReadFile),
            Some(0x06)
        );
        assert_eq!(
            translator.lookup_number(WindowsSyscallName::NtWriteFile),
            Some(0x08)
        );
        assert_eq!(
            translator.lookup_number(WindowsSyscallName::NtClose),
            Some(0x0F)
        );
    }

    #[test]
    fn windows_translator_implements_trait() {
        fn takes_translator<T: WindowsSyscallTranslator>(_t: &T) {}
        let translator = WindowsNtSyscallTranslator::new();
        takes_translator(&translator);
    }

    #[test]
    fn windows_translator_default() {
        let translator = WindowsNtSyscallTranslator::default();
        assert_eq!(
            translator.lookup_name(0x55),
            Some(&WindowsSyscallName::NtCreateFile)
        );
        assert_eq!(
            translator.lookup_name(0x06),
            Some(&WindowsSyscallName::NtReadFile)
        );
    }

    #[test]
    fn windows_translator_translates_file_syscalls() {
        let translator = WindowsNtSyscallTranslator::new();
        assert_eq!(
            translator.translate(0x55, [0; 6]).unwrap().name,
            WindowsSyscallName::NtCreateFile
        );
        assert_eq!(
            translator.translate(0x06, [0; 6]).unwrap().name,
            WindowsSyscallName::NtReadFile
        );
        assert_eq!(
            translator.translate(0x08, [0; 6]).unwrap().name,
            WindowsSyscallName::NtWriteFile
        );
        assert_eq!(
            translator.translate(0x0F, [0; 6]).unwrap().name,
            WindowsSyscallName::NtClose
        );
        assert_eq!(
            translator.translate(0x33, [0; 6]).unwrap().name,
            WindowsSyscallName::NtOpenFile
        );
        assert_eq!(
            translator.translate(0x11, [0; 6]).unwrap().name,
            WindowsSyscallName::NtQueryInformationFile
        );
        assert_eq!(
            translator.translate(0x27, [0; 6]).unwrap().name,
            WindowsSyscallName::NtSetInformationFile
        );
        assert_eq!(
            translator.translate(0x91, [0; 6]).unwrap().name,
            WindowsSyscallName::NtQueryDirectoryFile
        );
        assert_eq!(
            translator.translate(0x41, [0; 6]).unwrap().name,
            WindowsSyscallName::NtFlushBuffersFile
        );
        assert_eq!(
            translator.translate(0x07, [0; 6]).unwrap().name,
            WindowsSyscallName::NtDeviceIoControlFile
        );
        assert_eq!(
            translator.translate(0x09, [0; 6]).unwrap().name,
            WindowsSyscallName::NtFsControlFile
        );
    }

    #[test]
    fn windows_translator_translates_memory_syscalls() {
        let translator = WindowsNtSyscallTranslator::new();
        assert_eq!(
            translator.translate(0x18, [0; 6]).unwrap().name,
            WindowsSyscallName::NtAllocateVirtualMemory
        );
        assert_eq!(
            translator.translate(0x1E, [0; 6]).unwrap().name,
            WindowsSyscallName::NtFreeVirtualMemory
        );
        assert_eq!(
            translator.translate(0x50, [0; 6]).unwrap().name,
            WindowsSyscallName::NtProtectVirtualMemory
        );
        assert_eq!(
            translator.translate(0x28, [0; 6]).unwrap().name,
            WindowsSyscallName::NtMapViewOfSection
        );
        assert_eq!(
            translator.translate(0x2A, [0; 6]).unwrap().name,
            WindowsSyscallName::NtUnmapViewOfSection
        );
        assert_eq!(
            translator.translate(0x23, [0; 6]).unwrap().name,
            WindowsSyscallName::NtQueryVirtualMemory
        );
        assert_eq!(
            translator.translate(0x3D, [0; 6]).unwrap().name,
            WindowsSyscallName::NtReadVirtualMemory
        );
        assert_eq!(
            translator.translate(0x3A, [0; 6]).unwrap().name,
            WindowsSyscallName::NtWriteVirtualMemory
        );
    }

    #[test]
    fn windows_translator_translates_process_and_thread_syscalls() {
        let translator = WindowsNtSyscallTranslator::new();
        assert_eq!(
            translator.translate(0x26, [0; 6]).unwrap().name,
            WindowsSyscallName::NtOpenProcess
        );
        assert_eq!(
            translator.translate(0x4D, [0; 6]).unwrap().name,
            WindowsSyscallName::NtOpenThread
        );
        assert_eq!(
            translator.translate(0x2C, [0; 6]).unwrap().name,
            WindowsSyscallName::NtTerminateProcess
        );
        assert_eq!(
            translator.translate(0x53, [0; 6]).unwrap().name,
            WindowsSyscallName::NtTerminateThread
        );
        assert_eq!(
            translator.translate(0x36, [0; 6]).unwrap().name,
            WindowsSyscallName::NtSuspendThread
        );
        assert_eq!(
            translator.translate(0x4F, [0; 6]).unwrap().name,
            WindowsSyscallName::NtResumeThread
        );
        assert_eq!(
            translator.translate(0xA6, [0; 6]).unwrap().name,
            WindowsSyscallName::NtCreateThread
        );
        assert_eq!(
            translator.translate(0xB9, [0; 6]).unwrap().name,
            WindowsSyscallName::NtCreateThreadEx
        );
        assert_eq!(
            translator.translate(0xC1, [0; 6]).unwrap().name,
            WindowsSyscallName::NtCreateUserProcess
        );
        assert_eq!(
            translator.translate(0x19, [0; 6]).unwrap().name,
            WindowsSyscallName::NtQueryInformationProcess
        );
        assert_eq!(
            translator.translate(0x25, [0; 6]).unwrap().name,
            WindowsSyscallName::NtQueryInformationThread
        );
        assert_eq!(
            translator.translate(0xD4, [0; 6]).unwrap().name,
            WindowsSyscallName::NtGetContextThread
        );
        assert_eq!(
            translator.translate(0xD5, [0; 6]).unwrap().name,
            WindowsSyscallName::NtSetContextThread
        );
    }

    #[test]
    fn windows_translator_translates_synchronization_syscalls() {
        let translator = WindowsNtSyscallTranslator::new();
        assert_eq!(
            translator.translate(0x04, [0; 6]).unwrap().name,
            WindowsSyscallName::NtWaitForSingleObject
        );
        assert_eq!(
            translator.translate(0x05, [0; 6]).unwrap().name,
            WindowsSyscallName::NtWaitForMultipleObjects
        );
        assert_eq!(
            translator.translate(0x0E, [0; 6]).unwrap().name,
            WindowsSyscallName::NtSetEvent
        );
        assert_eq!(
            translator.translate(0xD1, [0; 6]).unwrap().name,
            WindowsSyscallName::NtResetEvent
        );
        assert_eq!(
            translator.translate(0x48, [0; 6]).unwrap().name,
            WindowsSyscallName::NtCreateEvent
        );
        assert_eq!(
            translator.translate(0x49, [0; 6]).unwrap().name,
            WindowsSyscallName::NtOpenEvent
        );
        assert_eq!(
            translator.translate(0x34, [0; 6]).unwrap().name,
            WindowsSyscallName::NtDelayExecution
        );
        assert_eq!(
            translator.translate(0x46, [0; 6]).unwrap().name,
            WindowsSyscallName::NtYieldExecution
        );
    }

    #[test]
    fn windows_translator_translates_registry_syscalls() {
        let translator = WindowsNtSyscallTranslator::new();
        assert_eq!(
            translator.translate(0x77, [0; 6]).unwrap().name,
            WindowsSyscallName::NtCreateKey
        );
        assert_eq!(
            translator.translate(0x78, [0; 6]).unwrap().name,
            WindowsSyscallName::NtOpenKey
        );
        assert_eq!(
            translator.translate(0x79, [0; 6]).unwrap().name,
            WindowsSyscallName::NtQueryValueKey
        );
        assert_eq!(
            translator.translate(0x5D, [0; 6]).unwrap().name,
            WindowsSyscallName::NtSetValueKey
        );
        assert_eq!(
            translator.translate(0x63, [0; 6]).unwrap().name,
            WindowsSyscallName::NtDeleteKey
        );
    }

    #[test]
    fn windows_translator_translates_section_syscalls() {
        let translator = WindowsNtSyscallTranslator::new();
        assert_eq!(
            translator.translate(0x4A, [0; 6]).unwrap().name,
            WindowsSyscallName::NtCreateSection
        );
        assert_eq!(
            translator.translate(0x4B, [0; 6]).unwrap().name,
            WindowsSyscallName::NtOpenSection
        );
    }

    #[test]
    fn windows_translator_translates_query_syscalls() {
        let translator = WindowsNtSyscallTranslator::new();
        assert_eq!(
            translator.translate(0x24, [0; 6]).unwrap().name,
            WindowsSyscallName::NtQuerySystemInformation
        );
        assert_eq!(
            translator.translate(0x19, [0; 6]).unwrap().name,
            WindowsSyscallName::NtQueryInformationProcess
        );
        assert_eq!(
            translator.translate(0x25, [0; 6]).unwrap().name,
            WindowsSyscallName::NtQueryInformationThread
        );
        assert_eq!(
            translator.translate(0x11, [0; 6]).unwrap().name,
            WindowsSyscallName::NtQueryInformationFile
        );
        assert_eq!(
            translator.translate(0x23, [0; 6]).unwrap().name,
            WindowsSyscallName::NtQueryVirtualMemory
        );
        assert_eq!(
            translator.translate(0x91, [0; 6]).unwrap().name,
            WindowsSyscallName::NtQueryDirectoryFile
        );
        assert_eq!(
            translator.translate(0x79, [0; 6]).unwrap().name,
            WindowsSyscallName::NtQueryValueKey
        );
    }

    #[test]
    fn windows_translator_translates_handle_syscalls() {
        let translator = WindowsNtSyscallTranslator::new();
        assert_eq!(
            translator.translate(0x0F, [0; 6]).unwrap().name,
            WindowsSyscallName::NtClose
        );
        assert_eq!(
            translator.translate(0x57, [0; 6]).unwrap().name,
            WindowsSyscallName::NtDuplicateObject
        );
    }

    #[test]
    fn windows_syscall_error_display() {
        let err = WindowsSyscallError::UnknownSyscall(0x55);
        assert_eq!(err.to_string(), "Unknown Windows syscall number: 85");
        let err2 = WindowsSyscallError::InvalidArgument;
        assert_eq!(err2.to_string(), "Invalid argument");
    }

    #[test]
    fn windows_syscall_result_debug() {
        let result = super::WindowsSyscallResult {
            name: WindowsSyscallName::NtCreateFile,
            number: 0x55,
            args: [1, 2, 3, 4, 5, 6],
        };
        let dbg = format!("{:?}", result);
        assert!(dbg.contains("NtCreateFile"));
        assert!(dbg.contains("85"));
    }
}
