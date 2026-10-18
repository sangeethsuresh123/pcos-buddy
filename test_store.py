from backend.symptoms import store
print('Testing symptom store...')
try:
    # Test creating an entry
    entry = {
        'entry_date': '2026-10-18',
        'period_flow': 3,
        'period_day': 1,
        'abdominal_pain': 5,
        'fatigue': 6,
        'mood_swings': 4,
        'exercise_minutes': 30,
        'sleep_hours': 7.5
    }
    result = store.upsert_entry(3, entry)
    print('Success:', result)
except Exception as e:
    import traceback
    traceback.print_exc()