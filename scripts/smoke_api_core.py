from api.core_routes import router


def main():
    routes = {getattr(route, "path", None) for route in router.routes}
    expected = {
        "/api/v1/runtime",
        "/api/v1/workshops",
        "/api/v1/workshops/{workshop_id}",
        "/api/v1/workshops/{workshop_id}/readiness",
    }
    missing = expected - routes
    assert not missing, f"missing routes: {missing}"
    print(f"api core router smoke ok: {len(expected)} routes")


if __name__ == "__main__":
    main()
