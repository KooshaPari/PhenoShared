//! pine-syscall — Syscall translation layer.

pub mod linux;
pub mod plugin;
pub mod windows;

use std::collections::HashMap;
use std::fmt;

use pine_core::traits::SyscallHandler;

// --- Existing code (kept for compatibility) ---

pub struct LinuxSyscallHandler;

impl SyscallHandler for LinuxSyscallHandler {
    fn handle(&self, _number: u32, _args: &[u64]) -> Result<u64, String> {
        Ok(0)
    }
}

// --- New types and trait ---

/// Error returned when a syscall translation fails.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SyscallError {
    /// `UnknownSyscall`
    UnknownSyscall(u64),
    /// `InvalidArgument`
    InvalidArgument,
}

impl fmt::Display for SyscallError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            SyscallError::UnknownSyscall(num) => write!(f, "Unknown syscall number: {}", num),
            SyscallError::InvalidArgument => write!(f, "Invalid argument"),
        }
    }
}

impl std::error::Error for SyscallError {}

/// Named identifier for a Linux syscall.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum SyscallName {
    /// `Read`
    Read,
    /// `Write`
    Write,
    /// `Open`
    Open,
    /// `Close`
    Close,
    /// `Stat`
    Stat,
    /// `Fstat`
    Fstat,
    /// `Lstat`
    Lstat,
    /// `Poll`
    Poll,
    /// `Lseek`
    Lseek,
    /// `Mmap`
    Mmap,
    /// `Mprotect`
    Mprotect,
    /// `Munmap`
    Munmap,
    /// `Brk`
    Brk,
    /// `RtSigaction`
    RtSigaction,
    /// `RtSigprocmask`
    RtSigprocmask,
    /// `RtSigreturn`
    RtSigreturn,
    /// `Ioctl`
    Ioctl,
    /// `Pread64`
    Pread64,
    /// `Pwrite64`
    Pwrite64,
    /// `Readv`
    Readv,
    /// `Writev`
    Writev,
    /// `Access`
    Access,
    /// `Pipe`
    Pipe,
    /// `Select`
    Select,
    /// `SchedYield`
    SchedYield,
    /// `Mremap`
    Mremap,
    /// `Msync`
    Msync,
    /// `Mincore`
    Mincore,
    /// `Madvise`
    Madvise,
    /// `Shmget`
    Shmget,
    /// `Shmat`
    Shmat,
    /// `Shmctl`
    Shmctl,
    /// `Dup`
    Dup,
    /// `Dup2`
    Dup2,
    /// `Pause`
    Pause,
    /// `Nanosleep`
    Nanosleep,
    /// `Getitimer`
    Getitimer,
    /// `Alarm`
    Alarm,
    /// `Setitimer`
    Setitimer,
    /// `Getpid`
    Getpid,
    /// `Sendfile`
    Sendfile,
    /// `Socket`
    Socket,
    /// `Connect`
    Connect,
    /// `Accept`
    Accept,
    /// `Sendto`
    Sendto,
    /// `Recvfrom`
    Recvfrom,
    /// `Sendmsg`
    Sendmsg,
    /// `Recvmsg`
    Recvmsg,
    /// `Shutdown`
    Shutdown,
    /// `Bind`
    Bind,
    /// `Listen`
    Listen,
    /// `Getsockname`
    Getsockname,
    /// `Getpeername`
    Getpeername,
    /// `Socketpair`
    Socketpair,
    /// `Setsockopt`
    Setsockopt,
    /// `Getsockopt`
    Getsockopt,
    /// `Clone`
    Clone,
    /// `Fork`
    Fork,
    /// `Vfork`
    Vfork,
    /// `Execve`
    Execve,
    /// `Exit`
    Exit,
    /// `Wait4`
    Wait4,
    /// `Kill`
    Kill,
    /// `Uname`
    Uname,
    /// `Semget`
    Semget,
    /// `Semop`
    Semop,
    /// `Semctl`
    Semctl,
    /// `Shmdt`
    Shmdt,
    /// `Msgget`
    Msgget,
    /// `Msgsnd`
    Msgsnd,
    /// `Msgrcv`
    Msgrcv,
    /// `Msgctl`
    Msgctl,
    /// `Fcntl`
    Fcntl,
    /// `Flock`
    Flock,
    /// `Fsync`
    Fsync,
    /// `Fdatasync`
    Fdatasync,
    /// `Truncate`
    Truncate,
    /// `Ftruncate`
    Ftruncate,
    /// `Getdents`
    Getdents,
    /// `Getcwd`
    Getcwd,
    /// `Chdir`
    Chdir,
    /// `Fchdir`
    Fchdir,
    /// `Rename`
    Rename,
    /// `Mkdir`
    Mkdir,
    /// `Rmdir`
    Rmdir,
    /// `Creat`
    Creat,
    /// `Link`
    Link,
    /// `Unlink`
    Unlink,
    /// `Symlink`
    Symlink,
    /// `Readlink`
    Readlink,
    /// `Chmod`
    Chmod,
    /// `Fchmod`
    Fchmod,
    /// `Chown`
    Chown,
    /// `Fchown`
    Fchown,
    /// `Lchown`
    Lchown,
    /// `Umask`
    Umask,
    /// `Gettimeofday`
    Gettimeofday,
    /// `Getrlimit`
    Getrlimit,
    /// `Getrusage`
    Getrusage,
    /// `Sysinfo`
    Sysinfo,
    /// `Times`
    Times,
    /// `Ptrace`
    Ptrace,
    /// `Getuid`
    Getuid,
    /// `Syslog`
    Syslog,
    /// `Getgid`
    Getgid,
    /// `Setuid`
    Setuid,
    /// `Setgid`
    Setgid,
    /// `Geteuid`
    Geteuid,
    /// `Getegid`
    Getegid,
    /// `Setpgid`
    Setpgid,
    /// `Getppid`
    Getppid,
    /// `Getpgrp`
    Getpgrp,
    /// `Setsid`
    Setsid,
    /// `Setreuid`
    Setreuid,
    /// `Setregid`
    Setregid,
    /// `Getgroups`
    Getgroups,
    /// `Setgroups`
    Setgroups,
    /// `Setresuid`
    Setresuid,
    /// `Getresuid`
    Getresuid,
    /// `Setresgid`
    Setresgid,
    /// `Getresgid`
    Getresgid,
    /// `Getpgid`
    Getpgid,
    /// `Setfsuid`
    Setfsuid,
    /// `Setfsgid`
    Setfsgid,
    /// `Getsid`
    Getsid,
    /// `Capget`
    Capget,
    /// `Capset`
    Capset,
    /// `RtSigpending`
    RtSigpending,
    /// `RtSigtimedwait`
    RtSigtimedwait,
    /// `RtSigqueueinfo`
    RtSigqueueinfo,
    /// `RtSigsuspend`
    RtSigsuspend,
    /// `Sigaltstack`
    Sigaltstack,
    /// `Utime`
    Utime,
    /// `Mknod`
    Mknod,
    /// `Statfs`
    Statfs,
    /// `Fstatfs`
    Fstatfs,
    /// `Getpriority`
    Getpriority,
    /// `Setpriority`
    Setpriority,
    /// `Mlock`
    Mlock,
    /// `Munlock`
    Munlock,
    /// `Mlockall`
    Mlockall,
    /// `Munlockall`
    Munlockall,
    /// `Vhangup`
    Vhangup,
    /// `ModifyLdt`
    ModifyLdt,
    /// `PivotRoot`
    PivotRoot,
    /// `Prctl`
    Prctl,
    /// `ArchPrctl`
    ArchPrctl,
    /// `Adjtimex`
    Adjtimex,
    /// `Setrlimit`
    Setrlimit,
    /// `Chroot`
    Chroot,
    /// `Sync`
    Sync,
    /// `Acct`
    Acct,
    /// `Settimeofday`
    Settimeofday,
    /// `Mount`
    Mount,
    /// `Umount2`
    Umount2,
    /// `Swapon`
    Swapon,
    /// `Swapoff`
    Swapoff,
    /// `Reboot`
    Reboot,
    /// `Sethostname`
    Sethostname,
    /// `Setdomainname`
    Setdomainname,
    /// `Iopl`
    Iopl,
    /// `Ioperm`
    Ioperm,
    /// `Gettid`
    Gettid,
    /// `Readahead`
    Readahead,
    /// `Setxattr`
    Setxattr,
    /// `Lsetxattr`
    Lsetxattr,
    /// `Fsetxattr`
    Fsetxattr,
    /// `Getxattr`
    Getxattr,
    /// `Lgetxattr`
    Lgetxattr,
    /// `Fgetxattr`
    Fgetxattr,
    /// `Listxattr`
    Listxattr,
    /// `Llistxattr`
    Llistxattr,
    /// `Flistxattr`
    Flistxattr,
    /// `Removexattr`
    Removexattr,
    /// `Lremovexattr`
    Lremovexattr,
    /// `Fremovexattr`
    Fremovexattr,
    /// `Tkill`
    Tkill,
    /// `Time`
    Time,
    /// `Futex`
    Futex,
    /// `SchedSetaffinity`
    SchedSetaffinity,
    /// `SchedGetaffinity`
    SchedGetaffinity,
    /// `SetThreadArea`
    SetThreadArea,
    /// `IoSetup`
    IoSetup,
    /// `IoDestroy`
    IoDestroy,
    /// `IoGetevents`
    IoGetevents,
    /// `IoSubmit`
    IoSubmit,
    /// `IoCancel`
    IoCancel,
    /// `GetThreadArea`
    GetThreadArea,
    /// `LookupDcookie`
    LookupDcookie,
    /// `EpollCreate`
    EpollCreate,
    /// `RemapFilePages`
    RemapFilePages,
    /// `Getdents64`
    Getdents64,
    /// `SetTidAddress`
    SetTidAddress,
    /// `RestartSyscall`
    RestartSyscall,
    /// `Semtimedop`
    Semtimedop,
    /// `Fadvise64`
    Fadvise64,
    /// `TimerCreate`
    TimerCreate,
    /// `TimerSettime`
    TimerSettime,
    /// `TimerGettime`
    TimerGettime,
    /// `TimerGetoverrun`
    TimerGetoverrun,
    /// `TimerDelete`
    TimerDelete,
    /// `ClockSettime`
    ClockSettime,
    /// `ClockGettime`
    ClockGettime,
    /// `ClockGetres`
    ClockGetres,
    /// `ClockNanosleep`
    ClockNanosleep,
    /// `ExitGroup`
    ExitGroup,
    /// `EpollWait`
    EpollWait,
    /// `EpollCtl`
    EpollCtl,
    /// `Tgkill`
    Tgkill,
    /// `Utimes`
    Utimes,
    /// `Mbind`
    Mbind,
    /// `SetMempolicy`
    SetMempolicy,
    /// `GetMempolicy`
    GetMempolicy,
    /// `MqOpen`
    MqOpen,
    /// `MqTimedreceive`
    MqTimedreceive,
    /// `MqTimedsend`
    MqTimedsend,
    /// `MqNotify`
    MqNotify,
    /// `MqGetsetattr`
    MqGetsetattr,
    /// `KexecLoad`
    KexecLoad,
    /// `Waitid`
    Waitid,
    /// `AddKey`
    AddKey,
    /// `RequestKey`
    RequestKey,
    /// `Keyctl`
    Keyctl,
    /// `IoprioSet`
    IoprioSet,
    /// `IoprioGet`
    IoprioGet,
    /// `InotifyInit`
    InotifyInit,
    /// `InotifyAddWatch`
    InotifyAddWatch,
    /// `InotifyRmWatch`
    InotifyRmWatch,
    /// `MigratePages`
    MigratePages,
    /// `Openat`
    Openat,
    /// `Mkdirat`
    Mkdirat,
    /// `Mknodat`
    Mknodat,
    /// `Fchownat`
    Fchownat,
    /// `Futimesat`
    Futimesat,
    /// `Newfstatat`
    Newfstatat,
    /// `Unlinkat`
    Unlinkat,
    /// `Renameat`
    Renameat,
    /// `Linkat`
    Linkat,
    /// `Symlinkat`
    Symlinkat,
    /// `Readlinkat`
    Readlinkat,
    /// `Fchmodat`
    Fchmodat,
    /// `Faccessat`
    Faccessat,
    /// `Pselect6`
    Pselect6,
    /// `Ppoll`
    Ppoll,
    /// `Unshare`
    Unshare,
    /// `SetRobustList`
    SetRobustList,
    /// `GetRobustList`
    GetRobustList,
    /// `Splice`
    Splice,
    /// `Tee`
    Tee,
    /// `SyncFileRange`
    SyncFileRange,
    /// `Vmsplice`
    Vmsplice,
    /// `MovePages`
    MovePages,
    /// `Utimensat`
    Utimensat,
    /// `EpollPwait`
    EpollPwait,
    /// `Signalfd`
    Signalfd,
    /// `TimerfdCreate`
    TimerfdCreate,
    /// `Eventfd`
    Eventfd,
    /// `Fallocate`
    Fallocate,
    /// `TimerfdSettime`
    TimerfdSettime,
    /// `TimerfdGettime`
    TimerfdGettime,
    /// `Accept4`
    Accept4,
    /// `Signalfd4`
    Signalfd4,
    /// `Eventfd2`
    Eventfd2,
    /// `EpollCreate1`
    EpollCreate1,
    /// `Dup3`
    Dup3,
    /// `Pipe2`
    Pipe2,
    /// `InotifyInit1`
    InotifyInit1,
    /// `Preadv`
    Preadv,
    /// `Pwritev`
    Pwritev,
    /// `RtTgsigqueueinfo`
    RtTgsigqueueinfo,
    /// `PerfEventOpen`
    PerfEventOpen,
    /// `Recvmmsg`
    Recvmmsg,
    /// `FanotifyInit`
    FanotifyInit,
    /// `FanotifyMark`
    FanotifyMark,
    /// `Prlimit64`
    Prlimit64,
    /// `NameToHandleAt`
    NameToHandleAt,
    /// `OpenByHandleAt`
    OpenByHandleAt,
    /// `ClockAdjtime`
    ClockAdjtime,
    /// `Syncfs`
    Syncfs,
    /// `Sendmmsg`
    Sendmmsg,
    /// `Setns`
    Setns,
    /// `Getcpu`
    Getcpu,
    /// `ProcessVmReadv`
    ProcessVmReadv,
    /// `ProcessVmWritev`
    ProcessVmWritev,
    /// `Kcmp`
    Kcmp,
    /// `FinitModule`
    FinitModule,
    /// `SchedSetattr`
    SchedSetattr,
    /// `SchedGetattr`
    SchedGetattr,
    /// `Renameat2`
    Renameat2,
    /// `Seccomp`
    Seccomp,
    /// `Getrandom`
    Getrandom,
    /// `MemfdCreate`
    MemfdCreate,
    /// `KexecFileLoad`
    KexecFileLoad,
    /// `Bpf`
    Bpf,
    /// `Execveat`
    Execveat,
    /// `Userfaultfd`
    Userfaultfd,
    /// `Membarrier`
    Membarrier,
    /// `Mlock2`
    Mlock2,
    /// `CopyFileRange`
    CopyFileRange,
    /// `Preadv2`
    Preadv2,
    /// `Pwritev2`
    Pwritev2,
    /// `PkeyMprotect`
    PkeyMprotect,
    /// `PkeyAlloc`
    PkeyAlloc,
    /// `PkeyFree`
    PkeyFree,
    /// `Statx`
    Statx,
    /// `IoPgetevents`
    IoPgetevents,
    /// `Rseq`
    Rseq,
    /// `PidfdSendSignal`
    PidfdSendSignal,
    /// `IoUringSetup`
    IoUringSetup,
    /// `IoUringEnter`
    IoUringEnter,
    /// `IoUringRegister`
    IoUringRegister,
}

/// Result of a successful syscall translation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SyscallResult {
    pub name: SyscallName,
    pub number: u64,
    pub args: [u64; 6],
}

/// Trait for translating raw syscall numbers into structured results.
pub trait SyscallTranslator {
    fn translate(&self, syscall_num: u64, args: [u64; 6]) -> Result<SyscallResult, SyscallError>;
}

/// x86_64 Linux syscall translator backed by a lookup table.
#[derive(Debug, Clone)]
pub struct X86_64SyscallTranslator {
    table: HashMap<u64, SyscallName>,
}

impl X86_64SyscallTranslator {
    /// Create a new translator with the standard x86_64 syscall table.
    pub fn new() -> Self {
        let mut table = HashMap::new();
        table.insert(0, SyscallName::Read);
        table.insert(1, SyscallName::Write);
        table.insert(2, SyscallName::Open);
        table.insert(3, SyscallName::Close);
        table.insert(4, SyscallName::Stat);
        table.insert(5, SyscallName::Fstat);
        table.insert(6, SyscallName::Lstat);
        table.insert(7, SyscallName::Poll);
        table.insert(8, SyscallName::Lseek);
        table.insert(9, SyscallName::Mmap);
        table.insert(10, SyscallName::Mprotect);
        table.insert(11, SyscallName::Munmap);
        table.insert(12, SyscallName::Brk);
        table.insert(13, SyscallName::RtSigaction);
        table.insert(14, SyscallName::RtSigprocmask);
        table.insert(15, SyscallName::RtSigreturn);
        table.insert(16, SyscallName::Ioctl);
        table.insert(17, SyscallName::Pread64);
        table.insert(18, SyscallName::Pwrite64);
        table.insert(19, SyscallName::Readv);
        table.insert(20, SyscallName::Writev);
        table.insert(21, SyscallName::Access);
        table.insert(22, SyscallName::Pipe);
        table.insert(23, SyscallName::Select);
        table.insert(24, SyscallName::SchedYield);
        table.insert(25, SyscallName::Mremap);
        table.insert(26, SyscallName::Msync);
        table.insert(27, SyscallName::Mincore);
        table.insert(28, SyscallName::Madvise);
        table.insert(29, SyscallName::Shmget);
        table.insert(30, SyscallName::Shmat);
        table.insert(31, SyscallName::Shmctl);
        table.insert(32, SyscallName::Dup);
        table.insert(33, SyscallName::Dup2);
        table.insert(34, SyscallName::Pause);
        table.insert(35, SyscallName::Nanosleep);
        table.insert(36, SyscallName::Getitimer);
        table.insert(37, SyscallName::Alarm);
        table.insert(38, SyscallName::Setitimer);
        table.insert(39, SyscallName::Getpid);
        table.insert(40, SyscallName::Sendfile);
        table.insert(41, SyscallName::Socket);
        table.insert(42, SyscallName::Connect);
        table.insert(43, SyscallName::Accept);
        table.insert(44, SyscallName::Sendto);
        table.insert(45, SyscallName::Recvfrom);
        table.insert(46, SyscallName::Sendmsg);
        table.insert(47, SyscallName::Recvmsg);
        table.insert(48, SyscallName::Shutdown);
        table.insert(49, SyscallName::Bind);
        table.insert(50, SyscallName::Listen);
        table.insert(51, SyscallName::Getsockname);
        table.insert(52, SyscallName::Getpeername);
        table.insert(53, SyscallName::Socketpair);
        table.insert(54, SyscallName::Setsockopt);
        table.insert(55, SyscallName::Getsockopt);
        table.insert(56, SyscallName::Clone);
        table.insert(57, SyscallName::Fork);
        table.insert(58, SyscallName::Vfork);
        table.insert(59, SyscallName::Execve);
        table.insert(60, SyscallName::Exit);
        table.insert(61, SyscallName::Wait4);
        table.insert(62, SyscallName::Kill);
        table.insert(63, SyscallName::Uname);
        table.insert(64, SyscallName::Semget);
        table.insert(65, SyscallName::Semop);
        table.insert(66, SyscallName::Semctl);
        table.insert(67, SyscallName::Shmdt);
        table.insert(68, SyscallName::Msgget);
        table.insert(69, SyscallName::Msgsnd);
        table.insert(70, SyscallName::Msgrcv);
        table.insert(71, SyscallName::Msgctl);
        table.insert(72, SyscallName::Fcntl);
        table.insert(73, SyscallName::Flock);
        table.insert(74, SyscallName::Fsync);
        table.insert(75, SyscallName::Fdatasync);
        table.insert(76, SyscallName::Truncate);
        table.insert(77, SyscallName::Ftruncate);
        table.insert(78, SyscallName::Getdents);
        table.insert(79, SyscallName::Getcwd);
        table.insert(80, SyscallName::Chdir);
        table.insert(81, SyscallName::Fchdir);
        table.insert(82, SyscallName::Rename);
        table.insert(83, SyscallName::Mkdir);
        table.insert(84, SyscallName::Rmdir);
        table.insert(85, SyscallName::Creat);
        table.insert(86, SyscallName::Link);
        table.insert(87, SyscallName::Unlink);
        table.insert(88, SyscallName::Symlink);
        table.insert(89, SyscallName::Readlink);
        table.insert(90, SyscallName::Chmod);
        table.insert(91, SyscallName::Fchmod);
        table.insert(92, SyscallName::Chown);
        table.insert(93, SyscallName::Fchown);
        table.insert(94, SyscallName::Lchown);
        table.insert(95, SyscallName::Umask);
        table.insert(96, SyscallName::Gettimeofday);
        table.insert(97, SyscallName::Getrlimit);
        table.insert(98, SyscallName::Getrusage);
        table.insert(99, SyscallName::Sysinfo);
        table.insert(100, SyscallName::Times);
        table.insert(101, SyscallName::Ptrace);
        table.insert(102, SyscallName::Getuid);
        table.insert(103, SyscallName::Syslog);
        table.insert(104, SyscallName::Getgid);
        table.insert(105, SyscallName::Setuid);
        table.insert(106, SyscallName::Setgid);
        table.insert(107, SyscallName::Geteuid);
        table.insert(108, SyscallName::Getegid);
        table.insert(109, SyscallName::Setpgid);
        table.insert(110, SyscallName::Getppid);
        table.insert(111, SyscallName::Getpgrp);
        table.insert(112, SyscallName::Setsid);
        table.insert(113, SyscallName::Setreuid);
        table.insert(114, SyscallName::Setregid);
        table.insert(115, SyscallName::Getgroups);
        table.insert(116, SyscallName::Setgroups);
        table.insert(117, SyscallName::Setresuid);
        table.insert(118, SyscallName::Getresuid);
        table.insert(119, SyscallName::Setresgid);
        table.insert(120, SyscallName::Getresgid);
        table.insert(121, SyscallName::Getpgid);
        table.insert(122, SyscallName::Setfsuid);
        table.insert(123, SyscallName::Setfsgid);
        table.insert(124, SyscallName::Getsid);
        table.insert(125, SyscallName::Capget);
        table.insert(126, SyscallName::Capset);
        table.insert(127, SyscallName::RtSigpending);
        table.insert(128, SyscallName::RtSigtimedwait);
        table.insert(129, SyscallName::RtSigqueueinfo);
        table.insert(130, SyscallName::RtSigsuspend);
        table.insert(131, SyscallName::Sigaltstack);
        table.insert(132, SyscallName::Utime);
        table.insert(133, SyscallName::Mknod);
        table.insert(137, SyscallName::Statfs);
        table.insert(138, SyscallName::Fstatfs);
        table.insert(140, SyscallName::Getpriority);
        table.insert(141, SyscallName::Setpriority);
        table.insert(149, SyscallName::Mlock);
        table.insert(150, SyscallName::Munlock);
        table.insert(151, SyscallName::Mlockall);
        table.insert(152, SyscallName::Munlockall);
        table.insert(153, SyscallName::Vhangup);
        table.insert(154, SyscallName::ModifyLdt);
        table.insert(155, SyscallName::PivotRoot);
        table.insert(157, SyscallName::Prctl);
        table.insert(158, SyscallName::ArchPrctl);
        table.insert(159, SyscallName::Adjtimex);
        table.insert(160, SyscallName::Setrlimit);
        table.insert(161, SyscallName::Chroot);
        table.insert(162, SyscallName::Sync);
        table.insert(163, SyscallName::Acct);
        table.insert(164, SyscallName::Settimeofday);
        table.insert(165, SyscallName::Mount);
        table.insert(166, SyscallName::Umount2);
        table.insert(167, SyscallName::Swapon);
        table.insert(168, SyscallName::Swapoff);
        table.insert(169, SyscallName::Reboot);
        table.insert(170, SyscallName::Sethostname);
        table.insert(171, SyscallName::Setdomainname);
        table.insert(172, SyscallName::Iopl);
        table.insert(173, SyscallName::Ioperm);
        table.insert(186, SyscallName::Gettid);
        table.insert(187, SyscallName::Readahead);
        table.insert(188, SyscallName::Setxattr);
        table.insert(189, SyscallName::Lsetxattr);
        table.insert(190, SyscallName::Fsetxattr);
        table.insert(191, SyscallName::Getxattr);
        table.insert(192, SyscallName::Lgetxattr);
        table.insert(193, SyscallName::Fgetxattr);
        table.insert(194, SyscallName::Listxattr);
        table.insert(195, SyscallName::Llistxattr);
        table.insert(196, SyscallName::Flistxattr);
        table.insert(197, SyscallName::Removexattr);
        table.insert(198, SyscallName::Lremovexattr);
        table.insert(199, SyscallName::Fremovexattr);
        table.insert(200, SyscallName::Tkill);
        table.insert(201, SyscallName::Time);
        table.insert(202, SyscallName::Futex);
        table.insert(203, SyscallName::SchedSetaffinity);
        table.insert(204, SyscallName::SchedGetaffinity);
        table.insert(205, SyscallName::SetThreadArea);
        table.insert(206, SyscallName::IoSetup);
        table.insert(207, SyscallName::IoDestroy);
        table.insert(208, SyscallName::IoGetevents);
        table.insert(209, SyscallName::IoSubmit);
        table.insert(210, SyscallName::IoCancel);
        table.insert(211, SyscallName::GetThreadArea);
        table.insert(212, SyscallName::LookupDcookie);
        table.insert(213, SyscallName::EpollCreate);
        table.insert(216, SyscallName::RemapFilePages);
        table.insert(217, SyscallName::Getdents64);
        table.insert(218, SyscallName::SetTidAddress);
        table.insert(219, SyscallName::RestartSyscall);
        table.insert(220, SyscallName::Semtimedop);
        table.insert(221, SyscallName::Fadvise64);
        table.insert(222, SyscallName::TimerCreate);
        table.insert(223, SyscallName::TimerSettime);
        table.insert(224, SyscallName::TimerGettime);
        table.insert(225, SyscallName::TimerGetoverrun);
        table.insert(226, SyscallName::TimerDelete);
        table.insert(227, SyscallName::ClockSettime);
        table.insert(228, SyscallName::ClockGettime);
        table.insert(229, SyscallName::ClockGetres);
        table.insert(230, SyscallName::ClockNanosleep);
        table.insert(231, SyscallName::ExitGroup);
        table.insert(232, SyscallName::EpollWait);
        table.insert(233, SyscallName::EpollCtl);
        table.insert(234, SyscallName::Tgkill);
        table.insert(235, SyscallName::Utimes);
        table.insert(237, SyscallName::Mbind);
        table.insert(238, SyscallName::SetMempolicy);
        table.insert(239, SyscallName::GetMempolicy);
        table.insert(240, SyscallName::MqOpen);
        table.insert(241, SyscallName::MqTimedreceive);
        table.insert(242, SyscallName::MqTimedsend);
        table.insert(243, SyscallName::MqNotify);
        table.insert(244, SyscallName::MqGetsetattr);
        table.insert(245, SyscallName::KexecLoad);
        table.insert(246, SyscallName::Waitid);
        table.insert(247, SyscallName::AddKey);
        table.insert(248, SyscallName::RequestKey);
        table.insert(249, SyscallName::Keyctl);
        table.insert(250, SyscallName::IoprioSet);
        table.insert(251, SyscallName::IoprioGet);
        table.insert(252, SyscallName::InotifyInit);
        table.insert(253, SyscallName::InotifyAddWatch);
        table.insert(254, SyscallName::InotifyRmWatch);
        table.insert(256, SyscallName::MigratePages);
        table.insert(257, SyscallName::Openat);
        table.insert(258, SyscallName::Mkdirat);
        table.insert(259, SyscallName::Mknodat);
        table.insert(260, SyscallName::Fchownat);
        table.insert(261, SyscallName::Futimesat);
        table.insert(262, SyscallName::Newfstatat);
        table.insert(263, SyscallName::Unlinkat);
        table.insert(264, SyscallName::Renameat);
        table.insert(265, SyscallName::Linkat);
        table.insert(266, SyscallName::Symlinkat);
        table.insert(267, SyscallName::Readlinkat);
        table.insert(268, SyscallName::Fchmodat);
        table.insert(269, SyscallName::Faccessat);
        table.insert(270, SyscallName::Pselect6);
        table.insert(271, SyscallName::Ppoll);
        table.insert(272, SyscallName::Unshare);
        table.insert(273, SyscallName::SetRobustList);
        table.insert(274, SyscallName::GetRobustList);
        table.insert(275, SyscallName::Splice);
        table.insert(276, SyscallName::Tee);
        table.insert(277, SyscallName::SyncFileRange);
        table.insert(278, SyscallName::Vmsplice);
        table.insert(279, SyscallName::MovePages);
        table.insert(280, SyscallName::Utimensat);
        table.insert(281, SyscallName::EpollPwait);
        table.insert(282, SyscallName::Signalfd);
        table.insert(283, SyscallName::TimerfdCreate);
        table.insert(284, SyscallName::Eventfd);
        table.insert(285, SyscallName::Fallocate);
        table.insert(286, SyscallName::TimerfdSettime);
        table.insert(287, SyscallName::TimerfdGettime);
        table.insert(288, SyscallName::Accept4);
        table.insert(289, SyscallName::Signalfd4);
        table.insert(290, SyscallName::Eventfd2);
        table.insert(291, SyscallName::EpollCreate1);
        table.insert(292, SyscallName::Dup3);
        table.insert(293, SyscallName::Pipe2);
        table.insert(294, SyscallName::InotifyInit1);
        table.insert(295, SyscallName::Preadv);
        table.insert(296, SyscallName::Pwritev);
        table.insert(297, SyscallName::RtTgsigqueueinfo);
        table.insert(298, SyscallName::PerfEventOpen);
        table.insert(299, SyscallName::Recvmmsg);
        table.insert(300, SyscallName::FanotifyInit);
        table.insert(301, SyscallName::FanotifyMark);
        table.insert(302, SyscallName::Prlimit64);
        table.insert(303, SyscallName::NameToHandleAt);
        table.insert(304, SyscallName::OpenByHandleAt);
        table.insert(305, SyscallName::ClockAdjtime);
        table.insert(306, SyscallName::Syncfs);
        table.insert(307, SyscallName::Sendmmsg);
        table.insert(308, SyscallName::Setns);
        table.insert(309, SyscallName::Getcpu);
        table.insert(310, SyscallName::ProcessVmReadv);
        table.insert(311, SyscallName::ProcessVmWritev);
        table.insert(312, SyscallName::Kcmp);
        table.insert(313, SyscallName::FinitModule);
        table.insert(314, SyscallName::SchedSetattr);
        table.insert(315, SyscallName::SchedGetattr);
        table.insert(316, SyscallName::Renameat2);
        table.insert(317, SyscallName::Seccomp);
        table.insert(318, SyscallName::Getrandom);
        table.insert(319, SyscallName::MemfdCreate);
        table.insert(320, SyscallName::KexecFileLoad);
        table.insert(321, SyscallName::Bpf);
        table.insert(322, SyscallName::Execveat);
        table.insert(323, SyscallName::Userfaultfd);
        table.insert(324, SyscallName::Membarrier);
        table.insert(325, SyscallName::Mlock2);
        table.insert(326, SyscallName::CopyFileRange);
        table.insert(327, SyscallName::Preadv2);
        table.insert(328, SyscallName::Pwritev2);
        table.insert(329, SyscallName::PkeyMprotect);
        table.insert(330, SyscallName::PkeyAlloc);
        table.insert(331, SyscallName::PkeyFree);
        table.insert(332, SyscallName::Statx);
        table.insert(333, SyscallName::IoPgetevents);
        table.insert(334, SyscallName::Rseq);
        table.insert(424, SyscallName::PidfdSendSignal);
        table.insert(425, SyscallName::IoUringSetup);
        table.insert(426, SyscallName::IoUringEnter);
        table.insert(427, SyscallName::IoUringRegister);
        Self { table }
    }

    /// Look up the syscall name for a given number.
    pub fn lookup_name(&self, number: u64) -> Option<&SyscallName> {
        self.table.get(&number)
    }

    /// Look up the syscall number for a given name.
    pub fn lookup_number(&self, name: SyscallName) -> Option<u64> {
        self.table
            .iter()
            .find(|(_, n)| **n == name)
            .map(|(num, _)| *num)
    }
}

impl Default for X86_64SyscallTranslator {
    fn default() -> Self {
        Self::new()
    }
}

impl SyscallTranslator for X86_64SyscallTranslator {
    fn translate(&self, syscall_num: u64, args: [u64; 6]) -> Result<SyscallResult, SyscallError> {
        match self.table.get(&syscall_num) {
            Some(&name) => Ok(SyscallResult {
                name,
                number: syscall_num,
                args,
            }),
            None => Err(SyscallError::UnknownSyscall(syscall_num)),
        }
    }
}

#[cfg(test)]
mod tests {
    use crate::{
        LinuxSyscallHandler, SyscallError, SyscallName, SyscallResult, SyscallTranslator,
        X86_64SyscallTranslator,
    };
    use pine_core::traits::SyscallHandler;

    // --- Existing tests ---

    #[test]
    fn linux_handler_returns_zero_for_unknown_syscall() {
        let handler = LinuxSyscallHandler;
        let result = handler.handle(999, &[1, 2, 3]);
        assert_eq!(result.unwrap(), 0);
    }

    #[test]
    fn linux_handler_implements_syscall_handler() {
        let handler = LinuxSyscallHandler;
        let result = handler.handle(0, &[]);
        assert!(result.is_ok());
    }

    // --- New tests ---

    #[test]
    fn x86_64_translator_translates_read() {
        let translator = X86_64SyscallTranslator::new();
        let result = translator.translate(0, [1, 2, 3, 4, 5, 6]).unwrap();
        assert_eq!(result.name, SyscallName::Read);
        assert_eq!(result.number, 0);
        assert_eq!(result.args, [1, 2, 3, 4, 5, 6]);
    }

    #[test]
    fn x86_64_translator_translates_write() {
        let translator = X86_64SyscallTranslator::new();
        let result = translator.translate(1, [0; 6]).unwrap();
        assert_eq!(result.name, SyscallName::Write);
        assert_eq!(result.number, 1);
    }

    #[test]
    fn x86_64_translator_translates_open() {
        let translator = X86_64SyscallTranslator::new();
        let result = translator.translate(2, [0; 6]).unwrap();
        assert_eq!(result.name, SyscallName::Open);
    }

    #[test]
    fn x86_64_translator_translates_close() {
        let translator = X86_64SyscallTranslator::new();
        let result = translator.translate(3, [0; 6]).unwrap();
        assert_eq!(result.name, SyscallName::Close);
    }

    #[test]
    fn x86_64_translator_translates_mmap() {
        let translator = X86_64SyscallTranslator::new();
        let result = translator.translate(9, [0; 6]).unwrap();
        assert_eq!(result.name, SyscallName::Mmap);
    }

    #[test]
    fn x86_64_translator_returns_error_for_unknown() {
        let translator = X86_64SyscallTranslator::new();
        let result = translator.translate(9999, [0; 6]);
        assert!(result.is_err());
        assert_eq!(result.unwrap_err(), SyscallError::UnknownSyscall(9999));
    }

    #[test]
    fn x86_64_translator_lookup_name() {
        let translator = X86_64SyscallTranslator::new();
        assert_eq!(translator.lookup_name(0), Some(&SyscallName::Read));
        assert_eq!(translator.lookup_name(60), Some(&SyscallName::Exit));
        assert_eq!(translator.lookup_name(99999), None);
    }

    #[test]
    fn x86_64_translator_lookup_number() {
        let translator = X86_64SyscallTranslator::new();
        assert_eq!(translator.lookup_number(SyscallName::Read), Some(0));
        assert_eq!(translator.lookup_number(SyscallName::Write), Some(1));
        assert_eq!(translator.lookup_number(SyscallName::Exit), Some(60));
        assert_eq!(translator.lookup_number(SyscallName::Mmap), Some(9));
    }

    #[test]
    fn x86_64_translator_implements_trait() {
        fn takes_translator<T: SyscallTranslator>(_t: &T) {}
        let translator = X86_64SyscallTranslator::new();
        takes_translator(&translator);
    }

    #[test]
    fn x86_64_translator_default() {
        let translator = X86_64SyscallTranslator::default();
        assert_eq!(translator.lookup_name(0), Some(&SyscallName::Read));
    }

    #[test]
    fn x86_64_translator_translates_socket_and_network() {
        let translator = X86_64SyscallTranslator::new();
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
    fn x86_64_translator_translates_process_and_signal() {
        let translator = X86_64SyscallTranslator::new();
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
            translator.translate(60, [0; 6]).unwrap().name,
            SyscallName::Exit
        );
        assert_eq!(
            translator.translate(62, [0; 6]).unwrap().name,
            SyscallName::Kill
        );
    }

    #[test]
    fn x86_64_translator_translates_newer_at_syscalls() {
        let translator = X86_64SyscallTranslator::new();
        assert_eq!(
            translator.translate(257, [0; 6]).unwrap().name,
            SyscallName::Openat
        );
        assert_eq!(
            translator.translate(263, [0; 6]).unwrap().name,
            SyscallName::Unlinkat
        );
        assert_eq!(
            translator.translate(264, [0; 6]).unwrap().name,
            SyscallName::Renameat
        );
        assert_eq!(
            translator.translate(316, [0; 6]).unwrap().name,
            SyscallName::Renameat2
        );
    }

    #[test]
    fn syscall_error_display() {
        let err = SyscallError::UnknownSyscall(42);
        assert_eq!(err.to_string(), "Unknown syscall number: 42");
        let err2 = SyscallError::InvalidArgument;
        assert_eq!(err2.to_string(), "Invalid argument");
    }

    #[test]
    fn syscall_result_debug() {
        let result = SyscallResult {
            name: SyscallName::Read,
            number: 0,
            args: [1, 2, 3, 4, 5, 6],
        };
        let dbg = format!("{:?}", result);
        assert!(dbg.contains("Read"));
        assert!(dbg.contains("0"));
    }
}
