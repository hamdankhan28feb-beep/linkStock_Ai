from app.routers.delivery_routes import _build_optimized_route_payload


def test_build_optimized_route_payload_includes_distance_and_time_estimate():
    stop_details = [
        {
            "id": "stop-1",
            "order_id": "order-1",
            "retailer_id": "retailer-1",
            "retailer_name": "Retailer One",
            "address": "Main Street",
            "latitude": 24.86,
            "longitude": 67.0,
            "order_total": 1500,
        },
        {
            "id": "stop-2",
            "order_id": "order-2",
            "retailer_id": "retailer-2",
            "retailer_name": "Retailer Two",
            "address": "Garden Road",
            "latitude": 24.87,
            "longitude": 67.01,
            "order_total": 2300,
        },
    ]

    payload = _build_optimized_route_payload(
        depot_address="Warehouse",
        depot_latitude=24.85,
        depot_longitude=67.0,
        stop_details=stop_details,
        ordered_stop_ids=["stop-2", "stop-1"],
        total_distance_km=3.2,
        average_speed_kmh=30,
    )

    assert payload["depot_address"] == "Warehouse"
    assert [stop["stop_number"] for stop in payload["ordered_stops"]] == [1, 2]
    assert payload["total_distance_km"] == 3.2
    assert payload["estimated_travel_time_minutes"] > 0
