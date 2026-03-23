class GreenGapEngine:
    def calculate_score(self, temp, ndvi): # <-- This must have 4 spaces before it
        score = temp * (1 - ndvi)           # <-- This must have 8 spaces before it
        return round(score, 1)              # <-- This must have 8 spaces before it

    def evaluate_zone(self, score):         # <-- This must have 4 spaces before it
        if score > 25.0:                    # <-- This must have 8 spaces before it
            status = "CRITICAL GREEN GAP"   # <-- This must have 12 spaces before it
            action = "EMERGENCY: High thermal retention. Immediate tree planting required."
            color = "text-red-500"
        elif score > 15.0:
            status = "WARNING ZONE"
            action = "CAUTION: Canopy is thinning. Proactive greening needed."
            color = "text-yellow-500"
        else:
            status = "HEALTHY CANOPY"
            action = "STABLE: Strong ecosystem. Maintain current greenery."
            color = "text-green-500"
            
        return status, action, color        # <-- This must have 8 spaces before it