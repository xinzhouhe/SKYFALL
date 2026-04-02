#!/usr/bin/python
# -*- coding: UTF-8 -*-

# In this code, we analyze the risks and the variabilities for the Dynamic Flipping topology,
# as described in the Analysis Stage (Section IV.C).
# Specifically, the worst case under the Dynamic Flipping Structure is analyzed.
# Key difference from time_slot_analysis_grid.py: find_landing_gs() uses BFS over the
# loaded topology frame adjacency instead of grid Manhattan-distance arithmetic.

import numpy as np
import math
import os
import sys
import json
import random
from collections import deque

f = open("../config.json", "r", encoding='utf8')
table = json.load(f)
cons_name = table["Name"]
altitude = int(table["Altitude (km)"])
orbit_num = table["# of orbit"]
sat_per_cycle = table["# of satellites"]
inclination = table["Inclination"]
topology_json = table.get("topology_json", "../topology_test.json")

CDN_STEP = 15   # CDN frame interval in seconds

bot_num = 0
traffic_thre = 20
sat_num = orbit_num * sat_per_cycle
GSL_capacity = 4096
unit_traffic = 20
vital_gs = []

# Adjacency for the current timeslot's CDN frame
neighbors = {}   # sat_idx -> list of neighbor sat_idx


def load_frame_neighbors(topo: dict, time_slot: int):
    """Load adjacency for the CDN frame corresponding to time_slot."""
    global neighbors
    frame_idx = min(time_slot // CDN_STEP, len(topo["frames"]) - 1)
    frame = topo["frames"][frame_idx]
    all_links = frame["intra_orbit_links"] + frame["inter_orbit_links"]
    neighbors = {}
    for a, b in all_links:
        neighbors.setdefault(a, []).append(b)
        neighbors.setdefault(b, []).append(a)


def find_landing_gs(index: int, sat_connect_gs: list) -> int:
    """
    BFS from satellite `index` over the current frame's topology to find
    the GS serving the nearest reachable GS-connected satellite.
    Returns the GS index (same semantics as the grid version), or -1 if unreachable.
    """
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


if __name__ == "__main__":
    time_slot = sys.argv[1]
    ratio = float(sys.argv[2])  # throughput degradation

    # Load CDN topology and build adjacency for this timeslot
    with open(topology_json) as f_topo:
        topo = json.load(f_topo)
    load_frame_neighbors(topo, int(time_slot))

    data_dir = '../' + cons_name + '/flipping_data/link_traffic_data/' + str(time_slot) + '/'

    overlapping_gs = np.loadtxt(data_dir + 'vital_gs.txt')
    vital_gs = list(map(int, overlapping_gs))

    traffic = list(map(int, np.loadtxt(data_dir + 'downlink_traffic.txt')))
    uplink_traffic = list(map(int, np.loadtxt(data_dir + 'uplink_traffic.txt')))
    sat_connect_gs = list(map(int, np.loadtxt(data_dir + 'sat_connect_gs.txt')))
    user_connect_sat = list(map(int, np.loadtxt(data_dir + 'user_connect_sat.txt')))
    traffic_sum = np.sum(traffic)

    attack_gsl = []
    bot_sat = []
    bot_block = []
    bot_block_bot_num_per_block = []
    cumu_affected_traffic_volume = 0
    total_target_traffic = 0
    attack_traffic = [0 for _ in range(len(traffic))]

    traffic_count = []
    with open('./starlink_count.txt', 'r') as fr:
        lines = fr.readlines()
        for row in range(90 - inclination, 90 + inclination):
            traffic_count.extend([float(x) for x in lines[row].split(' ')[:-1]] + [0])

    target_gs = 0
    while True:
        max_data = max(traffic)
        max_index = traffic.index(max_data)

        if max_data <= GSL_capacity / 2:
            break

        if sat_connect_gs[max_index] in vital_gs:
            total_target_traffic += max_data
            target_gs = sat_connect_gs[max_index]

            needed_bot_traffic = GSL_capacity / ratio - max_data
            needed_bot_num = math.ceil(needed_bot_traffic / unit_traffic)

            # BFS-based candidate satellite selection: all sats that route through target_gs
            # Rank by BFS hop distance from max_index (closest first)
            possible_sats = [s for s in range(sat_num)
                             if find_landing_gs(s, sat_connect_gs) == target_gs]

            # Rank by hop distance from max_index via BFS
            hop_dist = {max_index: 0}
            bfs_q = deque([max_index])
            while bfs_q:
                node = bfs_q.popleft()
                for nb in neighbors.get(node, []):
                    if nb not in hop_dist:
                        hop_dist[nb] = hop_dist[node] + 1
                        bfs_q.append(nb)
            # Satellites not reachable from max_index get large distance
            possible_sat_diff = sorted(possible_sats,
                                       key=lambda s: hop_dist.get(s, 99999))
            candidate_sat = possible_sat_diff

            # Prefer satellites adjacent to existing bot blocks (same as grid version)
            neighbor_block = []
            for block_index in bot_block:
                for delta in [-1, 1, -inclination * 2, inclination * 2]:
                    nb_blk = block_index + delta
                    if 0 <= nb_blk <= inclination * 2 * 360 - 1:
                        neighbor_block.append(nb_blk)

            chosen_candidate_sat = []
            for neighbor in neighbor_block:
                if (user_connect_sat[neighbor] in candidate_sat
                        and user_connect_sat[neighbor] not in chosen_candidate_sat
                        and traffic_count[neighbor] > 0):
                    chosen_candidate_sat.append(int(user_connect_sat[neighbor]))

            for cur_sat in chosen_candidate_sat:
                new_bot_num = min(
                    traffic_thre,
                    math.ceil((GSL_capacity - uplink_traffic[cur_sat] -
                               attack_traffic[cur_sat]) / unit_traffic))
                flag = 0
                if new_bot_num > 0:
                    for block_id in range(len(user_connect_sat)):
                        if user_connect_sat[block_id] == cur_sat and traffic_count[block_id] > 0:
                            bot_block.append(block_id)
                            bot_block_bot_num_per_block.append(
                                new_bot_num if needed_bot_num - new_bot_num >= 0 else needed_bot_num)
                            flag = 1
                            break
                if flag == 1:
                    if needed_bot_num - new_bot_num >= 0:
                        bot_num += new_bot_num
                        needed_bot_num -= new_bot_num
                        attack_traffic[cur_sat] += new_bot_num * unit_traffic
                        for _ in range(new_bot_num):
                            bot_sat.append(cur_sat)
                    else:
                        bot_num += needed_bot_num
                        attack_traffic[cur_sat] += needed_bot_num * unit_traffic
                        for _ in range(needed_bot_num):
                            bot_sat.append(cur_sat)
                        needed_bot_num = 0
                        cumu_affected_traffic_volume += max_data * 1.1
                        break

            for cur_sat in candidate_sat:
                if cur_sat in chosen_candidate_sat:
                    continue
                new_bot_num = min(
                    traffic_thre,
                    math.ceil((GSL_capacity - uplink_traffic[cur_sat] -
                               attack_traffic[cur_sat]) / unit_traffic))
                flag = 0
                if new_bot_num > 0:
                    for block_id in range(len(user_connect_sat)):
                        if user_connect_sat[block_id] == cur_sat and traffic_count[block_id] > 0:
                            bot_block.append(block_id)
                            bot_block_bot_num_per_block.append(
                                new_bot_num if needed_bot_num - new_bot_num >= 0 else needed_bot_num)
                            flag = 1
                            break
                if flag == 1:
                    if needed_bot_num - new_bot_num >= 0:
                        bot_num += new_bot_num
                        needed_bot_num -= new_bot_num
                        attack_traffic[cur_sat] += new_bot_num * unit_traffic
                        for _ in range(new_bot_num):
                            bot_sat.append(cur_sat)
                    else:
                        bot_num += needed_bot_num
                        attack_traffic[cur_sat] += needed_bot_num * unit_traffic
                        for _ in range(needed_bot_num):
                            bot_sat.append(cur_sat)
                        if needed_bot_num != 0:
                            cumu_affected_traffic_volume += max_data * 1.1
                        needed_bot_num = 0
                        break
            attack_gsl.append(max_index)
        traffic[max_index] = 0

    for _ in range(40):
        attack_gsl.append(random.randint(0, sat_num))
    cumu_affected_traffic_volume += 180 * 1024

    out_dir = ('../' + cons_name + '/flipping_data/attack_traffic_data_land_only_bot/'
               + str(ratio) + '-' + str(traffic_thre) + '-' + str(sat_per_cycle) + '-'
               + str(GSL_capacity) + '-' + str(unit_traffic) + '/' + time_slot)
    os.system('mkdir -p ' + out_dir)

    np.savetxt(out_dir + '/attack_gsl.txt', np.array(attack_gsl, dtype=int), fmt='%d')
    np.savetxt(out_dir + '/bot_num.txt', np.array([bot_num], dtype=int), fmt='%d')
    np.savetxt(out_dir + '/cumu_affected_traffic_volume.txt',
               np.array([int(cumu_affected_traffic_volume)], dtype=int), fmt='%d')
    np.savetxt(out_dir + '/total_target_traffic.txt',
               np.array([total_target_traffic], dtype=int), fmt='%d')
    np.savetxt(out_dir + '/bot_block.txt', np.array(bot_block, dtype=int), fmt='%d')
    np.savetxt(out_dir + '/bot_block_bot_num_per_block.txt',
               np.array(bot_block_bot_num_per_block, dtype=int), fmt='%d')
    np.savetxt(out_dir + '/bot_sat.txt', np.array(bot_sat, dtype=int), fmt='%d')

    print("Finished calculating malicious terminals deployment and generating malicious traffic "
          "for Dynamic Flipping at timeslot", time_slot)
