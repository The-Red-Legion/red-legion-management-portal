"""Payroll calculation and management endpoints."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from typing import Dict, List, Optional, Any
import logging
import json
import io
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

from database import get_db_pool
from validation import validate_event_id, PayrollCalculateRequest
from services.payroll_service import PayrollService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/payroll/{event_id}/calculate")
@router.post("/mgmt/api/payroll/{event_id}/calculate")
async def calculate_payroll_endpoint(event_id: str, request: PayrollCalculateRequest):
    """Calculate payroll for a mining event using ore quantities and custom prices."""
    event_id = validate_event_id(event_id)

    try:
        pool = await get_db_pool()
        if pool is None:
            # Generate mock payroll calculation for testing
            return generate_mock_payroll_calculation(event_id, request)

        payroll_service = PayrollService(pool)
        result = await payroll_service.calculate_payroll(
            event_id,
            request.ore_quantities,
            request.custom_prices,
            request.donating_users
        )

        return result

    except Exception as e:
        logger.error(f"Error calculating payroll for {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Payroll calculation failed: {str(e)}")

@router.post("/payroll/{event_id}/finalize")
@router.post("/mgmt/api/payroll/{event_id}/finalize")
async def finalize_payroll_endpoint(event_id: str, request: PayrollCalculateRequest):
    """Finalize payroll calculations and save to database."""
    event_id = validate_event_id(event_id)

    try:
        pool = await get_db_pool()
        if pool is None:
            return {
                "success": True,
                "message": f"Payroll for event {event_id} finalized successfully (mock mode)",
                "payroll_id": f"pr-{event_id}",
                "total_payout": 25000000.0
            }

        payroll_service = PayrollService(pool)
        result = await payroll_service.finalize_payroll(
            event_id,
            request.ore_quantities,
            request.custom_prices,
            request.donating_users
        )

        return result

    except Exception as e:
        logger.error(f"Error finalizing payroll for {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Payroll finalization failed: {str(e)}")

@router.get("/payroll/{event_id}/export")
@router.get("/mgmt/api/payroll/{event_id}/export")
async def export_payroll_endpoint(event_id: str):
    """Export payroll data for an event."""
    event_id = validate_event_id(event_id)

    try:
        pool = await get_db_pool()
        if pool is None:
            return {
                "success": False,
                "error": "Database not available - payroll export not possible in mock mode"
            }

        payroll_service = PayrollService(pool)
        result = await payroll_service.export_payroll(event_id)

        return result

    except Exception as e:
        logger.error(f"Error exporting payroll for {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Payroll export failed: {str(e)}")

@router.get("/payroll/{event_id}/summary")
@router.get("/mgmt/api/payroll/{event_id}/summary")
async def get_payroll_summary_endpoint(event_id: str):
    """Get payroll summary for an event."""
    event_id = validate_event_id(event_id)

    try:
        pool = await get_db_pool()
        if pool is None:
            return {
                "event_id": event_id,
                "event_name": f"Mock Event {event_id}",
                "organizer": "MockUser",
                "event_status": "closed",
                "total_participants": 5,
                "total_duration_minutes": 240,
                "payroll_status": "not_created",
                "payroll_id": None,
                "total_payout": 0.0
            }

        payroll_service = PayrollService(pool)
        result = await payroll_service.get_payroll_summary(event_id)

        return result

    except Exception as e:
        logger.error(f"Error getting payroll summary for {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get payroll summary: {str(e)}")

@router.get("/payroll/{event_id}/pdf")
@router.get("/mgmt/api/payroll/{event_id}/pdf")
async def generate_payroll_pdf(event_id: str):
    """Generate PDF report for payroll data."""
    event_id = validate_event_id(event_id)

    try:
        pool = await get_db_pool()
        if pool is None:
            raise HTTPException(status_code=503, detail="Database not available")

        payroll_service = PayrollService(pool)
        data = await payroll_service.export_payroll(event_id)

        if not data["success"]:
            raise HTTPException(status_code=404, detail=data.get("error", "Payroll not found"))

        # Create PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                              topMargin=0.5*inch, bottomMargin=0.5*inch,
                              leftMargin=0.5*inch, rightMargin=0.5*inch)

        # Build PDF content
        story = []
        styles = getSampleStyleSheet()

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            spaceAfter=30,
            textColor=colors.black,
            alignment=1  # Center alignment
        )
        story.append(Paragraph(f"Payroll Summary - Event {event_id}", title_style))
        story.append(Spacer(1, 20))

        # Event info section
        info_data = [
            ['Event ID:', data['event_id']],
            ['Payroll ID:', data['payroll_id']],
            ['Total Participants:', str(len(data['participants']))],
            ['Total Payout:', f"{data['total_payout']:,.0f} aUEC"],
            ['Created:', data['created_at'][:10]]  # Just date part
        ]

        info_table = Table(info_data, colWidths=[2*inch, 3*inch])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 30))

        # Ore breakdown section (if available)
        if data.get('ore_quantities') and any(qty > 0 for qty in data['ore_quantities'].values()):
            story.append(Paragraph("Ore Breakdown", styles['Heading2']))
            story.append(Spacer(1, 12))

            ore_data = [['Ore Type', 'Quantity (SCU)', 'Price per Unit', 'Total Value']]
            for ore, quantity in data['ore_quantities'].items():
                if quantity > 0:
                    price = data.get('custom_prices', {}).get(ore, 0)
                    total_value = quantity * price
                    ore_data.append([
                        ore.upper(),
                        f"{quantity:,.0f}",
                        f"{price:,.0f} aUEC",
                        f"{total_value:,.0f} aUEC"
                    ])

            ore_table = Table(ore_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
            ore_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(ore_table)
            story.append(Spacer(1, 30))

        # Participants section
        story.append(Paragraph("Individual Payouts", styles['Heading2']))
        story.append(Spacer(1, 12))

        # Participants table
        participants_data = [['#', 'Participant', 'Time (min)', 'Payout (aUEC)', 'Status']]
        for i, participant in enumerate(data['participants'], 1):
            status = "Donor" if participant.get('is_donating', False) else "Standard"
            participants_data.append([
                str(i),
                participant.get('display_name', participant['username']),
                str(participant['duration_minutes']),
                f"{participant['payout']:,.0f}",
                status
            ])

        participants_table = Table(participants_data, colWidths=[0.5*inch, 2*inch, 1*inch, 1.5*inch, 1*inch])
        participants_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(participants_table)

        # Build PDF
        doc.build(story)
        buffer.seek(0)

        # Return PDF as response
        return Response(
            content=buffer.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=payroll_{event_id}.pdf"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating PDF for {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")

def generate_mock_payroll_calculation(event_id: str, request: PayrollCalculateRequest) -> Dict[str, Any]:
    """Generate mock payroll calculation for testing donations."""
    # Mock event and participants data
    mock_participants = [
        {"user_id": 123456789, "username": "TestMiner1", "display_name": "Test Miner One", "duration_minutes": 120, "is_org_member": True},
        {"user_id": 987654321, "username": "TestMiner2", "display_name": "Test Miner Two", "duration_minutes": 90, "is_org_member": True},
        {"user_id": 555666777, "username": "TestMiner3", "display_name": "Test Miner Three", "duration_minutes": 60, "is_org_member": True},
        {"user_id": 111222333, "username": "TestMiner4", "display_name": "Test Miner Four", "duration_minutes": 180, "is_org_member": True},
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

    for ore_name, quantity in request.ore_quantities.items():
        ore_upper = ore_name.upper()
        if request.custom_prices and ore_upper in request.custom_prices:
            price_per_scu = request.custom_prices[ore_upper]
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
        is_donating = request.donating_users and user_id_str in request.donating_users

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

    # Log the calculation details for debugging
    logger.info(f"💰 Mock payroll calculation for {event_id}:")
    logger.info(f"  - Total participants: {len(mock_participants)}")
    logger.info(f"  - Donating user IDs received: {request.donating_users}")
    logger.info(f"  - Total ore value: {total_ore_value:,.2f} aUEC")
    for p in payroll_data:
        logger.info(f"  - {p['username']} (ID: {p['user_id']}): {p['payout']:,.2f} aUEC, donating: {p['is_donating']}")

    # Apply donation redistribution
    if request.donating_users:
        total_donated = sum(p["payout"] for p in payroll_data if p["is_donating"])
        non_donating_participants = [p for p in payroll_data if not p["is_donating"]]

        if non_donating_participants and total_donated > 0:
            donation_per_person = total_donated / len(non_donating_participants)

            logger.info(f"🎁 Mock donation redistribution:")
            logger.info(f"  - Total donated: {total_donated:,.2f} aUEC")
            logger.info(f"  - Non-donating participants: {len(non_donating_participants)}")
            logger.info(f"  - Donation per person: {donation_per_person:,.2f} aUEC")

            for p in payroll_data:
                if p["is_donating"]:
                    logger.info(f"    - {p['username']}: 0 aUEC (donated)")
                    p["payout"] = 0.0
                else:
                    original_payout = p["payout"]
                    p["payout"] = original_payout + donation_per_person
                    logger.info(f"    + {p['username']}: {p['payout']:,.2f} aUEC (base: {original_payout:,.2f} + bonus: {donation_per_person:,.2f})")

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
        "donating_users": request.donating_users or []
    }