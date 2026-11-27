//go:build windows

package hook

// shellPathsComparable is false on Windows.
//
// The hook's `pwd` text is not portable here: Git's sh reports the caller's temp
// directory as /tmp rather than /c/Users/.../AppData/Local/Temp, because MSYS maps
// its mounts. Comparing that string to a Windows path proves nothing about where
// the hook ran.
//
// What the test does prove on this platform is stronger anyway: the hook writes
// where.txt with a relative path, and the file is then read from the directory the
// caller supplied. If the hook had run anywhere else, that read would fail.
const shellPathsComparable = false
