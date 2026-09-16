#!/bin/bash
export PATH=/usr/bin:/bin:~/bin:$PATH
cd /tmp
rm -f test.key test.pub test.txt test.sig test.cert
echo test123 > test.txt

# Generate key with both passwords via stdin
echo -e 'testpass123\ntestpass123' | cosign generate-key-pair --output-key-prefix test 2>&1
head -1 test.key

# Try the v2.x method: pipe password via stdin to sign
echo "---signing via stdin---"
echo -e 'testpass123' | cosign sign-blob --key test.key --output-signature test.sig --output-certificate test.cert --yes test.txt 2>&1

echo "---ls---"
ls -la test.sig test.cert 2>&1
