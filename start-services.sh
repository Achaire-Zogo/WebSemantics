#!/bin/bash

echo "🚀 Starting Food Semantic Web Service..."

# Start Fuseki server in background
echo "📚 Starting Jena Fuseki..."
cd /opt/fuseki
./fuseki-server --config=/var/fuseki/config.ttl --port=3030 &

# Wait for Fuseki to start
echo "⏳ Waiting for Fuseki to initialize..."
sleep 15

# Load ontology into Fuseki
echo "📥 Loading ontology data..."
curl -X POST \
  --data-binary @/app/data/ontology/WebSemantics.rdf \
  --header "Content-Type: application/rdf+xml" \
  "http://localhost:3030/food-kb/data"

echo ""
echo "✅ Ontology loaded successfully!"

# Wait for Elasticsearch to be ready
echo "🔍 Waiting for Elasticsearch to be ready..."
while ! curl -s http://elasticsearch:9200/_cluster/health > /dev/null; do
    echo "⏳ Elasticsearch not ready yet, waiting 5 seconds..."
    sleep 5
done

echo "✅ Elasticsearch is ready!"

# Start the Python web service
echo "🌐 Starting Flask web service..."
cd /app/service
python3 app.py