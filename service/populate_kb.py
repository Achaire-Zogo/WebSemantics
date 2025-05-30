"""
Script to populate the knowledge base with food instances using JSON mappings
"""
from rdflib import Graph, Namespace, RDF, RDFS, Literal, URIRef
from SPARQLWrapper import SPARQLWrapper, POST, DIGEST
import os
import requests
import json

FUSEKI_UPDATE_ENDPOINT = "http://localhost:3030/food-kb/update"
IMAGES_PATH = "/app/data/images"
MAPPINGS_FILE = "/app/data/food_mappings.json"
ONTOLOGY_NS = Namespace("http://www.semanticweb.org/zaz/ontologies/2025/4/untitled-ontology-8#")

def load_food_mappings():
    """Load food mappings from JSON file"""
    try:
        with open(MAPPINGS_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config.get('food_mappings', {})
    except FileNotFoundError:
        print(f"Mappings file not found: {MAPPINGS_FILE}")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing mappings file: {e}")
        return {}

def populate_knowledge_base():
    """Populate the knowledge base with food instances from JSON mappings"""
    
    # Load food mappings from JSON
    food_mappings = load_food_mappings()
    
    if not food_mappings:
        print("No food mappings found. Exiting.")
        return
    
    # Create RDF graph
    g = Graph()
    g.bind("", ONTOLOGY_NS)
    g.bind("rdfs", RDFS)
    
    # Add food instances with comprehensive data
    for food_name, properties in food_mappings.items():
        # Create URI for food instance
        safe_name = food_name.replace(' ', '_').replace(',', '').replace('(', '').replace(')', '').replace("'", "")
        food_uri = ONTOLOGY_NS[safe_name]
        
        # Add basic triples
        ontology_class = properties.get('ontology_class', 'Food')
        g.add((food_uri, RDF.type, ONTOLOGY_NS[ontology_class]))
        g.add((food_uri, RDFS.label, Literal(food_name)))
        
        # Add detailed properties from JSON mapping
        property_mappings = {
            'food_type': 'hasType',
            'category': 'hasCategory', 
            'region': 'belongsToRegion',
            'preparation': 'hasPreparation',
            'cultural_origin': 'hasCulturalOrigin',
            'nutritional_focus': 'hasNutritionalFocus'
        }
        
        for json_prop, rdf_prop in property_mappings.items():
            if json_prop in properties:
                g.add((food_uri, ONTOLOGY_NS[rdf_prop], Literal(properties[json_prop])))
        
        # Add primary ingredients
        if 'primary_ingredients' in properties:
            for ingredient in properties['primary_ingredients']:
                g.add((food_uri, ONTOLOGY_NS.hasIngredient, Literal(ingredient)))
        
        # Check if image exists
        if os.path.exists(os.path.join(IMAGES_PATH, food_name)):
            g.add((food_uri, ONTOLOGY_NS.hasImage, Literal(True)))
            g.add((food_uri, ONTOLOGY_NS.imagePath, Literal(f"/api/food/{food_name}/image")))
        else:
            g.add((food_uri, ONTOLOGY_NS.hasImage, Literal(False)))
    
    # Convert to SPARQL INSERT query
    turtle_data = g.serialize(format='turtle')
    
    insert_query = f"""
    PREFIX : <{ONTOLOGY_NS}>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    INSERT DATA {{
        {turtle_data}
    }}
    """
    
    # Send to Fuseki
    try:
        response = requests.post(
            FUSEKI_UPDATE_ENDPOINT,
            data={'update': insert_query},
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        if response.status_code == 200:
            print(f"Knowledge base populated successfully with {len(food_mappings)} food items!")
            print("Added properties for each food:")
            print("- Ontology class classification")
            print("- Regional and cultural information") 
            print("- Preparation methods")
            print("- Nutritional focus")
            print("- Primary ingredients")
            print("- Image availability")
        else:
            print(f"Error populating KB: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    populate_knowledge_base()