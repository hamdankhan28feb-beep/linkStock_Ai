from app.services.clustering_service import build_cluster_summaries


def test_build_cluster_summaries_returns_expected_shape():
    geo_orders = [
        {
            "id": "o-1",
            "lat": 24.8600,
            "lon": 67.0100,
            "retailer_name": "Retailer A",
            "order": {"id": "o-1", "total_amount": 1200},
        },
        {
            "id": "o-2",
            "lat": 24.8620,
            "lon": 67.0120,
            "retailer_name": "Retailer B",
            "order": {"id": "o-2", "total_amount": 800},
        },
        {
            "id": "o-3",
            "lat": 24.9000,
            "lon": 67.0700,
            "retailer_name": "Retailer C",
            "order": {"id": "o-3", "total_amount": 600},
        },
    ]

    label_map = {"o-1": 0, "o-2": 0, "o-3": 1}

    summaries = build_cluster_summaries(geo_orders, label_map)

    assert len(summaries) == 2
    first = summaries[0]
    assert first["cluster_id"] == "cluster-0"
    assert first["retailers"] == ["Retailer A", "Retailer B"]
    assert len(first["orders"]) == 2
    assert first["total_order_volume"] == 2000
    assert first["approximate_area"]["radius_km"] >= 0
