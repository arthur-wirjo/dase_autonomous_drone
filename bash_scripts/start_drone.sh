#!/bin/bash

# Name of our tmux session
SESSION="drone_flight"

# Check if the session already exists. If it does, just attach to it.
tmux has-session -t $SESSION 2>/dev/null
if [ $? == 0 ]; then
    echo "Session '$SESSION' is already running. Attaching to it..."
    tmux attach-session -t $SESSION
    exit 0
fi

# Determine which camera script to run based on the argument passed
# Default to fast camera if no argument is provided
CAM_SCRIPT="run_fast_camera.sh"
if [ "$1" == "smooth" ]; then
    CAM_SCRIPT="run_smooth_camera.sh"
    echo "Starting with SMOOTH camera..."
else
    echo "Starting with FAST camera..."
fi

# 1. Create a new detached tmux session
tmux new-session -d -s $SESSION

# 2. Pane 0 (Left half): Run the MicroXRCEAgent
tmux send-keys -t $SESSION:0.0 "~/ros2_ws/src/dase_autonomous_drone/bash_scripts/run_agent.sh" C-m

# 3. Split the window horizontally (creates Pane 1 on the right half)
tmux split-window -h -t $SESSION:0

# 4. Pane 1 (Top Right): Run the Hover Node
tmux send-keys -t $SESSION:0.1 "~/ros2_ws/src/dase_autonomous_drone/bash_scripts/run_hover.sh" C-m

# 5. Split Pane 1 vertically (creates Pane 2 on the bottom right)
tmux split-window -v -t $SESSION:0.1

# 6. Pane 2 (Bottom Right): Run the Camera
tmux send-keys -t $SESSION:0.2 "~/ros2_ws/src/dase_autonomous_drone/bash_scripts/$CAM_SCRIPT" C-m

# 7. Attach to the session so you can see everything
tmux attach-session -t $SESSION
