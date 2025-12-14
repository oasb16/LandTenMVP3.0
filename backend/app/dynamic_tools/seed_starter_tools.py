"""
Seed Starter Dynamic Tools

This script registers 3 essential diagnostic tools:
1. diagnose_water_leak - Intelligent plumbing diagnosis
2. estimate_hvac_repair - HVAC cost estimation
3. schedule_preventive_maintenance - Proactive maintenance scheduler

Run once to populate the dynamic tools system.

Usage:
    # From Heroku dyno:
    python -m backend.app.dynamic_tools.seed_starter_tools

    # Or use the standalone script:
    cd backend && python -c "from app.dynamic_tools.seed_starter_tools import seed_tools; seed_tools()"
"""
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

try:
    from backend.app.dynamic_tools.tool_runtime import get_dynamic_tool_runtime
except ImportError:
    # Fallback for relative import when run as module
    from .tool_runtime import get_dynamic_tool_runtime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_tools():
    """Register all starter tools"""

    runtime = get_dynamic_tool_runtime()

    # ==================== TOOL 1: Water Leak Diagnostic ====================
    water_leak_tool = """
def diagnose_water_leak(
    leak_location: str,
    water_color: str,
    flow_rate: str,
    odor: str = "none"
) -> dict:
    '''
    🚰 Intelligent Water Leak Diagnostic Tool

    Analyzes leak symptoms to determine severity, cause, and cost.

    Args:
        leak_location: Where the leak is (e.g., "kitchen sink", "bathroom ceiling", "basement")
        water_color: Color of water ("clear", "brown", "rusty", "black", "sewage")
        flow_rate: How fast water is leaking ("dripping", "steady stream", "gushing", "flooding")
        odor: Smell of water (default: "none", or "sewage", "musty", "chemical")

    Returns:
        dict with diagnosis, severity, estimated_cost, urgency, and recommendations
    '''

    # Initialize result
    result = {
        "diagnosis": "Unknown leak",
        "severity": "medium",
        "estimated_cost": "200-500",
        "urgency": "routine",
        "likely_cause": "",
        "recommendations": []
    }

    # 🚨 EMERGENCY: Sewage or black water
    if "sewage" in odor.lower() or water_color.lower() in ["black", "sewage"]:
        result.update({
            "diagnosis": "Sewage line breach or backup",
            "severity": "emergency",
            "estimated_cost": "800-2500",
            "urgency": "immediate",
            "likely_cause": "Main sewer line blockage or break",
            "recommendations": [
                "Evacuate area immediately (health hazard)",
                "Shut off water main",
                "Call emergency plumber within 1 hour",
                "Do not use any plumbing fixtures"
            ]
        })
        return result

    # 🚨 CRITICAL: Flooding or gushing water
    if flow_rate.lower() in ["gushing", "flooding"]:
        result.update({
            "diagnosis": "Major pipe burst or valve failure",
            "severity": "critical",
            "estimated_cost": "500-1500",
            "urgency": "immediate",
            "likely_cause": "Burst pipe or failed shut-off valve",
            "recommendations": [
                "Shut off water main immediately",
                "Call plumber within 2 hours",
                "Move valuables away from water damage area",
                "Document damage with photos for insurance"
            ]
        })
        return result

    # ⚠️ HIGH: Brown or rusty water (pipe corrosion)
    if water_color.lower() in ["brown", "rusty"]:
        result.update({
            "diagnosis": "Pipe corrosion or sediment buildup",
            "severity": "high",
            "estimated_cost": "400-1200",
            "urgency": "urgent",
            "likely_cause": "Old pipes corroding from inside",
            "recommendations": [
                "Schedule plumber within 24-48 hours",
                "Avoid drinking tap water",
                "Consider pipe replacement (not just repair)",
                "Check for other corroded pipes"
            ]
        })
        return result

    # 📍 Location-based diagnosis
    if "ceiling" in leak_location.lower():
        result.update({
            "diagnosis": "Leak from above (bathroom or roof)",
            "severity": "high",
            "estimated_cost": "300-800",
            "urgency": "urgent",
            "likely_cause": "Toilet wax ring, shower pan, or roof leak",
            "recommendations": [
                "Check upstairs bathroom fixtures",
                "Inspect attic for roof leaks",
                "Schedule plumber within 48 hours",
                "Monitor for mold growth"
            ]
        })
    elif "basement" in leak_location.lower():
        result.update({
            "diagnosis": "Foundation leak or sump pump failure",
            "severity": "medium",
            "estimated_cost": "250-900",
            "urgency": "routine",
            "likely_cause": "Foundation crack or failed sump pump",
            "recommendations": [
                "Check sump pump operation",
                "Inspect foundation for cracks",
                "Monitor during next rainfall",
                "Schedule waterproofing inspection"
            ]
        })

    # 💧 Flow rate adjustments
    if flow_rate.lower() == "dripping":
        result["estimated_cost"] = "150-350"
        result["urgency"] = "routine"
        result["recommendations"].append("Can wait 3-5 days for repair")
    elif flow_rate.lower() == "steady stream":
        result["estimated_cost"] = "300-700"
        result["urgency"] = "urgent"
        result["recommendations"].append("Schedule repair within 24-48 hours")

    return result
"""

    result1 = runtime.register_tool(
        tool_name="diagnose_water_leak",
        code=water_leak_tool,
        description="🚰 Intelligent water leak diagnostic - analyzes symptoms to determine severity, cause, and cost",
        category="plumbing"
    )
    logger.info(f"✅ Tool 1 registered: {result1}")


    # ==================== TOOL 2: HVAC Repair Estimator ====================
    hvac_tool = """
def estimate_hvac_repair(
    age_years: int,
    symptom: str,
    last_service_months_ago: int,
    season: str = "summer"
) -> dict:
    '''
    🌡️ HVAC Repair Cost Estimator

    Estimates repair cost based on age, symptoms, and maintenance history.

    Args:
        age_years: Age of HVAC unit in years
        symptom: Main problem ("not cooling", "not heating", "strange noise", "high bills", "no power")
        last_service_months_ago: Months since last professional service
        season: Current season (default: "summer", or "winter", "spring", "fall")

    Returns:
        dict with estimated_cost, likely_issue, urgency, and recommendations
    '''

    result = {
        "estimated_cost": "200-400",
        "likely_issue": "Unknown",
        "urgency": "routine",
        "recommendations": [],
        "replace_vs_repair": "repair"
    }

    # 🔴 OLD UNIT: Likely replacement needed
    if age_years > 15:
        result.update({
            "estimated_cost": "3500-7000",
            "likely_issue": "Unit beyond economical repair (>15 years old)",
            "urgency": "plan_replacement",
            "replace_vs_repair": "replace",
            "recommendations": [
                "Recommend full replacement vs repair",
                "Old unit is inefficient (wasting 30-40% on energy)",
                "Modern units have 10-year warranty",
                "Calculate ROI: $200/mo savings × 12 mo = $2400/yr"
            ]
        })
        return result

    # 🔶 AGING UNIT: Repair but monitor
    if age_years > 10:
        base_cost_multiplier = 1.5  # Older units cost more to repair
    else:
        base_cost_multiplier = 1.0

    # 🔧 SYMPTOM-BASED DIAGNOSIS
    symptom_lower = symptom.lower()

    if "not cooling" in symptom_lower:
        if season.lower() == "summer":
            urgency = "urgent"  # Summer cooling failure = emergency
        else:
            urgency = "routine"

        result.update({
            "estimated_cost": f"{int(300 * base_cost_multiplier)}-{int(800 * base_cost_multiplier)}",
            "likely_issue": "Refrigerant leak or compressor failure",
            "urgency": urgency,
            "recommendations": [
                "Check thermostat settings first (free)",
                "Replace air filter ($20 DIY fix)",
                "Likely needs refrigerant recharge ($150-400)",
                "If compressor failed: $800-1500 repair"
            ]
        })

    elif "not heating" in symptom_lower:
        if season.lower() == "winter":
            urgency = "urgent"  # Winter heating failure = emergency
        else:
            urgency = "routine"

        result.update({
            "estimated_cost": f"{int(250 * base_cost_multiplier)}-{int(700 * base_cost_multiplier)}",
            "likely_issue": "Igniter or heat exchanger issue",
            "urgency": urgency,
            "recommendations": [
                "Check thermostat and circuit breaker first",
                "Replace furnace filter ($15-30)",
                "Igniter replacement: $150-300",
                "Heat exchanger: $500-1200 (consider replacement if >12 years old)"
            ]
        })

    elif "strange noise" in symptom_lower or "loud" in symptom_lower:
        result.update({
            "estimated_cost": f"{int(200 * base_cost_multiplier)}-{int(600 * base_cost_multiplier)}",
            "likely_issue": "Blower motor or belt issue",
            "urgency": "routine",
            "recommendations": [
                "Squealing = belt replacement ($100-200)",
                "Grinding = blower motor bearings ($300-500)",
                "Rattling = loose panels (DIY fix with screwdriver)",
                "Schedule service within 1-2 weeks"
            ]
        })

    elif "high bill" in symptom_lower or "expensive" in symptom_lower:
        result.update({
            "estimated_cost": "150-400",
            "likely_issue": "Dirty filter or low refrigerant causing inefficiency",
            "urgency": "routine",
            "recommendations": [
                "Replace air filter monthly ($15-30/month)",
                "Seal duct leaks (30% energy waste from leaks)",
                "Service unit for efficiency tune-up ($150-250)",
                "Consider programmable thermostat ($200, saves $180/yr)"
            ]
        })

    elif "no power" in symptom_lower:
        result.update({
            "estimated_cost": "100-300",
            "likely_issue": "Electrical issue or blown capacitor",
            "urgency": "urgent",
            "recommendations": [
                "Check circuit breaker first (free DIY)",
                "Blown capacitor: $150-300 (common issue)",
                "Bad thermostat wiring: $100-200",
                "Schedule electrician/HVAC tech within 24 hours"
            ]
        })

    # ⚠️ MAINTENANCE PENALTY
    if last_service_months_ago > 24:
        result["recommendations"].append(
            f"⚠️ Unit hasn't been serviced in {last_service_months_ago} months. "
            "Lack of maintenance likely caused this issue. "
            "Schedule annual service to prevent future breakdowns ($150-250/yr < repair costs)."
        )

    return result
"""

    result2 = runtime.register_tool(
        tool_name="estimate_hvac_repair",
        code=hvac_tool,
        description="🌡️ HVAC repair cost estimator - calculates costs based on age, symptoms, and maintenance history",
        category="hvac"
    )
    logger.info(f"✅ Tool 2 registered: {result2}")


    # ==================== TOOL 3: Preventive Maintenance Scheduler ====================
    preventive_tool = """
def schedule_preventive_maintenance(
    property_age_years: int,
    last_hvac_service: str,
    last_plumbing_inspection: str,
    last_roof_inspection: str = "never",
    property_type: str = "single_family"
) -> dict:
    '''
    📅 Preventive Maintenance Scheduler

    Generates proactive maintenance schedule to prevent costly breakdowns.

    Args:
        property_age_years: Age of property in years
        last_hvac_service: Last HVAC service date or months ago (e.g., "6 months ago", "2023-06-15")
        last_plumbing_inspection: Last plumbing inspection (e.g., "never", "1 year ago")
        last_roof_inspection: Last roof inspection (default: "never")
        property_type: Type of property (default: "single_family", or "condo", "multi_family")

    Returns:
        dict with maintenance schedule, priorities, and estimated annual cost
    '''

    tasks = []
    total_annual_cost = 0

    # Helper function to parse "X months ago" or dates (no imports needed)
    def months_since(date_str):
        if "never" in date_str.lower():
            return 999

        # Parse "X months ago" or "X years ago"
        date_lower = date_str.lower()
        words = date_lower.split()

        for i, word in enumerate(words):
            if word.isdigit() or word.replace('.', '').isdigit():
                num = int(float(word))
                # Check next word for unit
                if i + 1 < len(words):
                    unit = words[i + 1]
                    if "year" in unit:
                        return num * 12
                    elif "month" in unit:
                        return num
        return 0

    # 🌡️ HVAC MAINTENANCE
    hvac_months = months_since(last_hvac_service)
    if hvac_months > 6:
        tasks.append({
            "task": "HVAC filter replacement",
            "urgency": "immediate" if hvac_months > 12 else "routine",
            "frequency": "monthly",
            "estimated_cost": "15-30 per month",
            "diy": True,
            "notes": "DIY task. Change filter 1st of every month. Prevents 80% of HVAC breakdowns."
        })
        total_annual_cost += 25 * 12  # $25/mo average

    if hvac_months > 12:
        tasks.append({
            "task": "Professional HVAC service (tune-up)",
            "urgency": "urgent",
            "frequency": "annual",
            "estimated_cost": "150-250",
            "diy": False,
            "notes": "Annual service prevents $800+ breakdowns. Schedule before summer (cooling) or winter (heating)."
        })
        total_annual_cost += 200

    # 🚰 PLUMBING MAINTENANCE
    plumbing_months = months_since(last_plumbing_inspection)
    if plumbing_months > 24 or property_age_years > 20:
        tasks.append({
            "task": "Professional plumbing inspection",
            "urgency": "routine" if property_age_years < 30 else "urgent",
            "frequency": "every 2-3 years",
            "estimated_cost": "200-350",
            "diy": False,
            "notes": "Catch small leaks before they become $2000 flood damage. Critical for properties >20 years old."
        })
        total_annual_cost += 100  # Amortized over 2 years

    if property_age_years > 40:
        tasks.append({
            "task": "⚠️ Water heater replacement planning",
            "urgency": "plan_ahead",
            "frequency": "every 10-12 years",
            "estimated_cost": "800-1500",
            "diy": False,
            "notes": "Water heaters last 10-12 years. Yours is likely overdue. Failure = flooding. Budget for replacement."
        })

    # 🏠 ROOF MAINTENANCE
    roof_months = months_since(last_roof_inspection)
    if roof_months > 36 or property_age_years > 15:
        tasks.append({
            "task": "Roof inspection",
            "urgency": "routine",
            "frequency": "every 3-5 years",
            "estimated_cost": "150-300",
            "diy": False,
            "notes": "Small leak caught early = $200 fix. Ignored leak = $5000 mold remediation + ceiling repair."
        })
        total_annual_cost += 50  # Amortized over 5 years

    # 🌳 SEASONAL MAINTENANCE
    tasks.append({
        "task": "Gutter cleaning",
        "urgency": "routine",
        "frequency": "twice per year (spring + fall)",
        "estimated_cost": "100-200 per cleaning",
        "diy": True,
        "notes": "Clogged gutters = water damage to foundation. DIY or hire handyman. Do before rainy season."
    })
    total_annual_cost += 200  # 2x per year

    if property_type == "single_family":
        tasks.append({
            "task": "Smoke/CO detector battery replacement",
            "urgency": "immediate",
            "frequency": "annual",
            "estimated_cost": "20-40",
            "diy": True,
            "notes": "Required by law. Replace batteries every year. Replace entire units every 10 years."
        })
        total_annual_cost += 30

    # 🎯 PRIORITIZE TASKS
    urgent_tasks = [t for t in tasks if t["urgency"] in ["immediate", "urgent"]]
    routine_tasks = [t for t in tasks if t["urgency"] == "routine"]
    plan_ahead_tasks = [t for t in tasks if t["urgency"] == "plan_ahead"]

    return {
        "total_tasks": len(tasks),
        "urgent_tasks": len(urgent_tasks),
        "estimated_annual_cost": f"${total_annual_cost:.0f}",
        "tasks": tasks,
        "priority_summary": {
            "immediate_action": urgent_tasks,
            "schedule_soon": routine_tasks,
            "plan_budget": plan_ahead_tasks
        },
        "savings_note": f"Preventive maintenance (${total_annual_cost:.0f}/yr) prevents $5000-15000 in emergency repairs",
        "recommendation": "Schedule urgent tasks this month. Set calendar reminders for recurring tasks."
    }
"""

    result3 = runtime.register_tool(
        tool_name="schedule_preventive_maintenance",
        code=preventive_tool,
        description="📅 Preventive maintenance scheduler - generates proactive maintenance schedule to prevent costly breakdowns",
        category="general"
    )
    logger.info(f"✅ Tool 3 registered: {result3}")


    # ==================== TOOL 4: Garage Door Diagnostic ====================
    garage_door_tool = """
def diagnose_garage_door_failure(
    symptom: str,
    location: str,
    severity_indicators: str,
    additional_context: str = ""
) -> dict:
    '''
    🚪 Intelligent Garage Door Diagnostic Tool

    Analyzes garage door symptoms to determine cause, severity, and cost.

    Args:
        symptom: Main problem (e.g., "door won't open", "grinding noise", "door reverses")
        location: Specific location (e.g., "garage door", "main garage", "2-car garage")
        severity_indicators: Observable symptoms (e.g., "unresponsive to remote", "broken spring visible")
        additional_context: Additional details

    Returns:
        dict with diagnosis, severity, estimated_cost, urgency, and recommendations
    '''

    result = {
        "diagnosis": "Unknown garage door issue",
        "severity": "medium",
        "estimated_cost": "150-400",
        "urgency": "urgent",
        "likely_causes": [],
        "recommendations": []
    }

    symptom_lower = symptom.lower()
    severity_lower = severity_indicators.lower()

    # 🔧 SYMPTOM ANALYSIS

    # Broken Spring (most common, 26% of failures)
    if "spring" in severity_lower or "won't lift" in symptom_lower or "lifts 6 inches" in symptom_lower:
        result.update({
            "diagnosis": "Broken torsion spring",
            "severity": "medium",
            "estimated_cost": "200-400",
            "urgency": "urgent",
            "likely_causes": [
                "Metal fatigue from 10,000+ cycles (typical spring lifespan)",
                "Rust/corrosion in humid climates",
                "Temperature extremes (cold makes springs brittle)"
            ],
            "recommendations": [
                "⚠️ DO NOT attempt DIY spring replacement (300+ lbs tension = serious injury risk)",
                "Call professional garage door technician within 24-48 hours",
                "Cost: $200-$400 for professional spring replacement",
                "While waiting: Use manual release to open/close (if door isn't too heavy)"
            ]
        })
        return result

    # Misaligned Safety Sensors (18% of failures)
    if "hums but" in symptom_lower or "reverses" in symptom_lower or "blinking light" in severity_lower:
        result.update({
            "diagnosis": "Misaligned safety sensors",
            "severity": "low",
            "estimated_cost": "0-150",
            "urgency": "routine",
            "likely_causes": [
                "Sensor knocked out of alignment (common with garage activity)",
                "Dirty sensor lens blocking infrared beam",
                "Damaged sensor wiring"
            ],
            "recommendations": [
                "✅ DIY FIX (2 minutes): Gently adjust sensor until both show solid green lights",
                "Check for obstructions in sensor beam path",
                "Clean sensor lenses with soft cloth",
                "If DIY doesn't work: Professional service $75-150",
                "Safety note: Sensors prevent door from closing on objects/people"
            ]
        })
        return result

    # Worn Opener Motor/Gears (14% of failures)
    if "grinding" in symptom_lower or "clicking" in symptom_lower or "intermittent" in symptom_lower:
        result.update({
            "diagnosis": "Worn opener motor gears or chain",
            "severity": "medium",
            "estimated_cost": "150-300",
            "urgency": "urgent",
            "likely_causes": [
                "Stripped plastic gears inside opener (common after 10-15 years)",
                "Worn/dry chain or belt drive",
                "Motor capacitor failure"
            ],
            "recommendations": [
                "Schedule garage door technician within 1-2 weeks",
                "Gear replacement: $150-250",
                "Full opener replacement: $200-500 (may be better value if unit >15 years old)",
                "Lubricate chain/rails while waiting (may temporarily improve)"
            ]
        })
        return result

    # No Power / Complete Failure
    if "no power" in symptom_lower or "complete silence" in symptom_lower or "no response" in symptom_lower:
        result.update({
            "diagnosis": "Electrical issue or dead opener",
            "severity": "medium",
            "estimated_cost": "100-300",
            "urgency": "urgent",
            "likely_causes": [
                "Tripped circuit breaker or blown fuse",
                "Unplugged opener power cord",
                "Failed GFCI outlet",
                "Dead opener motor or control board"
            ],
            "recommendations": [
                "✅ DIY CHECK: Verify circuit breaker isn't tripped (flip off then on)",
                "✅ DIY CHECK: Ensure opener is plugged in securely",
                "✅ DIY CHECK: Test GFCI outlet reset button",
                "If power confirmed working: Call technician for motor/board diagnosis ($100-300)"
            ]
        })
        return result

    # Off-Track Door (serious structural issue)
    if "off track" in symptom_lower or "crooked" in symptom_lower or "bent" in symptom_lower:
        result.update({
            "diagnosis": "Door off track or bent rails",
            "severity": "high",
            "estimated_cost": "200-600",
            "urgency": "immediate",
            "likely_causes": [
                "Impact damage (car bumped door)",
                "Broken cable or pulley",
                "Worn rollers causing misalignment"
            ],
            "recommendations": [
                "⚠️ STOP USING DOOR IMMEDIATELY (prevents further damage)",
                "⚠️ DO NOT attempt to realign yourself (pinch/crush hazard)",
                "Call emergency garage door service within 24 hours",
                "Cost: $200-600 for track realignment + roller/cable replacement"
            ]
        })
        return result

    # Generic diagnosis if no specific pattern matched
    result.update({
        "diagnosis": "Multiple possible causes",
        "likely_causes": [
            "Broken torsion spring (26% of failures) - $200-400",
            "Misaligned safety sensors (18% of failures) - $0-150 (often DIY fix)",
            "Worn opener motor gears (14% of failures) - $150-300"
        ],
        "recommendations": [
            "Check for blinking sensor lights (indicates misalignment)",
            "Listen for motor sound when pressing button (hum = motor works, silence = power issue)",
            "Look for visible gap in spring coil above door (indicates broken spring)",
            "Try manual release cord to test if door lifts manually",
            "Call garage door technician for professional diagnosis: $75-150 service call"
        ]
    })

    return result
"""

    result4 = runtime.register_tool(
        tool_name="diagnose_garage_door_failure",
        code=garage_door_tool,
        description="🚪 Intelligent garage door diagnostic - analyzes symptoms to identify springs, sensors, motor, or track issues",
        category="garage"
    )
    logger.info(f"✅ Tool 4 registered: {result4}")


    # ==================== TOOL 5: Electrical Hazard Diagnostic ====================
    electrical_tool = """
def diagnose_electrical_hazard(
    symptom: str,
    location: str,
    severity_indicators: str,
    additional_context: str = ""
) -> dict:
    '''
    ⚡ Electrical Hazard Diagnostic Tool

    Analyzes electrical symptoms to determine safety risks and required actions.

    Args:
        symptom: Main problem (e.g., "outlet sparking", "breaker tripping", "flickering lights")
        location: Specific location (e.g., "kitchen outlet", "main panel", "bedroom lights")
        severity_indicators: Observable symptoms (e.g., "burning smell", "smoke", "heat")
        additional_context: Additional details

    Returns:
        dict with diagnosis, severity, estimated_cost, urgency, and safety warnings
    '''

    result = {
        "diagnosis": "Unknown electrical issue",
        "severity": "high",
        "estimated_cost": "150-500",
        "urgency": "urgent",
        "safety_warnings": [],
        "recommendations": []
    }

    symptom_lower = symptom.lower()
    severity_lower = severity_indicators.lower()

    # 🚨 EMERGENCY: Sparking, smoke, or fire
    if any(word in symptom_lower or word in severity_lower for word in ["sparking", "spark", "smoke", "burning smell", "fire"]):
        result.update({
            "diagnosis": "ELECTRICAL FIRE HAZARD - Immediate danger",
            "severity": "emergency",
            "estimated_cost": "200-1000",
            "urgency": "immediate",
            "safety_warnings": [
                "🚨 SHUT OFF BREAKER TO AFFECTED CIRCUIT IMMEDIATELY",
                "🚨 DO NOT TOUCH the outlet, switch, or any electrical components",
                "🚨 EVACUATE if you see smoke or smell burning plastic",
                "🚨 CALL ELECTRICIAN EMERGENCY LINE within 1 hour",
                "If fire visible: Call 911 immediately"
            ],
            "recommendations": [
                "Turn off power at main breaker if safe to do so",
                "Keep fire extinguisher nearby (Class C for electrical fires)",
                "Do not use water on electrical fires",
                "Emergency electrician visit: $200-500 (worth it to prevent house fire)",
                "Likely cause: Arcing from loose connection or damaged wiring"
            ]
        })
        return result

    # ⚡ HIGH RISK: Breaker keeps tripping
    if "breaker trip" in symptom_lower or "keeps tripping" in symptom_lower:
        result.update({
            "diagnosis": "Circuit overload or short circuit",
            "severity": "high",
            "estimated_cost": "200-600",
            "urgency": "urgent",
            "safety_warnings": [
                "⚠️ DO NOT keep resetting breaker repeatedly (fire risk)",
                "⚠️ Unplug all devices on that circuit",
                "⚠️ Breakers trip to prevent fires - this is a safety mechanism"
            ],
            "recommendations": [
                "Identify what causes trip (specific appliance, time of day)",
                "If microwave/AC causes trip: Circuit likely undersized (needs dedicated 20A circuit)",
                "If random tripping: Short circuit or faulty breaker",
                "Licensed electrician visit: $200-400 for diagnosis + circuit work",
                "Dedicated circuit installation: $300-600",
                "DO NOT upgrade breaker size without rewiring (fire hazard)"
            ]
        })
        return result

    # ⚠️ MEDIUM: Flickering lights
    if "flicker" in symptom_lower or "dimming" in symptom_lower:
        result.update({
            "diagnosis": "Loose connection or voltage fluctuation",
            "severity": "medium",
            "estimated_cost": "100-400",
            "urgency": "routine",
            "safety_warnings": [
                "Loose connections can cause arcing (fire risk over time)",
                "Widespread flickering may indicate main panel issue"
            ],
            "recommendations": [
                "If only one fixture flickers: Likely loose bulb or bad socket ($0-50 DIY fix)",
                "If multiple lights flicker when appliance starts: Undersized circuit",
                "If whole-house flickering: Loose service connection (utility company or electrician)",
                "Electrician diagnosis: $100-200",
                "Fix ranges from $50 (tighten connection) to $400 (rewiring)"
            ]
        })
        return result

    # ⚠️ MEDIUM: Outlet not working
    if "outlet" in symptom_lower and ("not work" in symptom_lower or "dead" in symptom_lower):
        result.update({
            "diagnosis": "Tripped GFCI or bad outlet",
            "severity": "low",
            "estimated_cost": "0-150",
            "urgency": "routine",
            "safety_warnings": [
                "GFCI outlets protect against electrocution in wet areas (required by code)"
            ],
            "recommendations": [
                "✅ DIY CHECK: Look for GFCI outlet nearby with TEST/RESET buttons (often in bathroom/kitchen)",
                "✅ DIY CHECK: Press RESET button on GFCI - may restore power to chain of outlets",
                "✅ DIY CHECK: Check circuit breaker panel for tripped breaker",
                "If GFCI/breaker OK: Outlet may be faulty (electrician replacement $100-150)",
                "If multiple outlets dead: Wiring issue (electrician diagnosis $150-300)"
            ]
        })
        return result

    # Generic electrical issue
    result.update({
        "safety_warnings": [
            "⚠️ Electrical work requires licensed electrician (DIY risks electrocution)",
            "⚠️ Never ignore electrical issues - small problems escalate to fires"
        ],
        "recommendations": [
            "Turn off power to affected circuit at breaker panel",
            "Do not use affected outlet/switch until inspected",
            "Call licensed electrician for diagnosis: $100-200 service call",
            "Electrical fires cause $1.3 billion in damages annually - don't delay",
            "Permits required for electrical work in most jurisdictions"
        ]
    })

    return result
"""

    result5 = runtime.register_tool(
        tool_name="diagnose_electrical_hazard",
        code=electrical_tool,
        description="⚡ Electrical hazard diagnostic - identifies fire risks, circuit issues, and required safety actions",
        category="electrical"
    )
    logger.info(f"✅ Tool 5 registered: {result5}")


    logger.info("\n" + "="*60)
    logger.info("🎉 ALL 5 STARTER TOOLS REGISTERED SUCCESSFULLY!")
    logger.info("="*60)
    logger.info("Tools available:")
    logger.info("  1. diagnose_water_leak - Plumbing diagnostic")
    logger.info("  2. estimate_hvac_repair - HVAC cost estimator")
    logger.info("  3. schedule_preventive_maintenance - Maintenance scheduler")
    logger.info("  4. diagnose_garage_door_failure - Garage door diagnostic")
    logger.info("  5. diagnose_electrical_hazard - Electrical safety diagnostic")
    logger.info("="*60)

    return {
        "success": True,
        "tools_registered": 5,
        "tools": [result1, result2, result3, result4, result5]
    }


if __name__ == "__main__":
    seed_tools()
