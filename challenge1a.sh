!/bin/bash

tmux new-session -d -s 1A

tmux send-keys "nvim ~/adobe/challenge1A" C-m
tmux rename-window "Code"

tmux new-window -t 1A:2 -n "term"
tmux send-keys "nvim ~/adobe/challenge1A -c 'terminal'" C-m

tmux attach -t 1A
