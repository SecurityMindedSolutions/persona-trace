#! /usr/bin/env python3

# Setup argparse
import argparse
parser = argparse.ArgumentParser(description='Load data into graph database')
########################################################
# Data source
########################################################
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('--example_data', action='store_true', help='Load example data')
group.add_argument('--live_data', action='store_true', help='Load live data')
parser.add_argument('--neo4j_endpoint', type=str, help='Neo4j endpoint', default='bolt://localhost:7687')
parser.add_argument('--neo4j_username', type=str, help='Neo4j username', default='neo4j')
parser.add_argument('--neo4j_password', type=str, help='Neo4j password', default='personatrace')
parser.add_argument('--batch_size', type=int, help='Batch size of observations to process at a time', default=100)
parser.add_argument('--example_data_folder', type=str, help='Full folder path for example data if not in data/example_data')
parser.add_argument('--live_data_folder', type=str, help='Full folder path for live data if not in data/live_data')
args = parser.parse_args()
########################################################
# Neo4j configuration
########################################################
NEO4J_ENDPOINT = args.neo4j_endpoint
NEO4J_USERNAME = args.neo4j_username
NEO4J_PASSWORD = args.neo4j_password
########################################################
# Batch size
########################################################
BATCH_SIZE = args.batch_size
########################################################
# Folder paths
########################################################
from pathlib import Path
DATA_FOLDER = Path(__file__).parent.parent / "data"
EXAMPLE_DATA_FOLDER = args.example_data_folder if args.example_data_folder else f"{DATA_FOLDER}/example_data"
LIVE_DATA_FOLDER = args.live_data_folder if args.live_data_folder else f"{DATA_FOLDER}/live_data"
########################################################
# Logging configuration
########################################################
import colorlog
import logging
from rich.console import Console
from rich.traceback import install
logger = colorlog.getLogger('personatrace')
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(asctime)s %(levelname)s:%(name)s:%(message)s',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }
))
logger.addHandler(handler)
logger.setLevel(logging.INFO)
# Install rich traceback handling
install(show_locals=True)
console = Console()


########################################################
# Vertex types
########################################################
VERTEX_SCHEMAS = {
    'source': {
        'vertex_type': 'source',
        'value_field': 'value',
        'edge_type': 'observed_in',
        'properties': ['value']
    },
    'names': {
        'vertex_type': 'name',
        'value_field': 'value',
        'edge_type': 'has_name',
        'properties': ['value']
    },
    'online_identifiers': {
        'vertex_type': 'dynamic',  # Will use the 'type' field from each object
        'value_field': 'value', 
        'edge_type': 'dynamic',  # Will use 'has_' + type field
        'properties': ['value', 'category', 'type']
    },
    'location_identifiers': {
        'vertex_type': 'dynamic',  # Will use the 'type' field from each object
        'value_field': 'value',
        'edge_type': 'dynamic',  # Will use 'has_' + type field
        'properties': ['value', 'category', 'type']
    },
    'identity_documents': {
        'vertex_type': 'identity_document',
        'value_field': 'value', 
        'edge_type': 'has_identity_document',
        'properties': ['value', 'type', 'issuer']
    }
}