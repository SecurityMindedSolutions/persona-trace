# PersonaTrace Data Loader

This tool loads identity observations into a Neo4j graph database for analysis. The data loader processes structured JSON files containing identity observations and creates nodes and relationships in the graph database, enabling the visualization and analysis of identity correlations in the PersonaTrace web application.

## Prerequisites

This tool is best used via [uv](https://github.com/astral-sh/uv) to handle dependency management and virtual environments. You can install uv by following the instructions at https://github.com/astral-sh/uv#installation.

For testing with Neo4j, you can use the provided Docker configuration in [neo4j-setup/README.md](../neo4j-setup/README.md):

### Schema Overview

The observation schema is defined in [observation_schema.json](data/observation_schema.json). Here's a summary of the data structure:

#### Required Fields

Each observation must contain:
- `node_type` (string): Always "observation_of_identity"
- `id` (string): Unique UUID identifier
- `source` (string): Data source identifier
- `observation_date` (string): Date in YYYY-MM-DD format

#### Optional Fields

##### Nodes - without nodes there's not really a point to an observation :-)
- `nodes.names` (array<string>): List of associated names
- `nodes.online_identifiers` (array<object>): Online identifiers with:
  - `type` (string): Identifier type (e.g., "email_address", "ip_address")
  - `value` (string): The identifier value
  - `category` (string): Usage category (e.g., "personal", "home")
- `nodes.location_identifiers` (array<object>): Location identifiers with:
  - `type` (string): Location type (e.g., "address", "geo_location")
  - `value` (string): The location value
  - `category` (string): Location category
- `nodes.identity_documents` (array<object>): Identity documents with:
  - `type` (string): Document type (e.g., "state_id", "passport")
  - `value` (string): Document identifier
  - `issuer` (string): Issuing authority

##### Metadata
The following metadata fields are optional. See example_observations.json for examples.
- `metadata.date_of_birth` (string): YYYY-MM-DD format
- `metadata.age` (integer): Age in years
- `metadata.gender` (string)
- `metadata.nationality` (string)
- `metadata.languages` (array<string>)
- `metadata.religion` (string)
- `metadata.ethnicity` (string)
- `metadata.height` (string)
- `metadata.weight` (string)
- `metadata.eye_color` (string)
- `metadata.hair_color` (string)
- `metadata.city` (string)
- `metadata.state` (string)
- `metadata.country` (string)
- `metadata.relationships` (array<object>):
  - `type` (string): Relationship type
  - `name` (string): Person's name
- `metadata.companies` (array<object>):
  - `name` (string): Company name
  - `start_date` (string): YYYY-MM-DD format
  - `end_date` (string): YYYY-MM-DD format
- `metadata.schools` (array<object>):
  - `name` (string): School name
  - `start_date` (string): YYYY-MM-DD format
  - `end_date` (string): YYYY-MM-DD format

## Usage

The data loader requires specifying:
1. Data source (`--example_data` or `--live_data`)
2. Database target (`--database_target neo4j`)

### Data Sources

- `--example_data`: Loads sample observations from the `data/example_data` folder
- `--live_data`: Loads real observations from the `data/live_data` folder

Optional parameters:
- `--clear_graph`: Deletes current data in the graph before loading the new data
- `--example_data_folder`: Override default example data folder path
- `--live_data_folder`: Override default live data folder path

### Database Configuration

#### Neo4j Configuration
Required parameters:
- `--neo4j_uri`: Neo4j database URI (e.g. `bolt://localhost:7687`)
- `--neo4j_user`: Neo4j username
- `--neo4j_password`: Neo4j password

**Security Note**: The username `neo4j` and password `personatrace` in lib/constants.py is used as an example for development purposes only. For production use, you should change this to a strong, unique password and use a secret management system to retrieve and use it.

### Example Commands

```bash
# Load example data into Neo4j
uv run load_data.py \
    --example_data \
    --neo4j_endpoint bolt://localhost:7687 \
    --neo4j_username neo4j \
    --neo4j_password personatrace

# Load live data into Neo4j
uv run load_data.py \
    --live_data \
    --live_data_folder /some/folder/of/observations \
    --neo4j_endpoint bolt://localhost:7687 \
    --neo4j_username neo4j \
    --neo4j_password personatrace
```

## Example Observation

```json
{
  "node_type": "observation_of_identity",
  "id": "00000000-0000-0000-0000-000000000003",
  "source": "social_media_platform",
  "observation_date": "2023-05-12",
  "nodes": {
    "names": [
      "Michael Wilson"
    ],
    "online_identifiers": [
      {
        "type": "email_address",
        "value": "mike.wilson@email.org",
        "category": "personal"
      },
      {
        "type": "ip_address",
        "value": "192.168.1.50",
        "category": "home"
      },
      {
        "type": "username",
        "value": "tech_wizard",
        "category": "personal"
      },
      {
        "type": "phone_number",
        "value": "+15125557890",
        "category": "mobile"
      }
    ],
    "location_identifiers": [
      {
        "type": "address",
        "value": "321 Maple Drive, Austin, TX 78701",
        "category": "home"
      },
      {
        "type": "geo_location",
        "value": "30.2672,-97.7431",
        "category": "home"
      }
    ],
    "identity_documents": [
      {
        "type": "state_id",
        "value": "TX87654321",
        "issuer": "Texas DPS"
      }
    ]
  },
  "metadata": {
    "date_of_birth": "1992-11-30",
    "age": 31,
    "city": "Austin",
    "state": "TX",
    "country": "USA",
    "companies": [
      {
        "name": "Austin Digital",
        "start_date": "2020-01-15",
        "end_date": "2023-05-12"
      }
    ],
    "schools": [
      {
        "name": "University of Texas",
        "start_date": "2010-09-01",
        "end_date": "2014-05-15"
      }
    ]
  }
}
```
