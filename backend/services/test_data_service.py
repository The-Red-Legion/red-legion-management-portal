"""Test data generation service for creating mock events and participants."""

import random
import string
import uuid
import asyncpg
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TestDataService:
    """Service for creating test events and mock data."""

    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool

    def get_valid_event_types(self) -> List[str]:
        """Get list of valid event types."""
        return ["mining", "salvage", "combat", "exploration", "trading", "social"]

    def generate_event_id(self) -> str:
        """Generate event ID matching pattern used by payroll system: sm-[a-z0-9]{6}"""
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return f"sm-{suffix}"

    async def generate_fake_participants(self, count: int) -> List[Dict[str, Any]]:
        """Generate fake participant data for testing."""
        fake_usernames = [
            "MinerAlpha", "SalvageKing", "RedLegionPilot", "SpaceRanger", "StarCollector",
            "OreMaster", "QuantumMiner", "AsteroidHunter", "CrystalSeeker", "VoidRunner",
            "DeepSpaceMiner", "StellarSalvage", "GalaxyHarvester", "NebulaNavigator",
            "CosmicCrawler", "PlanetaryProspector", "InterstellarMiner", "SpacePirate",
            "RockHound", "CrystalCrafter", "MetalHarvester", "ElementExtractor",
            "QuantumScavenger", "AsteroidAce", "SystemScanner", "ResourceRaider"
        ]

        fake_display_names = [
            "Alpha Miner", "The Salvage King", "Red Legion Elite", "Space Ranger X",
            "Crystal Collector", "Ore Master Pro", "Quantum Explorer", "Asteroid Hunter",
            "Crystal Seeker", "Void Runner", "Deep Space Miner", "Stellar Salvage",
            "Galaxy Harvester", "Nebula Navigator", "Cosmic Crawler", "Planetary Prospector",
            "Interstellar Miner", "Space Pirate", "Rock Hound", "Crystal Crafter"
        ]

        participants = []
        used_names = set()

        for i in range(count):
            # Ensure unique usernames
            username = random.choice(fake_usernames)
            counter = 1
            original_username = username
            while username in used_names:
                username = f"{original_username}{counter}"
                counter += 1
            used_names.add(username)

            display_name = random.choice(fake_display_names)
            user_id = random.randint(100000000000000000, 999999999999999999)

            participants.append({
                'user_id': user_id,
                'username': username,
                'display_name': display_name
            })

        return participants

    def get_test_organizers(self) -> List[str]:
        """Get list of test organizer names."""
        return [
            "NewSticks", "Saladin80", "Tealstone", "LowNslow", "Ferny133",
            "Jaeger31", "Blitz0117", "Prometheus114", "RockHound", "CrystalCrafter",
            "VoidRunner", "AsteroidAce", "QuantumMiner", "StellarSalvage",
            "SpaceRanger", "CosmicCrawler", "MetalHarvester", "SystemScanner",
            "FleetCommander", "WingLeader", "TradeCaptain", "ExplorerOne",
            "CombatVet", "CargoHauler", "RouteRunner", "DeepSpaceScout"
        ]

    async def create_test_event(self, event_type: str) -> Dict[str, Any]:
        """Create a test event with random participants and data."""
        valid_event_types = self.get_valid_event_types()
        if event_type not in valid_event_types:
            raise ValueError(f"Event type must be one of: {', '.join(valid_event_types)}")

        try:
            if self.db_pool is None:
                # Return mock success response when database is not available
                event_id = f'test_{uuid.uuid4().hex[:8]}'
                num_participants = random.randint(5, 25)
                duration_hours = random.randint(1, 7)
                event_name = f'Test {event_type.title()} Op {random.randint(100, 999)}'

                return {
                    'success': True,
                    'message': f'Test {event_type} event created successfully (mock mode)',
                    'event': {
                        'event_id': event_id,
                        'event_name': event_name,
                        'event_type': event_type,
                        'organizer_name': 'TestBot',
                        'participants': num_participants,
                        'duration_hours': duration_hours,
                        'status': 'completed'
                    }
                }

            async with self.db_pool.acquire() as conn:
                async with conn.transaction():
                    # Generate random event data
                    event_id = self.generate_event_id()
                    num_participants = random.randint(5, 25)
                    duration_hours = random.randint(1, 7)
                    duration_minutes = duration_hours * 60

                    # Random start time between 1-30 days ago
                    days_ago = random.randint(1, 30)
                    started_at = datetime.utcnow() - timedelta(days=days_ago)
                    ended_at = started_at + timedelta(hours=duration_hours)

                    event_name = f"Test {event_type.title()} Op {random.randint(100, 999)}"

                    # Generate realistic organizer data
                    test_organizers = self.get_test_organizers()
                    organizer_name = random.choice(test_organizers)
                    organizer_id = random.randint(100000000000000000, 999999999999999999)

                    # Create the event
                    await conn.execute("""
                        INSERT INTO events (
                            event_id, event_type, event_name, organizer_name, organizer_id,
                            guild_id, started_at, ended_at, status, total_participants,
                            total_duration_minutes, created_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    """,
                        event_id, event_type, event_name, organizer_name, organizer_id,
                        814699481912049704, started_at, ended_at, 'closed', num_participants,
                        duration_minutes, datetime.utcnow()
                    )

                    # Generate random participants
                    fake_users = await self.generate_fake_participants(num_participants)
                    total_participation_time = 0

                    for user in fake_users:
                        # Random participation time (15-240 minutes)
                        participation_minutes = random.randint(15, min(240, duration_minutes))
                        total_participation_time += participation_minutes

                        # Random join time within event duration
                        max_join_offset = max(1, duration_minutes - participation_minutes)
                        join_offset = random.randint(0, max_join_offset)
                        joined_at = started_at + timedelta(minutes=join_offset)
                        left_at = joined_at + timedelta(minutes=participation_minutes)

                        await conn.execute("""
                            INSERT INTO participation (
                                event_id, user_id, username, display_name, joined_at, left_at,
                                was_active, duration_minutes, created_at
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        """,
                            event_id, user['user_id'], user['username'], user['display_name'],
                            joined_at, left_at, True, participation_minutes, datetime.utcnow()
                        )

                    # Update event totals
                    await conn.execute("""
                        UPDATE events
                        SET total_participants = $1, total_duration_minutes = $2
                        WHERE event_id = $3
                    """, num_participants, total_participation_time, event_id)

                    logger.info(f"Created test {event_type} event {event_id} with {num_participants} participants")

                    # Return event details
                    event_data = await conn.fetchrow("""
                        SELECT * FROM events WHERE event_id = $1
                    """, event_id)

                    return {
                        "success": True,
                        "message": f"Test {event_type} event created successfully",
                        "event": dict(event_data)
                    }

        except Exception as e:
            logger.error(f"Error creating test {event_type} event: {e}")
            raise

    def generate_mock_payroll_calculation(self, event_id: str, ore_quantities: Dict[str, Any],
                                         custom_prices: Dict[str, float] = None,
                                         donating_users: List[str] = None) -> Dict[str, Any]:
        """Generate mock payroll calculation for testing donations."""
        # Mock event and participants data
        mock_participants = [
            {"user_id": 123456789, "username": "TestMiner1", "display_name": "Test Miner One",
             "duration_minutes": 120, "is_org_member": True},
            {"user_id": 987654321, "username": "TestMiner2", "display_name": "Test Miner Two",
             "duration_minutes": 90, "is_org_member": True},
            {"user_id": 555666777, "username": "TestMiner3", "display_name": "Test Miner Three",
             "duration_minutes": 60, "is_org_member": True},
            {"user_id": 111222333, "username": "TestMiner4", "display_name": "Test Miner Four",
             "duration_minutes": 180, "is_org_member": True},
        ]

        # Calculate ore values
        default_prices = {
            'QUANTAINIUM': 275500.0,
            'BEXALITE': 10750.0,
            'TARANITE': 8750.0,
            'AGRICIUM': 44250.0,
        }

        total_ore_value = 0
        ore_breakdown = {}

        for ore_name, quantity in ore_quantities.items():
            ore_upper = ore_name.upper()
            if custom_prices and ore_upper in custom_prices:
                price_per_scu = custom_prices[ore_upper]
            else:
                price_per_scu = default_prices.get(ore_upper, 10000.0)  # Default fallback

            ore_value = quantity * price_per_scu
            total_ore_value += ore_value
            ore_breakdown[ore_upper] = {
                "quantity": quantity,
                "price_per_scu": price_per_scu,
                "total_value": ore_value
            }

        # Calculate payroll
        total_participation_time = sum(p["duration_minutes"] for p in mock_participants)

        payroll_data = []
        for participant in mock_participants:
            user_id_str = str(participant["user_id"])
            is_donating = donating_users and user_id_str in donating_users

            if is_donating:
                payout = 0.0
            else:
                # Calculate payout based on participation time ratio
                time_ratio = participant["duration_minutes"] / total_participation_time
                payout = total_ore_value * time_ratio

            payroll_data.append({
                "user_id": user_id_str,
                "username": participant["username"],
                "display_name": participant["display_name"],
                "duration_minutes": participant["duration_minutes"],
                "payout": round(payout, 2),
                "is_donating": is_donating
            })

        return {
            "success": True,
            "event_id": event_id,
            "event_name": f"Test Mining Event {event_id}",
            "organizer": "TestBot",
            "total_participants": len(mock_participants),
            "total_participation_time": total_participation_time,
            "total_ore_value": total_ore_value,
            "total_payout": sum(p["payout"] for p in payroll_data),
            "participants": payroll_data,
            "ore_breakdown": ore_breakdown,
            "donating_users": donating_users or []
        }