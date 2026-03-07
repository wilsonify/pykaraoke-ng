Feature: Main Window UI Elements
  As a karaoke user
  I want to see all essential UI elements when the app opens
  So that I know the interface is fully loaded and interactive

  Scenario: Primary UI elements are visible on launch
    Given the application is running
    Then the search input should be visible
    And the search button should be visible
    And the play button should be visible
    And the stop button should be visible
    And the next track button should be visible
    And the previous track button should be visible
    And the volume slider should be visible
    And the settings button should be visible

  Scenario: Player section displays default state
    Given the application is running
    Then the now-playing title should show "No song loaded"
    And the time display should show "0:00"

  Scenario: Queue section is visible and empty by default
    Given the application is running
    Then the queue section should be visible
    And the queue should display "Playlist is empty"
    And the clear queue button should be visible
