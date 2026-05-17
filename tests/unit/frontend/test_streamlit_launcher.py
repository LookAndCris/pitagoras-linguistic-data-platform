import apps.frontend.main


def test_streamlit_root_launcher_delegates_to_frontend_shell(monkeypatch):
    import streamlit_app

    calls = {"render_shell": 0}
    monkeypatch.setattr(
        apps.frontend.main,
        "render_shell",
        lambda: calls.__setitem__("render_shell", calls["render_shell"] + 1),
    )

    streamlit_app.main()

    assert calls == {"render_shell": 1}
