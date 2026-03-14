import os
import sys

# Ensure the project root is in the Python path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from vault import create_app
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)