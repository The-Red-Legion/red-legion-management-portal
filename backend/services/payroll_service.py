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
                    is_donating = donating_users and username in donating_users

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
                    is_donating = donating_users and username in donating_users

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

                await conn.execute("""
                    INSERT INTO payroll_sessions (
                        payroll_id, event_id, status, total_payout, ore_quantities,
                        custom_prices, donating_users, created_at, updated_at
                    ) VALUES ($1, $2, 'finalized', $3, $4, $5, $6, NOW(), NOW())
                    ON CONFLICT (payroll_id) DO UPDATE SET
                        status = 'finalized',
                        total_payout = EXCLUDED.total_payout,
                        ore_quantities = EXCLUDED.ore_quantities,
                        custom_prices = EXCLUDED.custom_prices,
                        donating_users = EXCLUDED.donating_users,
                        updated_at = NOW()
                """, payroll_id, event_id, calculation["total_payout"],
                    json.dumps(ore_quantities), json.dumps(custom_prices or {}),
                    json.dumps(donating_users or []))

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

                # Get payroll session if exists
                payroll = await conn.fetchrow("""
                    SELECT payroll_id, status, total_payout, created_at, updated_at
                    FROM payroll_sessions WHERE event_id = $1
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
                    "payroll_status": payroll['status'] if payroll else "not_created",
                    "payroll_id": payroll['payroll_id'] if payroll else None,
                    "total_payout": float(payroll['total_payout']) if payroll else 0.0,
                    "payroll_created_at": payroll['created_at'].isoformat() if payroll else None,
                    "payroll_updated_at": payroll['updated_at'].isoformat() if payroll else None
                }

        except Exception as e:
            logger.error(f"Error getting payroll summary for {event_id}: {e}")
            raise

    async def export_payroll(self, event_id: str) -> Dict[str, Any]:
        """Export payroll data for an event."""
        try:
            async with self.db_pool.acquire() as conn:
                # Get payroll session
                payroll = await conn.fetchrow("""
                    SELECT payroll_id, status, total_payout, ore_quantities,
                           custom_prices, donating_users, created_at
                    FROM payroll_sessions WHERE event_id = $1
                """, event_id)

                if not payroll:
                    return {"success": False, "error": "No payroll found for this event"}

                # Get participants with payroll data
                participants = await conn.fetch("""
                    SELECT p.user_id, p.username, p.display_name, p.duration_minutes,
                           p.is_org_member
                    FROM participation p
                    WHERE p.event_id = $1 AND p.duration_minutes > 0
                    ORDER BY p.duration_minutes DESC
                """, event_id)

                # Calculate individual payouts (simplified)
                total_duration = sum(p['duration_minutes'] for p in participants)
                base_rate = 1000
                donating_users = json.loads(payroll['donating_users'] or '[]')

                participant_data = []
                for p in participants:
                    is_donating = str(p['user_id']) in donating_users
                    payout = 0.0 if is_donating else base_rate * p['duration_minutes']

                    participant_data.append({
                        "user_id": str(p['user_id']),
                        "username": p['username'],
                        "display_name": p['display_name'],
                        "duration_minutes": p['duration_minutes'],
                        "payout": payout,
                        "is_donating": is_donating
                    })

                return {
                    "success": True,
                    "payroll_id": payroll['payroll_id'],
                    "event_id": event_id,
                    "status": payroll['status'],
                    "total_payout": float(payroll['total_payout']),
                    "participants": participant_data,
                    "created_at": payroll['created_at'].isoformat(),
                    "ore_quantities": json.loads(payroll['ore_quantities'] or '{}'),
                    "custom_prices": json.loads(payroll['custom_prices'] or '{}')
                }

        except Exception as e:
            logger.error(f"Error exporting payroll for {event_id}: {e}")
            raise