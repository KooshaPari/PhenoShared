//! Syscall table completeness tests.
//!
//! These tests verify that the x86_64 syscall translation table is comprehensive,
//! bidirectional, and free of duplicates.

use pine_syscall::{SyscallName, X86_64SyscallTranslator};
use std::collections::HashSet;

// ---------------------------------------------------------------------------
// Top 100 common Linux syscalls on x86_64
// ---------------------------------------------------------------------------
static TOP_100_SYSCALLS: &[(u64, SyscallName)] = &[
    (0, SyscallName::Read),
    (1, SyscallName::Write),
    (2, SyscallName::Open),
    (3, SyscallName::Close),
    (4, SyscallName::Stat),
    (5, SyscallName::Fstat),
    (6, SyscallName::Lstat),
    (7, SyscallName::Poll),
    (8, SyscallName::Lseek),
    (9, SyscallName::Mmap),
    (10, SyscallName::Mprotect),
    (11, SyscallName::Munmap),
    (12, SyscallName::Brk),
    (13, SyscallName::RtSigaction),
    (14, SyscallName::RtSigprocmask),
    (16, SyscallName::Ioctl),
    (17, SyscallName::Pread64),
    (18, SyscallName::Pwrite64),
    (19, SyscallName::Readv),
    (20, SyscallName::Writev),
    (21, SyscallName::Access),
    (22, SyscallName::Pipe),
    (23, SyscallName::Select),
    (24, SyscallName::SchedYield),
    (25, SyscallName::Mremap),
    (32, SyscallName::Dup),
    (33, SyscallName::Dup2),
    (35, SyscallName::Nanosleep),
    (39, SyscallName::Getpid),
    (40, SyscallName::Sendfile),
    (41, SyscallName::Socket),
    (42, SyscallName::Connect),
    (43, SyscallName::Accept),
    (44, SyscallName::Sendto),
    (45, SyscallName::Recvfrom),
    (46, SyscallName::Sendmsg),
    (47, SyscallName::Recvmsg),
    (48, SyscallName::Shutdown),
    (49, SyscallName::Bind),
    (50, SyscallName::Listen),
    (51, SyscallName::Getsockname),
    (52, SyscallName::Getpeername),
    (53, SyscallName::Socketpair),
    (54, SyscallName::Setsockopt),
    (55, SyscallName::Getsockopt),
    (56, SyscallName::Clone),
    (57, SyscallName::Fork),
    (58, SyscallName::Vfork),
    (59, SyscallName::Execve),
    (60, SyscallName::Exit),
    (61, SyscallName::Wait4),
    (62, SyscallName::Kill),
    (63, SyscallName::Uname),
    (72, SyscallName::Fcntl),
    (73, SyscallName::Flock),
    (74, SyscallName::Fsync),
    (75, SyscallName::Fdatasync),
    (76, SyscallName::Truncate),
    (77, SyscallName::Ftruncate),
    (78, SyscallName::Getdents),
    (79, SyscallName::Getcwd),
    (80, SyscallName::Chdir),
    (82, SyscallName::Rename),
    (83, SyscallName::Mkdir),
    (84, SyscallName::Rmdir),
    (85, SyscallName::Creat),
    (86, SyscallName::Link),
    (87, SyscallName::Unlink),
    (88, SyscallName::Symlink),
    (89, SyscallName::Readlink),
    (90, SyscallName::Chmod),
    (91, SyscallName::Fchmod),
    (92, SyscallName::Chown),
    (93, SyscallName::Fchown),
    (94, SyscallName::Lchown),
    (95, SyscallName::Umask),
    (96, SyscallName::Gettimeofday),
    (97, SyscallName::Getrlimit),
    (102, SyscallName::Getuid),
    (104, SyscallName::Getgid),
    (105, SyscallName::Setuid),
    (107, SyscallName::Geteuid),
    (108, SyscallName::Getegid),
    (110, SyscallName::Getppid),
    (111, SyscallName::Getpgrp),
    (112, SyscallName::Setsid),
    (186, SyscallName::Gettid),
    (201, SyscallName::Time),
    (202, SyscallName::Futex),
    (217, SyscallName::Getdents64),
    (218, SyscallName::SetTidAddress),
    (228, SyscallName::ClockGettime),
    (231, SyscallName::ExitGroup),
    (232, SyscallName::EpollWait),
    (233, SyscallName::EpollCtl),
    (257, SyscallName::Openat),
    (262, SyscallName::Newfstatat),
    (263, SyscallName::Unlinkat),
    (264, SyscallName::Renameat),
    (288, SyscallName::Accept4),
    (293, SyscallName::Pipe2),
    (318, SyscallName::Getrandom),
    (319, SyscallName::MemfdCreate),
    (321, SyscallName::Bpf),
    (322, SyscallName::Execveat),
    (332, SyscallName::Statx),
];

// ---------------------------------------------------------------------------
// Complete list of all syscalls in the x86_64 table (311 entries)
// ---------------------------------------------------------------------------
static ALL_SYSCALLS: &[(u64, SyscallName)] = &[
    (0, SyscallName::Read),
    (1, SyscallName::Write),
    (2, SyscallName::Open),
    (3, SyscallName::Close),
    (4, SyscallName::Stat),
    (5, SyscallName::Fstat),
    (6, SyscallName::Lstat),
    (7, SyscallName::Poll),
    (8, SyscallName::Lseek),
    (9, SyscallName::Mmap),
    (10, SyscallName::Mprotect),
    (11, SyscallName::Munmap),
    (12, SyscallName::Brk),
    (13, SyscallName::RtSigaction),
    (14, SyscallName::RtSigprocmask),
    (15, SyscallName::RtSigreturn),
    (16, SyscallName::Ioctl),
    (17, SyscallName::Pread64),
    (18, SyscallName::Pwrite64),
    (19, SyscallName::Readv),
    (20, SyscallName::Writev),
    (21, SyscallName::Access),
    (22, SyscallName::Pipe),
    (23, SyscallName::Select),
    (24, SyscallName::SchedYield),
    (25, SyscallName::Mremap),
    (26, SyscallName::Msync),
    (27, SyscallName::Mincore),
    (28, SyscallName::Madvise),
    (29, SyscallName::Shmget),
    (30, SyscallName::Shmat),
    (31, SyscallName::Shmctl),
    (32, SyscallName::Dup),
    (33, SyscallName::Dup2),
    (34, SyscallName::Pause),
    (35, SyscallName::Nanosleep),
    (36, SyscallName::Getitimer),
    (37, SyscallName::Alarm),
    (38, SyscallName::Setitimer),
    (39, SyscallName::Getpid),
    (40, SyscallName::Sendfile),
    (41, SyscallName::Socket),
    (42, SyscallName::Connect),
    (43, SyscallName::Accept),
    (44, SyscallName::Sendto),
    (45, SyscallName::Recvfrom),
    (46, SyscallName::Sendmsg),
    (47, SyscallName::Recvmsg),
    (48, SyscallName::Shutdown),
    (49, SyscallName::Bind),
    (50, SyscallName::Listen),
    (51, SyscallName::Getsockname),
    (52, SyscallName::Getpeername),
    (53, SyscallName::Socketpair),
    (54, SyscallName::Setsockopt),
    (55, SyscallName::Getsockopt),
    (56, SyscallName::Clone),
    (57, SyscallName::Fork),
    (58, SyscallName::Vfork),
    (59, SyscallName::Execve),
    (60, SyscallName::Exit),
    (61, SyscallName::Wait4),
    (62, SyscallName::Kill),
    (63, SyscallName::Uname),
    (64, SyscallName::Semget),
    (65, SyscallName::Semop),
    (66, SyscallName::Semctl),
    (67, SyscallName::Shmdt),
    (68, SyscallName::Msgget),
    (69, SyscallName::Msgsnd),
    (70, SyscallName::Msgrcv),
    (71, SyscallName::Msgctl),
    (72, SyscallName::Fcntl),
    (73, SyscallName::Flock),
    (74, SyscallName::Fsync),
    (75, SyscallName::Fdatasync),
    (76, SyscallName::Truncate),
    (77, SyscallName::Ftruncate),
    (78, SyscallName::Getdents),
    (79, SyscallName::Getcwd),
    (80, SyscallName::Chdir),
    (81, SyscallName::Fchdir),
    (82, SyscallName::Rename),
    (83, SyscallName::Mkdir),
    (84, SyscallName::Rmdir),
    (85, SyscallName::Creat),
    (86, SyscallName::Link),
    (87, SyscallName::Unlink),
    (88, SyscallName::Symlink),
    (89, SyscallName::Readlink),
    (90, SyscallName::Chmod),
    (91, SyscallName::Fchmod),
    (92, SyscallName::Chown),
    (93, SyscallName::Fchown),
    (94, SyscallName::Lchown),
    (95, SyscallName::Umask),
    (96, SyscallName::Gettimeofday),
    (97, SyscallName::Getrlimit),
    (98, SyscallName::Getrusage),
    (99, SyscallName::Sysinfo),
    (100, SyscallName::Times),
    (101, SyscallName::Ptrace),
    (102, SyscallName::Getuid),
    (103, SyscallName::Syslog),
    (104, SyscallName::Getgid),
    (105, SyscallName::Setuid),
    (106, SyscallName::Setgid),
    (107, SyscallName::Geteuid),
    (108, SyscallName::Getegid),
    (109, SyscallName::Setpgid),
    (110, SyscallName::Getppid),
    (111, SyscallName::Getpgrp),
    (112, SyscallName::Setsid),
    (113, SyscallName::Setreuid),
    (114, SyscallName::Setregid),
    (115, SyscallName::Getgroups),
    (116, SyscallName::Setgroups),
    (117, SyscallName::Setresuid),
    (118, SyscallName::Getresuid),
    (119, SyscallName::Setresgid),
    (120, SyscallName::Getresgid),
    (121, SyscallName::Getpgid),
    (122, SyscallName::Setfsuid),
    (123, SyscallName::Setfsgid),
    (124, SyscallName::Getsid),
    (125, SyscallName::Capget),
    (126, SyscallName::Capset),
    (127, SyscallName::RtSigpending),
    (128, SyscallName::RtSigtimedwait),
    (129, SyscallName::RtSigqueueinfo),
    (130, SyscallName::RtSigsuspend),
    (131, SyscallName::Sigaltstack),
    (132, SyscallName::Utime),
    (133, SyscallName::Mknod),
    (137, SyscallName::Statfs),
    (138, SyscallName::Fstatfs),
    (140, SyscallName::Getpriority),
    (141, SyscallName::Setpriority),
    (149, SyscallName::Mlock),
    (150, SyscallName::Munlock),
    (151, SyscallName::Mlockall),
    (152, SyscallName::Munlockall),
    (153, SyscallName::Vhangup),
    (154, SyscallName::ModifyLdt),
    (155, SyscallName::PivotRoot),
    (157, SyscallName::Prctl),
    (158, SyscallName::ArchPrctl),
    (159, SyscallName::Adjtimex),
    (160, SyscallName::Setrlimit),
    (161, SyscallName::Chroot),
    (162, SyscallName::Sync),
    (163, SyscallName::Acct),
    (164, SyscallName::Settimeofday),
    (165, SyscallName::Mount),
    (166, SyscallName::Umount2),
    (167, SyscallName::Swapon),
    (168, SyscallName::Swapoff),
    (169, SyscallName::Reboot),
    (170, SyscallName::Sethostname),
    (171, SyscallName::Setdomainname),
    (172, SyscallName::Iopl),
    (173, SyscallName::Ioperm),
    (186, SyscallName::Gettid),
    (187, SyscallName::Readahead),
    (188, SyscallName::Setxattr),
    (189, SyscallName::Lsetxattr),
    (190, SyscallName::Fsetxattr),
    (191, SyscallName::Getxattr),
    (192, SyscallName::Lgetxattr),
    (193, SyscallName::Fgetxattr),
    (194, SyscallName::Listxattr),
    (195, SyscallName::Llistxattr),
    (196, SyscallName::Flistxattr),
    (197, SyscallName::Removexattr),
    (198, SyscallName::Lremovexattr),
    (199, SyscallName::Fremovexattr),
    (200, SyscallName::Tkill),
    (201, SyscallName::Time),
    (202, SyscallName::Futex),
    (203, SyscallName::SchedSetaffinity),
    (204, SyscallName::SchedGetaffinity),
    (205, SyscallName::SetThreadArea),
    (206, SyscallName::IoSetup),
    (207, SyscallName::IoDestroy),
    (208, SyscallName::IoGetevents),
    (209, SyscallName::IoSubmit),
    (210, SyscallName::IoCancel),
    (211, SyscallName::GetThreadArea),
    (212, SyscallName::LookupDcookie),
    (213, SyscallName::EpollCreate),
    (216, SyscallName::RemapFilePages),
    (217, SyscallName::Getdents64),
    (218, SyscallName::SetTidAddress),
    (219, SyscallName::RestartSyscall),
    (220, SyscallName::Semtimedop),
    (221, SyscallName::Fadvise64),
    (222, SyscallName::TimerCreate),
    (223, SyscallName::TimerSettime),
    (224, SyscallName::TimerGettime),
    (225, SyscallName::TimerGetoverrun),
    (226, SyscallName::TimerDelete),
    (227, SyscallName::ClockSettime),
    (228, SyscallName::ClockGettime),
    (229, SyscallName::ClockGetres),
    (230, SyscallName::ClockNanosleep),
    (231, SyscallName::ExitGroup),
    (232, SyscallName::EpollWait),
    (233, SyscallName::EpollCtl),
    (234, SyscallName::Tgkill),
    (235, SyscallName::Utimes),
    (237, SyscallName::Mbind),
    (238, SyscallName::SetMempolicy),
    (239, SyscallName::GetMempolicy),
    (240, SyscallName::MqOpen),
    (241, SyscallName::MqTimedreceive),
    (242, SyscallName::MqTimedsend),
    (243, SyscallName::MqNotify),
    (244, SyscallName::MqGetsetattr),
    (245, SyscallName::KexecLoad),
    (246, SyscallName::Waitid),
    (247, SyscallName::AddKey),
    (248, SyscallName::RequestKey),
    (249, SyscallName::Keyctl),
    (250, SyscallName::IoprioSet),
    (251, SyscallName::IoprioGet),
    (252, SyscallName::InotifyInit),
    (253, SyscallName::InotifyAddWatch),
    (254, SyscallName::InotifyRmWatch),
    (256, SyscallName::MigratePages),
    (257, SyscallName::Openat),
    (258, SyscallName::Mkdirat),
    (259, SyscallName::Mknodat),
    (260, SyscallName::Fchownat),
    (261, SyscallName::Futimesat),
    (262, SyscallName::Newfstatat),
    (263, SyscallName::Unlinkat),
    (264, SyscallName::Renameat),
    (265, SyscallName::Linkat),
    (266, SyscallName::Symlinkat),
    (267, SyscallName::Readlinkat),
    (268, SyscallName::Fchmodat),
    (269, SyscallName::Faccessat),
    (270, SyscallName::Pselect6),
    (271, SyscallName::Ppoll),
    (272, SyscallName::Unshare),
    (273, SyscallName::SetRobustList),
    (274, SyscallName::GetRobustList),
    (275, SyscallName::Splice),
    (276, SyscallName::Tee),
    (277, SyscallName::SyncFileRange),
    (278, SyscallName::Vmsplice),
    (279, SyscallName::MovePages),
    (280, SyscallName::Utimensat),
    (281, SyscallName::EpollPwait),
    (282, SyscallName::Signalfd),
    (283, SyscallName::TimerfdCreate),
    (284, SyscallName::Eventfd),
    (285, SyscallName::Fallocate),
    (286, SyscallName::TimerfdSettime),
    (287, SyscallName::TimerfdGettime),
    (288, SyscallName::Accept4),
    (289, SyscallName::Signalfd4),
    (290, SyscallName::Eventfd2),
    (291, SyscallName::EpollCreate1),
    (292, SyscallName::Dup3),
    (293, SyscallName::Pipe2),
    (294, SyscallName::InotifyInit1),
    (295, SyscallName::Preadv),
    (296, SyscallName::Pwritev),
    (297, SyscallName::RtTgsigqueueinfo),
    (298, SyscallName::PerfEventOpen),
    (299, SyscallName::Recvmmsg),
    (300, SyscallName::FanotifyInit),
    (301, SyscallName::FanotifyMark),
    (302, SyscallName::Prlimit64),
    (303, SyscallName::NameToHandleAt),
    (304, SyscallName::OpenByHandleAt),
    (305, SyscallName::ClockAdjtime),
    (306, SyscallName::Syncfs),
    (307, SyscallName::Sendmmsg),
    (308, SyscallName::Setns),
    (309, SyscallName::Getcpu),
    (310, SyscallName::ProcessVmReadv),
    (311, SyscallName::ProcessVmWritev),
    (312, SyscallName::Kcmp),
    (313, SyscallName::FinitModule),
    (314, SyscallName::SchedSetattr),
    (315, SyscallName::SchedGetattr),
    (316, SyscallName::Renameat2),
    (317, SyscallName::Seccomp),
    (318, SyscallName::Getrandom),
    (319, SyscallName::MemfdCreate),
    (320, SyscallName::KexecFileLoad),
    (321, SyscallName::Bpf),
    (322, SyscallName::Execveat),
    (323, SyscallName::Userfaultfd),
    (324, SyscallName::Membarrier),
    (325, SyscallName::Mlock2),
    (326, SyscallName::CopyFileRange),
    (327, SyscallName::Preadv2),
    (328, SyscallName::Pwritev2),
    (329, SyscallName::PkeyMprotect),
    (330, SyscallName::PkeyAlloc),
    (331, SyscallName::PkeyFree),
    (332, SyscallName::Statx),
    (333, SyscallName::IoPgetevents),
    (334, SyscallName::Rseq),
    (424, SyscallName::PidfdSendSignal),
    (425, SyscallName::IoUringSetup),
    (426, SyscallName::IoUringEnter),
    (427, SyscallName::IoUringRegister),
];

// ---------------------------------------------------------------------------
// Category representatives
// ---------------------------------------------------------------------------
static FILE_SYSCALLS: &[SyscallName] = &[
    SyscallName::Read,
    SyscallName::Write,
    SyscallName::Open,
    SyscallName::Close,
    SyscallName::Stat,
    SyscallName::Fstat,
    SyscallName::Lstat,
    SyscallName::Lseek,
    SyscallName::Pread64,
    SyscallName::Pwrite64,
    SyscallName::Readv,
    SyscallName::Writev,
    SyscallName::Access,
    SyscallName::Dup,
    SyscallName::Dup2,
    SyscallName::Fcntl,
    SyscallName::Flock,
    SyscallName::Fsync,
    SyscallName::Fdatasync,
    SyscallName::Truncate,
    SyscallName::Ftruncate,
    SyscallName::Getdents,
    SyscallName::Getcwd,
    SyscallName::Chdir,
    SyscallName::Rename,
    SyscallName::Mkdir,
    SyscallName::Rmdir,
    SyscallName::Creat,
    SyscallName::Link,
    SyscallName::Unlink,
    SyscallName::Symlink,
    SyscallName::Readlink,
    SyscallName::Chmod,
    SyscallName::Fchmod,
    SyscallName::Chown,
    SyscallName::Fchown,
    SyscallName::Lchown,
    SyscallName::Openat,
    SyscallName::Unlinkat,
    SyscallName::Renameat,
    SyscallName::Renameat2,
    SyscallName::Statx,
    SyscallName::Faccessat,
    SyscallName::Newfstatat,
];

static NETWORK_SYSCALLS: &[SyscallName] = &[
    SyscallName::Socket,
    SyscallName::Connect,
    SyscallName::Accept,
    SyscallName::Sendto,
    SyscallName::Recvfrom,
    SyscallName::Sendmsg,
    SyscallName::Recvmsg,
    SyscallName::Shutdown,
    SyscallName::Bind,
    SyscallName::Listen,
    SyscallName::Getsockname,
    SyscallName::Getpeername,
    SyscallName::Socketpair,
    SyscallName::Setsockopt,
    SyscallName::Getsockopt,
    SyscallName::Accept4,
    SyscallName::Sendmmsg,
    SyscallName::Recvmmsg,
];

static PROCESS_SYSCALLS: &[SyscallName] = &[
    SyscallName::Clone,
    SyscallName::Fork,
    SyscallName::Vfork,
    SyscallName::Execve,
    SyscallName::Exit,
    SyscallName::Wait4,
    SyscallName::Getpid,
    SyscallName::Getppid,
    SyscallName::Getpgrp,
    SyscallName::Setsid,
    SyscallName::Setpgid,
    SyscallName::ExitGroup,
    SyscallName::Waitid,
    SyscallName::Kill,
    SyscallName::Tkill,
    SyscallName::Tgkill,
    SyscallName::Gettid,
    SyscallName::Execveat,
    SyscallName::Unshare,
    SyscallName::Setns,
    SyscallName::Prctl,
];

static MEMORY_SYSCALLS: &[SyscallName] = &[
    SyscallName::Mmap,
    SyscallName::Mprotect,
    SyscallName::Munmap,
    SyscallName::Brk,
    SyscallName::Mremap,
    SyscallName::Msync,
    SyscallName::Mincore,
    SyscallName::Madvise,
    SyscallName::Mlock,
    SyscallName::Munlock,
    SyscallName::Mlockall,
    SyscallName::Munlockall,
    SyscallName::Mbind,
    SyscallName::SetMempolicy,
    SyscallName::GetMempolicy,
    SyscallName::Mlock2,
    SyscallName::MemfdCreate,
    SyscallName::PkeyMprotect,
    SyscallName::PkeyAlloc,
    SyscallName::PkeyFree,
];

static SIGNAL_SYSCALLS: &[SyscallName] = &[
    SyscallName::RtSigaction,
    SyscallName::RtSigprocmask,
    SyscallName::RtSigreturn,
    SyscallName::RtSigpending,
    SyscallName::RtSigtimedwait,
    SyscallName::RtSigqueueinfo,
    SyscallName::RtSigsuspend,
    SyscallName::Sigaltstack,
    SyscallName::Kill,
    SyscallName::Tkill,
    SyscallName::Tgkill,
    SyscallName::Signalfd,
    SyscallName::Signalfd4,
    SyscallName::PidfdSendSignal,
    SyscallName::RestartSyscall,
];

// ---------------------------------------------------------------------------
// (1) Top-100 completeness
// ---------------------------------------------------------------------------
#[test]
fn all_top_100_common_syscalls_present() {
    let translator = X86_64SyscallTranslator::new();
    let mut missing = Vec::new();

    for &(number, expected_name) in TOP_100_SYSCALLS {
        match translator.lookup_name(number) {
            Some(&name) => {
                if name != expected_name {
                    missing.push(format!(
                        "number {} maps to {:?} but expected {:?}",
                        number, name, expected_name
                    ));
                }
            }
            None => {
                missing.push(format!("number {} ({:?}) missing", number, expected_name));
            }
        }
    }

    assert!(
        missing.is_empty(),
        "Missing or incorrect top-100 syscalls:\n{}",
        missing.join("\n")
    );
}

// ---------------------------------------------------------------------------
// (2) Bidirectional lookup
// ---------------------------------------------------------------------------
#[test]
fn bidirectional_lookup_for_all_entries() {
    let translator = X86_64SyscallTranslator::new();
    let mut failures = Vec::new();

    for &(number, expected_name) in ALL_SYSCALLS {
        // number -> name
        match translator.lookup_name(number) {
            Some(&name) => {
                if name != expected_name {
                    failures.push(format!(
                        "lookup_name({}) -> {:?} (expected {:?})",
                        number, name, expected_name
                    ));
                }
            }
            None => {
                failures.push(format!(
                    "lookup_name({}) -> None (expected {:?})",
                    number, expected_name
                ));
            }
        }

        // name -> number
        match translator.lookup_number(expected_name) {
            Some(found_num) => {
                if found_num != number {
                    failures.push(format!(
                        "lookup_number({:?}) -> {} (expected {})",
                        expected_name, found_num, number
                    ));
                }
            }
            None => {
                failures.push(format!(
                    "lookup_number({:?}) -> None (expected {})",
                    expected_name, number
                ));
            }
        }
    }

    assert!(
        failures.is_empty(),
        "Bidirectional lookup failures:\n{}",
        failures.join("\n")
    );
}

// ---------------------------------------------------------------------------
// (3) No duplicate numbers
// ---------------------------------------------------------------------------
#[test]
fn no_duplicate_numbers() {
    let mut seen = HashSet::new();
    let mut duplicates = Vec::new();

    for &(number, _name) in ALL_SYSCALLS {
        if !seen.insert(number) {
            duplicates.push(number);
        }
    }

    assert!(
        duplicates.is_empty(),
        "Duplicate syscall numbers found: {:?}",
        duplicates
    );
}

// ---------------------------------------------------------------------------
// (4) No duplicate names
// ---------------------------------------------------------------------------
#[test]
fn no_duplicate_names() {
    let mut seen = HashSet::new();
    let mut duplicates = Vec::new();

    for &(_number, name) in ALL_SYSCALLS {
        if !seen.insert(name) {
            duplicates.push(format!("{:?}", name));
        }
    }

    assert!(
        duplicates.is_empty(),
        "Duplicate syscall names found: {}",
        duplicates.join(", ")
    );
}

// ---------------------------------------------------------------------------
// (5) Category coverage
// ---------------------------------------------------------------------------
#[test]
fn file_category_coverage() {
    let translator = X86_64SyscallTranslator::new();
    let mut missing = Vec::new();

    for &name in FILE_SYSCALLS {
        if translator.lookup_number(name).is_none() {
            missing.push(format!("{:?}", name));
        }
    }

    assert!(
        missing.is_empty(),
        "Missing file syscalls: {}",
        missing.join(", ")
    );
}

#[test]
fn network_category_coverage() {
    let translator = X86_64SyscallTranslator::new();
    let mut missing = Vec::new();

    for &name in NETWORK_SYSCALLS {
        if translator.lookup_number(name).is_none() {
            missing.push(format!("{:?}", name));
        }
    }

    assert!(
        missing.is_empty(),
        "Missing network syscalls: {}",
        missing.join(", ")
    );
}

#[test]
fn process_category_coverage() {
    let translator = X86_64SyscallTranslator::new();
    let mut missing = Vec::new();

    for &name in PROCESS_SYSCALLS {
        if translator.lookup_number(name).is_none() {
            missing.push(format!("{:?}", name));
        }
    }

    assert!(
        missing.is_empty(),
        "Missing process syscalls: {}",
        missing.join(", ")
    );
}

#[test]
fn memory_category_coverage() {
    let translator = X86_64SyscallTranslator::new();
    let mut missing = Vec::new();

    for &name in MEMORY_SYSCALLS {
        if translator.lookup_number(name).is_none() {
            missing.push(format!("{:?}", name));
        }
    }

    assert!(
        missing.is_empty(),
        "Missing memory syscalls: {}",
        missing.join(", ")
    );
}

#[test]
fn signal_category_coverage() {
    let translator = X86_64SyscallTranslator::new();
    let mut missing = Vec::new();

    for &name in SIGNAL_SYSCALLS {
        if translator.lookup_number(name).is_none() {
            missing.push(format!("{:?}", name));
        }
    }

    assert!(
        missing.is_empty(),
        "Missing signal syscalls: {}",
        missing.join(", ")
    );
}
