"""
Simple asciimatics demo for MC2 evaluation
"""
from asciimatics.screen import Screen
from asciimatics.scene import Scene
from asciimatics.effects import Print
from asciimatics.renderers import FigletText, Box, StaticRenderer
from asciimatics.exceptions import ResizeScreenError, NextScene, StopApplication
import sys


class MCPanes(StaticRenderer):
    """
    Custom renderer to draw MC-style interface with two panes
    """
    def __init__(self, width, height):
        super(MCPanes, self).__init__()
        self._width = width
        self._height = height

    def _render_now(self):
        # Create a canvas
        canvas = []
        
        # Top menubar
        menubar = " File  Edit  View  Help " + " " * max(0, self._width - 25) + "F1=Help F9=Menu F10=Quit"
        canvas.append(menubar[:self._width])
        
        # Calculate pane heights (subtract menubar and status bar)
        content_height = self._height - 2  # -1 for menubar, -1 for status
        
        # Draw the two panes separated by a vertical line
        for i in range(content_height):
            # Left pane content
            left_content = "Sessions"
            if i == 1:
                left_content = "Sessions"
            elif i == 2:
                left_content = " - Session 1"
            elif i == 3:
                left_content = " - Session 2"
            elif i == 4:
                left_content = " - Session 3"
            else:
                left_content = " " * min(30, self._width // 2)
                
            # Separator
            separator = "|"
            
            # Right pane content
            right_content = "Session Details"
            if i == 1:
                right_content = "Session Details"
            elif i == 2:
                right_content = "ID: abc123..."
            elif i == 3:
                right_content = "Status: Active"
            elif i == 4:
                right_content = "Created: Today"
            else:
                right_content = " " * max(0, self._width - (self._width // 2 + 1))
                
            row = (left_content + " " * max(0, (self._width // 2) - len(left_content) - 1) +
                   separator +
                   right_content + " " * max(0, self._width - (self._width // 2) - len(right_content) - 1))
            canvas.append(row[:self._width])
        
        # Status line at bottom
        status = "Ready | FOCUS: LEFT | Session: None"
        canvas.append(status[:self._width] + " " * max(0, self._width - len(status)))
        
        return canvas


def demo(screen):
    # Create the panes renderer
    panes = MCPanes(screen.width, screen.height)
    
    # Create a simple effect to display the panes
    effect = Print(screen, panes, y=0)
    
    # Create the scene with the effect
    scene = Scene([effect], duration=100)  # Show for 100 frames then exit
    
    # Schedule exit after 1 second
    import time
    start_time = time.time()
    
    # Add the scene to screen's play list
    screen.play([scene], stop_on_resize=True, unhandled_input=lambda c: (
        None if time.time() - start_time < 1.0 else screen.set_play_state(False)
    ))


def main():
    while True:
        try:
            Screen.wrapper(demo)
            break
        except ResizeScreenError:
            # If terminal is resized, try again
            continue
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()