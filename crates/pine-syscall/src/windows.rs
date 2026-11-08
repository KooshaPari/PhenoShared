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
            },
            WindowsSyscallError::InvalidArgument => write!(f, "Invalid argument"),
        }
    }
}

impl std::error::Error for WindowsSyscallError {}

/// Named identifier for a Windows NT syscall.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum WindowsSyscallName {
    /// `NtAccessCheck`
    AccessCheck,
    /// `NtAllocateVirtualMemory`
    AllocateVirtualMemory,
    /// `NtClose`
    Close,
    /// `NtCreateEvent`
    CreateEvent,
    /// `NtCreateFile`
    CreateFile,
    /// `NtCreateKey`
    CreateKey,
    /// `NtCreateSection`
    CreateSection,
    /// `NtCreateThread`
    CreateThread,
    /// `NtCreateThreadEx`
    CreateThreadEx,
    /// `NtCreateUserProcess`
    CreateUserProcess,
    /// `NtDelayExecution`
    DelayExecution,
    /// `NtDeleteKey`
    DeleteKey,
    /// `NtDeviceIoControlFile`
    DeviceIoControlFile,
    /// `NtDuplicateObject`
    DuplicateObject,
    /// `NtFlushBuffersFile`
    FlushBuffersFile,
    /// `NtFreeVirtualMemory`
    FreeVirtualMemory,
    /// `NtFsControlFile`
    FsControlFile,
    /// `NtGetContextThread`
    GetContextThread,
    /// `NtMapViewOfSection`
    MapViewOfSection,
    /// `NtOpenEvent`
    OpenEvent,
    /// `NtOpenFile`
    OpenFile,
    /// `NtOpenKey`
    OpenKey,
    /// `NtOpenProcess`
    OpenProcess,
    /// `NtOpenSection`
    OpenSection,
    /// `NtOpenThread`
    OpenThread,
    /// `NtProtectVirtualMemory`
    ProtectVirtualMemory,
    /// `NtQueryDirectoryFile`
    QueryDirectoryFile,
    /// `NtQueryInformationFile`
    QueryInformationFile,
    /// `NtQueryInformationProcess`
    QueryInformationProcess,
    /// `NtQueryInformationThread`
    QueryInformationThread,
    /// `NtQuerySystemInformation`
    QuerySystemInformation,
    /// `NtQueryValueKey`
    QueryValueKey,
    /// `NtQueryVirtualMemory`
    QueryVirtualMemory,
    /// `NtReadFile`
    ReadFile,
    /// `NtReadVirtualMemory`
    ReadVirtualMemory,
    /// `NtResetEvent`
    ResetEvent,
    /// `NtResumeThread`
    ResumeThread,
    /// `NtSetContextThread`
    SetContextThread,
    /// `NtSetEvent`
    SetEvent,
    /// `NtSetInformationFile`
    SetInformationFile,
    /// `NtSetInformationProcess`
    SetInformationProcess,
    /// `NtSetValueKey`
    SetValueKey,
    /// `NtSuspendThread`
    SuspendThread,
    /// `NtTerminateProcess`
    TerminateProcess,
    /// `NtTerminateThread`
    TerminateThread,
    /// `NtUnmapViewOfSection`
    UnmapViewOfSection,
    /// `NtWaitForMultipleObjects`
    WaitForMultipleObjects,
    /// `NtWaitForSingleObject`
    WaitForSingleObject,
    /// `NtWriteFile`
    WriteFile,
    /// `NtWriteVirtualMemory`
    WriteVirtualMemory,
    /// `NtYieldExecution`
    YieldExecution,
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
    pub const NT_CLOSE: u32 = 0x0f;
    /// `NtCreateFile` — create or open a file
    pub const NT_CREATE_FILE: u32 = 0x55;
    /// `NtCreateSection` — create a section object
    pub const NT_CREATE_SECTION: u32 = 0x4a;
    /// `NtDeviceIoControlFile` — perform device I/O control
    pub const NT_DEVICE_IO_CONTROL_FILE: u32 = 0x07;
    /// `NtDuplicateObject` — duplicate an object handle
    pub const NT_DUPLICATE_OBJECT: u32 = 0x57;
    /// `NtFlushBuffersFile` — flush buffers for a file
    pub const NT_FLUSH_BUFFERS_FILE: u32 = 0x41;
    /// `NtFreeVirtualMemory` — free virtual memory
    pub const NT_FREE_VIRTUAL_MEMORY: u32 = 0x1e;
    /// `NtFsControlFile` — perform file system control
    pub const NT_FS_CONTROL_FILE: u32 = 0x09;
    /// `NtMapViewOfSection` — map a view of a section
    pub const NT_MAP_VIEW_OF_SECTION: u32 = 0x28;
    /// `NtOpenFile` — open a file
    pub const NT_OPEN_FILE: u32 = 0x33;
    /// `NtOpenProcess` — open a process object
    pub const NT_OPEN_PROCESS: u32 = 0x26;
    /// `NtOpenSection` — open a section object
    pub const NT_OPEN_SECTION: u32 = 0x4b;
    /// `NtOpenThread` — open a thread object
    pub const NT_OPEN_THREAD: u32 = 0x4d;
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
    pub const NT_READ_VIRTUAL_MEMORY: u32 = 0x3d;
    /// `NtResumeThread` — resume a thread
    pub const NT_RESUME_THREAD: u32 = 0x4f;
    /// `NtSetEvent` — set an event to signaled state
    pub const NT_SET_EVENT: u32 = 0x0e;
    /// `NtSetInformationFile` — set file information
    pub const NT_SET_INFORMATION_FILE: u32 = 0x27;
    /// `NtSuspendThread` — suspend a thread
    pub const NT_SUSPEND_THREAD: u32 = 0x36;
    /// `NtTerminateProcess` — terminate a process
    pub const NT_TERMINATE_PROCESS: u32 = 0x2c;
    /// `NtTerminateThread` — terminate a thread
    pub const NT_TERMINATE_THREAD: u32 = 0x53;
    /// `NtUnmapViewOfSection` — unmap a view of a section
    pub const NT_UNMAP_VIEW_OF_SECTION: u32 = 0x2a;
    /// `NtWaitForMultipleObjects` — wait for multiple objects
    pub const NT_WAIT_FOR_MULTIPLE_OBJECTS: u32 = 0x05;
    /// `NtWaitForSingleObject` — wait for a single object
    pub const NT_WAIT_FOR_SINGLE_OBJECT: u32 = 0x04;
    /// `NtWriteFile` — write to a file
    pub const NT_WRITE_FILE: u32 = 0x08;
    /// `NtWriteVirtualMemory` — write virtual memory
    pub const NT_WRITE_VIRTUAL_MEMORY: u32 = 0x3a;
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
    pub const NT_SET_VALUE_KEY: u32 = 0x5d;
    /// `NtDeleteKey` — delete a registry key
    pub const NT_DELETE_KEY: u32 = 0x63;
    /// `NtCreateThread` — create a thread
    pub const NT_CREATE_THREAD: u32 = 0xa6;
    /// `NtCreateThreadEx` — create a thread (extended)
    pub const NT_CREATE_THREAD_EX: u32 = 0xb9;
    /// `NtCreateUserProcess` — create a user process
    pub const NT_CREATE_USER_PROCESS: u32 = 0xc1;
    /// `NtGetContextThread` — get thread context
    pub const NT_GET_CONTEXT_THREAD: u32 = 0xd4;
    /// `NtSetContextThread` — set thread context
    pub const NT_SET_CONTEXT_THREAD: u32 = 0xd5;
    /// `NtAccessCheck` — check access rights
    pub const NT_ACCESS_CHECK: u32 = 0x00;
    /// `NtResetEvent` — reset an event to non-signaled state
    pub const NT_RESET_EVENT: u32 = 0xd1;

    /// Create a new translator with the standard Windows NT syscall table.
    pub fn new() -> Self {
        let mut table = HashMap::new();
        table.insert(0x00, WindowsSyscallName::AccessCheck);
        table.insert(0x04, WindowsSyscallName::WaitForSingleObject);
        table.insert(0x05, WindowsSyscallName::WaitForMultipleObjects);
        table.insert(0x06, WindowsSyscallName::ReadFile);
        table.insert(0x07, WindowsSyscallName::DeviceIoControlFile);
        table.insert(0x08, WindowsSyscallName::WriteFile);
        table.insert(0x09, WindowsSyscallName::FsControlFile);
        table.insert(0x0e, WindowsSyscallName::SetEvent);
        table.insert(0x0f, WindowsSyscallName::Close);
        table.insert(0x11, WindowsSyscallName::QueryInformationFile);
        table.insert(0x18, WindowsSyscallName::AllocateVirtualMemory);
        table.insert(0x19, WindowsSyscallName::QueryInformationProcess);
        table.insert(0x1e, WindowsSyscallName::FreeVirtualMemory);
        table.insert(0x23, WindowsSyscallName::QueryVirtualMemory);
        table.insert(0x24, WindowsSyscallName::QuerySystemInformation);
        table.insert(0x25, WindowsSyscallName::QueryInformationThread);
        table.insert(0x26, WindowsSyscallName::OpenProcess);
        table.insert(0x27, WindowsSyscallName::SetInformationFile);
        table.insert(0x28, WindowsSyscallName::MapViewOfSection);
        table.insert(0x2a, WindowsSyscallName::UnmapViewOfSection);
        table.insert(0x2c, WindowsSyscallName::TerminateProcess);
        table.insert(0x33, WindowsSyscallName::OpenFile);
        table.insert(0x34, WindowsSyscallName::DelayExecution);
        table.insert(0x36, WindowsSyscallName::SuspendThread);
        table.insert(0x3a, WindowsSyscallName::WriteVirtualMemory);
        table.insert(0x3d, WindowsSyscallName::ReadVirtualMemory);
        table.insert(0x41, WindowsSyscallName::FlushBuffersFile);
        table.insert(0x46, WindowsSyscallName::YieldExecution);
        table.insert(0x48, WindowsSyscallName::CreateEvent);
        table.insert(0x49, WindowsSyscallName::OpenEvent);
        table.insert(0x4a, WindowsSyscallName::CreateSection);
        table.insert(0x4b, WindowsSyscallName::OpenSection);
        table.insert(0x4d, WindowsSyscallName::OpenThread);
        table.insert(0x4f, WindowsSyscallName::ResumeThread);
        table.insert(0x50, WindowsSyscallName::ProtectVirtualMemory);
        table.insert(0x53, WindowsSyscallName::TerminateThread);
        table.insert(0x55, WindowsSyscallName::CreateFile);
        table.insert(0x57, WindowsSyscallName::DuplicateObject);
        table.insert(0x5d, WindowsSyscallName::SetValueKey);
        table.insert(0x63, WindowsSyscallName::DeleteKey);
        table.insert(0x77, WindowsSyscallName::CreateKey);
        table.insert(0x78, WindowsSyscallName::OpenKey);
        table.insert(0x79, WindowsSyscallName::QueryValueKey);
        table.insert(0x91, WindowsSyscallName::QueryDirectoryFile);
        table.insert(0xa6, WindowsSyscallName::CreateThread);
        table.insert(0xb9, WindowsSyscallName::CreateThreadEx);
        table.insert(0xc1, WindowsSyscallName::CreateUserProcess);
        table.insert(0xd4, WindowsSyscallName::GetContextThread);
        table.insert(0xd5, WindowsSyscallName::SetContextThread);
        table.insert(0xd1, WindowsSyscallName::ResetEvent);
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
        assert_eq!(result.name, WindowsSyscallName::CreateFile);
        assert_eq!(result.number, 0x55);
        assert_eq!(result.args, [1, 2, 3, 4, 5, 6]);
    }

    #[test]
    fn windows_translator_translates_nt_read_file() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_READ_FILE, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::ReadFile);
        assert_eq!(result.number, 0x06);
    }

    #[test]
    fn windows_translator_translates_nt_write_file() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_WRITE_FILE, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::WriteFile);
        assert_eq!(result.number, 0x08);
    }

    #[test]
    fn windows_translator_translates_nt_close() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_CLOSE, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::Close);
        assert_eq!(result.number, 0x0f);
    }

    #[test]
    fn windows_translator_translates_nt_open_file() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_OPEN_FILE, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::OpenFile);
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
        assert_eq!(result.name, WindowsSyscallName::AllocateVirtualMemory);
    }

    #[test]
    fn windows_translator_translates_nt_free_virtual_memory() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_FREE_VIRTUAL_MEMORY, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::FreeVirtualMemory);
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
        assert_eq!(result.name, WindowsSyscallName::ProtectVirtualMemory);
    }

    #[test]
    fn windows_translator_translates_nt_map_view_of_section() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_MAP_VIEW_OF_SECTION, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::MapViewOfSection);
    }

    #[test]
    fn windows_translator_translates_nt_unmap_view_of_section() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_UNMAP_VIEW_OF_SECTION, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::UnmapViewOfSection);
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
        assert_eq!(result.name, WindowsSyscallName::QuerySystemInformation);
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
        assert_eq!(result.name, WindowsSyscallName::QueryInformationProcess);
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
        assert_eq!(result.name, WindowsSyscallName::WaitForSingleObject);
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
        assert_eq!(result.name, WindowsSyscallName::WaitForMultipleObjects);
    }

    #[test]
    fn windows_translator_translates_nt_set_event() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_SET_EVENT, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::SetEvent);
    }

    #[test]
    fn windows_translator_translates_nt_create_event() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_CREATE_EVENT, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::CreateEvent);
    }

    #[test]
    fn windows_translator_translates_nt_open_event() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_OPEN_EVENT, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::OpenEvent);
    }

    #[test]
    fn windows_translator_translates_nt_terminate_process() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_TERMINATE_PROCESS, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::TerminateProcess);
    }

    #[test]
    fn windows_translator_translates_nt_terminate_thread() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_TERMINATE_THREAD, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::TerminateThread);
    }

    #[test]
    fn windows_translator_translates_nt_suspend_thread() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_SUSPEND_THREAD, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::SuspendThread);
    }

    #[test]
    fn windows_translator_translates_nt_resume_thread() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_RESUME_THREAD, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::ResumeThread);
    }

    #[test]
    fn windows_translator_translates_nt_create_thread() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_CREATE_THREAD, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::CreateThread);
    }

    #[test]
    fn windows_translator_translates_nt_create_thread_ex() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_CREATE_THREAD_EX, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::CreateThreadEx);
    }

    #[test]
    fn windows_translator_translates_nt_create_user_process() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_CREATE_USER_PROCESS, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::CreateUserProcess);
    }

    #[test]
    fn windows_translator_translates_nt_create_key() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_CREATE_KEY, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::CreateKey);
    }

    #[test]
    fn windows_translator_translates_nt_open_key() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_OPEN_KEY, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::OpenKey);
    }

    #[test]
    fn windows_translator_translates_nt_set_value_key() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_SET_VALUE_KEY, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::SetValueKey);
    }

    #[test]
    fn windows_translator_translates_nt_query_value_key() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_QUERY_VALUE_KEY, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::QueryValueKey);
    }

    #[test]
    fn windows_translator_translates_nt_delete_key() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_DELETE_KEY, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::DeleteKey);
    }

    #[test]
    fn windows_translator_translates_nt_duplicate_object() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_DUPLICATE_OBJECT, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::DuplicateObject);
    }

    #[test]
    fn windows_translator_translates_nt_query_directory_file() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_QUERY_DIRECTORY_FILE, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::QueryDirectoryFile);
    }

    #[test]
    fn windows_translator_translates_nt_flush_buffers_file() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_FLUSH_BUFFERS_FILE, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::FlushBuffersFile);
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
        assert_eq!(result.name, WindowsSyscallName::DeviceIoControlFile);
    }

    #[test]
    fn windows_translator_translates_nt_fs_control_file() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_FS_CONTROL_FILE, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::FsControlFile);
    }

    #[test]
    fn windows_translator_translates_nt_yield_execution() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_YIELD_EXECUTION, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::YieldExecution);
    }

    #[test]
    fn windows_translator_translates_nt_delay_execution() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_DELAY_EXECUTION, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::DelayExecution);
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
        assert_eq!(result.name, WindowsSyscallName::QueryInformationFile);
    }

    #[test]
    fn windows_translator_translates_nt_set_information_file() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_SET_INFORMATION_FILE, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::SetInformationFile);
    }

    #[test]
    fn windows_translator_translates_nt_query_virtual_memory() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_QUERY_VIRTUAL_MEMORY, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::QueryVirtualMemory);
    }

    #[test]
    fn windows_translator_translates_nt_read_virtual_memory() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_READ_VIRTUAL_MEMORY, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::ReadVirtualMemory);
    }

    #[test]
    fn windows_translator_translates_nt_write_virtual_memory() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_WRITE_VIRTUAL_MEMORY, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::WriteVirtualMemory);
    }

    #[test]
    fn windows_translator_translates_nt_open_process() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_OPEN_PROCESS, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::OpenProcess);
    }

    #[test]
    fn windows_translator_translates_nt_open_thread() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_OPEN_THREAD, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::OpenThread);
    }

    #[test]
    fn windows_translator_translates_nt_create_section() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_CREATE_SECTION, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::CreateSection);
    }

    #[test]
    fn windows_translator_translates_nt_open_section() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_OPEN_SECTION, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::OpenSection);
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
        assert_eq!(result.name, WindowsSyscallName::QueryInformationThread);
    }

    #[test]
    fn windows_translator_translates_nt_get_context_thread() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_GET_CONTEXT_THREAD, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::GetContextThread);
    }

    #[test]
    fn windows_translator_translates_nt_set_context_thread() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_SET_CONTEXT_THREAD, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::SetContextThread);
    }

    #[test]
    fn windows_translator_translates_nt_reset_event() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_RESET_EVENT, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::ResetEvent);
    }

    #[test]
    fn windows_translator_translates_nt_access_check() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator
            .translate(WindowsNtSyscallTranslator::NT_ACCESS_CHECK, [0; 6])
            .unwrap();
        assert_eq!(result.name, WindowsSyscallName::AccessCheck);
    }

    #[test]
    fn windows_translator_returns_error_for_unknown() {
        let translator = WindowsNtSyscallTranslator::new();
        let result = translator.translate(0xffff, [0; 6]);
        assert!(result.is_err());
        assert_eq!(
            result.unwrap_err(),
            WindowsSyscallError::UnknownSyscall(0xffff)
        );
    }

    #[test]
    fn windows_translator_lookup_name() {
        let translator = WindowsNtSyscallTranslator::new();
        assert_eq!(
            translator.lookup_name(0x55),
            Some(&WindowsSyscallName::CreateFile)
        );
        assert_eq!(
            translator.lookup_name(0x06),
            Some(&WindowsSyscallName::ReadFile)
        );
        assert_eq!(
            translator.lookup_name(0x08),
            Some(&WindowsSyscallName::WriteFile)
        );
        assert_eq!(translator.lookup_name(0xffff), None);
    }

    #[test]
    fn windows_translator_lookup_number() {
        let translator = WindowsNtSyscallTranslator::new();
        assert_eq!(
            translator.lookup_number(WindowsSyscallName::CreateFile),
            Some(0x55)
        );
        assert_eq!(
            translator.lookup_number(WindowsSyscallName::ReadFile),
            Some(0x06)
        );
        assert_eq!(
            translator.lookup_number(WindowsSyscallName::WriteFile),
            Some(0x08)
        );
        assert_eq!(
            translator.lookup_number(WindowsSyscallName::Close),
            Some(0x0f)
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
            Some(&WindowsSyscallName::CreateFile)
        );
        assert_eq!(
            translator.lookup_name(0x06),
            Some(&WindowsSyscallName::ReadFile)
        );
    }

    #[test]
    fn windows_translator_translates_file_syscalls() {
        let translator = WindowsNtSyscallTranslator::new();
        assert_eq!(
            translator.translate(0x55, [0; 6]).unwrap().name,
            WindowsSyscallName::CreateFile
        );
        assert_eq!(
            translator.translate(0x06, [0; 6]).unwrap().name,
            WindowsSyscallName::ReadFile
        );
        assert_eq!(
            translator.translate(0x08, [0; 6]).unwrap().name,
            WindowsSyscallName::WriteFile
        );
        assert_eq!(
            translator.translate(0x0f, [0; 6]).unwrap().name,
            WindowsSyscallName::Close
        );
        assert_eq!(
            translator.translate(0x33, [0; 6]).unwrap().name,
            WindowsSyscallName::OpenFile
        );
        assert_eq!(
            translator.translate(0x11, [0; 6]).unwrap().name,
            WindowsSyscallName::QueryInformationFile
        );
        assert_eq!(
            translator.translate(0x27, [0; 6]).unwrap().name,
            WindowsSyscallName::SetInformationFile
        );
        assert_eq!(
            translator.translate(0x91, [0; 6]).unwrap().name,
            WindowsSyscallName::QueryDirectoryFile
        );
        assert_eq!(
            translator.translate(0x41, [0; 6]).unwrap().name,
            WindowsSyscallName::FlushBuffersFile
        );
        assert_eq!(
            translator.translate(0x07, [0; 6]).unwrap().name,
            WindowsSyscallName::DeviceIoControlFile
        );
        assert_eq!(
            translator.translate(0x09, [0; 6]).unwrap().name,
            WindowsSyscallName::FsControlFile
        );
    }

    #[test]
    fn windows_translator_translates_memory_syscalls() {
        let translator = WindowsNtSyscallTranslator::new();
        assert_eq!(
            translator.translate(0x18, [0; 6]).unwrap().name,
            WindowsSyscallName::AllocateVirtualMemory
        );
        assert_eq!(
            translator.translate(0x1e, [0; 6]).unwrap().name,
            WindowsSyscallName::FreeVirtualMemory
        );
        assert_eq!(
            translator.translate(0x50, [0; 6]).unwrap().name,
            WindowsSyscallName::ProtectVirtualMemory
        );
        assert_eq!(
            translator.translate(0x28, [0; 6]).unwrap().name,
            WindowsSyscallName::MapViewOfSection
        );
        assert_eq!(
            translator.translate(0x2a, [0; 6]).unwrap().name,
            WindowsSyscallName::UnmapViewOfSection
        );
        assert_eq!(
            translator.translate(0x23, [0; 6]).unwrap().name,
            WindowsSyscallName::QueryVirtualMemory
        );
        assert_eq!(
            translator.translate(0x3d, [0; 6]).unwrap().name,
            WindowsSyscallName::ReadVirtualMemory
        );
        assert_eq!(
            translator.translate(0x3a, [0; 6]).unwrap().name,
            WindowsSyscallName::WriteVirtualMemory
        );
    }

    #[test]
    fn windows_translator_translates_process_and_thread_syscalls() {
        let translator = WindowsNtSyscallTranslator::new();
        assert_eq!(
            translator.translate(0x26, [0; 6]).unwrap().name,
            WindowsSyscallName::OpenProcess
        );
        assert_eq!(
            translator.translate(0x4d, [0; 6]).unwrap().name,
            WindowsSyscallName::OpenThread
        );
        assert_eq!(
            translator.translate(0x2c, [0; 6]).unwrap().name,
            WindowsSyscallName::TerminateProcess
        );
        assert_eq!(
            translator.translate(0x53, [0; 6]).unwrap().name,
            WindowsSyscallName::TerminateThread
        );
        assert_eq!(
            translator.translate(0x36, [0; 6]).unwrap().name,
            WindowsSyscallName::SuspendThread
        );
        assert_eq!(
            translator.translate(0x4f, [0; 6]).unwrap().name,
            WindowsSyscallName::ResumeThread
        );
        assert_eq!(
            translator.translate(0xa6, [0; 6]).unwrap().name,
            WindowsSyscallName::CreateThread
        );
        assert_eq!(
            translator.translate(0xb9, [0; 6]).unwrap().name,
            WindowsSyscallName::CreateThreadEx
        );
        assert_eq!(
            translator.translate(0xc1, [0; 6]).unwrap().name,
            WindowsSyscallName::CreateUserProcess
        );
        assert_eq!(
            translator.translate(0x19, [0; 6]).unwrap().name,
            WindowsSyscallName::QueryInformationProcess
        );
        assert_eq!(
            translator.translate(0x25, [0; 6]).unwrap().name,
            WindowsSyscallName::QueryInformationThread
        );
        assert_eq!(
            translator.translate(0xd4, [0; 6]).unwrap().name,
            WindowsSyscallName::GetContextThread
        );
        assert_eq!(
            translator.translate(0xd5, [0; 6]).unwrap().name,
            WindowsSyscallName::SetContextThread
        );
    }

    #[test]
    fn windows_translator_translates_synchronization_syscalls() {
        let translator = WindowsNtSyscallTranslator::new();
        assert_eq!(
            translator.translate(0x04, [0; 6]).unwrap().name,
            WindowsSyscallName::WaitForSingleObject
        );
        assert_eq!(
            translator.translate(0x05, [0; 6]).unwrap().name,
            WindowsSyscallName::WaitForMultipleObjects
        );
        assert_eq!(
            translator.translate(0x0e, [0; 6]).unwrap().name,
            WindowsSyscallName::SetEvent
        );
        assert_eq!(
            translator.translate(0xd1, [0; 6]).unwrap().name,
            WindowsSyscallName::ResetEvent
        );
        assert_eq!(
            translator.translate(0x48, [0; 6]).unwrap().name,
            WindowsSyscallName::CreateEvent
        );
        assert_eq!(
            translator.translate(0x49, [0; 6]).unwrap().name,
            WindowsSyscallName::OpenEvent
        );
        assert_eq!(
            translator.translate(0x34, [0; 6]).unwrap().name,
            WindowsSyscallName::DelayExecution
        );
        assert_eq!(
            translator.translate(0x46, [0; 6]).unwrap().name,
            WindowsSyscallName::YieldExecution
        );
    }

    #[test]
    fn windows_translator_translates_registry_syscalls() {
        let translator = WindowsNtSyscallTranslator::new();
        assert_eq!(
            translator.translate(0x77, [0; 6]).unwrap().name,
            WindowsSyscallName::CreateKey
        );
        assert_eq!(
            translator.translate(0x78, [0; 6]).unwrap().name,
            WindowsSyscallName::OpenKey
        );
        assert_eq!(
            translator.translate(0x79, [0; 6]).unwrap().name,
            WindowsSyscallName::QueryValueKey
        );
        assert_eq!(
            translator.translate(0x5d, [0; 6]).unwrap().name,
            WindowsSyscallName::SetValueKey
        );
        assert_eq!(
            translator.translate(0x63, [0; 6]).unwrap().name,
            WindowsSyscallName::DeleteKey
        );
    }

    #[test]
    fn windows_translator_translates_section_syscalls() {
        let translator = WindowsNtSyscallTranslator::new();
        assert_eq!(
            translator.translate(0x4a, [0; 6]).unwrap().name,
            WindowsSyscallName::CreateSection
        );
        assert_eq!(
            translator.translate(0x4b, [0; 6]).unwrap().name,
            WindowsSyscallName::OpenSection
        );
    }

    #[test]
    fn windows_translator_translates_query_syscalls() {
        let translator = WindowsNtSyscallTranslator::new();
        assert_eq!(
            translator.translate(0x24, [0; 6]).unwrap().name,
            WindowsSyscallName::QuerySystemInformation
        );
        assert_eq!(
            translator.translate(0x19, [0; 6]).unwrap().name,
            WindowsSyscallName::QueryInformationProcess
        );
        assert_eq!(
            translator.translate(0x25, [0; 6]).unwrap().name,
            WindowsSyscallName::QueryInformationThread
        );
        assert_eq!(
            translator.translate(0x11, [0; 6]).unwrap().name,
            WindowsSyscallName::QueryInformationFile
        );
        assert_eq!(
            translator.translate(0x23, [0; 6]).unwrap().name,
            WindowsSyscallName::QueryVirtualMemory
        );
        assert_eq!(
            translator.translate(0x91, [0; 6]).unwrap().name,
            WindowsSyscallName::QueryDirectoryFile
        );
        assert_eq!(
            translator.translate(0x79, [0; 6]).unwrap().name,
            WindowsSyscallName::QueryValueKey
        );
    }

    #[test]
    fn windows_translator_translates_handle_syscalls() {
        let translator = WindowsNtSyscallTranslator::new();
        assert_eq!(
            translator.translate(0x0f, [0; 6]).unwrap().name,
            WindowsSyscallName::Close
        );
        assert_eq!(
            translator.translate(0x57, [0; 6]).unwrap().name,
            WindowsSyscallName::DuplicateObject
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
            name: WindowsSyscallName::CreateFile,
            number: 0x55,
            args: [1, 2, 3, 4, 5, 6],
        };
        let dbg = format!("{:?}", result);
        assert!(dbg.contains("NtCreateFile"));
        assert!(dbg.contains("85"));
    }
}
