import logging
import traceback
from start_app import main

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Detailed error logging
        logging.error(f"Error starting application: {str(e)}")
        print(f"Error: {str(e)}")
        traceback.print_exc()