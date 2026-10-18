#!/bin/bash
cd /home/sangeethsuresh/projects/chatbot
COOKIES=$(mktemp)

echo "=== Register ==="
curl -s -X POST http://localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@test.com","password":"testpassword123"}' \
  -c $COOKIES
echo ""

echo "=== Login ==="
curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@test.com","password":"testpassword123"}' \
  -c $COOKIES
echo ""

echo "=== Create symptom entry ==="
curl -s -X POST http://localhost:8000/api/symptoms/entries \
  -b $COOKIES -H 'Content-Type: application/json' \
  -d '{"date":"2026-10-18","period_flow":3,"period_day":1,"abdominal_pain":5,"fatigue":6,"mood_swings":4,"exercise_minutes":30,"sleep_hours":7.5}'
echo ""

echo "=== Get symptom entries ==="
curl -s -b $COOKIES http://localhost:8000/api/symptoms/entries
echo ""

echo "=== Get cycle analysis ==="
curl -s -b $COOKIES http://localhost:8000/api/symptoms/analysis
echo ""

echo "=== Get ML features from symptoms ==="
curl -s -b $COOKIES http://localhost:8000/api/symptoms/ml-features
echo ""

echo "=== Test ML prediction with symptom enrichment ==="
curl -s -X POST http://localhost:8000/api/ml/predict \
  -b $COOKIES -H 'Content-Type: application/json' \
  -d '{"Age (yrs)":25,"Blood Group":11,"Pulse rate(bpm)":72,"Hb(g/dl)":12.5,"Cycle(R/I)":2,"Cycle length(days)":28,"Marraige Status (Yrs)":0,"I   beta-HCG(mIU/mL)":2,"II    beta-HCG(mIU/mL)":180,"FSH(mIU/mL)":5.7,"Waist:Hip Ratio":0.88,"TSH (mIU/L)":2,"PRL(ng/mL)":22,"Vit D3 (ng/mL)":20,"PRG(ng/mL)":0.5,"RBS(mg/dl)":100,"Follicle No. (L)":8,"Follicle No. (R)":8}'
echo ""

rm $COOKIES