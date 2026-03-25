# Momentum Cascade Victory States
# Psychological context messages for mission mastery

def get_victory_state(total, done):
    if total == 0:
        return "Fresh start. Add your first win. 🌟"
    
    percent = (done / total) * 100 if total > 0 else 0
    
    if done == 0:
        return "Momentum building. Pick one. ⚡"
    if done >= 1 and done <= 3:
        return "Momentum building. Pick one. ⚡"
    if done >= 4 and done <= 7:
        return "Flow state activated. 🔥"
    if percent >= 50 and percent < 100:
        return "Mastery mode. You're unstoppable. 💪"
    if percent >= 100:
        return "Cleared! 🎉 Reset or celebrate?"
    
    return "Flow state activated. 🔥"
