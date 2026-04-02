# Dynamic Flipping Topology — Integration Notes

This document captures the full integration plan, what was built, and how everything works.
Reference this when working in the SKYFALL directory.

---

## Background: what the two codebases do

### CDN (`dynamic-flipping-topology/`)

Implements Algorithm 1 from *"Three Links Are Not a Grid: From Static Grids to Dynamic Flipping"*.
Takes real (or synthetic) TLE data and produces a JSON of time-varying ISL topologies.

**Pipeline:**
1. Read TLE → parse satellite orbital elements
2. SGP4 propagate → positions and velocities at each timestep
3. Orbit partition → assign satellites to 72 planes by RAAN binning
4. Ring construction → greedy nearest-neighbor matching across adjacent orbit pairs; each satellite gets at most 2 ring neighbors (one in the previous plane, one in the next)
5. Per-frame computation → for each timestep, compute which ring edges become active ISLs:
   - Intra-orbit: always active (2 per satellite, deterministic)
   - Inter-orbit: check distance ≤ 5,016 km and LOS angular velocity ≤ 0.0012 rad/s; if both candidates pass, pick the one on the left lateral side; link established only if both endpoints mutually select each other

**Output:** `topology.json` — a JSON with `metadata`, `orbit_partition`, `rings`, and `frames[]`. Each frame has `intra_orbit_links` and `inter_orbit_links` as `[sat_i, sat_j]` pairs, plus counts.

**Key numbers for the SKYFALL Walker constellation:**
- 1,584 satellites (72 × 22), same as SKYFALL's +Grid
- ~1,584 intra-orbit links per frame (2 per satellite)
- ~200–250 inter-orbit links active per frame
- ~240 satellites in re-acquisition (0 inter-orbit link) at any moment
- CDN frame interval: 15 seconds

### SKYFALL (`SKYFALL/`)

Simulates bottleneck GSL attacks on a LEO satellite network.

**Pipeline:**
1. `generate_lla.py` → generate satellite LLA positions for each second
2. `generate_flow_grid.py` or `generate_flow_circle.py` → simulate traffic on +Grid or Circle topology for a given timeslot
3. `time_slot_analysis_grid/circle.py` → find vulnerable GSLs, compute botnet placement
4. `aggregated_deployment_grid/circle.py` → aggregate attack data across timeslots

**How +Grid hardcodes topology (the core incompatibility):**

Everything is implicit in arithmetic. No adjacency list is ever stored.

```python
# Satellite numbering
sat_index = orbit_id * sat_of_orbit + sat_id   # e.g. orbit 3, sat 5 → index 71

# 4 ISL neighbors computed on-the-fly in link_seq():
# offset 0: next in same orbit      → sat + 1          (mod orbit size)
# offset 1: next orbit, same pos    → sat + 22          (mod 1584)
# offset 2: prev in same orbit      → sat - 1
# offset 3: prev orbit, same pos    → sat - 22

# link_traffic flat array:  sat_index * 6 + {0..3: ISL, 4: downlink, 5: uplink}
link_traffic = [0] * sat_num * 6
```

Routing (`find_next_sat` / `floyd`) finds the nearest GS-connected satellite using Manhattan
distance on the 72×22 grid — no graph traversal, pure arithmetic.

---

## Key incompatibilities between the two codebases

| Aspect | CDN / Dynamic Flipping | SKYFALL / +Grid |
|---|---|---|
| Satellite count | 1,170 (real TLE) or 1,584 (Walker) | 1,584 (72×22 Walker) |
| ISLs per satellite | 3 max (2 intra + 0–1 inter) | 4 fixed (2 intra + 2 inter) |
| Inter-orbit links | Time-varying, non-regular | Static, regular grid |
| Topology representation | Explicit edge list per frame | Implicit arithmetic |
| Link traffic array | Needs dynamic per-frame sizing | Fixed `sat * 6 + offset` |
| Routing | Not included | Hardcoded grid Manhattan distance |
| Time resolution | 15-second frames | 1-second timeslots |
| Satellite indexing | TLE order (arbitrary) | `orbit_id * 22 + sat_id` |

---

## Integration approach: run CDN on SKYFALL's constellation

Rather than mapping CDN's 1,170 Starlink satellites into SKYFALL, we run CDN's flipping
algorithm on SKYFALL's own 72×22 synthetic Walker constellation. This means:

- SKYFALL's satellite numbering, block grid, traffic model, GS connections, all analysis code stay intact
- Clean three-way comparison: +Grid vs Circle vs Dynamic Flipping on the exact same 1,584 satellites
- The only variable between the three modes is the ISL topology

**Caveat:** A perfectly regular Walker constellation produces more symmetric flipping behavior
than real Starlink (real orbital perturbations cause ring fragmentation and asymmetric
re-acquisition). Worth noting in the paper but not a problem for comparative analysis.

---

## What was built

### 1. `skyfall/write_skyfall_tle.py` — TLE writer

Converts SKYFALL's `sgp4init` parameters to 3-line TLE format so CDN can consume them.

Critical detail: satellites are written in SKYFALL's index order (`orbit_id * 22 + sat_id`),
so CDN satellite index k == SKYFALL satellite index k. No remapping is ever needed.

The orbital parameters come directly from `generate_lla.py`:
- RAAN = `orbit_id / 72 * 360°`
- Mean anomaly = `(sat_id * 360/22 + orbit_id * 360/1584) % 360°`
- Inclination = 53°, eccentricity = 0.001, altitude = 550 km

**Usage:**
```bash
cd skyfall/
python write_skyfall_tle.py --output ../skyfall_walker.tle
```

---

### 2. CDN `generate.py` run (external step, not a new file)

```bash
cd ../../dynamic-flipping-topology/
python generate.py \
    --tle ../SKYFALL/skyfall_walker.tle \
    --start "2020-06-01 00:00:00" \
    --end   "2020-06-01 01:30:00" \
    --step  15 \
    --output ../SKYFALL/topology.json
```

The `--start` time must match the SKYFALL simulation epoch (`2020-06-01 00:00:00` in
`generate_lla.py`). For 3600 timeslots (1 hour), you need at least 241 CDN frames (60 minutes
+ 1 frame), so `--end` should be at least 1 hour after `--start`.

The `topology_json` path in `config.json` tells the flipping scripts where to load this file.

---

### 3. `skyfall/generate_flow_flipping.py` — core flow simulator

Based on `generate_flow_grid.py`. The key changes:

**Topology loading** (replaces `link_seq()` arithmetic):
```python
# Load once at startup
with open(topology_json) as f:
    topo = json.load(f)

# Per timeslot: map to CDN frame
frame_idx = time_slot // CDN_STEP   # CDN_STEP = 15
frame = topo["frames"][frame_idx]
all_links = frame["intra_orbit_links"] + frame["inter_orbit_links"]

# Build adjacency + link ID lookup
neighbors = {}
link_id_map = {}
for idx, (a, b) in enumerate(all_links):
    neighbors.setdefault(a, []).append(b)
    neighbors.setdefault(b, []).append(a)
    link_id_map[(a, b)] = idx
    link_id_map[(b, a)] = idx

link_traffic_isl = [0] * len(all_links)
```

**BFS routing** (replaces `floyd()` + `find_next_sat()`):
```python
def bfs_next_hop(source):
    if sat_connect_gs[source] != -1:
        return source          # already a landing satellite
    visited = {source: None}
    queue = deque([source])
    while queue:
        node = queue.popleft()
        if sat_connect_gs[node] != -1:
            # trace back to first hop
            cur = node
            while visited[cur] != source:
                cur = visited[cur]
            return cur
        for nb in neighbors.get(node, []):
            if nb not in visited:
                visited[nb] = node
                queue.append(nb)
    return -1   # no reachable GS
```

**`add_flow()` changes:**
- Uses `link_id_map.get((from_sat, to_sat), -1)` instead of `link_seq()`
- Satellites in re-acquisition simply have no inter-orbit entry in `link_id_map`; the flow
  is still routed via available intra-orbit links
- GSL traffic (`uplink_traffic[]`, `downlink_traffic[]`) stays per-satellite, same as grid

**Link traffic array:**
Grid uses `sat_num * 6` (flat, fixed). Flipping uses `len(all_links)` per frame (varies
~1,780–1,840 edges). The `link_id_map` dict handles the indexing.

**Output directory:** `flipping_data/` (mirrors `+grid_data/` structure exactly, same file names).

---

### 4. `skyfall/time_slot_analysis_flipping.py` — attack analysis

Based on `time_slot_analysis_grid.py`. The only meaningful change is `find_landing_gs()`:

**Grid version** (Manhattan arithmetic):
```python
def find_landing_gs(index, sat_connect_gs):
    orbit_id = int(index / sat_per_cycle)
    sat_id = index % sat_per_cycle
    min_hops = int(sat_per_cycle / 2) + int(orbit_num / 2)
    # ... walks all satellites computing orbit_diff + sat_diff ...
```

**Flipping version** (BFS over current frame adjacency):
```python
def find_landing_gs(index, sat_connect_gs):
    if sat_connect_gs[index] != -1:
        return sat_connect_gs[index]
    visited = {index}
    queue = deque([index])
    while queue:
        node = queue.popleft()
        if sat_connect_gs[node] != -1:
            return sat_connect_gs[node]
        for nb in neighbors.get(node, []):
            if nb not in visited:
                visited.add(nb)
                queue.append(nb)
    return -1
```

Candidate satellite ranking also uses BFS hop distance from the target satellite (instead
of Manhattan orbit_diff + sat_diff).

Reads from / writes to `flipping_data/attack_traffic_data_land_only_bot/`.

---

### 5. `skyfall/aggregated_deployment_flipping.py` — cross-timeslot aggregation

Identical logic to `aggregated_deployment_grid.py`. The only changes are data directory
paths: `+grid_data` → `flipping_data`. No algorithmic changes needed here because
aggregation operates only on the per-timeslot output files, not on topology.

---

### 6. `config.json` — added `topology_json` field

```json
{
    "Name": "starlink_shell_one",
    "Altitude (km)": 550,
    "Inclination": 53,
    "# of orbit": 72,
    "# of satellites": 22,
    "topology_json": "../topology.json"
}
```

All three flipping scripts read this field. Default falls back to `"../topology.json"` if
the field is absent, so existing grid/circle scripts are unaffected.

---

## Full pipeline (end to end)

```bash
# ── One-time setup ──────────────────────────────────────────────────────────

# 1. Generate satellite positions (shared by all 3 topologies)
cd SKYFALL/skyfall/
python generate_lla.py 3600

# 2. Write SKYFALL constellation as TLE
python write_skyfall_tle.py --output ../skyfall_walker.tle

# 3. Run CDN topology generator
cd ../../dynamic-flipping-topology/
python generate.py \
    --tle ../SKYFALL/skyfall_walker.tle \
    --start "2020-06-01 00:00:00" \
    --end   "2020-06-01 01:30:00" \
    --step  15 \
    --output ../SKYFALL/topology.json

# ── Per timeslot (run in parallel for all N timeslots) ──────────────────────

cd ../SKYFALL/skyfall/
python generate_flow_flipping.py 0        # timeslot 0
python generate_flow_flipping.py 1        # timeslot 1
# ... repeat for all timeslots

# ── Attack analysis ─────────────────────────────────────────────────────────

python time_slot_analysis_flipping.py 0 1.5   # timeslot 0, ratio 1.5
# ... repeat for all timeslots

# ── Aggregate ───────────────────────────────────────────────────────────────

python aggregated_deployment_flipping.py 3600 1.5
```

---

## Data directory structure

After running the full pipeline, outputs mirror the +Grid structure:

```
SKYFALL/starlink_shell_one/
├── sat_lla/                            ← satellite positions (shared)
│   ├── 0.txt
│   ├── 1.txt
│   └── ...
├── +grid_data/                         ← +Grid outputs (unchanged)
│   └── link_traffic_data/
│       └── <timeslot>/
│           ├── isl_traffic.txt
│           ├── downlink_traffic.txt
│           ├── uplink_traffic.txt
│           ├── sat_connect_gs.txt
│           ├── user_connect_sat.txt
│           ├── gsl_occurrence_num.txt
│           └── gs_occurrence_num.txt
└── flipping_data/                      ← Dynamic Flipping outputs (new)
    ├── link_traffic_data/
    │   └── <timeslot>/
    │       ├── isl_traffic.txt         ← same schema as +grid_data
    │       ├── downlink_traffic.txt
    │       ├── uplink_traffic.txt
    │       ├── sat_connect_gs.txt
    │       ├── user_connect_sat.txt
    │       ├── gsl_occurrence_num.txt
    │       └── gs_occurrence_num.txt
    └── attack_traffic_data_land_only_bot/
        └── <ratio>-<params>/
            └── <timeslot>/
                ├── attack_gsl.txt
                ├── bot_num.txt
                ├── bot_block.txt
                ├── bot_sat.txt
                └── ...
```

---

## Things to watch out for

**Re-acquisition satellites:** ~240 satellites at any moment have no inter-orbit link.
Their traffic still routes via the 2 intra-orbit links — `add_flow()` handles this
naturally because `link_id_map` simply has no inter-orbit entry for them.

**Frame index clamping:** `frame_idx = min(time_slot // 15, len(frames) - 1)`. If you
simulate more timeslots than CDN frames cover, the last CDN frame is reused. Extend the
CDN `--end` time to avoid this.

**BFS performance:** BFS runs once per satellite per timeslot in `build_routing()` (1,584
BFS calls per timeslot). For large simulation runs, consider precomputing the routing table
once per CDN frame (every 15 timeslots) rather than recomputing each second.

**Vital GS file:** `time_slot_analysis_flipping.py` expects `vital_gs.txt` in
`flipping_data/link_traffic_data/<timeslot>/`. This file is produced by an upstream ranking
step (see `bottleneck_GS_rank.py`). Run that step on `flipping_data` first.
