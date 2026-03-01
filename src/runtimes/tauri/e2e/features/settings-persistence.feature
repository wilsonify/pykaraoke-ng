Feature: Settings Persistence
  As a karaoke user
  I want my settings to be saved when I change them
  So that my preferences are preserved across sessions

  Scenario: User saves settings successfully
    Given the application is running
    And the backend is connected
    When the user opens the settings modal
    And the user saves the settings
    Then the status bar should confirm settings were saved or show an error
    And the settings modal should not be visible

  Scenario: Settings modal shows current values
    Given the application is running
    And the backend is connected
    When the user opens the settings modal
    Then the fullscreen setting should be present
    And the zoom mode setting should be present

  Scenario: Cancelling settings does not save changes
    Given the application is running
    When the user opens the settings modal
    And the user closes the settings modal via cancel
    Then the settings modal should not be visible
