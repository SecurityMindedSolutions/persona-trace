# PersonaTrace Web Application

This is the web interface for PersonaTrace, providing interactive visualization and analysis of identity correlations.

## Prerequisites

This application uses [uv](https://github.com/astral-sh/uv) for dependency management. Install uv by following the instructions at https://github.com/astral-sh/uv#installation.

**Security Note**: The username `neo4j` and password `personatrace` in lib/constants.py is used as an example for development purposes only. For production use, you should change this to a strong, unique password and use a secret management system to retrieve and use it.

## Running the Application

The application connects to Neo4j as the backend graph database.

### Fake Data Mode

For development and testing purposes, if you haven't loaded our example data, you can use fake data by appending `?fake_data=true` to the application URL. This will use the `make_fake_graph_data` function from `graph.py` to generate a set of sample data for visualization and testing.

### Example Command

```bash
# Run the app to connect to Neo4j
uv run app.py \
    --database_target neo4j \
    --neo4j_endpoint bolt://localhost:7687 \
    --neo4j_username neo4j \
    --neo4j_password personatrace
```

###