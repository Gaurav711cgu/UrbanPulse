"""
MockDataService — Generates realistic synthetic traffic events
for development and demo purposes.
"""

import asyncio
import random
import math
from datetime import datetime
from typing import Any


JUNCTION_NAMES = [
    "Sitabuldi Crossing", "Dharampeth Square", "Ramdaspeth Chowk",
    "Shankar Nagar", "Laxmi Nagar Square", "Bajaj Nagar",
    "Pratap Nagar", "Hingna T-Point", "Mankapur Circle",
    "Gokulpeth Square", "Wardhaman Nagar", "Bhandara Road Junction",
    "Kamptee Road Chowk", "Wadi Junction", "Itwari Square", "Mahal Chowk"
]

JUNCTIONS = [
    {"id": i + 1, "name": JUNCTION_NAMES[i], "lat": 21.12 + (i % 4) * 0.015, "lng": 79.08 + (i // 4) * 0.015}
    for i in range(16)
]


class MockDataService:
    def __init__(self):
        self._task: asyncio.Task | None = None
        self._running = False
        self._emergency_active: dict[int, bool] = {}

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _loop(self):
        tick = 0
        while self._running:
            tick += 1
            await asyncio.sleep(2)

    def _time_factor(self) -> float:
        """Scale traffic volume based on hour of day."""
        h = datetime.now().hour + datetime.now().minute / 60
        # Morning peak 8-10, evening peak 17-19
        morning = math.exp(-0.5 * ((h - 9) / 1.2) ** 2)
        evening = math.exp(-0.5 * ((h - 18) / 1.2) ** 2)
        base = 0.2
        return base + 0.8 * max(morning, evening)

    def generate_tick(self, tick: int) -> list[dict[str, Any]]:
        """Generate a batch of live events for one tick."""
        tf = self._time_factor()
        events = []

        # Pick 4 random junctions to update each tick
        for j in random.sample(JUNCTIONS, min(4, len(JUNCTIONS))):
            jid = j["id"]

            # Traffic update
            directions = ["N", "S", "E", "W"]
            flows = []
            for d in directions:
                count = max(0, int(random.gauss(tf * 35, 8)))
                flows.append({
                    "direction": d,
                    "vehicle_count": count,
                    "avg_speed_kmh": round(random.uniform(10, 45) * (1 - tf * 0.4), 1),
                    "queue_length_m": round(count * random.uniform(5, 8), 1),
                    "vehicle_types": {
                        "car": int(count * 0.6),
                        "two_wheeler": int(count * 0.25),
                        "bus": int(count * 0.08),
                        "auto": int(count * 0.07),
                    }
                })

            total = sum(f["vehicle_count"] for f in flows)
            events.append({
                "event_type": "traffic_update",
                "payload": {
                    "junction_id": jid,
                    "junction_name": j["name"],
                    "lat": j["lat"],
                    "lng": j["lng"],
                    "flows": flows,
                    "total_vehicles": total,
                    "congestion_level": round(min(total / 180.0, 1.0), 2),
                },
                "timestamp": datetime.utcnow().isoformat(),
            })

            # Signal change (every 3rd tick per junction)
            if tick % 3 == jid % 3:
                ns = sum(f["vehicle_count"] for f in flows if f["direction"] in ["N", "S"])
                ew = sum(f["vehicle_count"] for f in flows if f["direction"] in ["E", "W"])
                phase = 0 if ns >= ew else 2
                duration = min(max(int(max(ns, ew) * 0.7), 10), 60)
                events.append({
                    "event_type": "signal_change",
                    "payload": {
                        "junction_id": jid,
                        "phase": phase,
                        "phase_name": "NS_GREEN" if phase == 0 else "EW_GREEN",
                        "duration_seconds": duration,
                        "decided_by": "dqn",
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                })

        # Rare emergency event (~2% chance per tick)
        if random.random() < 0.02:
            j = random.choice(JUNCTIONS)
            vtype = random.choice(["ambulance", "fire_truck", "police"])
            events.append({
                "event_type": "emergency",
                "payload": {
                    "junction_id": j["id"],
                    "junction_name": j["name"],
                    "vehicle_type": vtype,
                    "direction": random.choice(["N", "S", "E", "W"]),
                    "corridor_opened": True,
                    "estimated_time_saved_seconds": random.randint(60, 180),
                },
                "timestamp": datetime.utcnow().isoformat(),
            })

        # Aggregated stats every 5 ticks
        if tick % 5 == 0:
            events.append({
                "event_type": "stats",
                "payload": {
                    "avg_wait_time_min": round(random.gauss(8.4, 0.5), 1),
                    "total_vehicles_today": 12000 + tick * 4,
                    "active_junctions": 16,
                    "avg_congestion": round(tf * 0.7, 2),
                    "co2_saved_kg": round((12000 + tick * 4) * 0.004, 1),
                    "emergencies_resolved_today": random.randint(2, 8),
                },
                "timestamp": datetime.utcnow().isoformat(),
            })

        return events
