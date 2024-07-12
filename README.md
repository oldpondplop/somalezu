# Somalezu

<img src="somalezu.png" alt="Somalezu Logo" width="100"/>

A Discord bot to play music in a voice channel. 

## Installation

To set up and run Somalezu, follow these steps:

1. Create a Python virtual environment:

    ```bash
    python3 -m venv venv
    ```

2. Activate the virtual environment:

    - **Linux/MacOS:**

        ```bash
        source venv/bin/activate
        ```

    - **Windows:**

        ```bash
        .\venv\Scripts\activate
        ```

3. Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```
    Fix *uploader_id* error:
    ```
    pip install --upgrade --force-reinstall "git+https://github.com/ytdl-org/youtube-dl.git"
    ```
    Fix [js player issue](https://github.com/ytdl-org/youtube-dl/issues/30958)
    ```
    python -m pip install "https://github.com/ytdl-org/youtube-dl/archive/refs/heads/master.zip"
    ```

4. Run the bot:

    ```bash
    python somalezu.py
    ```