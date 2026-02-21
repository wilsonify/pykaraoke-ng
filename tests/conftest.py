"""
Shared test fixtures and configuration for PyKaraoke-NG tests.

Provides pygame mocking infrastructure so tests can run without
a display or audio device.
"""

import sys
from unittest.mock import MagicMock


def create_pygame_mock():
    """Create a comprehensive pygame mock for testing."""
    mock_pygame = MagicMock()

    # Mock pygame.time
    mock_pygame.time.get_ticks.return_value = 0
    mock_pygame.time.wait.return_value = None

    # Mock pygame.mixer
    mock_pygame.mixer.music.get_volume.return_value = 0.75
    mock_pygame.mixer.music.set_volume.return_value = None
    mock_pygame.mixer.init.return_value = None
    mock_pygame.mixer.quit.return_value = None
    mock_pygame.mixer.get_init.return_value = (44100, -16, 2)

    # Mock pygame.display
    mock_surface = MagicMock()
    mock_surface.get_size.return_value = (640, 480)
    mock_surface.get_flags.return_value = 0
    mock_surface.get_bitsize.return_value = 32
    mock_pygame.display.set_mode.return_value = mock_surface
    mock_pygame.display.init.return_value = None
    mock_pygame.display.quit.return_value = None
    mock_pygame.display.flip.return_value = None
    mock_pygame.display.set_caption.return_value = None

    # Mock pygame.mouse
    mock_pygame.mouse.set_visible.return_value = None

    # Mock pygame.joystick
    mock_pygame.joystick.get_count.return_value = 0

    # Mock pygame.event
    mock_pygame.event.get.return_value = []

    # Mock pygame.Surface
    mock_pygame.Surface.return_value = mock_surface

    # Mock pygame constants
    mock_pygame.FULLSCREEN = 0x80000000
    mock_pygame.RESIZABLE = 0x00000010
    mock_pygame.DOUBLEBUF = 0x40000000
    mock_pygame.HWSURFACE = 0x00000001
    mock_pygame.NOFRAME = 0x00000020
    mock_pygame.VIDEORESIZE = 16
    mock_pygame.KEYDOWN = 2
    mock_pygame.QUIT = 12
    mock_pygame.JOYBUTTONDOWN = 10

    # Mock pygame.error
    mock_pygame.error = type("error", (Exception,), {})

    # Mock pygame.init
    mock_pygame.init.return_value = (6, 0)
    mock_pygame.quit.return_value = None

    return mock_pygame


def install_pygame_mock():
    """Install pygame mock into sys.modules if pygame is not available."""
    if "pygame" not in sys.modules:
        sys.modules["pygame"] = create_pygame_mock()
    return sys.modules["pygame"]
