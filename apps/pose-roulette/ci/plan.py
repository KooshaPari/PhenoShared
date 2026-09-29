import os
platform=os.getenv("REQUESTED_PLATFORM","both")
event=os.getenv("EVENT_NAME","push")
android=platform in ("both","android") if event=="workflow_dispatch" else True
ios=platform in ("both","ios") if event=="workflow_dispatch" else True
out=os.environ["GITHUB_OUTPUT"]
with open(out,"a",encoding="utf-8") as f:
    f.write(f"android={'true' if android else 'false'}\n")
    f.write(f"ios={'true' if ios else 'false'}\n")
