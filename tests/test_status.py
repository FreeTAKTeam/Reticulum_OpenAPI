from reticulum_openapi.status import StatusCode


def test_status_codes_values():
    assert StatusCode.SUCCESS == 200
    assert StatusCode.NOT_FOUND == 404
    assert StatusCode.INTERNAL_SERVER_ERROR == 500
