"""Playback backend implementations used by the player coordinator."""
from abc import ABC, abstractmethod


class BackendPlayer(ABC):
    """Contract every playback service (MPD, Spotify, ...) implements.

    Only the calls every service needs are abstract. Library and queue extras
    (``list_albums``, ``play_folder``, ``queue_load``, ...) are optional; the
    coordinator raises ``NotImplementedError`` if a backend lacks one.
    """

    @abstractmethod
    def play_single(self, uri: str):
        pass

    @abstractmethod
    def get_song_by_url(self, uri: str):
        pass

    @abstractmethod
    def get_single_coverart(self, uri: str):
        pass

    @abstractmethod
    def play(self):
        pass

    @abstractmethod
    def pause(self, state: int = 1):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def next(self):
        pass

    @abstractmethod
    def prev(self):
        pass

    @abstractmethod
    def toggle(self):
        pass

    @abstractmethod
    def seek(self, new_time):
        pass

    @abstractmethod
    def shuffle(self, option='toggle'):
        pass

    @abstractmethod
    def repeat(self, option='toggle'):
        pass

    @abstractmethod
    def playerstatus(self):
        pass

    @abstractmethod
    def get_volume(self):
        pass

    @abstractmethod
    def set_volume(self, volume):
        pass

    @abstractmethod
    def exit(self):
        pass
