//! Linux-specific syscall translator.
//!
//! Maps common Linux syscalls to their x86_64 numbers and provides a
//! [`SyscallTranslator`] implementation for the Linux/x86_64 platform.

use crate::{SyscallError, SyscallName, SyscallResult, SyscallTranslator, X86_64SyscallTranslator};

/// Linux-specific syscall translator backed by the x86_64 syscall table.
///
/// This is the primary entry-point for translating raw Linux syscall numbers
/// on the x86_64 architecture. It delegates to [`X86_64SyscallTranslator`] internally
/// so that both structs share the same canonical table.
#[derive(Debug, Clone)]
pub struct LinuxSyscallTranslator {
    inner: X86_64SyscallTranslator,
}

/// Common Linux x86_64 syscall numbers.
///
/// These constants are kept in sync with the table used by [`X86_64SyscallTranslator`].
impl LinuxSyscallTranslator {
    /// `read` — read from a file descriptor
    pub const READ: u64 = 0;
    /// `write` — write to a file descriptor
    pub const WRITE: u64 = 1;
    /// `open` — open and possibly create a file
    pub const OPEN: u64 = 2;
    /// `close` — close a file descriptor
    pub const CLOSE: u64 = 3;
    /// `stat` — get file status
    pub const STAT: u64 = 4;
    /// `fstat` — get file status
    pub const FSTAT: u64 = 5;
    /// `lstat` — get file status
    pub const LSTAT: u64 = 6;
    /// `poll` — wait for some event on a file descriptor
    pub const POLL: u64 = 7;
    /// `lseek` — reposition read/write file offset
    pub const LSEEK: u64 = 8;
    /// `mmap` — map files or devices into memory
    pub const MMAP: u64 = 9;
    /// `mprotect` — set protection on a region of memory
    pub const MPROTECT: u64 = 10;
    /// `munmap` — unmap memory
    pub const MUNMAP: u64 = 11;
    /// `brk` — change data segment size
    pub const BRK: u64 = 12;
    /// `ioctl` — control device
    pub const IOCTL: u64 = 16;
    /// `pread64` — read from a file descriptor at a given offset
    pub const PREAD64: u64 = 17;
    /// `pwrite64` — write to a file descriptor at a given offset
    pub const PWRITE64: u64 = 18;
    /// `access` — check user's permissions for a file
    pub const ACCESS: u64 = 21;
    /// `dup` — duplicate a file descriptor
    pub const DUP: u64 = 32;
    /// `dup2` — duplicate a file descriptor
    pub const DUP2: u64 = 33;
    /// `getpid` — get process identification
    pub const GETPID: u64 = 39;
    /// `socket` — create an endpoint for communication
    pub const SOCKET: u64 = 41;
    /// `connect` — initiate a connection on a socket
    pub const CONNECT: u64 = 42;
    /// `accept` — accept a connection on a socket
    pub const ACCEPT: u64 = 43;
    /// `sendto` — send a message on a socket
    pub const SENDTO: u64 = 44;
    /// `recvfrom` — receive a message from a socket
    pub const RECVFROM: u64 = 45;
    /// `bind` — bind a name to a socket
    pub const BIND: u64 = 49;
    /// `listen` — listen for connections on a socket
    pub const LISTEN: u64 = 50;
    /// `clone` — create a child process
    pub const CLONE: u64 = 56;
    /// `fork` — create a child process
    pub const FORK: u64 = 57;
    /// `execve` — execute program
    pub const EXECVE: u64 = 59;
    /// `exit` — terminate the calling process
    pub const EXIT: u64 = 60;
    /// `wait4` — wait for process to change state, BSD style
    pub const WAIT4: u64 = 61;
    /// `kill` — send signal to a process
    pub const KILL: u64 = 62;
    /// `fcntl` — manipulate file descriptor
    pub const FCNTL: u64 = 72;
    /// `fsync` — synchronize a file's in-core state with storage
    pub const FSYNC: u64 = 74;
    /// `getcwd` — get current working directory
    pub const GETCWD: u64 = 79;
    /// `chdir` — change working directory
    pub const CHDIR: u64 = 80;
    /// `rename` — change the name or location of a file
    pub const RENAME: u64 = 82;
    /// `mkdir` — create a directory
    pub const MKDIR: u64 = 83;
    /// `unlink` — delete a name and possibly the file it refers to
    pub const UNLINK: u64 = 87;
    /// `chmod` — change permissions of a file
    pub const CHMOD: u64 = 90;
    /// `getuid` — get user identity
    pub const GETUID: u64 = 102;
    /// `getgid` — get group identity
    pub const GETGID: u64 = 104;
    /// `geteuid` — get effective user identity
    pub const GETEUID: u64 = 107;
    /// `getegid` — get effective group identity
    pub const GETEGID: u64 = 108;
    /// `getppid` — get parent process ID
    pub const GETPPID: u64 = 110;
    /// `gettid` — get thread identification
    pub const GETTID: u64 = 186;
    /// `exit_group` — exit all threads in a process
    pub const EXIT_GROUP: u64 = 231;
    /// `openat` — open file relative to directory file descriptor
    pub const OPENAT: u64 = 257;
    /// `mkdirat` — create a directory relative to directory file descriptor
    pub const MKDIRAT: u64 = 258;
    /// `unlinkat` — delete a name and possibly the file it refers to
    pub const UNLINKAT: u64 = 263;
    /// `renameat2` — rename a file
    pub const RENAMEAT2: u64 = 316;
    /// `getrandom` — obtain a series of random bytes
    pub const GETRANDOM: u64 = 318;
    /// `memfd_create` — create an anonymous file
    pub const MEMFD_CREATE: u64 = 319;
    /// `copy_file_range` — copy a range of data from one file to another
    pub const COPY_FILE_RANGE: u64 = 326;
    /// `statx` — get file status (extended)
    pub const STATX: u64 = 332;
    /// `io_uring_setup` — setup a context for performing asynchronous I/O
    pub const IO_URING_SETUP: u64 = 425;
    /// `io_uring_enter` — initiate and/or complete asynchronous I/O
    pub const IO_URING_ENTER: u64 = 426;
    /// `io_uring_register` — register files or user buffers for asynchronous I/O
    pub const IO_URING_REGISTER: u64 = 427;

    /// Create a new Linux-specific translator.
    pub fn new() -> Self {
        Self {
            inner: X86_64SyscallTranslator::new(),
        }
    }

    /// Look up the syscall name for a given number.
    pub fn lookup_name(&self, number: u64) -> Option<&SyscallName> {
        self.inner.lookup_name(number)
    }

    /// Look up the syscall number for a given name.
    pub fn lookup_number(&self, name: SyscallName) -> Option<u64> {
        self.inner.lookup_number(name)
    }
}

impl Default for LinuxSyscallTranslator {
    fn default() -> Self {
        Self::new()
    }
}

impl SyscallTranslator for LinuxSyscallTranslator {
    fn translate(&self, syscall_num: u64, args: [u64; 6]) -> Result<SyscallResult, SyscallError> {
        self.inner.translate(syscall_num, args)
    }
}

#[cfg(test)]
mod tests {
    use super::LinuxSyscallTranslator;
    use crate::{SyscallError, SyscallName, SyscallTranslator};

    #[test]
    fn linux_translator_translates_read() {
        let translator = LinuxSyscallTranslator::new();
        let result = translator.translate(0, [1, 2, 3, 4, 5, 6]).unwrap();
        assert_eq!(result.name, SyscallName::Read);
        assert_eq!(result.number, 0);
        assert_eq!(result.args, [1, 2, 3, 4, 5, 6]);
    }

    #[test]
    fn linux_translator_translates_write() {
        let translator = LinuxSyscallTranslator::new();
        let result = translator.translate(1, [0; 6]).unwrap();
        assert_eq!(result.name, SyscallName::Write);
        assert_eq!(result.number, 1);
    }

    #[test]
    fn linux_translator_translates_open() {
        let translator = LinuxSyscallTranslator::new();
        let result = translator.translate(2, [0; 6]).unwrap();
        assert_eq!(result.name, SyscallName::Open);
    }

    #[test]
    fn linux_translator_translates_close() {
        let translator = LinuxSyscallTranslator::new();
        let result = translator.translate(3, [0; 6]).unwrap();
        assert_eq!(result.name, SyscallName::Close);
    }

    #[test]
    fn linux_translator_translates_mmap() {
        let translator = LinuxSyscallTranslator::new();
        let result = translator.translate(9, [0; 6]).unwrap();
        assert_eq!(result.name, SyscallName::Mmap);
    }

    #[test]
    fn linux_translator_translates_mprotect() {
        let translator = LinuxSyscallTranslator::new();
        let result = translator.translate(10, [0; 6]).unwrap();
        assert_eq!(result.name, SyscallName::Mprotect);
    }

    #[test]
    fn linux_translator_translates_munmap() {
        let translator = LinuxSyscallTranslator::new();
        let result = translator.translate(11, [0; 6]).unwrap();
        assert_eq!(result.name, SyscallName::Munmap);
    }

    #[test]
    fn linux_translator_translates_brk() {
        let translator = LinuxSyscallTranslator::new();
        let result = translator.translate(12, [0; 6]).unwrap();
        assert_eq!(result.name, SyscallName::Brk);
    }

    #[test]
    fn linux_translator_translates_ioctl() {
        let translator = LinuxSyscallTranslator::new();
        let result = translator.translate(16, [0; 6]).unwrap();
        assert_eq!(result.name, SyscallName::Ioctl);
    }

    #[test]
    fn linux_translator_translates_exit() {
        let translator = LinuxSyscallTranslator::new();
        let result = translator.translate(60, [0; 6]).unwrap();
        assert_eq!(result.name, SyscallName::Exit);
    }

    #[test]
    fn linux_translator_translates_exit_group() {
        let translator = LinuxSyscallTranslator::new();
        let result = translator.translate(231, [0; 6]).unwrap();
        assert_eq!(result.name, SyscallName::ExitGroup);
    }

    #[test]
    fn linux_translator_translates_openat() {
        let translator = LinuxSyscallTranslator::new();
        let result = translator.translate(257, [0; 6]).unwrap();
        assert_eq!(result.name, SyscallName::Openat);
    }

    #[test]
    fn linux_translator_translates_getrandom() {
        let translator = LinuxSyscallTranslator::new();
        let result = translator.translate(318, [0; 6]).unwrap();
        assert_eq!(result.name, SyscallName::Getrandom);
    }

    #[test]
    fn linux_translator_translates_io_uring_setup() {
        let translator = LinuxSyscallTranslator::new();
        let result = translator.translate(425, [0; 6]).unwrap();
        assert_eq!(result.name, SyscallName::IoUringSetup);
    }

    #[test]
    fn linux_translator_returns_error_for_unknown() {
        let translator = LinuxSyscallTranslator::new();
        let result = translator.translate(9999, [0; 6]);
        assert!(result.is_err());
        assert_eq!(result.unwrap_err(), SyscallError::UnknownSyscall(9999));
    }

    #[test]
    fn linux_translator_lookup_name() {
        let translator = LinuxSyscallTranslator::new();
        assert_eq!(translator.lookup_name(0), Some(&SyscallName::Read));
        assert_eq!(translator.lookup_name(60), Some(&SyscallName::Exit));
        assert_eq!(translator.lookup_name(99999), None);
    }

    #[test]
    fn linux_translator_lookup_number() {
        let translator = LinuxSyscallTranslator::new();
        assert_eq!(translator.lookup_number(SyscallName::Read), Some(0));
        assert_eq!(translator.lookup_number(SyscallName::Write), Some(1));
        assert_eq!(translator.lookup_number(SyscallName::Exit), Some(60));
        assert_eq!(translator.lookup_number(SyscallName::Mmap), Some(9));
    }

    #[test]
    fn linux_translator_constants_match_table() {
        let translator = LinuxSyscallTranslator::new();
        assert_eq!(
            translator
                .translate(LinuxSyscallTranslator::READ, [0; 6])
                .unwrap()
                .name,
            SyscallName::Read
        );
        assert_eq!(
            translator
                .translate(LinuxSyscallTranslator::WRITE, [0; 6])
                .unwrap()
                .name,
            SyscallName::Write
        );
        assert_eq!(
            translator
                .translate(LinuxSyscallTranslator::OPEN, [0; 6])
                .unwrap()
                .name,
            SyscallName::Open
        );
        assert_eq!(
            translator
                .translate(LinuxSyscallTranslator::CLOSE, [0; 6])
                .unwrap()
                .name,
            SyscallName::Close
        );
        assert_eq!(
            translator
                .translate(LinuxSyscallTranslator::MMAP, [0; 6])
                .unwrap()
                .name,
            SyscallName::Mmap
        );
        assert_eq!(
            translator
                .translate(LinuxSyscallTranslator::OPENAT, [0; 6])
                .unwrap()
                .name,
            SyscallName::Openat
        );
        assert_eq!(
            translator
                .translate(LinuxSyscallTranslator::GETRANDOM, [0; 6])
                .unwrap()
                .name,
            SyscallName::Getrandom
        );
        assert_eq!(
            translator
                .translate(LinuxSyscallTranslator::EXIT_GROUP, [0; 6])
                .unwrap()
                .name,
            SyscallName::ExitGroup
        );
    }

    #[test]
    fn linux_translator_implements_trait() {
        fn takes_translator<T: SyscallTranslator>(_t: &T) {}
        let translator = LinuxSyscallTranslator::new();
        takes_translator(&translator);
    }

    #[test]
    fn linux_translator_default() {
        let translator = LinuxSyscallTranslator::default();
        assert_eq!(translator.lookup_name(0), Some(&SyscallName::Read));
        assert_eq!(translator.lookup_name(1), Some(&SyscallName::Write));
    }

    #[test]
    fn linux_translator_translates_network_syscalls() {
        let translator = LinuxSyscallTranslator::new();
        assert_eq!(
            translator.translate(41, [0; 6]).unwrap().name,
            SyscallName::Socket
        );
        assert_eq!(
            translator.translate(42, [0; 6]).unwrap().name,
            SyscallName::Connect
        );
        assert_eq!(
            translator.translate(43, [0; 6]).unwrap().name,
            SyscallName::Accept
        );
        assert_eq!(
            translator.translate(49, [0; 6]).unwrap().name,
            SyscallName::Bind
        );
        assert_eq!(
            translator.translate(50, [0; 6]).unwrap().name,
            SyscallName::Listen
        );
    }

    #[test]
    fn linux_translator_translates_process_syscalls() {
        let translator = LinuxSyscallTranslator::new();
        assert_eq!(
            translator.translate(39, [0; 6]).unwrap().name,
            SyscallName::Getpid
        );
        assert_eq!(
            translator.translate(56, [0; 6]).unwrap().name,
            SyscallName::Clone
        );
        assert_eq!(
            translator.translate(59, [0; 6]).unwrap().name,
            SyscallName::Execve
        );
        assert_eq!(
            translator.translate(62, [0; 6]).unwrap().name,
            SyscallName::Kill
        );
    }

    #[test]
    fn linux_translator_translates_file_syscalls() {
        let translator = LinuxSyscallTranslator::new();
        assert_eq!(
            translator.translate(72, [0; 6]).unwrap().name,
            SyscallName::Fcntl
        );
        assert_eq!(
            translator.translate(74, [0; 6]).unwrap().name,
            SyscallName::Fsync
        );
        assert_eq!(
            translator.translate(79, [0; 6]).unwrap().name,
            SyscallName::Getcwd
        );
        assert_eq!(
            translator.translate(82, [0; 6]).unwrap().name,
            SyscallName::Rename
        );
        assert_eq!(
            translator.translate(83, [0; 6]).unwrap().name,
            SyscallName::Mkdir
        );
        assert_eq!(
            translator.translate(87, [0; 6]).unwrap().name,
            SyscallName::Unlink
        );
        assert_eq!(
            translator.translate(90, [0; 6]).unwrap().name,
            SyscallName::Chmod
        );
    }

    #[test]
    fn linux_translator_translates_identity_syscalls() {
        let translator = LinuxSyscallTranslator::new();
        assert_eq!(
            translator.translate(102, [0; 6]).unwrap().name,
            SyscallName::Getuid
        );
        assert_eq!(
            translator.translate(104, [0; 6]).unwrap().name,
            SyscallName::Getgid
        );
        assert_eq!(
            translator.translate(107, [0; 6]).unwrap().name,
            SyscallName::Geteuid
        );
        assert_eq!(
            translator.translate(108, [0; 6]).unwrap().name,
            SyscallName::Getegid
        );
        assert_eq!(
            translator.translate(110, [0; 6]).unwrap().name,
            SyscallName::Getppid
        );
        assert_eq!(
            translator.translate(186, [0; 6]).unwrap().name,
            SyscallName::Gettid
        );
    }

    #[test]
    fn linux_translator_translates_newer_at_syscalls() {
        let translator = LinuxSyscallTranslator::new();
        assert_eq!(
            translator.translate(257, [0; 6]).unwrap().name,
            SyscallName::Openat
        );
        assert_eq!(
            translator.translate(258, [0; 6]).unwrap().name,
            SyscallName::Mkdirat
        );
        assert_eq!(
            translator.translate(263, [0; 6]).unwrap().name,
            SyscallName::Unlinkat
        );
        assert_eq!(
            translator.translate(316, [0; 6]).unwrap().name,
            SyscallName::Renameat2
        );
    }

    #[test]
    fn linux_translator_translates_memory_syscalls() {
        let translator = LinuxSyscallTranslator::new();
        assert_eq!(
            translator.translate(9, [0; 6]).unwrap().name,
            SyscallName::Mmap
        );
        assert_eq!(
            translator.translate(10, [0; 6]).unwrap().name,
            SyscallName::Mprotect
        );
        assert_eq!(
            translator.translate(11, [0; 6]).unwrap().name,
            SyscallName::Munmap
        );
        assert_eq!(
            translator.translate(12, [0; 6]).unwrap().name,
            SyscallName::Brk
        );
    }

    #[test]
    fn linux_translator_translates_io_uring_syscalls() {
        let translator = LinuxSyscallTranslator::new();
        assert_eq!(
            translator.translate(425, [0; 6]).unwrap().name,
            SyscallName::IoUringSetup
        );
        assert_eq!(
            translator.translate(426, [0; 6]).unwrap().name,
            SyscallName::IoUringEnter
        );
        assert_eq!(
            translator.translate(427, [0; 6]).unwrap().name,
            SyscallName::IoUringRegister
        );
    }
}
