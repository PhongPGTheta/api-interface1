class ProcessURL:
    def __init__(self, url: str):
        self.url = url

    def ID_video(self) -> str:
        """
        Extracts the video ID from a YouTube URL.
        Handles both standard and shortened YouTube URLs.
        """
        if "youtu.be" in self.url:
            return self.url.split("/")[-1]
        elif "youtube.com/watch?v=" in self.url:
            return self.url.split("v=")[-1].split("&")[0]
        else:
            raise ValueError("Invalid YouTube URL format")