from flask import Flask
from blueprints.graph import graph_bp
from lib.constants import logger


def create_app():
    logger.info("Starting PersonaTrace Flask Application...")
    app = Flask(__name__)
    
    # Configuration
    logger.info("Loading configuration...")
    logger.info("Configuration loaded successfully")
    
    # Register blueprints
    logger.info("Registering blueprints...")
    app.register_blueprint(graph_bp)
    logger.info("Blueprints registered successfully")
    
    return app

if __name__ == '__main__':
    logger.info("Initializing application...")
    app = create_app()
    logger.info("Application created successfully, starting server...")
    app.run(debug=True, ssl_context=('test_certs/ssl_cert.pem', 'test_certs/ssl_key.pem'), host='0.0.0.0', port=5500)