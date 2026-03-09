#!/bin/bash
cd /root/.openclaw
git add workspace/ workspace-senior/ workspace-receptionist/
git diff --cached --quiet || (git commit -m "auto: workspace snapshot $(date '+%F %H:%M')" && git push)
