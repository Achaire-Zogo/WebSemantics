#!/usr/bin/env python3
import requests
import json

API_BASE = "http://localhost:8080"

def test_search(query, description=""):
    print(f"\n🔍 Testing: {description or query}")
    print("-" * 50)
    
    response = requests.get(f"{API_BASE}/api/search", params={'q': query})
    
    if response.status_code == 200:
        data = response.json()
        results = data.get('results', [])
        suggestions = data.get('suggestions', [])
        
        print(f"✅ Found {len(results)} results")
        
        for i, result in enumerate(results[:3]):  # Show top 3
            score = result.get('search_score', 0)
            match_type = result.get('match_type', 'unknown')
            print(f"   {i+1}. {result['name']} (score: {score:.2f}, type: {match_type})")
        
        if suggestions:
            print(f"💡 Suggestions:")
            for sugg in suggestions[:2]:
                print(f"   → {sugg['suggestion']} (similarity: {sugg['similarity']:.2f})")
    else:
        print(f"❌ Error: {response.status_code}")

# Test cases
test_cases = [
    ("bread", "Case-insensitive basic search"),
    ("PILAU", "Uppercase search"),
    ("bred", "Typo correction"),
    ("plaw", "Fuzzy matching"),
    ("spiced rice", "Alternative name"),
    ("beans", "Ingredient search"),
    ("swahili", "Cultural search"),
    ("mchu", "Partial matching"),
    ("xyz123", "No matches (should suggest)")
]

print("🧪 Smart Search Test Suite")
print("=" * 60)

for query, description in test_cases:
    test_search(query, description)

print("\n✅ Test complete!")