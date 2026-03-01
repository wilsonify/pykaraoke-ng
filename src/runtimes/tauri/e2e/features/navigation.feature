Feature: Navigation Flow
  As a karaoke user
  I want to navigate between different sections of the application
  So that I can access search, playback, and library management

  Scenario: Library section is collapsible
    Given the application is running
    When the user collapses the library section
    Then the folder input should not be visible
    When the user expands the library section
    Then the folder input should be visible

  Scenario: Settings modal opens and closes
    Given the application is running
    When the user opens the settings modal
    Then the settings modal should be visible
    And the fullscreen setting should be present
    And the zoom mode setting should be present
    When the user closes the settings modal via cancel
    Then the settings modal should not be visible

  Scenario: Keyboard shortcut focuses search bar
    Given the application is running
    And the search input does not have focus
    When the user presses the "/" key
    Then the search input should have focus

  Scenario: Escape key clears search input
    Given the application is running
    And the search input contains "test query"
    When the user presses the Escape key
    Then the search input should be empty
