#! /usr/bin/env python3

# Args
import argparse
parser = argparse.ArgumentParser(description='PersonaTrace App')
parser.add_argument('--neo4j_endpoint', type=str, help='Neo4j endpoint', default='bolt://localhost:7687')
parser.add_argument('--neo4j_username', type=str, help='Neo4j username', default='neo4j')
parser.add_argument('--neo4j_password', type=str, help='Neo4j password', default='personatrace')
args = parser.parse_args()

# Neo4j connection constants
NEO4J_ENDPOINT = args.neo4j_endpoint
NEO4J_USERNAME = args.neo4j_username
NEO4J_PASSWORD = args.neo4j_password


# Generic logger with colorlog but rich exception printing
import colorlog
import rich
logger = colorlog.getLogger()
# Set up colorlog handler
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(levelname)s:%(reset)s %(message)s',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }
))
logger.addHandler(handler)
logger.setLevel('INFO')
from rich.console import Console
console = Console()

# Max depth for finding paths if it's not given in the request
FIND_PATHS_MAX_DEPTH = 10

# Static color definitions for each node type
NODE_COLORS = {
    #########################################################
    #########################################################
    # Source - Orange
    'source': {
        'background': '#FF8000',  # Brighter Orange
        'border': '#FF4500'       # Deeper Orange-Red
    },
    
    #########################################################
    #########################################################
    # Observation - Bright Yellow
    'observation_of_identity': {
        'background': '#FFD700',  # Gold
        'border': '#DAA520'       # Goldenrod
    },


    #########################################################
    #########################################################
    # Color options for each node type
    # Default fallback
    'default': {
        'background': '#D3D3D3',  # Light Gray
        'border': '#808080'       # Gray
    },

    'node_color_options': [
        {
            'background': '#D8E6F2',  # Dull light blue
            'border': '#B8C6D2'       # Darker dull blue
        },
        {
            'background': '#E6D8F2',  # Dull light purple
            'border': '#C6B8D2'       # Darker dull purple
        },
        {
            'background': '#D8F2D8',  # Dull light green
            'border': '#B8D2B8'       # Darker dull green
        },
        {
            'background': '#F2F2D8',  # Dull light yellow
            'border': '#D2D2B8'       # Darker dull yellow
        },
        {
            'background': '#D8F2F2',  # Dull light cyan
            'border': '#B8D2D2'       # Darker dull cyan
        },
        {
            'background': '#F2E6D8',  # Dull light orange
            'border': '#D2C6B8'       # Darker dull orange
        },
        {
            'background': '#E6D8E6',  # Dull light magenta
            'border': '#C6B8C6'       # Darker dull magenta
        },
        {
            'background': '#D8E6E6',  # Dull light teal
            'border': '#B8C6C6'       # Darker dull teal
        },
        {
            'background': '#E6EDD8',  # Dull light olive
            'border': '#C6D4B8'       # Darker dull olive
        },
        {
            'background': '#DDE6D8',  # Dull pale sage
            'border': '#BDCEB8'       # Darker sage
        },
        {
            'background': '#F2EFE6',  # Dull cream
            'border': '#D2CEC6'       # Slightly darker cream
        },
        {
            'background': '#D8DEE6',  # Dull light steel blue
            'border': '#B8C0CE'       # Darker steel blue
        },
        {
            'background': '#ECEBD8',  # Dull linen
            'border': '#CCCBB8'       # Slightly darker linen
        },
        {
            'background': '#D8E6DC',  # Dull mint gray
            'border': '#B8C6BC'       # Muted green-gray
        },
        {
            'background': '#E0E6F2',  # Dull powder blue
            'border': '#C0C6D2'       # Muted periwinkle
        },
        {
            'background': '#E8E8D8',  # Dull parchment
            'border': '#C8C8B8'       # Dusty beige
        },
        {
            'background': '#E0D8F2',  # Dull lavender
            'border': '#C0B8D2'       # Muted lavender border
        },
        {
            'background': '#D8F2EC',  # Dull pale aqua
            'border': '#B8D2CC'       # Muted aqua border
        }
    ]


}

# Static color definitions for relationship types
RELATIONSHIP_COLORS_OPTIONS = [
    {'color': '#708090', 'width': 2, 'dashes': True},   # Slate Gray
    {'color': '#556B2F', 'width': 2, 'dashes': True},   # Dark Olive Green
    {'color': '#8B4513', 'width': 2, 'dashes': True},   # Saddle Brown
    {'color': '#2F4F4F', 'width': 2, 'dashes': True},   # Dark Slate Gray
    {'color': '#6B8E23', 'width': 2, 'dashes': True},   # Olive Drab
    {'color': '#808000', 'width': 2, 'dashes': True},   # Olive
    {'color': '#696969', 'width': 2, 'dashes': True},   # Dim Gray
    {'color': '#5F9EA0', 'width': 2, 'dashes': True},   # Cadet Blue
    {'color': '#778899', 'width': 2, 'dashes': True},   # Light Slate Gray
    {'color': '#9ACD32', 'width': 2, 'dashes': True},   # Yellow Green
    {'color': '#C0C0C0', 'width': 1, 'dashes': False},  # Silver (light neutral)
    {'color': '#A9A9A9', 'width': 1, 'dashes': False},  # Dark Gray
    {'color': '#D3D3D3', 'width': 1, 'dashes': False},  # Light Gray
    {'color': '#B0C4DE', 'width': 2, 'dashes': True},   # Light Steel Blue
]
