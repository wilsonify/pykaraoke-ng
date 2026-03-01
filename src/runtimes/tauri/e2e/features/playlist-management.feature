Feature: Playlist Management
  As a karaoke DJ
  I want to manage the playback queue
  So that I can organize the order of songs for the session

  Scenario: Clearing an empty playlist does not crash
    Given the application is running
    When the user clicks the clear queue button
    Then the queue should display "Playlist is empty"
    And the app should remain stable

  Scenario: Queue shows empty state by default
    Given the application is running
    Then the queue should display "Playlist is empty"
