#! /usr/bin/env python3

# Setup argparse
import argparse
parser = argparse.ArgumentParser(description='Load data into graph database')
########################################################
# Data source
########################################################
# Data source
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('--example_data', action='store_true', help='Load example data')
group.add_argument('--live_data', action='store_true', help='Load live data')
# Other arguments
parser.add_argument('--debug', action='store_true', help='Debug mode')
parser.add_argument('--clear_graph', action='store_true', help='Delete graph data before loading')
parser.add_argument('--neo4j_endpoint', type=str, help='Neo4j endpoint', default='bolt://localhost:7687')
parser.add_argument('--neo4j_username', type=str, help='Neo4j username', default='neo4j')
parser.add_argument('--neo4j_password', type=str, help='Neo4j password', default='personatrace')
parser.add_argument('--batch_size', type=int, help='Batch size of observations to process at a time', default=5000)
parser.add_argument('--deletion_batch_size', type=int, help='Batch size for deletion operations', default=50000)
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
DELETION_BATCH_SIZE = args.deletion_batch_size
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
logger.setLevel(logging.DEBUG if args.debug else logging.INFO)
# Install rich traceback handling
install(show_locals=True)
console = Console()


########################################################
# Node types
########################################################
NODE_SCHEMAS = {
    'observation_of_identity': {
        'node_type': 'observation_of_identity',
        'value_field': 'id',
        'relationship_type': 'has_observation',
        'properties': ['id', 'source', 'observation_date']
    },
    'source': {
        'node_type': 'source',
        'value_field': 'value',
        'relationship_type': 'observed_in',
        'properties': ['value']
    },
    'names': {
        'node_type': 'dynamic',  # Will use the 'type' field from each object
        'value_field': 'value', 
        'relationship_type': 'dynamic',  # Will use 'has_' + type field
        'properties': ['value', 'type']
    },
    'online_identifiers': {
        'node_type': 'dynamic',  # Will use the 'type' field from each object
        'value_field': 'value', 
        'relationship_type': 'dynamic',  # Will use 'has_' + type field
        'properties': ['value', 'category', 'type']
    },
    'location_identifiers': {
        'node_type': 'dynamic',  # Will use the 'type' field from each object
        'value_field': 'value',
        'relationship_type': 'dynamic',  # Will use 'has_' + type field
        'properties': ['value', 'category', 'type']
    },
    'identity_documents': {
        'node_type': 'identity_document',
        'value_field': 'value', 
        'relationship_type': 'has_identity_document',
        'properties': ['value', 'type', 'issuer']
    }
}