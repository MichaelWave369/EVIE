def test_imports():
    import app
    from app.main import app as fastapi_app
    assert fastapi_app is not None
