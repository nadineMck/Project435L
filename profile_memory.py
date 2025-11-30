from memory_profiler import profile
from app.main import app
from fastapi.testclient import TestClient

# Create a test client for the FastAPI app
client = TestClient(app)


@profile
def run_scenario():
    """
    Simple scenario to exercise the main endpoints while tracking memory.
    You don't need to assert anything here – it's only for profiling.
    """
    # Hit a few endpoints to simulate normal usage
    client.get("/health")            # if you have it
    client.get("/rooms")             # list rooms
    client.get("/bookings")          # (will work for admin token if open)
    client.get("/")                  # root endpoint if you have one


if __name__ == "__main__":
    run_scenario()
