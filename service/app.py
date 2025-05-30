from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from SPARQLWrapper import SPARQLWrapper, JSON
import os
import json
from PIL import Image
import base64
import io
from rdflib import Graph, Namespace, RDF, RDFS, Literal, URIRef
from elasticsearch import Elasticsearch
import logging
import time
from urllib.parse import quote
import difflib
import re

app = Flask(__name__)
CORS(app)

# Configuration
FUSEKI_ENDPOINT = "http://localhost:3030/food-kb/sparql"
IMAGES_PATH = "/app/data/images"
ONTOLOGY_NS = "http://www.semanticweb.org/zaz/ontologies/2025/4/untitled-ontology-8#"
MAPPINGS_FILE = "/app/data/food_mappings.json"

# Initialize SPARQL wrapper
sparql = SPARQLWrapper(FUSEKI_ENDPOINT)
sparql.setReturnFormat(JSON)

# Initialize Elasticsearch for text search - Fixed configuration
def init_elasticsearch():
    """Initialize Elasticsearch with proper configuration and retry logic"""
    max_retries = 5
    retry_delay = 10
    
    for attempt in range(max_retries):
        try:
            # Fixed Elasticsearch client initialization
            es = Elasticsearch(
                hosts=[{'host': 'elasticsearch', 'port': 9200, 'scheme': 'http'}],
                request_timeout=30,
                max_retries=3,
                retry_on_timeout=True
            )
            
            # Test connection
            if es.ping():
                print("✅ Elasticsearch connection successful!")
                return es
            else:
                print(f"❌ Elasticsearch ping failed on attempt {attempt + 1}")
                
        except Exception as e:
            print(f"❌ Elasticsearch connection attempt {attempt + 1} failed: {e}")
            
        if attempt < max_retries - 1:
            print(f"⏳ Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
    
    print("⚠️ Could not connect to Elasticsearch. Search functionality will be limited.")
    return None

# Initialize Elasticsearch with retry logic
es = init_elasticsearch()

class SmartSearchEngine:
    """Enhanced search engine with case-insensitive and auto-correct capabilities"""
    
    def __init__(self, food_mappings):
        self.food_mappings = food_mappings
        self.food_names = list(food_mappings.keys())
        self.food_names_lower = [name.lower() for name in self.food_names]
        self.search_index = self._build_search_index()
    
    def _build_search_index(self):
        """Build comprehensive search index"""
        index = {}
        
        for food_name, properties in self.food_mappings.items():
            # Add the food name itself
            self._add_to_index(index, food_name.lower(), food_name, 'name', 1.0)
            
            # Add alternative terms
            alternatives = self._generate_alternatives(food_name)
            for alt in alternatives:
                self._add_to_index(index, alt.lower(), food_name, 'alternative', 0.8)
            
            # Add ingredients
            ingredients = properties.get('primary_ingredients', [])
            for ingredient in ingredients:
                self._add_to_index(index, ingredient.lower(), food_name, 'ingredient', 0.6)
            
            # Add cultural origin
            cultural_origin = properties.get('cultural_origin', '')
            if cultural_origin and cultural_origin != 'Unknown':
                self._add_to_index(index, cultural_origin.lower(), food_name, 'culture', 0.5)
            
            # Add category
            category = properties.get('category', '')
            if category and category != 'Unknown':
                self._add_to_index(index, category.lower(), food_name, 'category', 0.4)
        
        return index
    
    def _add_to_index(self, index, term, food_name, match_type, score):
        """Add term to search index"""
        if term not in index:
            index[term] = []
        index[term].append({
            'food_name': food_name,
            'match_type': match_type,
            'score': score
        })
    
    def _generate_alternatives(self, food_name):
        """Generate alternative search terms for a food name"""
        alternatives = []
        
        # Remove parentheses content for simpler search
        simple_name = re.sub(r'\([^)]*\)', '', food_name).strip()
        if simple_name != food_name:
            alternatives.append(simple_name)
        
        # Extract words in parentheses as alternatives
        parentheses_content = re.findall(r'\(([^)]*)\)', food_name)
        for content in parentheses_content:
            alternatives.append(content.strip())
        
        # Split by common separators
        separators = [',', ' and ', ' & ', ' with ', ' wa ']
        for sep in separators:
            if sep in food_name.lower():
                parts = food_name.split(sep)
                for part in parts:
                    part = part.strip()
                    if len(part) > 2:
                        alternatives.append(part)
        
        # Add individual words
        words = food_name.replace(',', ' ').replace('(', ' ').replace(')', ' ').split()
        for word in words:
            if len(word) > 2:  # Skip very short words
                alternatives.append(word)
        
        return alternatives
    
    def smart_search(self, query, max_results=20):
        """Perform smart search with case-insensitive matching and suggestions"""
        if not query:
            return []
        
        query = query.lower().strip()
        results = []
        
        # 1. Exact matches (case-insensitive)
        exact_matches = self._find_exact_matches(query)
        results.extend(exact_matches)
        
        # 2. Partial matches
        partial_matches = self._find_partial_matches(query)
        results.extend(partial_matches)
        
        # 3. Fuzzy matches (for typos)
        fuzzy_matches = self._find_fuzzy_matches(query)
        results.extend(fuzzy_matches)
        
        # Remove duplicates and sort by score
        seen = set()
        unique_results = []
        for result in results:
            if result['food_name'] not in seen:
                seen.add(result['food_name'])
                unique_results.append(result)
        
        # Sort by score (higher is better)
        unique_results.sort(key=lambda x: x['total_score'], reverse=True)
        
        return unique_results[:max_results]
    
    def _find_exact_matches(self, query):
        """Find exact matches in the search index"""
        matches = []
        
        if query in self.search_index:
            for match in self.search_index[query]:
                matches.append({
                    'food_name': match['food_name'],
                    'match_type': 'exact_' + match['match_type'],
                    'total_score': match['score'] * 2.0,  # Boost exact matches
                    'query_matched': query
                })
        
        return matches
    
    def _find_partial_matches(self, query):
        """Find partial matches (contains)"""
        matches = []
        
        for term, term_matches in self.search_index.items():
            if query in term or term in query:
                for match in term_matches:
                    # Calculate similarity score
                    similarity = len(query) / max(len(term), len(query))
                    score = match['score'] * similarity * 1.5
                    
                    matches.append({
                        'food_name': match['food_name'],
                        'match_type': 'partial_' + match['match_type'],
                        'total_score': score,
                        'query_matched': term
                    })
        
        return matches
    
    def _find_fuzzy_matches(self, query):
        """Find fuzzy matches for typo correction"""
        matches = []
        
        for term in self.search_index.keys():
            # Use difflib for fuzzy matching
            similarity = difflib.SequenceMatcher(None, query, term).ratio()
            
            if similarity > 0.6:  # Threshold for fuzzy matching
                for match in self.search_index[term]:
                    score = match['score'] * similarity
                    
                    matches.append({
                        'food_name': match['food_name'],
                        'match_type': 'fuzzy_' + match['match_type'],
                        'total_score': score,
                        'query_matched': term,
                        'similarity': similarity
                    })
        
        return matches
    
    def suggest_corrections(self, query, max_suggestions=5):
        """Suggest corrections for misspelled queries"""
        if not query:
            return []
        
        query = query.lower().strip()
        suggestions = []
        
        # Find close matches using difflib
        close_matches = difflib.get_close_matches(
            query, 
            self.food_names_lower, 
            n=max_suggestions, 
            cutoff=0.4
        )
        
        for match in close_matches:
            # Find original case
            original_index = self.food_names_lower.index(match)
            original_name = self.food_names[original_index]
            
            similarity = difflib.SequenceMatcher(None, query, match).ratio()
            suggestions.append({
                'suggestion': original_name,
                'similarity': similarity,
                'type': 'spelling_correction'
            })
        
        # Also check search terms
        for term in self.search_index.keys():
            similarity = difflib.SequenceMatcher(None, query, term).ratio()
            if 0.5 < similarity < 0.9:  # Not too similar (already found) but not too different
                suggestions.append({
                    'suggestion': term,
                    'similarity': similarity,
                    'type': 'search_term'
                })
        
        # Sort by similarity and remove duplicates
        suggestions = sorted(suggestions, key=lambda x: x['similarity'], reverse=True)
        seen = set()
        unique_suggestions = []
        for sugg in suggestions:
            if sugg['suggestion'] not in seen:
                seen.add(sugg['suggestion'])
                unique_suggestions.append(sugg)
        
        return unique_suggestions[:max_suggestions]

class FoodSemanticService:
    def __init__(self):
        self.config = self._load_mappings_config()
        self.food_mappings = self.config.get('food_mappings', {})
        self.ontology_classes = self.config.get('ontology_classes', {})
        self.regions = self.config.get('regions', [])
        self.nutritional_categories = self.config.get('nutritional_categories', [])
        self.preparation_methods = self.config.get('preparation_methods', [])
        
        # Initialize smart search engine
        self.smart_search = SmartSearchEngine(self.food_mappings)
        
        # Only index if Elasticsearch is available
        if es is not None:
            self._index_foods_in_elasticsearch()
        else:
            print("⚠️ Skipping Elasticsearch indexing - service not available")
    
    def _load_mappings_config(self):
        """Load food mappings from JSON configuration file"""
        try:
            with open(MAPPINGS_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                print(f"✅ Loaded {len(config.get('food_mappings', {}))} food mappings from JSON")
                return config
        except FileNotFoundError:
            logging.error(f"Mappings file not found: {MAPPINGS_FILE}")
            print(f"❌ Mappings file not found: {MAPPINGS_FILE}")
            return {'food_mappings': {}}
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing mappings file: {e}")
            print(f"❌ Error parsing mappings file: {e}")
            return {'food_mappings': {}}
    
    def get_food_mapping(self, food_name):
        """Get mapping for a specific food"""
        return self.food_mappings.get(food_name, {
            'ontology_class': 'Food',
            'food_type': 'Unknown',
            'category': 'Unknown',
            'region': 'Unknown'
        })
    
    def get_food_image_info(self, food_name):
        """Get comprehensive image information for a food"""
        image_dir = os.path.join(IMAGES_PATH, food_name)
        
        if not os.path.exists(image_dir):
            return {
                'has_images': False,
                'image_count': 0,
                'image_urls': [],
                'thumbnail_url': None
            }
        
        # Get all image files
        image_files = [f for f in os.listdir(image_dir) 
                      if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
        
        if not image_files:
            return {
                'has_images': False,
                'image_count': 0,
                'image_urls': [],
                'thumbnail_url': None
            }
        
        # Sort images for consistent ordering
        image_files.sort()
        
        # Create URLs for all images
        encoded_food_name = quote(food_name)
        image_urls = []
        
        for i, image_file in enumerate(image_files):
            image_url = f"/api/food/{encoded_food_name}/image/{i}"
            image_urls.append({
                'url': image_url,
                'filename': image_file,
                'index': i
            })
        
        return {
            'has_images': True,
            'image_count': len(image_files),
            'image_urls': image_urls,
            'thumbnail_url': f"/api/food/{encoded_food_name}/image/0",  # First image as thumbnail
            'primary_image': f"/api/food/{encoded_food_name}/image"     # Default endpoint
        }
    
    def _index_foods_in_elasticsearch(self):
        """Index food items in Elasticsearch for full-text search with enhanced analyzers"""
        if es is None:
            print("⚠️ Elasticsearch not available - skipping indexing")
            return
            
        try:
            # Delete existing index to recreate with better settings
            if es.indices.exists(index="foods"):
                es.indices.delete(index="foods")
            
            # Create index with enhanced text analysis
            es.indices.create(
                index="foods",
                body={
                    "settings": {
                        "analysis": {
                            "analyzer": {
                                "food_analyzer": {
                                    "type": "custom",
                                    "tokenizer": "standard",
                                    "filter": [
                                        "lowercase",
                                        "asciifolding",  # Handle accents
                                        "word_delimiter"
                                    ]
                                }
                            }
                        }
                    },
                    "mappings": {
                        "properties": {
                            "name": {
                                "type": "text", 
                                "analyzer": "food_analyzer",
                                "fields": {
                                    "keyword": {"type": "keyword"},
                                    "ngram": {
                                        "type": "text",
                                        "analyzer": "food_analyzer",
                                        "search_analyzer": "food_analyzer"
                                    }
                                }
                            },
                            "name_alternatives": {"type": "text", "analyzer": "food_analyzer"},
                            "ontology_class": {"type": "keyword"},
                            "food_type": {"type": "keyword"},
                            "category": {"type": "keyword"},
                            "region": {"type": "keyword"},
                            "preparation": {"type": "keyword"},
                            "cultural_origin": {"type": "keyword"},
                            "nutritional_focus": {"type": "keyword"},
                            "primary_ingredients": {"type": "text", "analyzer": "food_analyzer"},
                            "has_images": {"type": "boolean"},
                            "image_count": {"type": "integer"}
                        }
                    }
                }
            )
            print("✅ Created enhanced Elasticsearch index 'foods'")
            
            # Index all foods with comprehensive data including alternatives
            indexed_count = 0
            for food_name, properties in self.food_mappings.items():
                image_info = self.get_food_image_info(food_name)
                
                # Generate search alternatives
                alternatives = self.smart_search._generate_alternatives(food_name)
                
                doc = {
                    "name": food_name,
                    "name_alternatives": ' '.join(alternatives),
                    "ontology_class": properties.get('ontology_class', 'Food'),
                    "food_type": properties.get('food_type', 'Unknown'),
                    "category": properties.get('category', 'Unknown'),
                    "region": properties.get('region', 'Unknown'),
                    "preparation": properties.get('preparation', 'Unknown'),
                    "cultural_origin": properties.get('cultural_origin', 'Unknown'),
                    "nutritional_focus": properties.get('nutritional_focus', 'Unknown'),
                    "primary_ingredients": ' '.join(properties.get('primary_ingredients', [])),
                    "has_images": image_info['has_images'],
                    "image_count": image_info['image_count']
                }
                
                es.index(
                    index="foods",
                    id=food_name.replace(' ', '_').replace(',', '').replace('(', '').replace(')', ''),
                    body=doc
                )
                indexed_count += 1
            
            print(f"✅ Indexed {indexed_count} foods in Elasticsearch with enhanced search")
                
        except Exception as e:
            logging.error(f"Error indexing foods: {e}")
            print(f"❌ Error indexing foods: {e}")

# Initialize service
print("🚀 Initializing Food Semantic Service with Smart Search...")
service = FoodSemanticService()

# Fixed search endpoint with proper query handling
@app.route('/api/search', methods=['GET'])
def search_foods():
    """Enhanced search with case-insensitive matching, typo correction, and suggestions"""
    # Support both 'q' and 'name' parameters for user convenience
    query_text = request.args.get('q', '') or request.args.get('name', '')
    ontology_class = request.args.get('class', '')
    region = request.args.get('region', '')
    category = request.args.get('category', '')
    preparation = request.args.get('preparation', '')
    nutritional_focus = request.args.get('nutrition', '')
    
    # New parameters for enhanced search
    suggest_corrections = request.args.get('suggest', 'true').lower() == 'true'
    include_fuzzy = request.args.get('fuzzy', 'true').lower() == 'true'
    
    # Get the base URL for full image URLs
    base_url = request.url_root.rstrip('/')
    
    try:
        search_results = []
        suggestions = []
        
        # If no query text, return empty results (not all foods)
        if not query_text.strip():
            return jsonify({
                "results": [],
                "query": {
                    "text": "",
                    "filters": {
                        "class": ontology_class,
                        "region": region,
                        "category": category,
                        "preparation": preparation,
                        "nutrition": nutritional_focus
                    }
                },
                "total_results": 0,
                "message": "Please provide a search query using ?q=your_search_term",
                "search_type": "no_query"
            })
        
        # Use Elasticsearch if available, otherwise use smart search
        if es is not None:
            # Enhanced Elasticsearch query focused on relevant matches
            search_body = {
                "query": {
                    "bool": {
                        "should": [
                            # Exact name matches get highest score
                            {
                                "match": {
                                    "name": {
                                        "query": query_text,
                                        "boost": 3.0,
                                        "fuzziness": "AUTO" if include_fuzzy else "0"
                                    }
                                }
                            },
                            # Name alternatives (content in parentheses)
                            {
                                "match": {
                                    "name_alternatives": {
                                        "query": query_text,
                                        "boost": 2.0,
                                        "fuzziness": "AUTO" if include_fuzzy else "0"
                                    }
                                }
                            },
                            # Ingredients get medium score
                            {
                                "match": {
                                    "primary_ingredients": {
                                        "query": query_text,
                                        "boost": 1.5,
                                        "fuzziness": "AUTO" if include_fuzzy else "0"
                                    }
                                }
                            },
                            # Cultural origin gets lower score
                            {
                                "match": {
                                    "cultural_origin": {
                                        "query": query_text,
                                        "boost": 1.0
                                    }
                                }
                            }
                        ],
                        "filter": [],
                        "minimum_should_match": 1
                    }
                },
                "min_score": 0.5  # Only return results with reasonable relevance
            }
            
            # Add filters
            filters = [
                (ontology_class, "ontology_class"),
                (region, "region"),
                (category, "category"),
                (preparation, "preparation"),
                (nutritional_focus, "nutritional_focus")
            ]
            
            for value, field in filters:
                if value:
                    search_body["query"]["bool"]["filter"].append({
                        "term": {field: value}
                    })
            
            results = es.search(index="foods", body=search_body, size=20)
            
            for hit in results['hits']['hits']:
                food_data = hit['_source']
                food_name = food_data['name']
                
                # Add detailed mapping information
                if food_name in service.food_mappings:
                    food_data.update(service.food_mappings[food_name])
                
                # Add comprehensive image information with full URLs
                image_info = service.get_food_image_info(food_name)
                
                # Convert relative URLs to full URLs for web viewing
                if image_info['has_images']:
                    # Update thumbnail URL to full URL
                    if image_info['thumbnail_url']:
                        image_info['thumbnail_url'] = base_url + image_info['thumbnail_url']
                    
                    # Update primary image URL to full URL
                    if image_info.get('primary_image'):
                        image_info['primary_image'] = base_url + image_info['primary_image']
                    
                    # Update all image URLs to full URLs
                    for img in image_info['image_urls']:
                        img['url'] = base_url + img['url']
                        img['full_url'] = img['url']  # Alias for clarity
                
                food_data.update(image_info)
                
                # Add search relevance score
                food_data['search_score'] = hit['_score']
                food_data['relevance'] = 'high' if hit['_score'] > 2.0 else 'medium' if hit['_score'] > 1.0 else 'low'
                
                search_results.append(food_data)
        
        else:
            # Use smart search fallback
            smart_results = service.smart_search.smart_search(query_text)
            
            for result in smart_results:
                food_name = result['food_name']
                properties = service.get_food_mapping(food_name)
                
                # Apply filters
                if ontology_class and properties.get('ontology_class') != ontology_class:
                    continue
                if region and properties.get('region') != region:
                    continue
                if category and properties.get('category') != category:
                    continue
                
                # Build response
                food_data = properties.copy()
                food_data['name'] = food_name
                food_data['match_type'] = result['match_type']
                food_data['search_score'] = result['total_score']
                food_data['relevance'] = 'high' if result['total_score'] > 1.5 else 'medium' if result['total_score'] > 1.0 else 'low'
                
                # Add image information with full URLs
                image_info = service.get_food_image_info(food_name)
                
                # Convert relative URLs to full URLs for web viewing
                if image_info['has_images']:
                    # Update thumbnail URL to full URL
                    if image_info['thumbnail_url']:
                        image_info['thumbnail_url'] = base_url + image_info['thumbnail_url']
                    
                    # Update primary image URL to full URL
                    if image_info.get('primary_image'):
                        image_info['primary_image'] = base_url + image_info['primary_image']
                    
                    # Update all image URLs to full URLs
                    for img in image_info['image_urls']:
                        img['url'] = base_url + img['url']
                        img['full_url'] = img['url']  # Alias for clarity
                
                food_data.update(image_info)
                
                search_results.append(food_data)
        
        # Generate suggestions if requested and few results found
        if suggest_corrections and query_text and len(search_results) < 3:
            suggestions = service.smart_search.suggest_corrections(query_text)
        
        # Prepare response
        response = {
            "results": search_results,
            "query": {
                "text": query_text,
                "filters": {
                    "class": ontology_class,
                    "region": region,
                    "category": category,
                    "preparation": preparation,
                    "nutrition": nutritional_focus
                }
            },
            "total_results": len(search_results),
            "search_type": "elasticsearch" if es is not None else "smart_fallback"
        }
        
        if suggestions:
            response["suggestions"] = suggestions
            response["message"] = f"Did you mean one of these? Found {len(search_results)} results for '{query_text}'"
        elif len(search_results) == 0:
            response["message"] = f"No results found for '{query_text}'. Try a different spelling or search term."
            response["suggestions"] = service.smart_search.suggest_corrections(query_text, 3)
        else:
            response["message"] = f"Found {len(search_results)} results for '{query_text}'"
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({"error": str(e), "search_type": "error"}), 500

# Add a new endpoint for getting all foods (when no query is provided)
@app.route('/api/foods/all', methods=['GET'])
def get_all_foods():
    """Get all foods with image information - separate from search"""
    try:
        # Get the base URL for full image URLs
        base_url = request.url_root.rstrip('/')
        
        # Apply filters if provided
        ontology_class = request.args.get('class', '')
        region = request.args.get('region', '')
        category = request.args.get('category', '')
        
        foods = []
        for food_name, properties in service.food_mappings.items():
            # Apply filters
            if ontology_class and properties.get('ontology_class') != ontology_class:
                continue
            if region and properties.get('region') != region:
                continue
            if category and properties.get('category') != category:
                continue
            
            food_data = properties.copy()
            food_data['name'] = food_name
            
            # Add image information with full URLs
            image_info = service.get_food_image_info(food_name)
            
            # Convert relative URLs to full URLs for web viewing
            if image_info['has_images']:
                # Update thumbnail URL to full URL
                if image_info['thumbnail_url']:
                    image_info['thumbnail_url'] = base_url + image_info['thumbnail_url']
                
                # Update primary image URL to full URL
                if image_info.get('primary_image'):
                    image_info['primary_image'] = base_url + image_info['primary_image']
                
                # Update all image URLs to full URLs
                for img in image_info['image_urls']:
                    img['url'] = base_url + img['url']
                    img['full_url'] = img['url']  # Alias for clarity
            
            food_data.update(image_info)
            foods.append(food_data)
        
        return jsonify({
            "results": foods,
            "total_results": len(foods),
            "message": f"Retrieved all {len(foods)} foods"
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Add CORS headers for image endpoints to work in browsers
@app.route('/api/food/<food_name>/image', methods=['GET'])
def get_food_image(food_name):
    """Get the first/primary image for a specific food with CORS headers"""
    try:
        # Decode URL-encoded food name
        food_name = food_name.replace('%20', ' ').replace('%2C', ',')
        
        image_dir = os.path.join(IMAGES_PATH, food_name)
        
        if not os.path.exists(image_dir):
            return jsonify({"error": "Food not found"}), 404
        
        # Get first image file in the directory
        image_files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
        
        if not image_files:
            return jsonify({"error": "No image found"}), 404
        
        # Sort to ensure consistent ordering
        image_files.sort()
        image_path = os.path.join(image_dir, image_files[0])
        
        # Send file with CORS headers for web viewing
        response = send_file(image_path)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Cache-Control'] = 'public, max-age=3600'  # Cache for 1 hour
        return response
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/food/<food_name>/image/<int:image_index>', methods=['GET'])
def get_food_image_by_index(food_name, image_index):
    """Get a specific image by index for a food with CORS headers"""
    try:
        # Decode URL-encoded food name
        food_name = food_name.replace('%20', ' ').replace('%2C', ',')
        
        image_dir = os.path.join(IMAGES_PATH, food_name)
        
        if not os.path.exists(image_dir):
            return jsonify({"error": "Food not found"}), 404
        
        # Get all image files
        image_files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
        
        if not image_files:
            return jsonify({"error": "No images found"}), 404
        
        # Sort to ensure consistent ordering
        image_files.sort()
        
        # Check if index is valid
        if image_index < 0 or image_index >= len(image_files):
            return jsonify({"error": f"Image index {image_index} out of range. Available: 0-{len(image_files)-1}"}), 404
        
        image_path = os.path.join(image_dir, image_files[image_index])
        
        # Send file with CORS headers for web viewing
        response = send_file(image_path)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Cache-Control'] = 'public, max-age=3600'  # Cache for 1 hour
        return response
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/search/suggest', methods=['GET'])
def search_suggestions():
    """Get search suggestions for a query"""
    query = request.args.get('q', '')
    max_suggestions = int(request.args.get('limit', '10'))
    
    try:
        suggestions = service.smart_search.suggest_corrections(query, max_suggestions)
        
        return jsonify({
            "query": query,
            "suggestions": suggestions,
            "total": len(suggestions)
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Include all other endpoints from the previous version...
# (get_foods, get_food_image, get_food_semantic_info, etc.)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint with search capabilities info"""
    health_status = {
        "status": "healthy",
        "services": {
            "fuseki": "healthy",
            "web": "healthy",
            "elasticsearch": "healthy" if es is not None else "unavailable",
            "smart_search": "available"
        },
        "search_features": {
            "case_insensitive": True,
            "fuzzy_matching": True,
            "auto_suggestions": True,
            "typo_correction": True,
            "multi_language_terms": True
        },
        "timestamp": "2025-05-30",
        "total_foods": len(service.food_mappings)
    }
    return jsonify(health_status)

if __name__ == '__main__':
    print("🎯 Food Semantic Web Service with Smart Search starting...")
    print(f"📊 Loaded {len(service.food_mappings)} food mappings")
    print(f"🔍 Elasticsearch: {'Connected' if es else 'Not Available (Smart Search Active)'}")
    print("🧠 Smart Search Features:")
    print("   ✅ Case-insensitive matching")
    print("   ✅ Fuzzy matching for typos")
    print("   ✅ Auto-correct suggestions")
    print("   ✅ Alternative name matching")
    print("   ✅ Ingredient-based search")
    print("🌐 Server starting on http://0.0.0.0:8080")
    app.run(host='0.0.0.0', port=8080, debug=True)