#!/bin/bash
export PATH=/usr/bin:/bin:~/bin:$PATH
cd /tmp
rm -f test.key test.pub test.txt test.sig test.cert
echo test123 > test.txt
printf 'testpass123\ntestpass123\n' | cosign generate-key-pair --output-key-prefix test 2>&1
head -1 test.key
export COSIGN_PASSWORD=testpass123
echo "---signing---"
cosign sign-blob --key test.key --output-signature test.sig --output-certificate test.cert --yes test.txt 2>&1
echo "---ls---"
ls -la test.sig test.cert 2>&1
