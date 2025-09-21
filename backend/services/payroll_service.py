"""Payroll calculation and management service."""

import asyncpg
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class PayrollService:
    """Service for managing payroll calculations and operations."""

    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool

    async def calculate_payroll(self, event_id: str, ore_quantities: Dict[str, Any],
                               custom_prices: Optional[Dict[str, float]] = None,
                               donating_users: Optional[List[str]] = None) -> Dict[str, Any]:
        """Calculate payroll for an event."""
        try:
            async with self.db_pool.acquire() as conn:
                # Get event details
                event = await conn.fetchrow("""
                    SELECT event_id, event_name, organizer_name, total_participants,
                           total_duration_minutes, status
                    FROM events WHERE event_id = $1
                """, event_id)

                if not event:
                    raise ValueError(f"Event {event_id} not found")

                # Get participants
                participants = await conn.fetch("""
                    SELECT DISTINCT ON (user_id)
                        user_id, username, display_name, duration_minutes, is_org_member
                    FROM participation
                    WHERE event_id = $1 AND duration_minutes > 0
                    ORDER BY user_id, joined_at DESC
                """, event_id)

                if not participants:
                    return {
                        "success": False,
                        "error": "No participants found for this event",
                        "participants": []
                    }

                # Calculate total ore value using actual quantities and prices
                total_ore_value = 0
                if ore_quantities and custom_prices:
                    for material, quantity in ore_quantities.items():
                        if material in custom_prices and quantity > 0:
                            total_ore_value += quantity * custom_prices[material]

                logger.info(f"🔍 Debug - Total ore value: {total_ore_value}")
                logger.info(f"🔍 Debug - Donating users received: {donating_users}")

                # Step 1: Calculate each participant's base share (based on time)
                total_duration = sum(p['duration_minutes'] for p in participants)

                base_shares = {}
                for participant in participants:
                    if total_duration > 0:
                        time_ratio = participant['duration_minutes'] / total_duration
                        base_shares[str(participant['user_id'])] = total_ore_value * time_ratio
                    else:
                        base_shares[str(participant['user_id'])] = 0

                # Step 2: Identify donating users and collect their shares
                donating_share_total = 0
                non_donating_users = []

                for participant in participants:
                    user_id_str = str(participant['user_id'])
                    username = participant['username']
                    is_donating = bool(donating_users and username in donating_users)

                    if is_donating:
                        donating_share_total += base_shares[user_id_str]
                        logger.info(f"🔍 Debug - {username} is donating share: {base_shares[user_id_str]}")
                    else:
                        non_donating_users.append(user_id_str)

                logger.info(f"🔍 Debug - Total donating share to redistribute: {donating_share_total}")
                logger.info(f"🔍 Debug - Non-donating users: {len(non_donating_users)}")

                # Step 3: Redistribute donating shares among non-donating users (proportionally)
                if non_donating_users and donating_share_total > 0:
                    non_donating_duration = sum(p['duration_minutes'] for p in participants
                                               if str(p['user_id']) in non_donating_users)

                    for user_id_str in non_donating_users:
                        participant = next(p for p in participants if str(p['user_id']) == user_id_str)
                        if non_donating_duration > 0:
                            redistribution_ratio = participant['duration_minutes'] / non_donating_duration
                            base_shares[user_id_str] += donating_share_total * redistribution_ratio

                # Step 4: Build final payroll data
                payroll_data = []
                for participant in participants:
                    user_id_str = str(participant['user_id'])
                    username = participant['username']
                    is_donating = bool(donating_users and username in donating_users)

                    if is_donating:
                        payout = 0.0  # Donating users get 0
                    else:
                        payout = base_shares[user_id_str]  # Non-donating users get their share + redistributed amount

                    logger.info(f"🔍 Debug - Final payout for {username}: {payout} (donating: {is_donating})")

                    payroll_data.append({
                        "user_id": user_id_str,
                        "username": username,
                        "display_name": participant['display_name'],
                        "duration_minutes": participant['duration_minutes'],
                        "payout": round(payout),  # Round to whole numbers as requested
                        "is_donating": is_donating
                    })

                # Total payout distributed (should equal total_ore_value)
                total_payout = sum(p['payout'] for p in payroll_data)
                logger.info(f"🔍 Debug - Total payout distributed: {total_payout} (should equal {total_ore_value})")

                return {
                    "success": True,
                    "event_id": event_id,
                    "event_name": event['event_name'],
                    "organizer": event['organizer_name'],
                    "total_participants": len(participants),
                    "total_duration_minutes": total_duration,
                    "total_ore_value": total_ore_value,
                    "total_payout": total_payout,
                    "total_value_auec": total_ore_value,  # For frontend compatibility
                    "participants": payroll_data,
                    "ore_quantities": ore_quantities,
                    "custom_prices": custom_prices or {},
                    "donating_users": donating_users or []
                }

        except Exception as e:
            logger.error(f"Error calculating payroll for {event_id}: {e}")
            raise

    async def finalize_payroll(self, event_id: str, ore_quantities: Dict[str, Any],
                              custom_prices: Optional[Dict[str, float]] = None,
                              donating_users: Optional[List[str]] = None) -> Dict[str, Any]:
        """Finalize payroll calculations and create payroll record."""
        try:
            # First calculate the payroll
            calculation = await self.calculate_payroll(event_id, ore_quantities, custom_prices, donating_users)

            if not calculation["success"]:
                return calculation

            async with self.db_pool.acquire() as conn:
                # Create or update payroll session
                payroll_id = f"pr-{event_id}"

                # Create payroll record using bot schema
                await conn.execute("""
                    INSERT INTO payrolls (
                        payroll_id, event_id, total_scu_collected, total_value_auec,
                        ore_prices_used, mining_yields, calculated_by_id, calculated_by_name
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (payroll_id) DO UPDATE SET
                        total_scu_collected = EXCLUDED.total_scu_collected,
                        total_value_auec = EXCLUDED.total_value_auec,
                        ore_prices_used = EXCLUDED.ore_prices_used,
                        mining_yields = EXCLUDED.mining_yields
                """, payroll_id, event_id,
                    sum(ore_quantities.values()) if ore_quantities else 0,  # total_scu_collected
                    calculation["total_payout"],  # total_value_auec
                    json.dumps(custom_prices or {}),  # ore_prices_used
                    json.dumps(ore_quantities or {}),  # mining_yields
                    0,  # calculated_by_id (placeholder)
                    "Management Portal"  # calculated_by_name
                )

                # Delete existing payout records for this payroll (in case of re-calculation)
                await conn.execute("DELETE FROM payouts WHERE payroll_id = $1", payroll_id)

                # Create individual payout records
                for participant in calculation["participants"]:
                    await conn.execute("""
                        INSERT INTO payouts (
                            payroll_id, user_id, username, participation_minutes,
                            base_payout_auec, final_payout_auec, is_donor
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """, payroll_id, int(participant["user_id"]), participant["username"],
                        participant["duration_minutes"], participant["payout"],
                        participant["payout"], participant["is_donating"])

                return {
                    "success": True,
                    "payroll_id": payroll_id,
                    "message": "Payroll finalized successfully",
                    **calculation
                }

        except Exception as e:
            logger.error(f"Error finalizing payroll for {event_id}: {e}")
            raise

    async def get_payroll_summary(self, event_id: str) -> Dict[str, Any]:
        """Get payroll summary for an event."""
        try:
            async with self.db_pool.acquire() as conn:
                # Get event details
                event = await conn.fetchrow("""
                    SELECT event_id, event_name, organizer_name, status, ended_at,
                           total_participants, total_duration_minutes
                    FROM events WHERE event_id = $1
                """, event_id)

                if not event:
                    raise ValueError(f"Event {event_id} not found")

                # Get payroll if exists
                payroll = await conn.fetchrow("""
                    SELECT payroll_id, total_value_auec, calculated_at
                    FROM payrolls WHERE event_id = $1
                """, event_id)

                # Get participants count
                participant_count = await conn.fetchval("""
                    SELECT COUNT(DISTINCT user_id) FROM participation WHERE event_id = $1
                """, event_id)

                return {
                    "event_id": event_id,
                    "event_name": event['event_name'],
                    "organizer": event['organizer_name'],
                    "event_status": event['status'],
                    "ended_at": event['ended_at'].isoformat() if event['ended_at'] else None,
                    "total_participants": participant_count or 0,
                    "total_duration_minutes": event['total_duration_minutes'] or 0,
                    "payroll_status": "finalized" if payroll else "not_created",
                    "payroll_id": payroll['payroll_id'] if payroll else None,
                    "total_payout": float(payroll['total_value_auec']) if payroll else 0.0,
                    "payroll_created_at": payroll['calculated_at'].isoformat() if payroll else None,
                    "payroll_updated_at": payroll['calculated_at'].isoformat() if payroll else None
                }

        except Exception as e:
            logger.error(f"Error getting payroll summary for {event_id}: {e}")
            raise

    async def export_payroll(self, event_id: str) -> Dict[str, Any]:
        """Export payroll data for an event."""
        try:
            async with self.db_pool.acquire() as conn:
                # Get payroll record using bot schema
                payroll = await conn.fetchrow("""
                    SELECT payroll_id, total_value_auec, ore_prices_used,
                           mining_yields, calculated_at
                    FROM payrolls WHERE event_id = $1
                """, event_id)

                if not payroll:
                    return {"success": False, "error": "No payroll found for this event"}

                # Get payout records from the payouts table
                payouts = await conn.fetch("""
                    SELECT user_id, username, participation_minutes,
                           final_payout_auec, is_donor
                    FROM payouts WHERE payroll_id = $1
                    ORDER BY final_payout_auec DESC
                """, payroll['payroll_id'])

                # Get additional participant data from participation table
                participants = await conn.fetch("""
                    SELECT DISTINCT ON (user_id)
                        user_id, username, display_name, duration_minutes, is_org_member
                    FROM participation
                    WHERE event_id = $1 AND duration_minutes > 0
                    ORDER BY user_id, joined_at DESC
                """, event_id)

                # Create lookup for display names
                participant_lookup = {p['username']: p for p in participants}

                participant_data = []
                for payout in payouts:
                    participant = participant_lookup.get(payout['username'], {})

                    participant_data.append({
                        "user_id": str(payout['user_id']),
                        "username": payout['username'],
                        "display_name": participant.get('display_name', payout['username']),
                        "duration_minutes": payout['participation_minutes'],
                        "payout": float(payout['final_payout_auec']),
                        "is_donating": payout['is_donor']
                    })

                return {
                    "success": True,
                    "payroll_id": payroll['payroll_id'],
                    "event_id": event_id,
                    "total_payout": float(payroll['total_value_auec']),
                    "participants": participant_data,
                    "created_at": payroll['calculated_at'].isoformat(),
                    "ore_quantities": json.loads(payroll['mining_yields'] or '{}'),
                    "custom_prices": json.loads(payroll['ore_prices_used'] or '{}')
                }

        except Exception as e:
            logger.error(f"Error exporting payroll for {event_id}: {e}")
            raise