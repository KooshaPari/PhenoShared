# PR277 CI label-event guard

Prevent unrelated PR label edits from running expensive CI. Own only ci.rs, same-file tests, generated ci.yml, and these docs. No commits/pushes. No lint.yml, test.yml, conversation, or LSP changes.
