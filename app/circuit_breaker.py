from pybreaker import CircuitBreaker

# Create a circuit breaker instance for the booking service
booking_circuit_breaker = CircuitBreaker(
    fail_max=3,
    reset_timeout=60,
    name="booking_service_breaker",
)
