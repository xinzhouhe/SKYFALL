#!/bin/bash
# Automates Steps 5 and 6 of the SKYFALL pipeline:
#   Step 5: Time-slot analysis for all degradation ratios
#   Step 6: Aggregated deployment for all degradation ratios
#
# Usage: bash run_steps_5_6.sh <total_timeslots> <cpu_cores>
# Example: bash run_steps_5_6.sh 3600 64
# Demo:    bash run_steps_5_6.sh 100 8

set -e

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <total_timeslots> <cpu_cores>"
    echo "Example (full): $0 3600 64"
    echo "Example (demo): $0 100 8"
    exit 1
fi

TOTAL_TIMESLOTS=$1
CPU_CORES=$2
RATIOS=(0.9 0.8 0.7 0.6 0.5)

echo "========================================"
echo "SKYFALL Pipeline: Steps 5 and 6"
echo "Total timeslots : $TOTAL_TIMESLOTS"
echo "CPU cores       : $CPU_CORES"
echo "Ratios          : ${RATIOS[*]}"
echo "========================================"
echo ""

# Step 5: Time-slot analysis for each degradation ratio
echo "--- Step 5: Time-Slot Analysis ---"
for ratio in "${RATIOS[@]}"; do
    echo "  Running time_slot_analysis.sh with ratio=$ratio ..."
    bash time_slot_analysis.sh "$TOTAL_TIMESLOTS" "$CPU_CORES" "$ratio"
    echo "  Done: ratio=$ratio"
    echo ""
done
echo "Step 5 complete."
echo ""

# Step 6: Aggregated deployment for each degradation ratio
echo "--- Step 6: Aggregated Deployment ---"
for ratio in "${RATIOS[@]}"; do
    echo "  Running aggregated_deployment.sh with ratio=$ratio ..."
    bash aggregated_deployment.sh "$TOTAL_TIMESLOTS" "$ratio"
    echo "  Done: ratio=$ratio"
    echo ""
done
echo "Step 6 complete."
echo ""

echo "========================================"
echo "Steps 5 and 6 finished successfully."
echo "Next: run 'bash get_results.sh' for Step 7."
echo "========================================"
