"""Where the dashboard pages get their database connection string."""

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from streamlit.errors import StreamlitSecretNotFoundError

# The same .env the loader reads, so a local run needs no secrets file.
load_dotenv(Path(__file__).with_name(".env"))


def database_url():
    """DATABASE_URL_NEON from Streamlit secrets, which is how Streamlit Cloud
    provides it, or else from the environment or .env, for local runs.

    st.secrets raises instead of returning the default when there's no
    secrets file at all, so the fallback needs the try.
    """
    try:
        url = st.secrets.get("DATABASE_URL_NEON")
    except StreamlitSecretNotFoundError:
        url = None
    url = url or os.getenv("DATABASE_URL_NEON")
    if not url:
        st.error(
            "No database connection string. Set DATABASE_URL_NEON in .env, in "
            ".streamlit/secrets.toml, or in your Streamlit Cloud app's secrets."
        )
        st.stop()
    return url
