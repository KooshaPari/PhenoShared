#!/bin/zsh
# Refresh zsh startup caches
mkdir -p ~/.zsh_cache

zoxide init zsh > ~/.zsh_cache/zoxide.zsh
fzf --zsh > ~/.zsh_cache/fzf.zsh
mcfly init zsh > ~/.zsh_cache/mcfly.zsh

# Compile them
zcompile ~/.zsh_cache/zoxide.zsh
zcompile ~/.zsh_cache/fzf.zsh
zcompile ~/.zsh_cache/mcfly.zsh

echo "Zsh caches refreshed and compiled."
