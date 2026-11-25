#!/usr/bin/env python3
"""Mail fetcher (ships DISABLED: the poller ignores it unless INTAKE_MAIL_ENABLED=1).

Reads RFC822 files from INTAKE_MAIL_DIR (whatever delivery path lands Dot's
mail there) and prints JSON lines {"id","sender","body"} ONLY for messages
whose Authentication-Results header shows spf=pass, dkim=pass and dmarc=pass.
Everything else is skipped silently (never forwarded to the writer).
"""
import email, email.policy, email.utils, json, os, re, sys

def auth_pass(msg):
    results = " ".join(msg.get_all("Authentication-Results", [])).lower()
    return all(re.search(r"\b%s=pass\b" % k, results) for k in ("spf", "dkim", "dmarc"))

def plain_body(msg):
    part = msg.get_body(preferencelist=("plain",))
    return part.get_content() if part else ""

def main():
    root = os.environ["INTAKE_MAIL_DIR"]
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name)
        if not os.path.isfile(path):
            continue
        with open(path, "rb") as f:
            msg = email.message_from_binary_file(f, policy=email.policy.default)
        if not auth_pass(msg):
            continue
        sender = email.utils.parseaddr(str(msg.get("From", "")))[1]
        print(json.dumps({"id": str(msg.get("Message-ID", name)), "sender": sender, "body": plain_body(msg)}))

if __name__ == "__main__":
    main()
