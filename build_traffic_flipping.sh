#! /bin/bash
# Generate legal traffic for the Dynamic Flipping topology across all timeslots.
# Usage: bash build_traffic_flipping.sh <total_timeslots> <cpu_cores>
# Example (full 1-hour run): bash build_traffic_flipping.sh 3599 8
echo "Legal traffic (Dynamic Flipping): build"
echo ""
echo "Generating traffic..."

cd skyfall || exit 1
total_timeslots=$1
cpu_cores=$2
seq 0 $total_timeslots | xargs -n 1 -P $cpu_cores python3 generate_flow_flipping.py
cd .. || exit 1

echo "Traffic calculation finished!"
